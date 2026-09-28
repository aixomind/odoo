# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    untracked_qty = fields.Float(
        string='Update Lot/Serial Qty',
        compute='_compute_untracked_qty',
        digits='Product Unit',
        help='Quantity in warehouse that has no lot/serial assigned or needs conversion to unique serial numbers.',
    )

    @api.depends('product_variant_ids.untracked_qty')
    def _compute_untracked_qty(self):
        for tmpl in self:
            tmpl.untracked_qty = sum(tmpl.product_variant_ids.mapped('untracked_qty'))

    def action_update_lot_serial(self):
        self.ensure_one()
        if not self.is_storable:
            raise UserError(_("Tracking and Lot/Serial updates are only applicable to storable products."))
        if self.untracked_qty <= 0 and self.qty_available <= 0:
            raise UserError(_("There is no positive on-hand quantity in the warehouse to update for product '%s'.", self.display_name))

        product = self.product_variant_id if self.product_variant_count == 1 else False
        return {
            'name': _('Update Lot / Serial Number'),
            'type': 'ir.actions.act_window',
            'res_model': 'aix.update.lot.serial.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_id': self.id,
                'default_product_id': product.id if product else False,
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    untracked_qty = fields.Float(
        string='Update Lot/Serial Qty',
        compute='_compute_untracked_qty',
        digits='Product Unit',
        help='Quantity in warehouse that has no lot/serial assigned or needs conversion to unique serial numbers.',
    )

    @api.depends('stock_quant_ids.quantity', 'stock_quant_ids.lot_id', 'stock_quant_ids.location_id', 'tracking')
    def _compute_untracked_qty(self):
        for product in self:
            if not product.is_storable:
                product.untracked_qty = 0.0
                continue

            domain_quant_loc = product._get_domain_locations()[0]

            # 1. Untracked positive stock in warehouse
            untracked_quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('lot_id', '=', False),
                ('quantity', '>', 0),
            ] + domain_quant_loc)
            untracked_amount = sum(untracked_quants.mapped('quantity'))

            # 2. If tracked by serial number, check for stock in lots that needs conversion to serials
            if product.tracking == 'serial':
                lot_quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('lot_id', '!=', False),
                    ('quantity', '>', 0),
                ] + domain_quant_loc)
                # Quants with quantity > 1 are lots (not unique serial numbers)
                improper_serials = lot_quants.filtered(
                    lambda q: float_compare(q.quantity, 1.0, precision_rounding=product.uom_id.rounding) != 0
                )
                if improper_serials:
                    untracked_amount += sum(improper_serials.mapped('quantity'))
                elif untracked_amount == 0 and lot_quants:
                    # If all lot quants have quantity == 1, check if the lots themselves have multiple units
                    lots_with_multi = lot_quants.mapped('lot_id').filtered(lambda l: l.product_qty > 1)
                    if lots_with_multi:
                        untracked_amount += sum(lot_quants.filtered(lambda q: q.lot_id in lots_with_multi).mapped('quantity'))
                    else:
                        # Allow re-assigning any lot stock to serials
                        untracked_amount = sum(lot_quants.mapped('quantity'))

            product.untracked_qty = untracked_amount

    def action_update_lot_serial(self):
        self.ensure_one()
        if not self.is_storable:
            raise UserError(_("Tracking and Lot/Serial updates are only applicable to storable products."))
        if self.untracked_qty <= 0 and self.qty_available <= 0:
            raise UserError(_("There is no positive on-hand quantity in the warehouse to update for product '%s'.", self.display_name))

        return {
            'name': _('Update Lot / Serial Number'),
            'type': 'ir.actions.act_window',
            'res_model': 'aix.update.lot.serial.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_id': self.product_tmpl_id.id,
                'default_product_id': self.id,
            },
        }
