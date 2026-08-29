# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    company_enable_stamp = fields.Boolean(
        related='company_id.enable_company_stamp',
        string="Company Stamp Allowed",
        readonly=True
    )
    show_company_stamp = fields.Boolean(
        string="Print Company Stamp",
        default=True,
        help="If checked, the company stamp/seal will be printed on the quotation/order report."
    )
    show_customer_signature = fields.Boolean(
        string="Print Digital Customer Signature",
        default=False,
        help="If checked, you can sign or upload a digital customer signature."
    )
    customer_signature = fields.Binary(
        string="Customer Signature",
        help="Digital signature pad or upload image for customer."
    )

    @api.onchange('company_id')
    def _onchange_company_id_stamp(self):
        if self.company_id:
            self.show_company_stamp = self.company_id.enable_company_stamp
