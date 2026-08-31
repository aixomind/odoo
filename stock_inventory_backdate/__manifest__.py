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
    'name': 'Inventory Adjustment Backdating',
    'version': '16.0.1.5.0',
    'category': 'Inventory/Inventory',
    'summary': 'Move a validated inventory adjustment to a past date, together with its '
               'stock moves and journal entries',
    'description': """
Inventory Adjustment Backdating & Historical Counts
===================================================
Validating an inventory adjustment stamps "now" on several records at once:

    stock.move.date
    stock.move.line.date
    account.move.date  ->  account.move.line.date  ->  account.analytic.line.date

Odoo offers no supported way to correct that date afterwards, so an adjustment
entered today can never be reported in the period it actually belongs to.

This module adds:
1. Bulk Backdate Wizard: Filter validated adjustments by date range, product, or
   location, and rewrite every linked record to a chosen past date in a single atomic
   transaction with full audit logging.
2. Past Inventory Counts: Import historical counting sheets priced at historical
   purchase cost, posted and valued directly in the historical period with zero sequence gaps.
3. Complete Audit Trail: Read-only history tracking of all date modifications.

This is the Odoo 16 edition. Odoo 16 removed stock.valuation.layer and moved
the valuation onto stock.move itself.
""",
    'author': 'Links4Engg Pvt. Ltd',
    'website': 'https://www.links4engg.com/',
    'license': 'LGPL-3',
    'depends': ['stock_account'],
    'data': [
        'security/backdate_security.xml',
        'security/ir.model.access.csv',
        'views/inventory_backdate_log_views.xml',
        'views/inventory_past_count_views.xml',
        'wizard/inventory_backdate_wizard_views.xml',
        'views/menu.xml',
    ],
    'images': [
        'static/description/banner.gif',
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
