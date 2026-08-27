import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

from . import backdate_common

_logger = logging.getLogger(__name__)


class InventoryPastCount(models.Model):
    """A counted quantity for a past date, applied as a real adjustment.

    One row is one line of the counting sheet. Creating the row - by import or
    by hand - posts the whole adjustment for the counted date: stock move, move
    lines, valuation layer and journal entry, all dated to the day of the count.
    """

    _name = 'inventory.past.count'
    _description = 'Past-Dated Inventory Count'
    _order = 'counted_date desc, id desc'
    _rec_name = 'product_id'

    # --- the counting sheet ---------------------------------------------
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, index=True,
        help="Imports match on the product name, reference or barcode.")
    counted_date = fields.Date(
        string='Counted Date', required=True, index=True,
        help="The day the stock was actually counted. Everything created for "
             "this row is dated to it.")
    counted_qty = fields.Float(
        string='Counted Quantity', required=True,
        digits='Product Unit of Measure',
        help="The quantity found on the shelf, not the difference.")
    cost_price = fields.Float(
        string='Cost Price (Unit)', digits='Product Price',
        help="What this stock actually cost per unit on the counted date. "
             "Left empty, the count is valued at whatever cost Odoo would "
             "normally use for an adjustment - usually the product's current "
             "cost, which is wrong for a historical correction if the cost "
             "has since changed.\n\n"
             "Set it and the valuation layer and journal entry this count "
             "creates are corrected to (movement quantity x this cost), so "
             "the Inventory Valuation report reads the value this stock "
             "actually carried on the counted date.\n\n"
             "Only this count's own layer and entry are corrected. The "
             "product's standard cost / running average is not touched, so "
             "later moves keep whatever cost they already posted at.")
    count_basis = fields.Selection(
        [('as_of_date', 'Stock as it was on the counted date'),
         ('current', 'Current stock on hand')],
        string='Count Basis', default='as_of_date', required=True,
        help="What the counted quantity is compared against.\n\n"
             "'Stock as it was on the counted date' is the historical reading: "
             "the movement posted is the gap between your count and what Odoo "
             "believed was on hand on that day. Everything counted after that "
             "date keeps stacking on top, so today's on-hand shifts by the same "
             "amount.\n\n"
             "'Current stock on hand' compares against today instead, which "
             "makes today's on-hand end up exactly at the counted quantity.")
    counted_time = fields.Float(
        string='Counted Time', default=9.0,
        help="Time of day, in your own timezone, stamped on the stock move and "
             "valuation layer. The journal entry only carries the date.")
    location_id = fields.Many2one(
        'stock.location', string='Location', domain="[('usage', '=', 'internal')]",
        help="Left empty, the warehouse's default stock location is used.")
    lot_id = fields.Many2one(
        'stock.lot', string='Lot/Serial',
        help="Required for products tracked by lot or serial number.")
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    auto_apply = fields.Boolean(
        string='Apply on Import', default=False,
        help="Left ticked, the count is posted as soon as the row is created. "
             "Put 0 in this column to stage rows for review and apply them "
             "later with the Apply button.")

    # --- what came of it -------------------------------------------------
    state = fields.Selection(
        [('draft', 'To Apply'), ('done', 'Applied'), ('failed', 'Failed')],
        string='Status', default='draft', required=True, index=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    valuation_layer_count = fields.Integer(string='Valuation Layers', readonly=True)
    applied_value = fields.Monetary(
        string='Valuation Value', readonly=True, currency_field='currency_id',
        help="Total value posted for this count's movement - the sum of its "
             "valuation layer(s), at the Cost Price above if one was given, "
             "otherwise at whatever cost Odoo used by default.")
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Currency', readonly=True)
    quantity_before = fields.Float(
        string='Current Stock Before', readonly=True, digits='Product Unit of Measure',
        help="On-hand quantity at the moment the row was applied.")
    quantity_at_date = fields.Float(
        string='Stock on Counted Date', readonly=True, digits='Product Unit of Measure',
        help="What Odoo believed was on hand on the counted date, before this row.")
    difference_qty = fields.Float(
        string='Difference', readonly=True, digits='Product Unit of Measure')
    applied_datetime = fields.Datetime(string='Applied On', readonly=True)
    message = fields.Text(string='Result', readonly=True)

    # ------------------------------------------------------------------
    # Creation applies the count
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda record: record.auto_apply)._apply_in_date_order()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'cost_price' in vals:
            for record in self.filtered(lambda r: r.state == 'done' and r.cost_price):
                if record.move_id:
                    record.move_id._backdate_write_value(record.cost_price)
                    targets = record.move_id._backdate_collect_targets()
                    applied_value = sum(targets['valuation_layers'].mapped('value'))
                    vals_to_write = {'applied_value': applied_value}
                    if targets['account_moves']:
                        vals_to_write['account_move_id'] = targets['account_moves'][0].id
                    super(InventoryPastCount, record).write(vals_to_write)
                record._backdate_update_product_cost()
        return res

    def action_apply(self):
        """Apply (or retry) the selected rows."""
        self._apply_in_date_order()
        return True

    def _apply_in_date_order(self):
        """Apply these rows oldest first, whatever order they arrived in.

        Counts are cumulative: each one measures against the stock level the
        earlier ones left behind. A sheet listing 24/07 above 23/07 would
        otherwise compute the 23/07 difference against a baseline that already
        includes the 24/07 movement, and both rows would land wrong.
        """
        for record in self.filtered(lambda r: r.state != 'done').sorted(
                lambda r: (r.counted_date, r.id)):
            record._apply_safely()

    def action_reset_to_draft(self):
        for record in self:
            if record.state == 'done' and record.move_id:
                move = record.move_id.sudo()
                targets = move._backdate_collect_targets()
                
                # Revert stock quant quantity
                if record.difference_qty:
                    location = record.location_id or record._default_location()
                    quant = record._find_or_create_quant(location)
                    if quant:
                        new_qty = quant.quantity - record.difference_qty
                        quant.sudo().write({'quantity': max(0.0, new_qty)})

                # Delete analytic lines
                if targets['analytic_lines']:
                    self.env.cr.execute("DELETE FROM account_analytic_line WHERE id IN %s", (tuple(targets['analytic_lines'].ids),))
                
                # Delete account move lines & account moves
                if targets['account_moves']:
                    self.env.cr.execute("DELETE FROM account_move_line WHERE move_id IN %s", (tuple(targets['account_moves'].ids),))
                    self.env.cr.execute("DELETE FROM account_move WHERE id IN %s", (tuple(targets['account_moves'].ids),))
                
                # Delete valuation layers
                if targets['valuation_layers']:
                    self.env.cr.execute("DELETE FROM stock_valuation_layer WHERE id IN %s", (tuple(targets['valuation_layers'].ids),))
                
                # Delete move lines & stock move
                if move.move_line_ids:
                    self.env.cr.execute("DELETE FROM stock_move_line WHERE id IN %s", (tuple(move.move_line_ids.ids),))
                self.env.cr.execute("DELETE FROM stock_move WHERE id = %s", (move.id,))
                
            record.write({
                'state': 'draft',
                'move_id': False,
                'account_move_id': False,
                'valuation_layer_count': 0,
                'applied_value': 0.0,
                'quantity_before': 0.0,
                'quantity_at_date': 0.0,
                'difference_qty': 0.0,
                'applied_datetime': False,
                'message': False,
            })
            record._backdate_update_product_cost()
        return True
    
    def action_update_cost_price(self):
        """Recompute the product's Cost for the selected rows, on demand.

        For rows applied before the automatic cost update existed, or after
        hand-editing a row's Cost Price - lets the update be (re)triggered
        from the list view without re-applying the count itself. Only rows
        that are Applied and carry a Cost Price are touched; anything else
        is silently skipped and counted in the notification.
        """
        eligible = self.filtered(lambda r: r.state == 'done' and r.cost_price)
        for record in eligible:
            record._backdate_update_product_cost()

        updated_products = len(eligible.mapped('product_id'))
        skipped = len(self) - len(eligible)
        message = _("Cost updated for %(count)s product(s).", count=updated_products)
        if skipped:
            message += ' ' + _(
                "%(count)s row(s) skipped (not Applied, or no Cost Price set).",
                count=skipped)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Update Cost Price'),
                'message': message,
                'type': 'success' if eligible else 'warning',
                'sticky': False,
            },
        }

    def _apply_safely(self):
        """Post the count, keeping the row whatever happens.

        An import runs many rows in one transaction. Without the savepoint a
        single bad line would roll the whole batch back and lose the rows that
        did work, which is exactly the wrong behaviour for a counting sheet.
        The row survives carrying its error so it can be corrected and retried.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._apply_count()
        except Exception as error:
            # The rollback leaves the cache holding values computed from data
            # the database no longer has - quant quantities above all, which the
            # next row measures against. flush=False is the point: flushing here
            # would try to write those rolled-back values back out.
            self.env.invalidate_all(flush=False)
            _logger.warning(
                "Past inventory count for %s on %s failed: %s",
                self.product_id.display_name, self.counted_date, error)
            self.write({'state': 'failed', 'message': str(error)})

    # ------------------------------------------------------------------
    # The actual work
    # ------------------------------------------------------------------
    def _check_count(self):
        self.ensure_one()
        is_storable = getattr(self.product_id, 'is_storable', False) or self.product_id.type == 'product'
        if not is_storable:
            raise UserError(_(
                "%s is not a storable product, so it holds no stock to count.",
                self.product_id.display_name))
        if self.counted_qty < 0:
            raise UserError(_("A counted quantity cannot be negative."))
        if self.cost_price < 0:
            raise UserError(_("A cost price cannot be negative."))
        if self.product_id.tracking in ('lot', 'serial') and not self.lot_id:
            raise UserError(_(
                "%s is tracked by %s, so the count needs a Lot/Serial.",
                self.product_id.display_name, self.product_id.tracking))
        backdate_common.check_lock_dates(self.company_id, self.counted_date)

    def _default_location(self):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', self.company_id.id)], limit=1)
        if not warehouse.lot_stock_id:
            raise UserError(_(
                "No warehouse stock location found for %s. Set the Location "
                "column on the sheet.", self.company_id.display_name))
        return warehouse.lot_stock_id

    def _find_or_create_quant(self, location):
        """The quant this count applies to, without recording anything yet."""
        self.ensure_one()
        Quant = self.env['stock.quant'].with_context(inventory_mode=True).sudo()
        quant = Quant.search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', location.id),
            ('lot_id', '=', self.lot_id.id),
            ('package_id', '=', False),
            ('owner_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if quant:
            return quant
        return Quant.create({
            'product_id': self.product_id.id,
            'location_id': location.id,
            'lot_id': self.lot_id.id or False,
        })

    def _quantity_at_date(self, location, target_datetime):
        """On-hand as Odoo believes it stood on the counted date.

        qty_available with a past ``to_date`` replays the move history back to
        that moment - the same reading the Inventory report gives when you set
        its date selector. Without this the count would be compared against
        today's stock, and a historical sheet would post the wrong difference
        or, when today's figure already matches, nothing at all.
        """
        self.ensure_one()
        context = {'to_date': target_datetime, 'location': location.id}
        if self.lot_id:
            context['lot_id'] = self.lot_id.id
        return self.product_id.with_company(
            self.company_id).with_context(**context).qty_available

    def _apply_count(self):
        self.ensure_one()
        self._check_count()

        location = self.location_id or self._default_location()
        target_datetime = backdate_common.combine_local(
            self.env, self.counted_date, self.counted_time)

        quant = self._find_or_create_quant(location)
        quantity_before = quant.quantity
        rounding = self.product_id.uom_id.rounding

        if self.count_basis == 'as_of_date':
            # Compare against what stock looked like on the counted date, then
            # shift today's figure by the same amount so the movement lands on
            # that date rather than being swallowed by later history.
            quantity_at_date = self._quantity_at_date(location, target_datetime)
            difference = self.counted_qty - quantity_at_date
            inventory_quantity = quantity_before + difference
        else:
            quantity_at_date = quantity_before
            inventory_quantity = self.counted_qty
            difference = inventory_quantity - quantity_before

        if float_is_zero(difference, precision_rounding=rounding):
            self.write({
                'state': 'done',
                'location_id': location.id,
                'quantity_before': quantity_before,
                'quantity_at_date': quantity_at_date,
                'difference_qty': 0.0,
                'applied_datetime': fields.Datetime.now(),
                'message': _(
                    "Counted %(counted)s, and stock already stood at %(basis)s "
                    "on %(date)s. Nothing to post.",
                    counted=self.counted_qty, basis=quantity_at_date,
                    date=self.counted_date),
            })
            return

        quant.write({'inventory_quantity': inventory_quantity,
                     'inventory_quantity_set': True})

        # Watermark the move table so the moves this apply creates can be found
        # again - _apply_inventory returns nothing.
        self.env.flush_all()
        self.env.cr.execute("SELECT COALESCE(MAX(id), 0) FROM stock_move")
        watermark = self.env.cr.fetchone()[0]

        # force_period_date is honoured by stock_account when it builds the
        # entry, so the journal entry is dated to the count from the start and
        # its number is drawn from the right period - no renumbering needed.
        # _apply_inventory is called rather than action_apply_inventory, which
        # returns a conflict/tracking wizard action instead of posting.
        quant.with_context(force_period_date=self.counted_date)._apply_inventory()

        moves = self.env['stock.move'].sudo().search([
            ('id', '>', watermark),
            ('is_inventory', '=', True),
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
        ])
        if not moves:
            raise UserError(_(
                "Odoo posted no stock move for this count. Nothing was changed."))

        self._backdate_created_records(
            moves, location, target_datetime, quantity_before, quantity_at_date, difference)

    def _backdate_created_records(self, moves, location, target_datetime,
                                  quantity_before, quantity_at_date, difference):
        """Move everything Odoo just stamped with today onto the counted date."""
        self.ensure_one()
        self.env.flush_all()
        targets = {move.id: move._backdate_target_ids() for move in moves}
        for move in moves:
            move._backdate_write_dates(target_datetime, self.counted_date, targets[move.id])
        self.env.invalidate_all()

        value_warnings = []
        if self.cost_price:
            self.env.flush_all()
            for move in moves:
                value_warnings += move._backdate_write_value(self.cost_price)
                self.env.invalidate_all()

        account_move_ids = [mid for target in targets.values()
                            for mid in target['account_move_ids']]
        if not account_move_ids:
            account_moves = moves.sudo().stock_valuation_layer_ids.account_move_id | moves.sudo().account_move_ids
            if account_moves:
                account_move_ids = account_moves.ids
        layer_count = sum(len(target['valuation_layer_ids']) for target in targets.values())
        applied_value = sum(moves.sudo().stock_valuation_layer_ids.mapped('value'))
        primary = moves[0]

        value_note = ''
        if self.cost_price:
            value_note = _(
                "\nValued at %(cost)s per unit, as entered, for a total of "
                "%(value)s posted to the valuation layer and journal entry.",
                cost=self.cost_price, value=applied_value)
        if value_warnings:
            value_note += '\n' + '\n'.join(value_warnings)

        self.write({
            'state': 'done',
            'location_id': location.id,
            'move_id': primary.id,
            'account_move_id': account_move_ids[0] if account_move_ids else False,
            'valuation_layer_count': layer_count,
            'applied_value': applied_value,
            'quantity_before': quantity_before,
            'quantity_at_date': quantity_at_date,
            'difference_qty': difference,
            'applied_datetime': fields.Datetime.now(),
            'message': _(
                "Stock stood at %(basis)s on %(date)s and you counted %(qty)s, "
                "so a movement of %(diff)s was posted on that date: %(moves)s "
                "stock move(s), %(layers)s valuation layer(s) and %(entries)s "
                "journal entry(ies), all dated %(date)s.%(value_note)s\n"
                "On-hand was %(before)s before this row and moves to %(after)s, "
                "because a count is a movement and every movement recorded after "
                "%(date)s still applies on top of it.\n"
                "To leave on-hand at %(before)s, add another row counting "
                "%(before)s on the next date that already has stock activity - "
                "give it a late Counted Time such as 23:00 so it lands after "
                "what is already there - or on today if there is none.",
                basis=quantity_at_date, date=self.counted_date, qty=self.counted_qty,
                diff=difference, moves=len(moves), layers=layer_count,
                entries=len(set(account_move_ids)), before=quantity_before,
                after=quantity_before + difference, value_note=value_note,
            ),
        })

        if self.cost_price:
            self._backdate_update_product_cost()

    def _backdate_update_product_cost(self):
        """Update the product's Cost after a count with a Cost Price."""
        self.ensure_one()
        product = self.product_id.sudo()
        costing_method = product.categ_id.property_cost_method

        if self.cost_price:
            new_cost = self.cost_price
        elif costing_method == 'standard':
            new_cost = self.cost_price
        else:
            self.env.cr.execute(
                "SELECT SUM(quantity), SUM(value) FROM stock_valuation_layer "
                "WHERE product_id = %s AND company_id = %s",
                (product.id, self.company_id.id))
            total_qty, total_value = self.env.cr.fetchone()
            rounding = product.uom_id.rounding
            if not total_qty or float_is_zero(total_qty, precision_rounding=rounding):
                new_cost = 0.0
            else:
                new_cost = total_value / total_qty

        product.with_company(self.company_id).sudo().with_context(disable_auto_svl=True).write({'standard_price': new_cost})
        if product.product_tmpl_id:
            product.product_tmpl_id.with_company(self.company_id).sudo().with_context(disable_auto_svl=True).write({'standard_price': new_cost})

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Move'),
            'res_model': 'stock.move',
            'res_id': self.move_id.id,
            'views': [(False, 'form')],
            'view_mode': 'form',
        }

    def action_view_account_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'views': [(False, 'form')],
            'view_mode': 'form',
        }
