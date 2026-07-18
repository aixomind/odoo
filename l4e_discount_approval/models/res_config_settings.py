# -*- coding: utf-8 -*-
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
