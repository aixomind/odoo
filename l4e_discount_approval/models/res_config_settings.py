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
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l4e_discount_approval_required = fields.Boolean(
        string='Enable Discount Approval Workflow',
        config_parameter='l4e_discount_approval.required',
        help='When enabled, discounts exceeding a salesperson\'s limit require approval.',
    )
    l4e_default_global_limit = fields.Float(
        string='Default Global Discount Limit (%)',
        config_parameter='l4e_discount_approval.default_global_limit',
        digits=(5, 2),
        help='Fallback global discount limit for salespersons without a specific limit record.',
    )
    l4e_default_line_limit = fields.Float(
        string='Default Per-Line Discount Limit (%)',
        config_parameter='l4e_discount_approval.default_line_limit',
        digits=(5, 2),
        help='Fallback per-line discount limit for salespersons without a specific limit record.',
    )
