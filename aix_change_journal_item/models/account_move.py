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
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_change_journal_items(self):
        self.ensure_one()
        wizard = self.env['change.journal.items.wizard'].create({
            'move_id': self.id,
            'new_journal_id': self.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'move_line_id': line.id,
                    'new_account_id': line.account_id.id,
                }) for line in self.line_ids
            ]
        })
        return {
            'name': 'Change Journal Items',
            'type': 'ir.actions.act_window',
            'res_model': 'change.journal.items.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
