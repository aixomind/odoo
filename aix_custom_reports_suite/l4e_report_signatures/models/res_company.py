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
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_company_stamp = fields.Boolean(
        string="Enable Company Stamp/Seal",
        default=True,
        help="Master switch to allow printing company stamp on reports across documents."
    )
    company_stamp_image = fields.Binary(
        string="Company Stamp / Seal Image",
        help="Upload or draw the default company stamp or seal image to print on reports."
    )
