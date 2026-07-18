# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class L4eDiscountRefuseWizard(models.TransientModel):
    _name = 'l4e.discount.refuse.wizard'
    _description = 'Refuse Discount Approval'

    request_id = fields.Many2one(
        'l4e.discount.approval.request', required=True, ondelete='cascade',
    )
    note = fields.Text(string='Reason for Refusal', required=True)

    def action_confirm_refuse(self):
        self.ensure_one()
        if self.request_id.state != 'pending':
            raise UserError(_('This request is no longer pending.'))
        self.request_id._do_refuse(self.note)
        return {'type': 'ir.actions.act_window_close'}
