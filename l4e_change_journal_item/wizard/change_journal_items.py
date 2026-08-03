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

class ChangeJournalItemsWizard(models.TransientModel):
    _name = 'change.journal.items.wizard'
    _description = 'Change Journal Items Wizard'

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    current_journal_id = fields.Many2one('account.journal', string='Current Journal', related='move_id.journal_id', readonly=True)
    new_journal_id = fields.Many2one('account.journal', string='New Journal', required=True)
    line_ids = fields.One2many('change.journal.items.wizard.line', 'wizard_id', string='Journal Items')



    def action_confirm(self):
        self.ensure_one()
        # Direct SQL updates to bypass Odoo python write constraints on posted entries.
        if self.new_journal_id and self.new_journal_id != self.move_id.journal_id:
            self.env.cr.execute(
                "UPDATE account_move SET journal_id = %s WHERE id = %s",
                (self.new_journal_id.id, self.move_id.id)
            )
            self.env.cr.execute(
                "UPDATE account_move_line SET journal_id = %s WHERE move_id = %s",
                (self.new_journal_id.id, self.move_id.id)
            )

        for line in self.line_ids:
            if line.new_account_id:
                self.env.cr.execute(
                    "UPDATE account_move_line SET account_id = %s WHERE id = %s",
                    (line.new_account_id.id, line.move_line_id.id)
                )
                self.env.cr.execute(
                    "UPDATE account_analytic_line SET general_account_id = %s WHERE move_line_id = %s",
                    (line.new_account_id.id, line.move_line_id.id)
                )

        # Invalidate the entire environment cache to reflect changes instantly in the UI
        self.env.invalidate_all()

        return {'type': 'ir.actions.act_window_close'}


class ChangeJournalItemsWizardLine(models.TransientModel):
    _name = 'change.journal.items.wizard.line'
    _description = 'Change Journal Items Wizard Line'

    wizard_id = fields.Many2one('change.journal.items.wizard', string='Wizard')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item')
    account_id = fields.Many2one('account.account', string='Account', related='move_line_id.account_id', readonly=True)
    new_account_id = fields.Many2one('account.account', string='New Account', required=True)
    name = fields.Char(string='Label', related='move_line_id.name', readonly=True)
    analytic_distribution = fields.Json(string='Analytic Distribution', related='move_line_id.analytic_distribution', readonly=True)
    debit = fields.Monetary(string='Debit', related='move_line_id.debit', readonly=True)
    credit = fields.Monetary(string='Credit', related='move_line_id.credit', readonly=True)
    tax_tag_ids = fields.Many2many('account.account.tag', string='Tax Grids', related='move_line_id.tax_tag_ids', readonly=True)
    currency_id = fields.Many2one('res.currency', related='move_line_id.currency_id', readonly=True)
    analytic_precision = fields.Integer(string='Analytic Precision', default=2)
    company_id = fields.Many2one('res.company', related='move_line_id.company_id', readonly=True)
