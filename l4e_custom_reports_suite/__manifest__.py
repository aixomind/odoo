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
    "name": "Custom Reports & Digital Signatures Suite",
    "version": "16.0.1.0.1",
    "category": "Sales/Sales",
    "summary": "All-in-One Custom PDF Reports, Color Themes, Company Stamps & Digital Signatures",
    "description": """
        Custom Reports & Digital Signatures Suite for Odoo:
        ====================================================
        An all-in-one professional PDF reporting architecture combining customizable report
        templates with digital signatures and company stamps.

        1. Custom PDF Report Templates:
           - Professional layout for Sales Orders / Quotations, Purchase Orders, 
             Customer Invoices / Vendor Bills, and Delivery Slips.
           - High-resolution Company Header & Footer banner images (1024x122 px).
        2. Dynamic 3-Color Theme Customizer:
           - Interactive pickers for Report Text Color, Table Header Color, and Banner Background Color.
           - One-Click Reset to Default Colors button.
        3. Smart Null / Empty Field Auto-Hiding:
           - Automatically detects and hides blank/empty fields and labels to keep reports compact and clean.
        4. Official Company Stamp / Seal:
           - Master company stamp configuration with per-document print toggle.
        5. Interactive Digital Signatures:
           - Built-in touch/stylus customer and vendor signature pads docked cleanly on the last page.
    """,
    "author": "Links4Engg Private Limited",
    "website": "https://links4engg.com",
    "depends": [
        "base",
        "web",
        "sale",
        "account",
        "purchase",
        "stock",
    ],
    "data": [
        "l4e_custom_reports/views/paperformat_data.xml",
        "l4e_custom_reports/views/res_company_views.xml",
        "l4e_custom_reports/views/external_layout_template.xml",
        "l4e_custom_reports/views/sale_report_template.xml",
        "l4e_custom_reports/views/purchase_report_template.xml",
        "l4e_custom_reports/views/invoice_report_template.xml",
        "l4e_custom_reports/views/delivery_report_template.xml",
        "l4e_report_signatures/views/paperformat_data.xml",
        "l4e_report_signatures/views/res_company_views.xml",
        "l4e_report_signatures/views/sale_order_views.xml",
        "l4e_report_signatures/views/purchase_order_views.xml",
        "l4e_report_signatures/views/account_move_views.xml",
        "l4e_report_signatures/views/stock_picking_views.xml",
        "l4e_report_signatures/views/report_signature_templates.xml",
    ],
    "images": ["static/description/banner.gif"],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "OPL-1",
}
