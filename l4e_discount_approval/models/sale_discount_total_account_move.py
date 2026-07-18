# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountInvoice(models.Model):
    """This class inherits "account.move" model and adds discount_type,
    discount_rate, amount_discount
     """
    _name = "account.move"
    _inherit = "account.move"

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount'), ('line', 'Line-wise')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),
                                 help="Give the discount rate.")
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_compute_amount', readonly=True,
                                      help="Give the amount to be discounted.")
    line_auto_discount = fields.Boolean(
        string='Auto Apply to All Lines',
        default=False,
        store=True,
        help="When enabled, apply a single discount to all invoice lines automatically.",
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

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    @api.depends('discount_type', 'discount_rate', 'invoice_line_ids.discount', 'invoice_line_ids.price_unit', 'invoice_line_ids.quantity')
    def _compute_amount(self):
        super()._compute_amount()
        for move in self:
            if move.discount_type == 'percent':
                discount_totals = 0.0
                for line in move.invoice_line_ids:
                    total_price = line.price_unit * line.quantity
                    discount_totals += total_price - line.price_subtotal
                move.amount_discount = discount_totals
            elif move.discount_type == 'amount':
                move.amount_discount = move.discount_rate
            else:
                move.amount_discount = sum(line.discount_value for line in move.invoice_line_ids)

    @api.onchange('discount_type')
    def _onchange_discount_type_reset(self):
        """Reset auto-line discount fields whenever discount type is changed."""
        self.line_auto_discount = False
        self.line_discount_apply_value = 0.0

    @api.onchange('line_auto_discount', 'line_discount_apply_type', 'line_discount_apply_value')
    def _onchange_line_auto_discount(self):
        """UI feedback: distribute discount to all invoice lines when auto apply is enabled."""
        if self.discount_type != 'line' or not self.line_auto_discount:
            return
        for line in self.invoice_line_ids:
            if self.line_discount_apply_type == 'percent':
                disc_pct = self.line_discount_apply_value
                disc_val = line.price_unit * line.quantity * disc_pct / 100
            else:
                disc_val = self.line_discount_apply_value
                if line.price_unit and line.quantity:
                    disc_pct = (disc_val / (line.price_unit * line.quantity)) * 100
                else:
                    disc_pct = 0.0
            line.discount = disc_pct
            line.discount_value = disc_val
        self._compute_tax_totals()

    @api.onchange('discount_type', 'discount_rate', 'invoice_line_ids')
    def _supply_rate(self):
        """This function calculates supply rates based on change of
        discount_type, discount_rate and invoice_line_ids"""
        for inv in self:
            if inv.discount_type == 'line':
                return
            elif inv.discount_type == 'percent':
                discount_totals = 0
                for line in inv.invoice_line_ids:
                    line.discount = inv.discount_rate
                    total_price = line.price_unit * line.quantity
                    discount_total = total_price - line.price_subtotal
                    discount_totals = discount_totals + discount_total
                    inv.amount_discount = discount_totals
                    line._compute_totals()
            else:
                total = 0.0
                for line in inv.invoice_line_ids:
                    total += (line.quantity * line.price_unit)
                if inv.discount_rate != 0:
                    discount = (inv.discount_rate / total) * 100
                else:
                    discount = inv.discount_rate
                for line in inv.invoice_line_ids:
                    line.discount = discount
                    inv.amount_discount = inv.discount_rate
                    line._compute_totals()
            inv._compute_tax_totals()

    def _apply_line_auto_discount(self):
        """Apply auto discount to all invoice lines server-side on save."""
        for move in self:
            if not move.line_auto_discount or move.discount_type != 'line':
                continue
            for line in move.invoice_line_ids:
                if move.line_discount_apply_type == 'percent':
                    disc_pct = move.line_discount_apply_value
                    disc_val = line.price_unit * line.quantity * disc_pct / 100
                else:
                    disc_val = move.line_discount_apply_value
                    if line.price_unit and line.quantity:
                        disc_pct = (disc_val / (line.price_unit * line.quantity)) * 100
                    else:
                        disc_pct = 0.0
                line.write({'discount': disc_pct, 'discount_value': disc_val})

    def write(self, vals):
        result = super(AccountInvoice, self).write(vals)
        auto_fields = {'line_auto_discount', 'line_discount_apply_type', 'line_discount_apply_value', 'line_ids'}
        if auto_fields.intersection(vals):
            self._apply_line_auto_discount()
        return result

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
        to the supply rate and always return True"""
        self._supply_rate()
        return True


class AccountInvoiceLine(models.Model):
    """This class inherits "account.move.line" model and adds discount field"""
    _name = "account.move.line"
    _inherit = "account.move.line"

    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0,
                            help="Give the discount needed")
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

    @api.depends('price_unit', 'quantity')
    def _compute_l4e_actual_amount(self):
        for line in self:
            line.l4e_actual_amount = line.price_unit * line.quantity

    @api.onchange('discount_value')
    def _onchange_discount_value(self):
        for line in self:
            if line.price_unit and line.quantity:
                line.discount = (line.discount_value / (line.price_unit * line.quantity)) * 100
            else:
                line.discount = 0.0

    @api.onchange('discount')
    def _onchange_discount(self):
        for line in self:
            line.discount_value = line.price_unit * line.quantity * line.discount / 100
