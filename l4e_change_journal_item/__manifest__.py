# -*- coding: utf-8 -*-
{
    'name': 'Journal Entry Transfer / Bulk Change Journal & Account',
    'version': '1.0',
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
    'author': 'Links4engg',
    'website': 'https://www.links4engg.com',
    'depends': ['account', 'accountant'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/change_journal_items_views.xml',
        'wizard/bulk_transfer_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'application': True,
    'images': ['static/description/index.html'],
}