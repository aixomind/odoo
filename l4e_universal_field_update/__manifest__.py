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
    'name': 'Universal Field Update',
    'version': '1.0',
    'price': 199,
    'currency': 'USD',
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
* Compatible with Odoo 17 Community and Enterprise editions.
    """,
    'author': 'Links4Engg Pvt. Ltd',
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
