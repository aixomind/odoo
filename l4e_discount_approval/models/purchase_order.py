# -*- coding: utf-8 -*-
import logging
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ── Shared helpers reused by both purchase and invoice models ──────────────────

def _l4e_get_limit(env, user_id, company_id, field_name, param_key):
    """Read per-salesperson limit, fall back to system default."""
    default = float(env['ir.config_parameter'].sudo().get_param(param_key, '0.0'))
    if not user_id:
        return default
    rec = env['l4e.discount.limit'].sudo().search([
        ('user_id', '=', user_id),
        ('company_id', '=', company_id or env.company.id),
    ], limit=1)
    return getattr(rec, field_name) if rec else default


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    # ── Approval state ────────────────────────────────────────────────────────
    l4e_discount_approval_state = fields.Selection(
        [('not_required', 'Not Required'), ('pending', 'Pending Approval'),
         ('approved', 'Approved'), ('refused', 'Refused')],
        string='Discount Approval', default='not_required',
        copy=False, tracking=True, index=True,
    )
    l4e_discount_approval_request_id = fields.Many2one(
        'l4e.discount.approval.request', string='Discount Approval Request',
        copy=False, readonly=True,
    )

    # ── Computed flags ────────────────────────────────────────────────────────
    l4e_discount_exceeds_limit = fields.Boolean(
        compute='_compute_l4e_discount_flags', store=False,
    )
    l4e_max_discount = fields.Float(
        compute='_compute_l4e_discount_flags', store=False, digits=(5, 2),
    )
    l4e_matched_tier_id = fields.Many2one(
        'l4e.discount.tier', compute='_compute_l4e_discount_flags', store=False,
    )
    l4e_discount_approval_count = fields.Integer(
        compute='_compute_l4e_discount_approval_count',
    )

    @api.depends('order_line.discount', 'user_id', 'company_id',
                 'discount_type', 'discount_rate', 'amount_discount', 'amount_untaxed')
    def _compute_l4e_discount_flags(self):
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('l4e_discount_approval.required', 'False') == 'True'
        for order in self:
            if not enabled or not order.order_line:
                order.l4e_discount_exceeds_limit = False
                order.l4e_max_discount = 0.0
                order.l4e_matched_tier_id = False
                continue

            discount_type = order.discount_type
            uid = order.user_id.id
            cid = order.company_id.id

            if discount_type == 'line':
                limit = _l4e_get_limit(self.env, uid, cid, 'line_discount_limit',
                                       'l4e_discount_approval.default_line_limit')
                max_disc = max((l.discount or 0.0) for l in order.order_line)
            elif discount_type == 'percent':
                limit = _l4e_get_limit(self.env, uid, cid, 'global_discount_limit',
                                       'l4e_discount_approval.default_global_limit')
                max_disc = order.discount_rate or 0.0
            else:  # amount
                limit = _l4e_get_limit(self.env, uid, cid, 'global_discount_limit',
                                       'l4e_discount_approval.default_global_limit')
                total_before = (order.amount_untaxed or 0.0) + (order.amount_discount or 0.0)
                max_disc = (order.amount_discount / total_before * 100) if total_before else 0.0

            exceeds = max_disc > limit
            order.l4e_max_discount = max_disc
            order.l4e_discount_exceeds_limit = exceeds
            order.l4e_matched_tier_id = order._l4e_find_matching_tier(max_disc) if exceeds else False

    def _compute_l4e_discount_approval_count(self):
        for order in self:
            order.l4e_discount_approval_count = self.env[
                'l4e.discount.approval.request'
            ].search_count([('purchase_order_id', '=', order.id)])

    def _l4e_find_matching_tier(self, discount_pct):
        self.ensure_one()
        tiers = self.env['l4e.discount.tier'].sudo().search([
            ('active', '=', True),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ], order='discount_min asc')
        for tier in tiers:
            if tier._match_discount(discount_pct):
                return tier
        return False

    def _l4e_get_discount_info_text(self):
        self.ensure_one()
        uid, cid = self.user_id.id, self.company_id.id
        if self.discount_type == 'line':
            limit = _l4e_get_limit(self.env, uid, cid, 'line_discount_limit',
                                   'l4e_discount_approval.default_line_limit')
            lines = self.order_line.filtered(lambda l: (l.discount or 0.0) > limit)
            parts = [f"• {l.product_id.name or 'Product'}: {l.discount:.2f}% (limit: {limit:.2f}%)"
                     for l in lines]
            return '\n'.join(parts)
        else:
            limit = _l4e_get_limit(self.env, uid, cid, 'global_discount_limit',
                                   'l4e_discount_approval.default_global_limit')
            return f"Effective discount: {self.l4e_max_discount:.2f}% (limit: {limit:.2f}%)"

    # ── button_confirm override ───────────────────────────────────────────────

    def button_confirm(self):
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
                    'Please wait for it to be approved.'
                ) % order.name)
            if order.l4e_discount_approval_state == 'refused':
                raise UserError(_(
                    'The discount approval for "%s" was refused. '
                    'Please adjust the discounts or request a new approval.'
                ) % order.name)
            order.action_request_discount_approval()
            raise UserError(_(
                'Discount on "%s" exceeds the allowed limit.\n'
                'An approval request has been created and sent to the approvers.'
            ) % order.name)

        return super().button_confirm()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_request_discount_approval(self):
        self.ensure_one()
        existing = self.env['l4e.discount.approval.request'].search([
            ('purchase_order_id', '=', self.id), ('state', '=', 'pending'),
        ])
        existing.write({'state': 'cancelled'})

        limit_rec = None
        if self.user_id:
            limit_rec = self.env['l4e.discount.limit'].sudo().search([
                ('user_id', '=', self.user_id.id),
                ('company_id', '=', (self.company_id.id or self.env.company.id)),
            ], limit=1)

        if limit_rec and limit_rec.approver_ids:
            approvers = limit_rec.approver_ids
            tier = self.env['l4e.discount.tier']
            approval_mode = limit_rec.approval_mode
        else:
            tier = self.l4e_matched_tier_id
            if not tier:
                raise UserError(_(
                    'No approval tier is configured for a discount of %.2f%%.\n'
                    'Please ask your manager to configure a Discount Tier.'
                ) % self.l4e_max_discount)
            if not tier.approver_ids:
                raise UserError(_('The matched tier "%s" has no approvers configured.') % tier.name)
            approvers = tier.approver_ids
            approval_mode = tier.approval_mode

        request = self.env['l4e.discount.approval.request'].sudo().create({
            'purchase_order_id': self.id,
            'tier_id': tier.id if tier else False,
            'requester_id': self.env.uid,
            'max_discount': self.l4e_max_discount,
            'discount_info': self._l4e_get_discount_info_text(),
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
            ) % {'disc': self.l4e_max_discount, 'approvers': ', '.join(approvers.mapped('name'))},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        return request

    def action_view_discount_approval(self):
        self.ensure_one()
        requests = self.env['l4e.discount.approval.request'].search([
            ('purchase_order_id', '=', self.id),
        ])
        if len(requests) == 1:
            return {'type': 'ir.actions.act_window', 'res_model': 'l4e.discount.approval.request',
                    'res_id': requests.id, 'view_mode': 'form'}
        return {'type': 'ir.actions.act_window', 'res_model': 'l4e.discount.approval.request',
                'view_mode': 'list,form', 'domain': [('purchase_order_id', '=', self.id)]}


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    l4e_discount_over_limit = fields.Boolean(
        string='Over Limit', compute='_compute_l4e_discount_over_limit',
        store=False,
    )

    @api.depends('discount', 'order_id.user_id', 'order_id.company_id', 'order_id.discount_type')
    def _compute_l4e_discount_over_limit(self):
        for line in self:
            if line.order_id.discount_type != 'line':
                line.l4e_discount_over_limit = False
                continue
            uid = line.order_id.user_id.id
            cid = line.order_id.company_id.id
            limit = _l4e_get_limit(self.env, uid, cid, 'line_discount_limit',
                                   'l4e_discount_approval.default_line_limit')
            line.l4e_discount_over_limit = (line.discount or 0.0) > limit
