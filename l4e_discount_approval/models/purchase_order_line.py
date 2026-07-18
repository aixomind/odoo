# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    """Inherit 'purchase.order.line' to add discount fields."""
    _inherit = 'purchase.order.line'

    discount = fields.Float(
        string='Discount (%)',
        digits=(16, 2),
        default=0.0,
        help="Discount percentage applied on this line.",
    )
    discount_value = fields.Monetary(
        string='Disc Value',
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Fixed discount amount on this line. Auto-converts to/from Disc %.",
    )

    l4e_actual_amount = fields.Monetary(
        string='Actual Amount',
        compute='_compute_l4e_actual_amount',
        currency_field='currency_id',
        help="Original amount before discount (Unit Price × Quantity).",
    )

    @api.depends('price_unit', 'product_qty')
    def _compute_l4e_actual_amount(self):
        for line in self:
            line.l4e_actual_amount = line.price_unit * line.product_qty

    @api.onchange('discount_value')
    def _onchange_discount_value(self):
        for line in self:
            if line.price_unit and line.product_qty:
                line.discount = (line.discount_value / (line.price_unit * line.product_qty)) * 100
            else:
                line.discount = 0.0

    @api.onchange('discount')
    def _onchange_discount(self):
        for line in self:
            line.discount_value = line.price_unit * line.product_qty * line.discount / 100

    def _convert_to_tax_base_line_dict(self):
        """Include discount so tax computation respects the discount."""
        result = super()._convert_to_tax_base_line_dict()
        result['discount'] = self.discount
        return result
