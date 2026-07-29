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
