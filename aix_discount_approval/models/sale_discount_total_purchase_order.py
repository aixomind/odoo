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

class PurchaseOrder(models.Model):
    """Inherit 'purchase.order' to add discount fields."""
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount'), ('line', 'Line-wise')],
        string='Discount Type',
        default='percent',
        help="Type of discount applied on total.",
    )
    discount_rate = fields.Float(
        string='Discount Rate',
        digits=(16, 2),
        help="Discount rate to apply on all lines.",
    )
    amount_discount = fields.Monetary(
        string='Discount',
        store=True,
        compute='_compute_amounts',
        readonly=True,
        help="Total discount amount.",
    )
    line_auto_discount = fields.Boolean(
        string='Auto Apply to All Lines',
        default=False,
        store=True,
        help="When enabled, apply a single discount to all order lines automatically.",
    )
    line_discount_apply_type = fields.Selection(
        [('percent', 'Discount %'), ('amount', 'Discount Amount')],
        string='Apply By',
        default='percent',
        store=True,
        help="Choose whether to apply discount as a percentage or a fixed amount.",
    )
    line_discount_apply_value = fields.Float(
        string='Discount Value',
        digits=(16, 2),
        store=True,
        help="Enter the discount value to apply to all lines.",
    )

    @api.depends('order_line.price_total', 'order_line.price_subtotal',
                 'order_line.price_unit', 'order_line.product_qty',
                 'order_line.discount')
    def _compute_amounts(self):
        """Override to include amount_discount in totals."""
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (
                    line.product_qty * line.price_unit * line.discount
                ) / 100
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_discount = amount_discount
            order.amount_total = amount_untaxed + amount_tax

    @api.onchange('discount_type')
    def _onchange_discount_type_reset(self):
        """Reset auto-line discount fields whenever discount type is changed."""
        self.line_auto_discount = False
        self.line_discount_apply_value = 0.0

    @api.onchange('line_auto_discount', 'line_discount_apply_type', 'line_discount_apply_value')
    def _onchange_line_auto_discount(self):
        """UI feedback: distribute discount to all lines when auto apply is enabled."""
        if self.discount_type != 'line' or not self.line_auto_discount:
            return
        for line in self.order_line:
            if self.line_discount_apply_type == 'percent':
                disc_pct = self.line_discount_apply_value
                disc_val = line.price_unit * line.product_qty * disc_pct / 100
            else:
                disc_val = self.line_discount_apply_value
                if line.price_unit and line.product_qty:
                    disc_pct = (disc_val / (line.price_unit * line.product_qty)) * 100
                else:
                    disc_pct = 0.0
            line.discount = disc_pct
            line.discount_value = disc_val

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def _supply_rate(self):
        """Apply discount rate to all purchase order lines."""
        for order in self:
            if order.discount_type == 'line':
                return
            elif order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = sum(
                    line.product_qty * line.price_unit
                    for line in order.order_line
                )
                discount = (
                    (order.discount_rate / total) * 100
                    if total and order.discount_rate
                    else 0.0
                )
                for line in order.order_line:
                    line.discount = discount

    def _apply_line_auto_discount(self):
        """Apply auto discount to all order lines server-side on save."""
        for order in self:
            if not order.line_auto_discount or order.discount_type != 'line':
                continue
            for line in order.order_line:
                if order.line_discount_apply_type == 'percent':
                    disc_pct = order.line_discount_apply_value
                    disc_val = line.price_unit * line.product_qty * disc_pct / 100
                else:
                    disc_val = order.line_discount_apply_value
                    if line.price_unit and line.product_qty:
                        disc_pct = (disc_val / (line.price_unit * line.product_qty)) * 100
                    else:
                        disc_pct = 0.0
                line.write({'discount': disc_pct, 'discount_value': disc_val})

    def write(self, vals):
        result = super(PurchaseOrder, self).write(vals)
        auto_fields = {'line_auto_discount', 'line_discount_apply_type', 'line_discount_apply_value', 'order_line'}
        if auto_fields.intersection(vals):
            self._apply_line_auto_discount()
        return result

    def button_dummy(self):
        """Recompute discount rates."""
        self._supply_rate()
        return True

    def _prepare_invoice(self):
        """Pass discount fields to the vendor bill."""
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
            'amount_discount': self.amount_discount,
        })
        return invoice_vals

    def _creation_message(self):
        """ Override the default creation message for Chatter to show 'RFQ created'
            if it's in draft/sent state. """
        self.ensure_one()
        if self.state in ['draft', 'sent']:
            return _('RFQ created')
        return super(PurchaseOrder, self)._creation_message()
