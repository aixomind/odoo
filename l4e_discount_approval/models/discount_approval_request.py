# -*- coding: utf-8 -*-
import logging
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L4eDiscountApprovalRequest(models.Model):
    _name = 'l4e.discount.approval.request'
    _description = 'Discount Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       default=lambda self: _('New'))

    # ── Document references (exactly one will be set) ─────────────────────────
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        ondelete='set null', readonly=True, index=True,
    )
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Purchase Order',
        ondelete='set null', readonly=True, index=True,
    )
    account_move_id = fields.Many2one(
        'account.move', string='Invoice / Bill',
        ondelete='set null', readonly=True, index=True,
    )
    document_type = fields.Selection(
        [('sale', 'Sale Order'), ('purchase', 'Purchase Order'), ('invoice', 'Invoice/Bill')],
        string='Document Type', compute='_compute_document_type', store=True,
    )

    @api.depends('sale_order_id', 'purchase_order_id', 'account_move_id')
    def _compute_document_type(self):
        for rec in self:
            if rec.sale_order_id:
                rec.document_type = 'sale'
            elif rec.purchase_order_id:
                rec.document_type = 'purchase'
            elif rec.account_move_id:
                rec.document_type = 'invoice'
            else:
                rec.document_type = False

    # ── Approval metadata ─────────────────────────────────────────────────────
    tier_id = fields.Many2one('l4e.discount.tier', string='Approval Tier', readonly=True)
    requester_id = fields.Many2one('res.users', string='Requested By',
                                   default=lambda self: self.env.user, readonly=True)
    date_request = fields.Datetime(string='Requested On', default=fields.Datetime.now, readonly=True)
    state = fields.Selection(
        [('pending', 'Pending Approval'), ('approved', 'Approved'),
         ('refused', 'Refused'), ('cancelled', 'Cancelled')],
        default='pending', required=True, tracking=True,
    )
    max_discount = fields.Float(string='Max Discount (%)', digits=(5, 2), readonly=True)
    discount_info = fields.Text(string='Discount Details', readonly=True)
    approver_ids = fields.Many2many(
        'res.users', relation='l4e_discount_req_approver_rel',
        column1='request_id', column2='user_id', string='Approvers', readonly=True,
    )
    approval_mode = fields.Selection(
        [('any', 'Any one approver'), ('all', 'All approvers required')],
        string='Approval Mode', default='any', required=True,
    )
    approved_by_ids = fields.Many2many(
        'res.users', relation='l4e_discount_req_approved_by_rel',
        column1='request_id', column2='user_id', string='Approved By',
    )
    refuse_note = fields.Text(string='Refusal Reason', readonly=True)
    can_approve = fields.Boolean(compute='_compute_can_approve')

    @api.depends('approver_ids', 'state')
    def _compute_can_approve(self):
        for rec in self:
            rec.can_approve = self.env.user in rec.approver_ids and rec.state == 'pending'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'l4e.discount.approval.request') or _('New')
        return super().create(vals_list)

    # ── Document helpers ──────────────────────────────────────────────────────

    def _get_document(self):
        self.ensure_one()
        return self.sale_order_id or self.purchase_order_id or self.account_move_id

    def _get_document_name(self):
        doc = self._get_document()
        return doc.name if doc else '-'

    def _get_document_partner(self):
        doc = self._get_document()
        return getattr(doc, 'partner_id', self.env['res.partner'])

    def _set_document_approval_state(self, state):
        self.ensure_one()
        doc = self._get_document()
        if doc:
            doc.write({'l4e_discount_approval_state': state})

    def _post_to_document(self, message):
        self.ensure_one()
        try:
            doc = self._get_document()
            if doc and doc.exists():
                doc.message_post(body=message, message_type='notification',
                                 subtype_xmlid='mail.mt_note')
        except Exception:
            pass

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('This request is no longer pending.'))
        if self.env.user not in self.approver_ids:
            raise UserError(_('You are not an approver for this request.'))

        self.approved_by_ids = [(4, self.env.uid)]

        if self.approval_mode == 'any' or (
            self.approval_mode == 'all' and self.approver_ids <= self.approved_by_ids
        ):
            self.write({'state': 'approved'})
            self._set_document_approval_state('approved')
            self._notify_requester(approved=True)
            self._post_to_document(_('✅ Discount approved. The document can now be confirmed.'))
            if self.sale_order_id and (getattr(self.sale_order_id, 'is_partial', False) or '-R' in (self.sale_order_id.name or '')):
                self.sale_order_id.action_confirm()
        else:
            self._notify_remaining_approvers()

    def action_refuse(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('This request is no longer pending.'))
        if self.env.user not in self.approver_ids:
            raise UserError(_('You are not an approver for this request.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Discount Approval'),
            'res_model': 'l4e.discount.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def _do_refuse(self, note):
        self.ensure_one()
        self.write({'state': 'refused', 'refuse_note': note})
        self._set_document_approval_state('refused')
        self._notify_requester(approved=False, note=note)
        self._post_to_document(Markup(
            '<p>❌ Discount approval refused. Reason: <em>%(note)s</em></p>'
        ) % {'note': note})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        self._set_document_approval_state('not_required')

    def action_open_document(self):
        self.ensure_one()
        doc = self._get_document()
        if not doc:
            return
        model_map = {
            'sale': 'sale.order',
            'purchase': 'purchase.order',
            'invoice': 'account.move',
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': model_map.get(self.document_type, 'sale.order'),
            'res_id': doc.id,
            'view_mode': 'form',
        }

    # kept for backward compatibility
    def action_open_sale_order(self):
        return self.action_open_document()

    # ── Notifications ─────────────────────────────────────────────────────────

    def _notify_approvers(self):
        self.ensure_one()
        if not self.approver_ids:
            return
        partner_ids = self.approver_ids.mapped('partner_id').ids
        partner = self._get_document_partner()
        self.message_post(
            body=Markup(
                '<p>👋 Your discount approval is required for <b>%(doc)s</b> (%(customer)s).</p>'
                '<p><b>Max Discount:</b> %(discount)s%%</p>'
                '<p><b>Tier:</b> %(tier)s</p>'
            ) % {
                'doc': self._get_document_name(),
                'customer': partner.name if partner else '-',
                'discount': self.max_discount,
                'tier': self.tier_id.name if self.tier_id else '-',
            },
            partner_ids=partner_ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def _notify_remaining_approvers(self):
        remaining = self.approver_ids - self.approved_by_ids
        if not remaining:
            return
        self.message_post(
            body=Markup(
                '<p>⏳ Discount approval for <b>%(doc)s</b> still needs '
                'approval from: %(users)s</p>'
            ) % {
                'doc': self._get_document_name(),
                'users': ', '.join(remaining.mapped('name')),
            },
            partner_ids=remaining.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def _notify_requester(self, approved=True, note=''):
        self.ensure_one()
        if not self.requester_id.partner_id:
            return
        decision = _('Approved ✅') if approved else _('Refused ❌')
        body = Markup(
            '<p>Your discount approval request <b>%(ref)s</b> for '
            '<b>%(doc)s</b> has been <b>%(decision)s</b>.</p>'
        ) % {'ref': self.name, 'doc': self._get_document_name(), 'decision': decision}
        if note:
            body += Markup('<p><b>Reason:</b> <em>%(note)s</em></p>') % {'note': note}
        self.message_post(
            body=body,
            partner_ids=[self.requester_id.partner_id.id],
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
