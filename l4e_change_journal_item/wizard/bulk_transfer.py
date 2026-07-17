# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api

class BulkTransferWizard(models.TransientModel):
    _name = 'bulk.transfer.wizard'
    _description = 'Journal Entry Transfer'

    name = fields.Char(default="Journal Entry Transfer")

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    show_invoice = fields.Boolean(string="Invoice", default=False)
    show_bill = fields.Boolean(string="Bill", default=False)
    show_all = fields.Boolean(string="All", default=True)
    partner_ids = fields.Many2many('res.partner', string="Customer")
    invoice_no = fields.Char(string="Invoice No")
    journal_id = fields.Many2many('account.journal', relation='bulk_transfer_journal_rel', string="Journal")
    status_in_payment = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('blocked', 'Blocked'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
        ('draft', 'Draft'),
        ('cancel', 'Cancelled')
    ], string="Status")

    move_ids = fields.Many2many('account.move', string='Selected Entries')
    invoice_count = fields.Integer(string="Journal Entry Count", compute="_compute_invoice_count")

    change_journal = fields.Boolean(string='Change Journal', default=False)
    change_account = fields.Boolean(string='Change Account', default=False)
    change_analytic = fields.Boolean(string='Change Analytic', default=False)

    old_journal_id = fields.Many2many('account.journal', relation='bulk_transfer_old_journal_rel', string='Old Journal')
    new_journal_id = fields.Many2one('account.journal', string='New Journal')

    old_account_ids = fields.Many2many('account.account', 'bulk_transfer_old_account_rel', string='Old Account')
    new_account_id = fields.Many2one('account.account', string='New Account')

    old_analytic_ids = fields.Many2many('account.analytic.account', 'bulk_transfer_old_analytic_rel', string='Old Analytic')
    new_analytic_id = fields.Many2one('account.analytic.account', string='New Analytic')

    @api.onchange('show_invoice')
    def _onchange_show_invoice(self):
        if self.show_invoice:
            self.show_bill = False
            self.show_all = False
        elif not self.show_bill and not self.show_all:
            self.show_all = True

    @api.onchange('show_bill')
    def _onchange_show_bill(self):
        if self.show_bill:
            self.show_invoice = False
            self.show_all = False
        elif not self.show_invoice and not self.show_all:
            self.show_all = True

    @api.onchange('show_all')
    def _onchange_show_all(self):
        if self.show_all:
            self.show_invoice = False
            self.show_bill = False
        elif not self.show_invoice and not self.show_bill:
            self.show_all = True

    @api.onchange('journal_id')
    def _onchange_filter_journal_id(self):
        if self.journal_id:
            self.old_journal_id = self.journal_id

    @api.depends('move_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.move_ids)

    @api.onchange('date_from', 'date_to', 'partner_ids', 'invoice_no', 'journal_id', 'show_invoice', 'show_bill', 'show_all', 'status_in_payment')
    def _onchange_filters_fetch_invoices(self):
        domain = [('state', '=', 'posted')]
        if self.show_invoice:
            domain.append(('move_type', '=', 'out_invoice'))
        elif self.show_bill:
            domain.append(('move_type', '=', 'in_invoice'))
        else:
            domain.append(('move_type', 'in', ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')))

        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.invoice_no:
            domain.append(('name', 'ilike', self.invoice_no))
        if self.journal_id:
            domain.append(('journal_id', 'in', self.journal_id.ids))
        if self.status_in_payment:
            domain.append(('status_in_payment', '=', self.status_in_payment))

        moves = self.env['account.move'].search(domain)
        self.move_ids = [(6, 0, moves.ids)]

    @api.onchange('move_ids')
    def _onchange_move_ids(self):
        if self.journal_id:
            self.old_journal_id = self.journal_id
        else:
            journal_ids = self.move_ids.journal_id.ids
            self.old_journal_id = [(6, 0, list(set(journal_ids)))]

        account_ids = self.move_ids.line_ids.account_id.ids
        self.old_account_ids = [(6, 0, list(set(account_ids)))]

        analytic_ids = []
        for line in self.move_ids.line_ids:
            if line.analytic_distribution:
                dist = line.analytic_distribution
                if isinstance(dist, str):
                    try:
                        dist = json.loads(dist)
                    except Exception:
                        dist = None
                if dist and isinstance(dist, dict):
                    for k in dist.keys():
                        try:
                            analytic_ids.append(int(k))
                        except ValueError:
                            pass
        self.old_analytic_ids = [(6, 0, list(set(analytic_ids)))]

    def action_search(self):
        self.ensure_one() 
        domain = [('state', '=', 'posted')]
        if self.show_invoice:
            domain.append(('move_type', '=', 'out_invoice'))
        elif self.show_bill:
            domain.append(('move_type', '=', 'in_invoice'))
        else:
            domain.append(('move_type', 'in', ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')))

        if self.date_from:
            domain.extend([('date', '>=', self.date_from)])
        if self.date_to:
            domain.extend([('date', '<=', self.date_to)])
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.invoice_no:
            domain.append(('name', 'ilike', self.invoice_no))
        if self.journal_id:
            domain.append(('journal_id', 'in', self.journal_id.ids))
        if self.status_in_payment:
            domain.append(('status_in_payment', '=', self.status_in_payment))
        moves = self.env['account.move'].search(domain)
        self.write({'move_ids': [(6, 0, moves.ids)]})
        
        return False

    @api.model
    def default_get(self, fields_list):
        res = super(BulkTransferWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids and 'move_ids' in fields_list:
            res['move_ids'] = [(6, 0, active_ids)]
        return res

    def action_confirm(self):
        self.ensure_one()
        # Fallback to search if move_ids is empty but filters are set
        moves = self.move_ids
        if not moves and any([self.date_from, self.date_to, self.partner_ids, self.invoice_no, self.journal_id, self.status_in_payment]):
            domain = [('state', '=', 'posted')]
            if self.show_invoice:
                domain.append(('move_type', '=', 'out_invoice'))
            elif self.show_bill:
                domain.append(('move_type', '=', 'in_invoice'))
            else:
                domain.append(('move_type', 'in', ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')))

            if self.date_from:
                domain.append(('date', '>=', self.date_from))
            if self.date_to:
                domain.append(('date', '<=', self.date_to))
            if self.partner_ids:
                domain.append(('partner_id', 'in', self.partner_ids.ids))
            if self.invoice_no:
                domain.append(('name', 'ilike', self.invoice_no))
            if self.journal_id:
                domain.append(('journal_id', 'in', self.journal_id.ids))
            if self.status_in_payment:
                domain.append(('status_in_payment', '=', self.status_in_payment))
            moves = self.env['account.move'].search(domain)

        if not moves:
            return {'type': 'ir.actions.act_window_close'}

        for move in moves:
            # Change Journal Logic
            if self.change_journal and self.old_journal_id and self.new_journal_id:
                if move.journal_id in self.old_journal_id:
                    self.env.cr.execute(
                        "UPDATE account_move SET journal_id = %s WHERE id = %s",
                        (self.new_journal_id.id, move.id)
                    )
                    self.env.cr.execute(
                        "UPDATE account_move_line SET journal_id = %s WHERE move_id = %s",
                        (self.new_journal_id.id, move.id)
                    )

            # Change Account Logic
            if self.change_account and self.old_account_ids and self.new_account_id:
                old_acc_ids = self.old_account_ids.ids
                for line in move.line_ids:
                    if line.account_id.id in old_acc_ids:
                        self.env.cr.execute(
                            "UPDATE account_move_line SET account_id = %s WHERE id = %s",
                            (self.new_account_id.id, line.id)
                        )

            # Change Analytic Logic
            if self.change_analytic and self.new_analytic_id:
                new_analytic_str_id = str(self.new_analytic_id.id)
                plan = self.new_analytic_id.plan_id
                plan_accounts = self.env['account.analytic.account'].search([('plan_id', '=', plan.id)])
                plan_account_str_ids = [str(x) for x in plan_accounts.ids]

                for line in move.line_ids:
                    if line.display_type not in ('line_section', 'line_note'):
                        dist = line.analytic_distribution
                        if isinstance(dist, str):
                            try:
                                dist = json.loads(dist)
                            except Exception:
                                dist = None
                        
                        new_dist = dict(dist) if dist else {}
                        changed = False
                        
                        if self.old_analytic_ids:
                            old_analytic_str_ids = [str(x) for x in self.old_analytic_ids.ids]
                            for old_id in old_analytic_str_ids:
                                if old_id in new_dist:
                                    val = new_dist.pop(old_id)
                                    new_dist[new_analytic_str_id] = new_dist.get(new_analytic_str_id, 0.0) + val
                                    changed = True
                        else:
                            # If no old analytic is selected, update all analytic distribution of this plan to the new one
                            existing_plan_percentage = 0.0
                            for old_id in plan_account_str_ids:
                                if old_id in new_dist:
                                    existing_plan_percentage += float(new_dist.pop(old_id))
                            
                            if existing_plan_percentage == 0.0:
                                existing_plan_percentage = 100.0
                                
                            new_dist[new_analytic_str_id] = existing_plan_percentage
                            changed = True

                        if changed:
                            dist_val = json.dumps(new_dist) if new_dist else None
                            if dist_val:
                                self.env.cr.execute(
                                    "UPDATE account_move_line SET analytic_distribution = %s::jsonb WHERE id = %s",
                                    (dist_val, line.id)
                                )
                            else:
                                self.env.cr.execute(
                                    "UPDATE account_move_line SET analytic_distribution = NULL WHERE id = %s",
                                    (line.id,)
                                )

        # Force write synchronization by deleting and recreating the analytic lines
        # Invalidate cache first so recreate reads updated SQL values
        self.env.invalidate_all()
        
        lines_to_recreate = moves.line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
        if lines_to_recreate:
            self.env['account.analytic.line'].sudo().with_context(skip_analytic_sync=True).search([
                ('move_line_id', 'in', lines_to_recreate.ids)
            ]).unlink()
            lines_to_recreate.sudo().with_context(skip_analytic_sync=True)._create_analytic_lines()
            
        self.env.invalidate_all()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Successfully updated {len(moves)} invoices.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
