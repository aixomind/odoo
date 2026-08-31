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
    'name': 'Simplify & Advanced Access Management Pro',
    'version': '18.0.1.0.0',
    'category': 'Tools/Administration',
    'summary': 'All-in-one Access Management solution to restrict Menus, Models, Fields, Buttons, Tabs, Views, Chatter, Reports, Export/Import, and Debug Mode.',
    'description': """
Access Management Pro for Odoo 18
=================================
Complete centralized security and access control suite:
- Hide Menus & Sub-menus
- Model CRUD Permissions (Create, Read, Edit, Delete, Archive, Duplicate, Export)
- Field Access Rights (Invisible, Read-only, Required, Conditional)
- Record-Level Security & Domain Filters (Hard/Soft rules)
- Button & Notebook Tab Visibility (Header, Action, Stat buttons, Pages)
- Search Filters & Group By Restrictions
- Chatter Component Controls (Hide Chatter, Send Message, Log Note, Schedule Activity)
- Restrict View Modes (Tree, Form, Kanban, Pivot, Graph, Calendar, etc.)
- Hide Print Reports & Action Menu Items
- Disable Developer (Debug) Mode, Import/Export, and User Logins
- Multi-Company & Role-based Access Evaluation
    """,
    'author': 'Links4Engg Pvt. Ltd',
    'website': 'https://links4engg.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/access_management_views.xml',
        'views/res_users_views.xml',
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l4e_access_management_pro/static/src/js/access_management.js',
            'l4e_access_management_pro/static/src/js/debug_mode_hide.js',
            'l4e_access_management_pro/static/src/xml/access_management.xml',
            'l4e_access_management_pro/static/src/scss/access_management.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
