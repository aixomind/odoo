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
