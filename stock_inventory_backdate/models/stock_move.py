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
from odoo import _, models
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _backdate_collect_targets(self):
        """Return the records that carry a copy of this move's date.

        Odoo 18 exposes every link as a plain ORM relation on the move, so
        nothing here has to be discovered at runtime:

            stock_valuation_layer_ids  the valuation layers
            account_move_ids           the journal entries, inverse of
                                       account.move.stock_move_id
            analytic_account_line_ids  analytic lines posted for the move

        The layers are still followed to the journal entry as well: a layer
        carries its own account_move_id, and on older data the move-side
        back-reference is not always populated.
        """
        self.ensure_one()
        move = self.sudo()

        layers = getattr(move, 'stock_valuation_layer_ids', self.env['stock.valuation.layer'])
        account_moves = getattr(move, 'account_move_ids', self.env['account.move']) | layers.account_move_id
        account_move_lines = account_moves.line_ids

        analytic_lines = getattr(move, 'analytic_account_line_ids', False) or self.env['account.analytic.line']
        if account_move_lines:
            analytic_lines |= self.env['account.analytic.line'].sudo().search(
                [('move_line_id', 'in', account_move_lines.ids)])

        return {
            'valuation_layers': layers,
            'account_moves': account_moves,
            'account_move_lines': account_move_lines,
            'analytic_lines': analytic_lines,
        }

    def _backdate_target_ids(self):
        """Id-only view of :meth:`_backdate_collect_targets`.

        Ids survive the raw UPDATEs that follow; recordsets read through a cache
        that no longer matches the database once those have run.
        """
        self.ensure_one()
        targets = self._backdate_collect_targets()
        return {
            'move_line_ids': self.move_line_ids.ids,
            'valuation_layer_ids': targets['valuation_layers'].ids,
            'account_move_ids': targets['account_moves'].ids,
            'analytic_ids': targets['analytic_lines'].ids,
        }

    def _backdate_write_dates(self, target_datetime, target_date, targets, options=None):
        """Rewrite this move's date and every record that copied it.

        ``targets`` is a dict of id lists captured before the first UPDATE.
        ``options`` switches individual groups off; everything is rewritten by
        default. The caller owns the surrounding flush and invalidate.

        Direct SQL is used on purpose: the ORM blocks writes on the date of a
        posted journal entry and would re-trigger valuation logic on the move.
        Every statement runs in the caller's transaction.
        """
        self.ensure_one()
        options = options or {}
        cr = self.env.cr

        cr.execute("UPDATE stock_move SET date = %s WHERE id = %s",
                   (target_datetime, self.id))

        move_line_ids = targets.get('move_line_ids') or []
        if options.get('move_lines', True) and move_line_ids:
            cr.execute("UPDATE stock_move_line SET date = %s WHERE id IN %s",
                       (target_datetime, tuple(move_line_ids)))

        layer_ids = targets.get('valuation_layer_ids') or []
        if options.get('valuation', True) and layer_ids:
            # create_date is what the Inventory Valuation report shows as Date.
            cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE id IN %s",
                       (target_datetime, tuple(layer_ids)))

        account_move_ids = targets.get('account_move_ids') or []
        if options.get('journal', True) and account_move_ids:
            cr.execute("UPDATE account_move SET date = %s WHERE id IN %s",
                       (target_date, tuple(account_move_ids)))
            cr.execute("UPDATE account_move_line SET date = %s WHERE move_id IN %s",
                       (target_date, tuple(account_move_ids)))

        analytic_ids = targets.get('analytic_ids') or []
        if options.get('analytic', True) and analytic_ids:
            cr.execute("UPDATE account_analytic_line SET date = %s WHERE id IN %s",
                       (target_date, tuple(analytic_ids)))

    # ------------------------------------------------------------------
    # Value correction (used by the past-count import when the historical
    # cost is known and differs from whatever the product's cost was at the
    # moment Odoo valued the adjustment)
    # ------------------------------------------------------------------
    def _backdate_write_value(self, unit_cost):
        """Correct this move's valuation layer(s) to a known historical cost.

        Only the layer(s) this move created and their own journal entry
        line(s) are corrected. The product's standard_price / running average
        cost is left exactly as Odoo computed it, so later moves keep
        whatever cost they already posted at - this is a correction of the
        historical record, not a re-run of costing from this date forward.

        Each layer's target value is ``layer.quantity * unit_cost``, using
        the layer's own signed quantity so a decrease values the same way a
        decrease already would. Layers at zero quantity (nothing to value)
        are left alone.

        Returns the list of warning strings produced along the way, if any -
        the caller has somewhere to show them, this method doesn't.
        """
        self.ensure_one()
        move = self.sudo()
        cr = self.env.cr
        rounding = move.company_id.currency_id.rounding or 0.01

        layers = move.stock_valuation_layer_ids
        account_moves = self.env['account.move']
        total_delta = 0.0
        for layer in layers:
            if float_is_zero(layer.quantity, precision_rounding=rounding):
                continue
            target_value = layer.quantity * unit_cost
            delta = target_value - layer.value
            if float_is_zero(delta, precision_rounding=rounding):
                continue
            cr.execute(
                "UPDATE stock_valuation_layer SET value = %s, unit_cost = %s WHERE id = %s",
                (target_value, unit_cost, layer.id))
            total_delta += delta
            if layer.account_move_id:
                account_moves |= layer.account_move_id
            elif layer.product_id.with_company(layer.company_id).valuation == 'real_time' and not float_is_zero(target_value, precision_rounding=rounding):
                layer.invalidate_recordset(['value', 'unit_cost'])
                layer._validate_accounting_entries()
                if layer.account_move_id:
                    cr.execute("UPDATE account_move SET date = %s WHERE id = %s", (move.date.date(), layer.account_move_id.id))
                    cr.execute("UPDATE account_move_line SET date = %s WHERE move_id = %s", (move.date.date(), layer.account_move_id.id))
                    account_moves |= layer.account_move_id

        account_moves |= move.account_move_ids
        if not account_moves or float_is_zero(total_delta, precision_rounding=rounding):
            return []
        return move._backdate_adjust_journal_value(account_moves, total_delta, rounding)

    def _backdate_adjust_journal_value(self, account_moves, delta, rounding):
        """Shift a posted valuation entry's two lines by ``delta``, in place.

        A plain inventory-adjustment entry has exactly one line on the
        product's stock valuation account and one offsetting line (Stock
        Interim / Inventory Adjustment) on the other side, with no tax and no
        partner. Only that two-line shape is handled: an entry that doesn't
        match it (a manual entry later added to the same move, for example)
        is left untouched, and a warning is returned so the mismatch surfaces
        on the count's result rather than being silently skipped or guessed at.
        """
        self.ensure_one()
        move = self.sudo()
        accounts = move.product_id.with_company(move.company_id)._get_product_accounts()
        valuation_account = accounts.get('stock_valuation')

        warnings = []
        for account_move in account_moves.sudo():
            lines = account_move.line_ids
            valuation_lines = lines.filtered(lambda l: l.account_id == valuation_account)
            other_lines = lines - valuation_lines
            if len(valuation_lines) != 1 or len(other_lines) != 1:
                warnings.append(_(
                    "Journal entry %(name)s does not have the plain two-line "
                    "shape expected for a stock valuation entry, so its "
                    "value was not corrected - only the quantity/date side "
                    "of this count applied.",
                    name=account_move.name or account_move.id))
                continue
            move._backdate_shift_line_balance(valuation_lines[0], delta, rounding)
            move._backdate_shift_line_balance(other_lines[0], -delta, rounding)
        return warnings

    def _backdate_shift_line_balance(self, line, delta, rounding):
        if float_is_zero(delta, precision_rounding=rounding):
            return
        new_balance = line.balance + delta
        new_debit = new_balance if new_balance > 0 else 0.0
        new_credit = -new_balance if new_balance < 0 else 0.0
        self.env.cr.execute(
            "UPDATE account_move_line "
            "SET balance = %s, debit = %s, credit = %s, amount_currency = %s "
            "WHERE id = %s",
            (new_balance, new_debit, new_credit, new_balance, line.id))
