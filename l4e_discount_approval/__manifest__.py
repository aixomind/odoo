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
{
    'name': 'Discount + Approval (Sales , Purchase , Finance )',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'All-in-one discount governance: Per-salesperson global & line limits, tiered approval workflows, and total amount discounts with auto-distribution for Sales, Purchases, and Invoices.',
    'description': """
Discount Approval & Total Discount Management (Odoo 17)
======================================================

An all-in-one professional discount management and governance system. This module combines advanced, tiered approval workflows for salesperson discount limits with flexible options to apply and auto-distribute total discounts on sales, purchases, and invoices.

Key Highlights:
---------------
* **Multi-Layered Discount Limits**: Define fallback default limits at company settings or specify custom limits per salesperson.
* **Tiered Approval Workflows**: Route discount approval requests to different managers based on the discount percentage (e.g., 0-10% Sales Manager, 10-30% Director, 30%+ VP).
* **Total & Auto-Distributed Discounts**: Apply discounts on the total amount as a percentage or fixed value, and automatically distribute them across all document lines (Sales Orders, Purchase Orders, and Invoices).
* **Automatic Governance**: Blocks order confirmation or invoice posting if the discount exceeds salesperson limits, prompting a pending approval flow.
* **Approval Audit Trails**: Smart button with request counters, email & chatter notifications, and a full audit log (who approved, when, and refusal reasons).
* **Warnings & Banners**: Highlights over-limit lines and shows dynamic info banners on the document view.
""",
    'author': 'Links4Engg Pvt. Ltd',
    'images': [
        'static/description/banner_screenshot.gif',
        'static/description/screenshot1.png',
        'static/description/screenshot2.png',
        'static/description/screenshot3.png',
        'static/description/screenshot4.png',
        'static/description/screenshot5.png',
    ],
    'depends': [
        'sale_management',
        'purchase',
        'account',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/config_parameter_data.xml',
        'views/discount_limit_views.xml',
        'views/discount_tier_views.xml',
        'views/discount_approval_request_views.xml',
        'views/sale_discount_total_res_config_settings_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_discount_total_sale_order_views.xml',
        'views/sale_order_views.xml',
        'views/sale_discount_total_purchase_order_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_discount_total_account_move_views.xml',
        'views/account_move_views.xml',
        'views/account_move_templates.xml',
        'views/sale_order_templates.xml',
        'views/purchase_order_templates.xml',
        'wizard/discount_refuse_wizard_views.xml',
    ],
    # 'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
