# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2026 Links4Engg Private Limited.
# All Rights Reserved.
#
# This software is proprietary and confidential.
#
# Unauthorized copying, modification, redistribution,
# reverse engineering, decompilation, sublicensing,
# or commercial use of this software is strictly prohibited
# without prior written permission from
# Links4Engg Private Limited.
#
# Licensed under the Odoo Proprietary License v1.0 (OPL-1).
#
# Links4Engg Private Limited
# Website : https://links4engg.com
# Email   : info@links4engg.com
# Phone   : +91 471 3592209 | +91 7306889096
#
##############################################################################
import logging
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ── Discount Approval State ───────────────────────────────────────────────
    l4e_discount_approval_state = fields.Selection(
        [
            ('not_required', 'Not Required'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
        ],
        string='Discount Approval',
        default='not_required',
        copy=False, tracking=True, index=True,
    )
    l4e_discount_approval_request_id = fields.Many2one(
        'l4e.discount.approval.request',
        string='Discount Approval Request',
        copy=False, readonly=True,
    )

    # ── Computed flags ────────────────────────────────────────────────────────
    l4e_discount_exceeds_limit = fields.Boolean(
        string='Discount Exceeds Limit',
        compute='_compute_l4e_discount_flags', store=False,
    )
    l4e_max_discount = fields.Float(
        string='Max Discount (%)',
        compute='_compute_l4e_discount_flags', store=False,
        digits=(5, 2),
    )
    l4e_matched_tier_id = fields.Many2one(
        'l4e.discount.tier', string='Matched Tier',
        compute='_compute_l4e_discount_flags', store=False,
    )
    l4e_discount_approval_count = fields.Integer(
        compute='_compute_l4e_discount_approval_count',
    )

    @api.depends(
        'order_line.discount', 'user_id', 'company_id',
        'discount_type', 'discount_rate', 'amount_discount', 'amount_untaxed',
    )
    def _compute_l4e_discount_flags(self):
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('l4e_discount_approval.required', 'False') == 'True'
        for order in self:
            # Ignore discount validation entirely on partial orders if the parent order was approved/confirmed
            if '-R' in (order.name or ''):
                base_name = order.name.split('-R')[0]
                orig_order = self.env['sale.order'].sudo().search([('name', '=', base_name)], limit=1)
                if orig_order and (orig_order.l4e_discount_approval_state == 'approved' or orig_order.state in ('sale', 'done')):
                    order.l4e_discount_exceeds_limit = False
                    order.l4e_max_discount = max((l.discount or 0.0) for l in order.order_line) if order.order_line else 0.0
                    order.l4e_matched_tier_id = False
                    continue

            if not enabled or not order.order_line:
                order.l4e_discount_exceeds_limit = False
                order.l4e_max_discount = 0.0
                order.l4e_matched_tier_id = False
                continue

            discount_type = order.discount_type  # from sale_discount_total
            exceeds = False

            if discount_type == 'line':
                # Per-line: max line discount % vs per-line limit
                limit = order._get_line_discount_limit()
                max_disc = max((l.discount or 0.0) for l in order.order_line)
                for l in order.order_line:
                    disc = l.discount or 0.0
                    line_limit = limit
                    if '-R' in (order.name or ''):
                        base_name = order.name.split('-R')[0]
                        orig_order = self.env['sale.order'].sudo().search([('name', '=', base_name)], limit=1)
                        if orig_order:
                            orig_lines = orig_order.order_line.filtered(lambda ol: ol.product_id == l.product_id)
                            if orig_lines:
                                line_limit = max(limit, max(orig_lines.mapped('discount') or [0.0]))
                    elif hasattr(l, 'original_line_id') and l.original_line_id:
                        line_limit = max(limit, l.original_line_id.discount or 0.0)
                    if disc > line_limit + 0.001:
                        exceeds = True
            elif discount_type == 'percent':
                # Header %: discount_rate directly vs global limit
                limit = order._get_global_discount_limit()
                max_disc = order.discount_rate or 0.0
                exceeds = max_disc > limit
            else:  # amount
                # Header amount: convert to effective % vs global limit
                limit = order._get_global_discount_limit()
                total_before = (order.amount_untaxed or 0.0) + (order.amount_discount or 0.0)
                max_disc = (order.amount_discount / total_before * 100) if total_before else 0.0
                exceeds = max_disc > limit

            order.l4e_max_discount = max_disc
            order.l4e_discount_exceeds_limit = exceeds
            if exceeds:
                order.l4e_matched_tier_id = order._find_matching_tier(max_disc)
            else:
                order.l4e_matched_tier_id = False

    def _compute_l4e_discount_approval_count(self):
        for order in self:
            order.l4e_discount_approval_count = self.env[
                'l4e.discount.approval.request'
            ].search_count([('sale_order_id', '=', order.id)])

    # ── Discount limit helpers ─────────────────────────────────────────────────

    def _get_line_discount_limit(self):
        """Return the per-line discount limit for this order's salesperson."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        default = float(ICP.get_param('l4e_discount_approval.default_line_limit', '0.0'))
        if not self.user_id:
            return default
        limit_rec = self.env['l4e.discount.limit'].sudo().search([
            ('user_id', '=', self.user_id.id),
            ('company_id', '=', (self.company_id.id or self.env.company.id)),
        ], limit=1)
        return limit_rec.line_discount_limit if limit_rec else default

    def _get_global_discount_limit(self):
        """Return the global discount limit for this order's salesperson."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        default = float(ICP.get_param('l4e_discount_approval.default_global_limit', '0.0'))
        if not self.user_id:
            return default
        limit_rec = self.env['l4e.discount.limit'].sudo().search([
            ('user_id', '=', self.user_id.id),
            ('company_id', '=', (self.company_id.id or self.env.company.id)),
        ], limit=1)
        return limit_rec.global_discount_limit if limit_rec else default

    def _find_matching_tier(self, discount_pct):
        """Return the first matching l4e.discount.tier for the given discount %."""
        self.ensure_one()
        tiers = self.env['l4e.discount.tier'].sudo().search([
            ('active', '=', True),
            '|', ('company_id', '=', self.company_id.id),
                 ('company_id', '=', False),
        ], order='discount_min asc')
        for tier in tiers:
            if tier._match_discount(discount_pct):
                return tier
        return False

    def _get_discount_info_text(self):
        """Build a summary of the excessive discount."""
        self.ensure_one()
        discount_type = self.discount_type
        if discount_type == 'line':
            limit = self._get_line_discount_limit()
            lines = self.order_line.filtered(lambda l: (l.discount or 0.0) > limit)
            if not lines:
                return ''
            parts = []
            for line in lines:
                parts.append(
                    f"• {line.product_id.name or 'Product'}: {line.discount:.2f}% "
                    f"(limit: {limit:.2f}%)"
                )
            return '\n'.join(parts)
        else:
            limit = self._get_global_discount_limit()
            return (
                f"Effective discount: {self.l4e_max_discount:.2f}% "
                f"(limit: {limit:.2f}%)"
            )

    # ── Confirmation override ─────────────────────────────────────────────────

    def action_confirm(self):
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('l4e_discount_approval.required', 'False') == 'True'

        for order in self:
            if not enabled:
                continue
            if order.l4e_discount_approval_state == 'approved':
                continue
            if not order.l4e_discount_exceeds_limit:
                continue
            if order.l4e_discount_approval_state == 'pending':
                raise UserError(_(
                    'A discount approval request is pending for "%s". '
                    'Please wait for it to be approved before confirming.'
                ) % order.name)
            if order.l4e_discount_approval_state == 'refused':
                raise UserError(_(
                    'The discount approval for "%s" was refused. '
                    'Please adjust the discounts or request a new approval.'
                ) % order.name)

            # Discount exceeds limit but no request yet → create one
            order.action_request_discount_approval()
            raise UserError(_(
                'Discount on "%s" exceeds the allowed limit.\n'
                'An approval request has been created and sent to the approvers.\n'
                'You will be notified once a decision is made.'
            ) % order.name)

        return super().action_confirm()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_request_discount_approval(self):
        """Create a discount approval request for this order."""
        self.ensure_one()
        # Cancel any existing pending request
        existing = self.env['l4e.discount.approval.request'].search([
            ('sale_order_id', '=', self.id),
            ('state', '=', 'pending'),
        ])
        existing.write({'state': 'cancelled'})

        # 1. Check for salesperson-specific approvers first
        limit_rec = None
        if self.user_id:
            limit_rec = self.env['l4e.discount.limit'].sudo().search([
                ('user_id', '=', self.user_id.id),
                ('company_id', '=', (self.company_id.id or self.env.company.id)),
            ], limit=1)

        if limit_rec and limit_rec.approver_ids:
            # Use salesperson-specific approvers — no tier needed
            approvers = limit_rec.approver_ids
            tier = self.env['l4e.discount.tier']
            approval_mode = limit_rec.approval_mode
        else:
            # Fall back to tier-based approvers
            tier = self.l4e_matched_tier_id
            if not tier:
                raise UserError(_(
                    'No approval tier is configured for a discount of %.2f%%.\n'
                    'Please ask your manager to configure a Discount Tier for this range.'
                ) % self.l4e_max_discount)
            if not tier.approver_ids:
                raise UserError(_(
                    'The matched tier "%s" has no approvers configured.'
                ) % tier.name)
            approvers = tier.approver_ids
            approval_mode = tier.approval_mode

        request = self.env['l4e.discount.approval.request'].sudo().create({
            'sale_order_id': self.id,
            'tier_id': tier.id if tier else False,
            'requester_id': self.env.uid,
            'max_discount': self.l4e_max_discount,
            'discount_info': self._get_discount_info_text(),
            'approver_ids': [(6, 0, approvers.ids)],
            'approval_mode': approval_mode,
        })
        self.write({
            'l4e_discount_approval_state': 'pending',
            'l4e_discount_approval_request_id': request.id,
        })
        request._notify_approvers()
        self.message_post(
            body=Markup(
                '<p>⏳ Discount approval requested. '
                'Max discount: <b>%(disc)s%%</b> | '
                'Approvers: <b>%(approvers)s</b></p>'
            ) % {
                'disc': self.l4e_max_discount,
                'approvers': ', '.join(approvers.mapped('name')),
            },
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        return request

    def action_view_discount_approval(self):
        self.ensure_one()
        requests = self.env['l4e.discount.approval.request'].search([
            ('sale_order_id', '=', self.id),
        ])
        if len(requests) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'l4e.discount.approval.request',
                'res_id': requests.id,
                'view_mode': 'form',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l4e.discount.approval.request',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    l4e_discount_over_limit = fields.Boolean(
        string='Over Limit',
        compute='_compute_l4e_discount_over_limit',
        store=False,
        help='True when this line\'s discount exceeds the salesperson\'s configured limit.',
    )

    @api.depends('discount', 'order_id.user_id', 'order_id.company_id', 'order_id.discount_type')
    def _compute_l4e_discount_over_limit(self):
        for line in self:
            if line.order_id.discount_type != 'line':
                # For percent/amount types, order-level flag handles it — no per-line flagging
                line.l4e_discount_over_limit = False
                continue
            # Ignore discount validation entirely on partial orders if the parent order was approved/confirmed
            if '-R' in (line.order_id.name or ''):
                base_name = line.order_id.name.split('-R')[0]
                orig_order = self.env['sale.order'].sudo().search([('name', '=', base_name)], limit=1)
                if orig_order and (orig_order.l4e_discount_approval_state == 'approved' or orig_order.state in ('sale', 'done')):
                    line.l4e_discount_over_limit = False
                    continue
            limit = line.order_id._get_line_discount_limit()
            line_limit = limit
            if '-R' in (line.order_id.name or ''):
                base_name = line.order_id.name.split('-R')[0]
                orig_order = self.env['sale.order'].sudo().search([('name', '=', base_name)], limit=1)
                if orig_order:
                    orig_lines = orig_order.order_line.filtered(lambda ol: ol.product_id == line.product_id)
                    if orig_lines:
                        line_limit = max(limit, max(orig_lines.mapped('discount') or [0.0]))
            elif hasattr(line, 'original_line_id') and line.original_line_id:
                line_limit = max(limit, line.original_line_id.discount or 0.0)
            line.l4e_discount_over_limit = (line.discount or 0.0) > (line_limit + 0.001)

    def write(self, vals):
        result = super().write(vals)
        if 'discount' not in vals:
            return result
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('l4e_discount_approval.required', 'False') != 'True':
            return result
        orders = self.mapped('order_id').filtered(
            lambda o: o.l4e_discount_approval_state == 'approved'
        )
        for order in orders:
            approved_max = order.l4e_discount_approval_request_id.max_discount
            current_max = max((l.discount or 0.0) for l in order.order_line)
            if current_max > approved_max:
                order.write({'l4e_discount_approval_state': 'not_required'})
                order.message_post(
                    body=_(
                        '⚠️ Discount approval invalidated: discount was increased '
                        'from %(approved).2f%% (approved) to %(current).2f%% after approval. '
                        'A new approval request will be required before confirming.'
                    ) % {'approved': approved_max, 'current': current_max},
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
        return result
