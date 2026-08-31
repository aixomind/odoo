# -*- coding: utf-8 -*-
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class InventoryPastCount(models.Model):
    _name = 'inventory.past.count'
    _description = 'Past Inventory Count'
    _order = 'counted_date desc, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    counted_date = fields.Date(
        string='Counted Date', required=True, default=fields.Date.context_today,
        help="The past date you are recording a count for.")
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, domain="[('type', 'in', ('consu', 'product'))]",
        help="Storable product to record a count for.")
    product_tmpl_id = fields.Many2one(
        'product.template', related='product_id.product_tmpl_id', string='Product Template')
    counted_qty = fields.Float(
        string='Counted Quantity', required=True, default=0.0, digits='Product Unit of Measure',
        help="Physical quantity you actually counted on the counted date.")
    cost_price = fields.Monetary(
        string='Cost Price (Unit)', currency_field='currency_id',
        help="Optional. Specify a unit cost price to revalue the product as of the counted date.")

    count_basis = fields.Selection(
        [('as_of_date', 'Stock as it was on the counted date'),
         ('current', 'Current stock on hand')],
        string='Count Basis', default='as_of_date', required=True)
    counted_time = fields.Float(
        string='Counted Time', default=9.0)
    location_id = fields.Many2one(
        'stock.location', string='Location', domain="[('usage', '=', 'internal')]")
    lot_id = fields.Many2one(
        'stock.lot', string='Lot/Serial')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    auto_apply = fields.Boolean(
        string='Apply on Import', default=False)

    state = fields.Selection(
        [('draft', 'To Apply'), ('done', 'Applied'), ('failed', 'Failed')],
        string='Status', default='draft', required=True, index=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    valuation_layer_count = fields.Integer(string='Valuation Layers', readonly=True)
    applied_value = fields.Monetary(
        string='Valuation Value', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Currency', readonly=True)
    quantity_before = fields.Float(
        string='Current Stock Before', readonly=True, digits='Product Unit of Measure')
    quantity_at_date = fields.Float(
        string='Stock on Counted Date', readonly=True, digits='Product Unit of Measure')
    difference_qty = fields.Float(
        string='Difference', readonly=True, digits='Product Unit of Measure')
    applied_datetime = fields.Datetime(string='Applied On', readonly=True)
    message = fields.Text(string='Result', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('inventory.past.count') or _('New')
        records = super().create(vals_list)
        records.filtered(lambda record: record.auto_apply)._apply_in_date_order()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'cost_price' in vals:
            for record in self.filtered(lambda r: r.state == 'done' and r.cost_price):
                record._backdate_update_product_cost()
        return res

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_("You cannot delete an applied count row. Reset it to draft first."))
        return super().unlink()

    def action_apply(self):
        return self._apply_in_date_order()

    def _apply_in_date_order(self):
        rows = self.sorted(key=lambda r: (r.counted_date, r.id))
        failed = False
        for row in rows:
            if row.state == 'done':
                continue
            try:
                with self.env.cr.savepoint():
                    row._apply_count()
            except Exception as e:
                failed = True
                _logger.exception("Failed to apply count row %s", row.name)
                row.write({
                    'state': 'failed',
                    'message': str(e),
                })
        if failed:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Some Counts Failed'),
                    'message': _('One or more count rows failed to apply. See the Result column for details.'),
                    'type': 'warning',
                    'sticky': True,
                },
            }
        return True

    def action_reset_to_draft(self):
        for record in self:
            if record.state == 'done' and record.move_id:
                move = record.move_id.sudo()
                targets = move._backdate_collect_targets()
                
                location = record.location_id or record._default_location()
                quant = record._find_or_create_quant(location)
                if quant and move.product_qty:
                    if move.location_dest_id == location:
                        new_qty = quant.quantity - move.product_qty
                    else:
                        new_qty = quant.quantity + move.product_qty
                    quant.sudo().write({'quantity': max(0.0, new_qty)})

                if targets['analytic_lines']:
                    self.env.cr.execute("DELETE FROM account_analytic_line WHERE id IN %s", (tuple(targets['analytic_lines'].ids),))
                
                if targets['account_moves']:
                    self.env.cr.execute("DELETE FROM account_move_line WHERE move_id IN %s", (tuple(targets['account_moves'].ids),))
                    self.env.cr.execute("DELETE FROM account_move WHERE id IN %s", (tuple(targets['account_moves'].ids),))
                
                if targets['valuation_layers']:
                    self.env.cr.execute("DELETE FROM stock_valuation_layer WHERE id IN %s", (tuple(targets['valuation_layers'].ids),))
                
                if move.move_line_ids:
                    self.env.cr.execute("DELETE FROM stock_move_line WHERE id IN %s", (tuple(move.move_line_ids.ids),))
                self.env.cr.execute("DELETE FROM stock_move WHERE id = %s", (move.id,))
                
                self.env.invalidate_all()

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
        for record in self:
            record._backdate_update_product_cost()
        return True

    def _default_location(self):
        warehouse = self.env['stock.warehouse'].sudo().search([
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not warehouse or not warehouse.lot_stock_id:
            raise UserError(_("No warehouse found for company %s.", self.company_id.display_name))
        return warehouse.lot_stock_id

    def _quantity_at_date(self, location, target_datetime):
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('date', '<=', target_datetime),
        ]
        if self.lot_id:
            domain.append(('lot_id', '=', self.lot_id.id))

        moves = self.env['stock.move'].sudo().search(domain)
        qty = 0.0
        for move in moves:
            if move.location_dest_id == location:
                qty += move.product_qty
            elif move.location_id == location:
                qty -= move.product_qty
        return qty

    def _find_or_create_quant(self, location):
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', location.id),
            ('company_id', '=', self.company_id.id),
            ('package_id', '=', False),
            ('owner_id', '=', False),
        ]
        if self.lot_id:
            domain.append(('lot_id', '=', self.lot_id.id))
        else:
            domain.append(('lot_id', '=', False))

        quant = self.env['stock.quant'].sudo().search(domain, limit=1)
        if not quant:
            quant = self.env['stock.quant'].with_context(inventory_mode=True).sudo().create({
                'product_id': self.product_id.id,
                'location_id': location.id,
                'company_id': self.company_id.id,
                'lot_id': self.lot_id.id if self.lot_id else False,
            })
        return quant

    def _apply_count(self):
        self.ensure_one()
        location = self.location_id or self._default_location()
        quant = self._find_or_create_quant(location)
        quantity_before = quant.quantity

        target_date = self.counted_date
        time_hours = self.counted_time or 9.0
        hours = int(time_hours)
        minutes = int((time_hours - hours) * 60)
        target_datetime = fields.Datetime.to_datetime(target_date).replace(
            hour=hours, minute=minutes, second=0, microsecond=0)

        rounding = self.product_id.uom_id.rounding

        if self.count_basis == 'as_of_date':
            quantity_at_date = self._quantity_at_date(location, target_datetime)
            difference = self.counted_qty - quantity_at_date
            inventory_quantity = quantity_before + difference
        else:
            quantity_at_date = quantity_before
            inventory_quantity = self.counted_qty
            difference = inventory_quantity - quantity_before

        if float_is_zero(difference, precision_rounding=rounding):
            applied_val = 0.0
            account_move = False

            if self.cost_price:
                self.env.cr.execute(
                    "SELECT SUM(quantity), SUM(value) FROM stock_valuation_layer "
                    "WHERE product_id = %s AND company_id = %s AND create_date <= %s",
                    (self.product_id.id, self.company_id.id, target_datetime))
                row = self.env.cr.fetchone()
                current_qty = row[0] if row and row[0] is not None else quantity_at_date
                current_val = row[1] if row and row[1] is not None else 0.0

                target_val = (current_qty or self.counted_qty) * self.cost_price
                value_diff = target_val - current_val

                if not float_is_zero(value_diff, precision_rounding=0.01):
                    applied_val = value_diff
                    # 1. Create 0-quantity Valuation Layer
                    svl_vals = {
                        'product_id': self.product_id.id,
                        'company_id': self.company_id.id,
                        'quantity': 0.0,
                        'unit_cost': self.cost_price,
                        'value': value_diff,
                        'description': _("Product Quantity Updated [Accounted on %s]", self.counted_date),
                    }
                    svl = self.env['stock.valuation.layer'].sudo().create(svl_vals)
                    self.env.cr.execute(
                        "UPDATE stock_valuation_layer SET create_date = %s WHERE id = %s",
                        (target_datetime, svl.id))

                    # 2. Create accounting entry if automated valuation is enabled
                    categ = self.product_id.categ_id
                    if hasattr(categ, 'property_valuation') and categ.property_valuation == 'real_time':
                        stock_journal = getattr(categ, 'property_stock_journal', False) or self.env['account.journal'].search([
                            ('company_id', '=', self.company_id.id),
                            ('type', '=', 'general')
                        ], limit=1)
                        acc_valuation = getattr(categ, 'property_stock_valuation_account_id', False)
                        acc_variation = getattr(categ, 'property_stock_account_output_categ_id', False) or getattr(categ, 'property_stock_account_input_categ_id', False) or (stock_journal.default_account_id if stock_journal else False)

                        if stock_journal and acc_valuation and acc_variation:
                            val_amount = abs(value_diff)
                            if value_diff > 0:
                                debit_acc = acc_valuation.id
                                credit_acc = acc_variation.id
                            else:
                                debit_acc = acc_variation.id
                                credit_acc = acc_valuation.id

                            move_vals = {
                                'journal_id': stock_journal.id,
                                'date': self.counted_date,
                                'ref': _("Product Quantity Updated [Accounted on %s]", self.counted_date),
                                'company_id': self.company_id.id,
                                'stock_valuation_layer_ids': [(6, 0, [svl.id])],
                                'line_ids': [
                                    (0, 0, {
                                        'name': self.product_id.display_name,
                                        'product_id': self.product_id.id,
                                        'quantity': 0.0,
                                        'account_id': debit_acc,
                                        'debit': val_amount,
                                        'credit': 0.0,
                                    }),
                                    (0, 0, {
                                        'name': self.product_id.display_name,
                                        'product_id': self.product_id.id,
                                        'quantity': 0.0,
                                        'account_id': credit_acc,
                                        'debit': 0.0,
                                        'credit': val_amount,
                                    }),
                                ]
                            }
                            account_move = self.env['account.move'].sudo().create(move_vals)
                            account_move.action_post()
                            svl.sudo().write({'account_move_id': account_move.id})

            self.write({
                'state': 'done',
                'location_id': location.id,
                'quantity_before': quantity_before,
                'quantity_at_date': quantity_at_date,
                'difference_qty': 0.0,
                'applied_value': applied_val,
                'account_move_id': account_move.id if account_move else False,
                'applied_datetime': fields.Datetime.now(),
                'message': _("Counted %s, and stock already stood at %s on date. Valuation adjusted by %s.", self.counted_qty, quantity_at_date, applied_val) if applied_val else _("Counted %s, and stock already stood at %s on date. Nothing to post.", self.counted_qty, quantity_at_date),
            })
            self._backdate_update_product_cost()
            return

        quant.write({'inventory_quantity': inventory_quantity,
                     'inventory_quantity_set': True})

        self.env.flush_all()
        self.env.cr.execute("SELECT COALESCE(MAX(id), 0) FROM stock_move")
        watermark = self.env.cr.fetchone()[0]

        quant.with_context(force_period_date=self.counted_date)._apply_inventory()

        moves = self.env['stock.move'].sudo().search([
            ('id', '>', watermark),
            ('is_inventory', '=', True),
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
        ])
        if not moves:
            raise UserError(_("Odoo posted no stock move for this count. Nothing was changed."))

        self._backdate_created_records(
            moves, location, target_datetime, quantity_before, quantity_at_date, difference)

    def _backdate_created_records(self, moves, location, target_datetime,
                                  quantity_before, quantity_at_date, difference):
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
            value_note = _("Valued at %s per unit, for a total of %s posted.", self.cost_price, applied_value)
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
            'message': _("Stock stood at %s on date and you counted %s, so a movement of %s was posted.", quantity_at_date, self.counted_qty, difference),
        })
        self._backdate_update_product_cost()

    def _backdate_update_product_cost(self):
        self.ensure_one()
        product = self.product_id.sudo()
        company = self.company_id

        # Total valuation value across all valuation layers
        self.env.cr.execute(
            "SELECT SUM(value) FROM stock_valuation_layer "
            "WHERE product_id = %s AND company_id = %s",
            (product.id, company.id))
        row = self.env.cr.fetchone()
        total_value = row[0] if row and row[0] is not None else 0.0

        # Total physical stock on hand
        on_hand_qty = product.with_company(company).qty_available
        rounding = product.uom_id.rounding or 0.01

        if on_hand_qty and not float_is_zero(on_hand_qty, precision_rounding=rounding):
            new_cost = total_value / on_hand_qty
        elif self.state == 'done' and self.cost_price:
            new_cost = self.cost_price
        else:
            new_cost = 0.0

        product.with_company(company).sudo().with_context(disable_auto_svl=True).write({'standard_price': new_cost})
        if product.product_tmpl_id:
            product.product_tmpl_id.with_company(company).sudo().with_context(disable_auto_svl=True).write({'standard_price': new_cost})
