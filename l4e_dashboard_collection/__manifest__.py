# -*- coding: utf-8 -*-
{
    'name': 'All In One dashboard ( Sales , Finance , Inventory, AMC )',
    'version': '19.0.1.0.1',
    'category': 'Extra Tools',
    'summary': 'All-in-one Dashboard Collection: Sales, Inventory, Accounting, and AMC',
    'description': """
        This module consolidates four premium interactive dashboards:
        1. Sales Dashboard
        2. Inventory Dashboard
        3. Accounting Financial Dashboard
        4. AMC (Annual Maintenance Contract) Dashboard
        Visibility of each dashboard can be configured under settings, restricted to the system administrator.
    """,
    'author': 'Krishnaraj',
    'license': 'LGPL-3',
    'depends': [
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
        'views/dashboards_menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
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
        'static/description/screenshot_sale_dashboard.png',
        'static/description/screenshot_inventory_dashboard.png',
        'static/description/screenshot_financial_dashboard.png',
        'static/description/screenshot_amc_dashboard_kpis.png',
    ],
}

