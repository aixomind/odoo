# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    """This class inherits the model 'account.invoice.report'"""
    _inherit = 'account.invoice.report'

    discount = fields.Float('Discount', readonly=True,
                            help="Specify the discount.")

    def _select(self) -> SQL:
        return SQL("%s, line.discount AS discount", super()._select())
