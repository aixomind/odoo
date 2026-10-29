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
    'name': 'Journal Entry Transfer / Bulk Change Journal & Account',
    'version': '16.0.5.0.1',
    'price': 149,
    'currency': 'USD',
    'category': 'Accounting',
    'summary': 'Allows changing the Journal and Account lines of posted invoices/bills via wizard.',
    'description': """
Journal Entry Transfer
======================
This module provides a wizard to easily transfer and bulk update Journals, Accounts, and Analytics for posted invoices and bills.

Key Features:
-------------
* Filter by date ranges, specific partners, invoice numbers, journals, status, and document types.
* Auto-fetch matching invoices as filters change.
* Prune selection list before executing updates.
* Auto-extract and populate old journals, accounts, and analytic accounts.
* Success toast notification on update completion.
    """,
    'author': 'Links4Engg Pvt. Ltd',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/change_journal_items_views.xml',
        'wizard/bulk_transfer_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'application': True,
    'images': ['static/description/banner.gif',]
}
