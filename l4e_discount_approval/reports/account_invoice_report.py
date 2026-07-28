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


class AccountInvoiceReport(models.Model):
    """This class inherits the model 'account.invoice.report'"""
    _inherit = 'account.invoice.report'

    discount = fields.Float('Discount', readonly=True,
                            help="Specify the discount.")

    def _select(self) -> SQL:
        return SQL("%s, line.discount AS discount", super()._select())
