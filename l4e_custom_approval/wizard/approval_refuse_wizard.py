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
