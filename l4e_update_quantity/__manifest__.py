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
    'name': 'L4E – Lot & Serial Number Manager (New & Existing Quantities)',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Update and assign lot/serial numbers for existing on-hand stock quantity without duplicating stock',
    'description': """
L4E – Lot & Serial Number Manager (New & Existing Quantities)
===========================================================
This module allows warehouse managers and users to assign Lot or Serial numbers to existing
on-hand stock quantities when changing product tracking from 'By Quantity' to 'By Lots' or
'By Unique Serial Number', ensuring existing stock quantities are updated directly without
creating duplicate or extra quantities.

Key Features:
-------------
* Direct in-place quant update without artificial scrap moves.
* Bulk serial auto-generation with custom prefix, count, and zero-padding.
* Batch import of supplier serial lists from Excel (.xlsx, .xls) and CSV files.
* Lot to serial number breakdown for multi-unit batches.
* Real-time balance validation (Available, Assigned, Remaining).
* Full audit trail logged automatically in product chatter.
* Seamless unreservation and re-assignment of open stock moves.
    """,
    'author': 'Links4Engg Pvt. Ltd',
    'website': 'https://links4engg.com',
    'support': 'info@links4engg.com',
    'depends': [
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/update_lot_serial_wizard_views.xml',
        'views/product_views.xml',
    ],
    'images': [
        'static/description/banner.gif',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
