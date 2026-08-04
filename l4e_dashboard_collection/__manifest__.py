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
    'name': 'All In One dashboard ( CRM , Sales , Finance , Inventory, AMC )',
    'version': '19.0.1.0.1',
    'price': 199,
    'currency': 'USD',
    'category': 'Extra Tools',
    'summary': 'All-in-one Dashboard Collection: Sales, Inventory, Accounting, and AMC',
    'description': """
        This module consolidates four premium interactive dashboards:
        1. CRM Dashboard
        2. Sales Dashboard
        3. Inventory Dashboard
        3. Accounting Financial Dashboard
        4. AMC (Annual Maintenance Contract) Dashboard
        Visibility of each dashboard can be configured under settings, restricted to the system administrator.
    """,
    'author': 'Links4Engg Pvt. Ltd',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'sale_management',
        'stock',
        'stock_account',
        'account',
        'account_accountant',
        'project',
        'hr_payroll',
        'hr_payroll_account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/sale_dashboard_views.xml',
        'views/inventory_dashboard_views.xml',
        'views/financial_dashboard_views.xml',
        'views/amc_dashboard_views.xml',
        'views/crm_sale_views.xml',
                'views/crm_sale_views.xml',
        'views/crm_dashboard_views.xml',
        'views/dashboards_menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l4e_dashboard_collection/static/src/js/theme_bridge.js',
            'l4e_dashboard_collection/static/src/scss/analytics.scss',
            'l4e_dashboard_collection/static/src/scss/charts.scss',
            'l4e_dashboard_collection/static/src/scss/dashboard.scss',
            'l4e_dashboard_collection/static/src/scss/scroll.scss',
            'l4e_dashboard_collection/static/src/scss/summary.scss',
            'l4e_dashboard_collection/static/src/js/crm_dashboard.js',
            'l4e_dashboard_collection/static/src/xml/crm_dashboard.xml',

            'l4e_dashboard_collection/static/src/css/sale_dashboard.css',
            'l4e_dashboard_collection/static/src/js/sale_dashboard.js',
            'l4e_dashboard_collection/static/src/xml/sale_dashboard.xml',

            'l4e_dashboard_collection/static/src/css/inventory_dashboard.css',
            'l4e_dashboard_collection/static/src/js/inventory_dashboard.js',
            'l4e_dashboard_collection/static/src/xml/inventory_dashboard.xml',

            'l4e_dashboard_collection/static/src/scss/financial_dashboard.scss',
            'l4e_dashboard_collection/static/src/js/financial_dashboard.js',
            'l4e_dashboard_collection/static/src/xml/financial_dashboard.xml',

            'l4e_dashboard_collection/static/src/css/amc_dashboard.css',
            'l4e_dashboard_collection/static/src/scss/dark_mode.scss',
            'l4e_dashboard_collection/static/src/js/amc_dashboard.js',
            'l4e_dashboard_collection/static/src/xml/amc_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'images': [
        'static/description/banner.gif',
        'static/description/home_apps.png',
        'static/description/screenshot_settings.png',
        'static/description/screenshot_crm_dashboard.png',
        'static/description/screenshot_sale_dashboard.png',
        'static/description/screenshot_inventory_dashboard.png',
        'static/description/screenshot_financial_dashboard.png',
        'static/description/screenshot_amc_dashboard_kpis.png',
    ],
}

