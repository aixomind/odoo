# -*- coding: utf-8 -*-
{
    'name': 'Custom Reports & Digital Signatures Suite',
    'version': '16.0.1.0.1',
    'category': 'Sales/Sales',
    'summary': 'All-in-One Custom PDF Reports, Color Themes, Company Stamps & Digital Signatures',
    'description': """
        ========================================================================
        Custom Reports & Digital Signatures Suite for Odoo 16
        ========================================================================

        An all-in-one professional PDF reporting suite combining customizable report
        templates with digital signatures and company stamps.

        Key Features:
        -------------
        * Custom Report Templates for Sales Orders / Quotations, Purchase Orders, 
          Customer Invoices / Vendor Bills, and Delivery Slips.
        * Dynamic 3-Color Theme Customizer:
          - Text Color Picker
          - Table Header Color Picker
          - Text Background / Banner Color Picker
          - One-Click Reset to Default Colors
        * Automatic hiding of null / empty fields and labels on reports.
        * Custom Header and Footer banner image uploads per Company.
        * Official Company Stamp / Seal integration with per-document toggle.
        * Interactive Digital Customer & Vendor Signature pads.
        * Clean last-page docked signatures and company stamp layout.
    """,
    'author': 'L4E',
    # 'website': 'https://www.l4e.com',
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'purchase',
        'stock',
    ],
    'data': [
        'l4e_custom_reports/views/paperformat_data.xml',
        'l4e_custom_reports/views/res_company_views.xml',
        'l4e_custom_reports/views/external_layout_template.xml',
        'l4e_custom_reports/views/sale_report_template.xml',
        'l4e_custom_reports/views/purchase_report_template.xml',
        'l4e_custom_reports/views/invoice_report_template.xml',
        'l4e_custom_reports/views/delivery_report_template.xml',
        'l4e_report_signatures/views/paperformat_data.xml',
        'l4e_report_signatures/views/res_company_views.xml',
        'l4e_report_signatures/views/sale_order_views.xml',
        'l4e_report_signatures/views/purchase_order_views.xml',
        'l4e_report_signatures/views/account_move_views.xml',
        'l4e_report_signatures/views/stock_picking_views.xml',
        'l4e_report_signatures/views/report_signature_templates.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
