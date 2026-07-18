# -*- coding: utf-8 -*-
import logging
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .purchase_order import _l4e_get_limit

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'

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

    @api.depends('invoice_line_ids.discount', 'invoice_user_id', 'company_id',
                 'discount_type', 'discount_rate', 'amount_discount', 'amount_untaxed')
    def _compute_l4e_discount_flags(self):
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('l4e_discount_approval.required', 'False') == 'True'
        for move in self:
            if not enabled or not move.is_invoice() or not move.invoice_line_ids:
                move.l4e_discount_exceeds_limit = False
                move.l4e_max_discount = 0.0
                move.l4e_matched_tier_id = False
                continue

            uid = (move.invoice_user_id or move.env.user).id
            cid = move.company_id.id
            discount_type = move.discount_type

            if discount_type == 'line':
                limit = _l4e_get_limit(self.env, uid, cid, 'line_discount_limit',
                                       'l4e_discount_approval.default_line_limit')
                max_disc = max((l.discount or 0.0) for l in move.invoice_line_ids)
            elif discount_type == 'percent':
                limit = _l4e_get_limit(self.env, uid, cid, 'global_discount_limit',
                                       'l4e_discount_approval.default_global_limit')
                max_disc = move.discount_rate or 0.0
            else:  # amount
                limit = _l4e_get_limit(self.env, uid, cid, 'global_discount_limit',
                                       'l4e_discount_approval.default_global_limit')
                total_before = (move.amount_untaxed or 0.0) + (move.amount_discount or 0.0)
                max_disc = (move.amount_discount / total_before * 100) if total_before else 0.0

            exceeds = max_disc > limit
            move.l4e_max_discount = max_disc
            move.l4e_discount_exceeds_limit = exceeds
            move.l4e_matched_tier_id = move._l4e_find_matching_tier(max_disc) if exceeds else False

    def _compute_l4e_discount_approval_count(self):
        for move in self:
            move.l4e_discount_approval_count = self.env[
                'l4e.discount.approval.request'
            ].search_count([('account_move_id', '=', move.id)])

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
        uid = (self.invoice_user_id or self.env.user).id
        cid = self.company_id.id
        if self.discount_type == 'line':
            limit = _l4e_get_limit(self.env, uid, cid, 'line_discount_limit',
                                   'l4e_discount_approval.default_line_limit')
            lines = self.invoice_line_ids.filtered(lambda l: (l.discount or 0.0) > limit)
            parts = [f"• {l.product_id.name or 'Product'}: {l.discount:.2f}% (limit: {limit:.2f}%)"
                     for l in lines]
            return '\n'.join(parts)
        else:
            limit = _l4e_get_limit(self.env, uid, cid, 'global_discount_limit',
                                   'l4e_discount_approval.default_global_limit')
            return f"Effective discount: {self.l4e_max_discount:.2f}% (limit: {limit:.2f}%)"

    # ── action_post override ──────────────────────────────────────────────────

    def action_post(self):
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('l4e_discount_approval.required', 'False') == 'True'

        for move in self:
            if not enabled or not move.is_invoice():
                continue
            if move.l4e_discount_approval_state == 'approved':
                continue
            if not move.l4e_discount_exceeds_limit:
                continue
            if move.l4e_discount_approval_state == 'pending':
                raise UserError(_(
                    'A discount approval request is pending for "%s". '
                    'Please wait for it to be approved.'
                ) % move.name)
            if move.l4e_discount_approval_state == 'refused':
                raise UserError(_(
                    'The discount approval for "%s" was refused. '
                    'Please adjust the discounts or request a new approval.'
                ) % move.name)
            move.action_request_discount_approval()
            raise UserError(_(
                'Discount on "%s" exceeds the allowed limit.\n'
                'An approval request has been created and sent to the approvers.'
            ) % move.name)

        return super().action_post()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_request_discount_approval(self):
        self.ensure_one()
        existing = self.env['l4e.discount.approval.request'].search([
            ('account_move_id', '=', self.id), ('state', '=', 'pending'),
        ])
        existing.write({'state': 'cancelled'})

        uid = (self.invoice_user_id or self.env.user).id
        limit_rec = self.env['l4e.discount.limit'].sudo().search([
            ('user_id', '=', uid),
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
            'account_move_id': self.id,
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
            ('account_move_id', '=', self.id),
        ])
        if len(requests) == 1:
            return {'type': 'ir.actions.act_window', 'res_model': 'l4e.discount.approval.request',
                    'res_id': requests.id, 'view_mode': 'form'}
        return {'type': 'ir.actions.act_window', 'res_model': 'l4e.discount.approval.request',
                'view_mode': 'list,form', 'domain': [('account_move_id', '=', self.id)]}


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'

    l4e_discount_over_limit = fields.Boolean(
        string='Over Limit',
        compute='_compute_l4e_discount_over_limit',
        store=False,
    )

    @api.depends('discount', 'move_id.invoice_user_id', 'move_id.company_id', 'move_id.discount_type')
    def _compute_l4e_discount_over_limit(self):
        for line in self:
            if not line.move_id.is_invoice() or line.move_id.discount_type != 'line':
                line.l4e_discount_over_limit = False
                continue
            uid = (line.move_id.invoice_user_id or line.env.user).id
            cid = line.move_id.company_id.id
            limit = _l4e_get_limit(self.env, uid, cid, 'line_discount_limit',
                                   'l4e_discount_approval.default_line_limit')
            line.l4e_discount_over_limit = (line.discount or 0.0) > limit
