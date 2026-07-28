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
from odoo import fields, models
from odoo.tools import SQL


class DiscountSaleReport(models.Model):
    """This class inherits 'sale.report' and adds field discount"""
    _inherit = 'sale.report'

    discount = fields.Float('Discount', readonly=True,
                            help="Specify the discount amount.")

    def _select(self) -> SQL:
        """It extends the behavior of a method in the class by adding a
            new column, discount, to the SQL query. This new column represents
            the total discount for sales transactions, calculated based on
            various factors and values related to the sale. """
        return SQL(
            "%s, sum(l.product_uom_qty / u.factor * u2.factor * cr.rate * l.price_unit * l.discount / 100.0) as discount",
            super()._select())
