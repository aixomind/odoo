# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class L4eApprovalRefuseWizard(models.TransientModel):
    """Simple wizard to capture a refusal note before refusing an approval request."""
    _name = 'l4e.approval.refuse.wizard'
    _description = 'Refuse Approval Wizard'

    request_id = fields.Many2one(
        'l4e.approval.record.request', string='Request',
        required=True, ondelete='cascade',
    )
    note = fields.Text(string='Reason for Refusal', required=True)

    def action_confirm_refuse(self):
        self.ensure_one()
        request = self.request_id
        if request.state != 'pending':
            raise UserError(_('This request is no longer pending.'))

        line = request.approver_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )[:1]
        if not line:
            raise UserError(_('You are not a pending approver for this request.'))

        line.write({
            'status': 'refused',
            'date': fields.Datetime.now(),
            'note': self.note,
        })
        request._finalize_refuse(note=self.note)
        return {'type': 'ir.actions.act_window_close'}
