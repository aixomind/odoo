# -*- coding: utf-8 -*-
{
    'name': 'L4E Custom Approval',
    'version': '19.0.5.0.0',
    'category': 'Approvals',
    'summary': 'Dynamic Approval Engine — any model, any field, any condition, user-configured',
    'description': """
L4E Custom Approval (v5 — Odoo 19)
====================================

Pure Dynamic Approval Engine — no PO/discount features (moved to separate modules).

Features:
* Configure approval rules for ANY Odoo model from the UI — zero code
* Trigger on any field change (state = sale, purchase, posted, done...)
* Conditions: any field comparison (=, !=, >, <, >=, <=, in, not in, set, not set)
* Approvers: Specific User | User Group | Field on Record (dynamic per-record)
* Approval modes: Any / All / Sequential (level-by-level)
* DM + Email notifications with configurable message templates
* Extra notification users per rule (on request + on decision)
* Adding a new model: 2 lines of code

Models covered out-of-the-box:
  Sale Order, Purchase Order, Invoice / Journal Entry
    """,
    'author': 'Links4engg',
    'depends': [
        'sale_management',
        'purchase',
        'account',
        'crm',
        'mail',
        'stock'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/approval_rule_views.xml',
        'views/approval_record_request_views.xml',
        'views/custom_raise_query_views.xml',
        'views/sale_order_views.xml',
    ],
    'images': [
        'static/description/banner_screenshot.gif',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
