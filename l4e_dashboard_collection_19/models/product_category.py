# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    show_in_dashboard = fields.Boolean(
        string='Show in Dashboard',
        default=True,
        help="If checked, products in this category and their stock data will be included in the Inventory Dashboard."
    )
