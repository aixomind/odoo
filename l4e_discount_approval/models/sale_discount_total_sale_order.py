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
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    """Inherit 'sale.order' model and add fields needed"""
    _inherit = "sale.order"
    # margin_auto_percent = fields.Float(string="Auto Margin %")
    margin_auto_value = fields.Monetary(
        string='Margin Value',
        store=True,
        help="Expected margin value after auto discount."
    )

    margin_auto_percent = fields.Float(string="Margin Percent %")

    @api.onchange('margin_auto_percent')
    def _onchange_margin_auto_percent(self):
        for line in self.order_line:
            # The cost price field on sale.order.line is 'purchase_price'
            cost_price = getattr(line, 'purchase_price', 0.0)
            if cost_price:
                # margin_auto_percent is plain float (no percentage widget)
                # so divide by 100 to assign to margin_percent
                margin_percent = self.margin_auto_percent / 100
                margin_value = cost_price * margin_percent
                line.price_unit = cost_price + margin_value
                if hasattr(line, 'margin_percent'):
                    line.margin_percent = margin_percent
                if hasattr(line, 'margin'):
                    line.margin = margin_value

    @api.onchange('margin_auto_value')
    def _onchange_margin_auto_value(self):
        for line in self.order_line:
            cost_price = getattr(line, 'purchase_price', 0.0)
            if cost_price:
                margin_value = self.margin_auto_value
                line.price_unit = cost_price + margin_value
                margin_percent = margin_value / cost_price if cost_price else 0.0
                if hasattr(line, 'margin_percent'):
                    line.margin_percent = margin_percent
                if hasattr(line, 'margin'):
                    line.margin = margin_value

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the SO."""
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (
                                           line.product_uom_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax,
            })

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount'), ('line', 'Line-wise')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),
                                 help="Give the discount rate.")
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_amount_all', readonly=True,
                                      help="Give the amount to be discounted.")
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True,
                                     readonly=True, compute='_amount_all',
                                     help="Untaxed amount displayed.")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True,
                                 compute='_amount_all',
                                 help="Taxes of product.")
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
                                   compute='_amount_all',
                                   help="Total amount provided.")
    margin_test = fields.Float(string="Margin", compute='_compute_margin_test',)
    line_auto_discount = fields.Boolean(
        string='Auto Apply to All Lines',
        default=False,
        store=True,
        help="When enabled, apply a single discount to all order lines automatically."
    )
    line_discount_apply_type = fields.Selection(
        [('percent', 'Discount %'), ('amount', 'Discount Amount')],
        string='Apply By',
        default='percent',
        store=True,
        help="Choose whether to apply discount as a percentage or a fixed amount."
    )
    line_discount_apply_value = fields.Float(
        string='Discount Value',
        digits=(16, 2),
        store=True,
        help="Enter the discount value to apply to all lines."
    )

    @api.depends('amount_untaxed','amount_tax','amount_total')
    def _compute_margin_test(self):
        # Compute logic for margin if sale_margin is installed
        if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'sale_margin'), ('state', '=', 'installed')]):
            # If sale_margin is installed, calculate margin
            for record in self:
                record.margin_test = record.margin
        else:
            for record in self:
                record.margin_test = False

    @api.onchange('discount_type')
    def _onchange_discount_type_reset(self):
        """Reset auto-line discount fields whenever discount type is changed."""
        self.line_auto_discount = False
        self.line_discount_apply_value = 0.0

    @api.onchange('line_auto_discount', 'line_discount_apply_type', 'line_discount_apply_value')
    def _onchange_line_auto_discount(self):
        """When auto apply is enabled, distribute the single discount to all lines.
        Both discount % and discount_value are set explicitly because child-level
        onchanges (_onchange_discount / _onchange_discount_value) do not fire
        automatically when modified from a parent onchange."""
        if self.discount_type != 'line' or not self.line_auto_discount:
            return
        for line in self.order_line:
            if self.line_discount_apply_type == 'percent':
                line.discount = self.line_discount_apply_value
                line.discount_value = (
                    line.price_unit * line.product_uom_qty * self.line_discount_apply_value / 100
                )
            else:
                line.discount_value = self.line_discount_apply_value
                if line.price_unit and line.product_uom_qty:
                    line.discount = (
                        self.line_discount_apply_value / (line.price_unit * line.product_uom_qty)
                    ) * 100
                else:
                    line.discount = 0.0

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        """This function calculates supply rates based on change of
        discount_type, discount_rate and invoice_line_ids"""
        for order in self:
            if order.discount_type == 'line':
                return
            elif order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = 0.0
                for line in order.order_line:
                    total += round((line.product_uom_qty * line.price_unit))
                if order.discount_rate != 0:
                    discount = (
                                           order.discount_rate / total) * 100 if total > 0 else 0
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount
                    new_sub_price = (line.price_unit * (discount / 100))
                    line.total_discount = line.price_unit - new_sub_price

    def _apply_line_auto_discount(self):
        """Apply the auto discount to all order lines. Called on write/create
        so that line values are always saved correctly regardless of client
        onchange tracking."""
        for order in self:
            if not order.line_auto_discount or order.discount_type != 'line':
                continue
            for line in order.order_line:
                if order.line_discount_apply_type == 'percent':
                    disc_pct = order.line_discount_apply_value
                    disc_val = line.price_unit * line.product_uom_qty * disc_pct / 100
                else:
                    disc_val = order.line_discount_apply_value
                    if line.price_unit and line.product_uom_qty:
                        disc_pct = (disc_val / (line.price_unit * line.product_uom_qty)) * 100
                    else:
                        disc_pct = 0.0
                line.write({'discount': disc_pct, 'discount_value': disc_val})

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        auto_fields = {'line_auto_discount', 'line_discount_apply_type', 'line_discount_apply_value', 'order_line'}
        if auto_fields.intersection(vals):
            self._apply_line_auto_discount()
        return result

    def _prepare_invoice(self, ):
        """Super sale order class and update with fields"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
            'amount_discount': self.amount_discount,
        })
        return invoice_vals

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
          to the supply rate and always return True"""
        self.supply_rate()
        return True


