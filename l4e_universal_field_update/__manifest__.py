# -*- coding: utf-8 -*-
{
    'name': 'Universal Field Update',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Inspect and bulk edit fields across all installed Odoo models safely with audit logs.',
    'description': """
Universal Field Update
======================
A premium data administration tool to view, explore, and modify data across all models in Odoo with strict manager security and a permanent audit log history.

Key Features:
-------------
* Dynamic field selection with automatic type detection.
* Dynamic record selector widget for relational fields (Many2one).
* Selection choice loading from schema configuration.
* Safe record fetching with a 1,000 record display warning.
* Target record selection pruning.
* Concurrency protection to prevent data overwrites.
* Audit log creation containing record-by-record execution statuses.
* Compatible with Odoo 18 Community and Enterprise editions.
    """,
    'author': 'Links4engg',
    'website': 'https://www.links4engg.com',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/universal_field_update_views.xml',
        'views/field_update_log_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l4e_universal_field_update/static/src/js/dynamic_record_selector.js',
            'l4e_universal_field_update/static/src/xml/dynamic_record_selector.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'images': ['static/description/banner_card.gif'],
}
