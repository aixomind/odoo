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
    'name': 'L4E Tracking System',
    'version': '18.0.1.0.0',
    'category': 'All Modules',
    'summary': 'All Modules to set a Tracking Automatically and store it for Deleted Records / Restore it',
    "description": """
            L4E Smart Chatter Tracking & Dust Bin System:
            1. Smart Chatter Field Tracking:
               - Custom green tracking cards in chatter for all field changes (text, numeric, dates, many2one).
               - Relational Field Diff (One2many / Many2many, e.g. Order Lines): displays only Added (green), Removed (red), and Unchanged counts without repeating full lists.
               - Vivid orange highlighting for empty/blank field changes.
            2. Dust Bin Data (Deleted Record Recovery):
               - Automatically snapshots deleted records for configured models.
               - System Administrator one-click restore functionality to recover deleted data back into original models.
               - Configurable data retention period (Tracking Days) with automatic scheduled cron cleanup.
            3. Centralized Tracking Configuration:
               - Per-model configuration menu to enable/disable custom tracking or remove tracking.
               - Mutually exclusive boolean controls to prevent configuration conflicts.
        """,
    'author': 'Links4Engg Pvt. Ltd',
    "website": 'https://links4engg.com',
    'depends': ['base', 'mail', 'sale_management', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/tracking_config_views.xml',
        'views/dust_bin_data_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l4e_odoo_tracking_system/static/src/js/message_model_patch.js',
            'l4e_odoo_tracking_system/static/src/scss/tracking_chatter.scss',
            'l4e_odoo_tracking_system/static/src/xml/tracking_chatter.xml',
        ],
        'web.assets_web_dark': [
            'l4e_odoo_tracking_system/static/src/scss/tracking_chatter.dark.scss',
        ],
    },
    "images": ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
