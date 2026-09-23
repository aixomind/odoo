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
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    company_enable_stamp = fields.Boolean(
        related='company_id.enable_company_stamp',
        string="Company Stamp Allowed",
        readonly=True
    )
    show_company_stamp = fields.Boolean(
        string="Print Company Stamp",
        default=True,
        help="If checked, the company stamp/seal will be printed on the invoice/bill report."
    )
    show_customer_signature = fields.Boolean(
        string="Print Digital Customer Signature",
        default=False,
        help="If checked, you can sign or upload a digital signature."
    )
    customer_signature = fields.Binary(
        string="Customer Signature",
        help="Digital signature pad or upload image."
    )

    @api.onchange('company_id')
    def _onchange_company_id_stamp(self):
        if self.company_id:
            self.show_company_stamp = self.company_id.enable_company_stamp
