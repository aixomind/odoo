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
import logging
from datetime import datetime, time as datetime_time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Company lock dates that block a plain miscellaneous entry. Odoo 18 has no
# period_lock_date, and tax / sale / purchase lock dates are deliberately not
# checked: a stock valuation entry carries no tax and belongs to no sale or
# purchase journal.
COMPANY_LOCK_DATE_FIELDS = (
    ('hard_lock_date', 'Hard Lock Date'),
    ('fiscalyear_lock_date', 'Fiscal Year Lock Date'),
)


class InventoryBackdateWizard(models.TransientModel):
    _name = 'inventory.backdate.wizard'
    _description = 'Backdate Inventory Adjustments'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    # --- search criteria -------------------------------------------------
    date_from = fields.Date(
        string='Validated From', required=True, default=fields.Date.context_today,
        help="Start of the range searched against the current date of the adjustment.")
    date_to = fields.Date(
        string='Validated To', required=True, default=fields.Date.context_today,
        help="End of the range searched against the current date of the adjustment.")
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    reference_filter = fields.Char(
        string='Reference Contains',
        help="Optional filter on the move reference, e.g. the adjustment name.")

    line_ids = fields.One2many(
        'inventory.backdate.wizard.line', 'wizard_id', string='Adjustments')
    line_count = fields.Integer(compute='_compute_line_count')
    selected_count = fields.Integer(compute='_compute_line_count')

    # --- target date -----------------------------------------------------
    new_date = fields.Date(
        string='New Date', required=True, default=fields.Date.context_today)
    new_time = fields.Float(
        string='New Time', default=9.0,
        help="Time of day, in your own timezone, stamped on the stock move and "
             "the valuation layer.")

    # --- what to rewrite -------------------------------------------------
    update_move_lines = fields.Boolean(string='Stock Move Lines', default=True)
    update_valuation_layer = fields.Boolean(string='Valuation Layers', default=True)
    update_journal_entry = fields.Boolean(string='Journal Entries', default=True)
    update_analytic_lines = fields.Boolean(string='Analytic Lines', default=True)
    update_quant_count_date = fields.Boolean(
        string='Recompute Last Count Date', default=False,
        help="Recompute the 'Last Counted' date of the impacted quants from the "
             "corrected move history.")
    post_chatter_note = fields.Boolean(
        string='Log in Journal Entry Chatter', default=True)
    resequence_journal_entry = fields.Boolean(
        string='Renumber Journal Entry', default=False,
        help="Give the journal entry a number belonging to its new period. This "
             "leaves a gap in the old period's numbering, which auditors treat as "
             "a red flag, so it is off by default. Refused on journals that secure "
             "posted entries with a hash.")
    ignore_lock_date = fields.Boolean(
        string='Ignore Accounting Lock Dates', default=False,
        help="Write into a locked period anyway. Reserved for administrators.")

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.line_ids)
            wizard.selected_count = len(wizard.line_ids.filtered('selected'))

    # ------------------------------------------------------------------
    # Timezone helpers
    # ------------------------------------------------------------------
    def _user_timezone(self):
        return pytz.timezone(self.env.user.tz or self.env.context.get('tz') or 'UTC')

    def _to_utc(self, local_datetime):
        """Turn a naive datetime expressed in the user's timezone into naive UTC."""
        return self._user_timezone().localize(local_datetime).astimezone(
            pytz.utc).replace(tzinfo=None)

    def _target_datetime(self):
        """The UTC datetime to stamp on the stock move and valuation layer."""
        self.ensure_one()
        hours = int(self.new_time)
        minutes = int(round((self.new_time - hours) * 60))
        if minutes >= 60:
            hours, minutes = hours + 1, 0
        if hours > 23:
            hours, minutes = 23, 59
        return self._to_utc(datetime.combine(self.new_date, datetime_time(hours, minutes)))

    # ------------------------------------------------------------------
    # Step 1 - find the adjustments
    # ------------------------------------------------------------------
    def _search_domain(self):
        self.ensure_one()
        domain = [
            ('is_inventory', '=', True),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self._to_utc(datetime.combine(self.date_from, datetime_time.min))),
            ('date', '<=', self._to_utc(datetime.combine(self.date_to, datetime_time.max))),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.location_id:
            domain += ['|', ('location_id', '=', self.location_id.id),
                       ('location_dest_id', '=', self.location_id.id)]
        if self.reference_filter:
            domain.append(('reference', 'ilike', self.reference_filter))
        return domain

    def action_load_moves(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("'Validated From' must not be later than 'Validated To'."))

        self.line_ids.unlink()
        moves = self.env['stock.move'].search(self._search_domain(), order='date desc, id desc')

        values = []
        for move in moves:
            targets = move._backdate_collect_targets()
            location = (move.location_dest_id if move.location_dest_id.usage == 'internal'
                        else move.location_id)
            values.append({
                'wizard_id': self.id,
                'move_id': move.id,
                'reference': move.reference or move.name,
                'product_id': move.product_id.id,
                'quantity': move.quantity,
                'location_name': location.complete_name or '',
                'current_date': move.date,
                'valuation_layer_count': len(targets['valuation_layers']),
                'account_move_names': ', '.join(
                    targets['account_moves'].mapped('name')) or _('none'),
            })
        self.env['inventory.backdate.wizard.line'].create(values)

        if not values:
            raise UserError(_(
                "No validated inventory adjustment was found between %(start)s and "
                "%(end)s with these criteria.",
                start=self.date_from, end=self.date_to,
            ))
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Backdate Inventory Adjustments'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_all(self):
        self.ensure_one()
        self.line_ids.selected = True
        return self._reopen()

    def action_unselect_all(self):
        self.ensure_one()
        self.line_ids.selected = False
        return self._reopen()

    # ------------------------------------------------------------------
    # Step 2 - safety checks
    # ------------------------------------------------------------------
    def _check_lock_dates(self, moves, target_date):
        """Refuse to write into a period the accountant has closed."""
        self.ensure_one()
        if self.ignore_lock_date:
            if not self.env.user.has_group('base.group_system'):
                raise UserError(_(
                    "Only a system administrator may ignore accounting lock dates."))
            return
        for company in moves.company_id:
            company_sudo = company.sudo()
            for field_name, label in COMPANY_LOCK_DATE_FIELDS:
                if field_name not in company_sudo._fields:
                    continue
                lock_date = company_sudo[field_name]
                if lock_date and target_date <= lock_date:
                    raise UserError(_(
                        "%(new_date)s falls inside a locked period of %(company)s "
                        "(%(label)s: %(lock)s).\n\n"
                        "Move the lock date, or tick 'Ignore Accounting Lock Dates' "
                        "as an administrator.",
                        new_date=target_date, company=company.display_name,
                        label=label, lock=lock_date,
                    ))

    def _check_moves(self, moves):
        wrong_state = moves.filtered(lambda m: m.state != 'done')
        if wrong_state:
            raise UserError(_(
                "Only validated adjustments can be backdated. Not done: %s",
                ', '.join(wrong_state.mapped('reference'))))
        not_inventory = moves.filtered(lambda m: not m.is_inventory)
        if not_inventory:
            raise UserError(_(
                "These moves are not inventory adjustments: %s",
                ', '.join(not_inventory.mapped('reference'))))

    # ------------------------------------------------------------------
    # Step 3 - rewrite the dates
    # ------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if not self.env.user.has_group('stock_inventory_backdate.group_inventory_backdate'):
            raise UserError(_("You are not allowed to change inventory adjustment dates."))

        lines = self.line_ids.filtered('selected')
        if not lines:
            raise UserError(_("Tick at least one inventory adjustment to backdate."))

        moves = lines.move_id
        self._check_moves(moves)

        target_date = self.new_date
        target_datetime = self._target_datetime()
        self._check_lock_dates(moves, target_date)

        # Read everything through the ORM first: once the raw UPDATEs start,
        # the cache no longer reflects the database.
        snapshots = []
        for move in moves:
            targets = move._backdate_collect_targets()
            account_moves = targets['account_moves']
            snapshots.append({
                'move': move,
                'old_date': move.date,
                'old_accounting_date': min(account_moves.mapped('date')) if account_moves else False,
                'valuation_layer_ids': targets['valuation_layers'].ids,
                'account_moves': account_moves,
                'analytic_ids': targets['analytic_lines'].ids,
                'move_line_ids': move.move_line_ids.ids,
                # (id, name) pairs so a renumbered entry can be told apart from
                # one still carrying its old number.
                'entries': [(entry.id, entry.name) for entry in account_moves],
            })

        self.env.flush_all()
        for snapshot in snapshots:
            self._rewrite_dates(snapshot, target_datetime, target_date)
        self.env.invalidate_all()

        if self.update_quant_count_date:
            self._recompute_quant_count_date(moves)

        rename_notes, renamed_ids = {}, set()
        if self.resequence_journal_entry:
            rename_notes, renamed_ids = self._resequence_entries(snapshots)

        logs = self._create_logs(
            snapshots, target_datetime, target_date, rename_notes, renamed_ids)
        if self.post_chatter_note:
            self._post_chatter_notes(snapshots, target_date)

        _logger.info(
            "Inventory backdating: %s move(s) moved to %s by %s",
            len(snapshots), target_datetime, self.env.user.login,
        )
        return self._result_action(logs, snapshots, target_date, renamed_ids)

    def _rewrite_dates(self, snapshot, target_datetime, target_date):
        """Hand one adjustment's captured ids to the shared rewriter.

        The SQL lives on stock.move so the past-count import applies dates the
        same way this wizard does. Every statement runs in the current request
        transaction, so an error on any of them rolls the whole batch back.
        """
        snapshot['move']._backdate_write_dates(
            target_datetime,
            target_date,
            {
                'move_line_ids': snapshot['move_line_ids'],
                'valuation_layer_ids': snapshot['valuation_layer_ids'],
                'account_move_ids': snapshot['account_moves'].ids,
                'analytic_ids': snapshot['analytic_ids'],
            },
            {
                'move_lines': self.update_move_lines,
                'valuation': self.update_valuation_layer,
                'journal': self.update_journal_entry,
                'analytic': self.update_analytic_lines,
            },
        )

    def _recompute_quant_count_date(self, moves):
        """Refresh 'Last Counted' on the quants behind the corrected moves."""
        Quant = self.env['stock.quant'].sudo()
        field = Quant._fields.get('last_count_date')
        if not field or not field.store or not field.compute:
            return
        locations = self.env['stock.location'].browse()
        for move in moves:
            locations |= (move.location_dest_id if move.location_dest_id.usage == 'internal'
                          else move.location_id)
        if not locations:
            return
        quants = Quant.search([
            ('product_id', 'in', moves.product_id.ids),
            ('location_id', 'in', locations.ids),
        ])
        if not quants:
            return
        self.env.add_to_compute(field, quants)
        quants.flush_recordset(['last_count_date'])

    # ------------------------------------------------------------------
    # Step 4 - renumbering
    # ------------------------------------------------------------------
    def _resequence_entries(self, snapshots):
        """Give each backdated entry a number belonging to its new period.

        Clearing the name and letting the sequence mixin assign the next one is
        the route Odoo's own Resequence wizard takes. account.move scopes the
        lookup to the entry's own date, so once the date has been rewritten the
        new number is drawn from the new period rather than the old one.

        Each entry is renumbered inside its own savepoint. The date change is
        the point of the exercise and is already written, so a numbering problem
        is recorded on the log instead of rolling the whole batch back.
        """
        notes = {}
        renamed_ids = set()
        for snapshot in snapshots:
            messages = []
            for account_move in snapshot['account_moves']:
                entry = account_move.sudo()
                if entry.state != 'posted':
                    continue
                if entry.journal_id.restrict_mode_hash_table:
                    messages.append(_(
                        "%(name)s was not renumbered: journal %(journal)s secures "
                        "posted entries with a hash, and renaming one would break "
                        "that chain.",
                        name=entry.name, journal=entry.journal_id.display_name))
                    continue
                if entry._sequence_matches_date():
                    continue
                old_name = entry.name
                try:
                    with self.env.cr.savepoint():
                        entry.name = False
                        entry.flush_recordset(['name'])
                        entry._set_next_sequence()
                        entry.flush_recordset(['name'])
                except Exception as error:
                    entry.invalidate_recordset(['name'])
                    _logger.warning(
                        "Could not renumber journal entry %s: %s", old_name, error)
                    messages.append(_(
                        "%(name)s could not be renumbered (%(error)s). The new "
                        "date was kept.", name=old_name, error=error))
                    continue
                renamed_ids.add(entry.id)
                messages.append(_(
                    "Journal entry %(old)s renumbered to %(new)s, leaving a gap at "
                    "%(old)s in the old period.", old=old_name, new=entry.name))
            if messages:
                notes[snapshot['move'].id] = messages
        return notes, renamed_ids

    # ------------------------------------------------------------------
    # Step 5 - audit trail
    # ------------------------------------------------------------------
    def _period_warning(self, snapshot, target_date, renamed_ids=frozenset()):
        """Journal entry numbers embed a period; flag it when they diverge."""
        old_date = snapshot['old_date']
        if not (snapshot['entries'] and old_date):
            return None
        if (old_date.year, old_date.month) == (target_date.year, target_date.month):
            return None
        pending = [name for entry_id, name in snapshot['entries']
                   if entry_id not in renamed_ids]
        if not pending:
            return None
        return _(
            "Journal entry number %(names)s still carries the sequence of "
            "%(old)s. Tick 'Renumber Journal Entry' to have it reassigned.",
            names=', '.join(pending),
            old=old_date.strftime('%m/%Y'),
        )

    def _create_logs(self, snapshots, target_datetime, target_date,
                     rename_notes, renamed_ids):
        Log = self.env['inventory.backdate.log'].sudo()
        values = []
        for snapshot in snapshots:
            move = snapshot['move']
            notes = [_(
                "Backdated from %(old)s to %(new)s.",
                old=snapshot['old_date'], new=target_datetime,
            )]
            notes.extend(rename_notes.get(move.id, []))
            warning = self._period_warning(snapshot, target_date, renamed_ids)
            if warning:
                notes.append(warning)
            values.append({
                'reference': move.reference or move.name,
                'move_id': move.id,
                'product_id': move.product_id.id,
                'company_id': move.company_id.id,
                'quantity': move.quantity,
                'old_date': snapshot['old_date'],
                'new_date': target_datetime,
                'old_accounting_date': snapshot['old_accounting_date'],
                'new_accounting_date': target_date if self.update_journal_entry else False,
                'account_move_ids': [(6, 0, snapshot['account_moves'].ids)],
                # Read live rather than from the snapshot: after a renumbering
                # these are the new numbers, and the old -> new rename is
                # spelled out in the note.
                'account_move_names': ', '.join(snapshot['account_moves'].mapped('name')),
                'valuation_layer_count': len(snapshot['valuation_layer_ids']),
                'move_line_count': len(snapshot['move_line_ids']),
                'analytic_line_count': len(snapshot['analytic_ids']),
                'note': '\n'.join(notes),
            })
        return Log.create(values)

    def _post_chatter_notes(self, snapshots, target_date):
        for snapshot in snapshots:
            for account_move in snapshot['account_moves']:
                account_move.sudo().message_post(body=_(
                    "Accounting date changed from %(old)s to %(new)s by %(user)s "
                    "through Inventory Adjustment Backdating (stock move %(move)s).",
                    old=snapshot['old_accounting_date'], new=target_date,
                    user=self.env.user.display_name, move=snapshot['move'].reference,
                ))

    def _result_action(self, logs, snapshots, target_date, renamed_ids=frozenset()):
        warnings = [w for w in (self._period_warning(s, target_date, renamed_ids)
                                for s in snapshots) if w]
        message = _("%(count)s inventory adjustment(s) moved to %(date)s.",
                    count=len(snapshots), date=target_date)
        if warnings:
            message = '%s\n\n%s' % (message, '\n'.join(warnings))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Dates updated"),
                'message': message,
                'type': 'warning' if warnings else 'success',
                'sticky': bool(warnings),
                # display_notification hands params.next straight to doAction on
                # the client, so this nested action never passes through the
                # server's clean_action - the step that would normally derive
                # "views" from "view_mode". Without it the web client throws
                # "Cannot read properties of undefined (reading 'map')" in
                # _preprocessAction. Supply what generate_views would have built.
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Backdating History'),
                    'res_model': 'inventory.backdate.log',
                    'views': [(False, 'list'), (False, 'form')],
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', logs.ids)],
                    'target': 'current',
                },
            },
        }


class InventoryBackdateWizardLine(models.TransientModel):
    _name = 'inventory.backdate.wizard.line'
    _description = 'Inventory Adjustment to Backdate'
    _order = 'current_date desc, id desc'

    wizard_id = fields.Many2one(
        'inventory.backdate.wizard', string='Wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Stock Move', required=True, readonly=True)
    selected = fields.Boolean(string='Update', default=True)

    reference = fields.Char(string='Reference', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    location_name = fields.Char(string='Location', readonly=True)
    current_date = fields.Datetime(string='Current Date', readonly=True)
    valuation_layer_count = fields.Integer(string='Valuation Layers', readonly=True)
    account_move_names = fields.Char(string='Journal Entries', readonly=True)
