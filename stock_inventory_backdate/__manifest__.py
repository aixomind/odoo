{
    'name': 'Inventory Adjustment Backdating',
    'version': '18.0.1.5.0',
    'category': 'Inventory/Inventory',
    'summary': 'Move a validated inventory adjustment to a past date, together with its '
               'stock moves, valuation layers and journal entries',
    'description': """
Inventory Adjustment Backdating
===============================
Validating an inventory adjustment stamps "now" on several records at once:

    stock.move.date
    stock.move.line.date
    stock.valuation.layer.create_date
    account.move.date  ->  account.move.line.date  ->  account.analytic.line.date

Odoo offers no supported way to correct that date afterwards, so an adjustment
entered today can never be reported in the period it actually belongs to.

This module adds a wizard that lets a user filter the adjustments validated in
a given date range, tick the ones to correct, and rewrite every linked record
to a chosen past date in a single transaction. Each change is written to a
history model (old date, new date, user, timestamp) and, optionally, to the
chatter of the affected journal entries.

Because the ORM refuses these writes on posted entries, the updates are issued
as direct SQL inside the request transaction - they either all land or all roll
back. Access is restricted to a dedicated security group, and company lock
dates are enforced unless an administrator explicitly overrides them.

This is the Odoo 18 edition. Odoo 19 removed stock.valuation.layer and moved
the valuation onto stock.move itself, so it needs the separate 19.0 build.
""",
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['stock_account'],
    'images': ['static/description/banner.png'],
    'data': [
        'security/backdate_security.xml',
        'security/ir.model.access.csv',
        'views/inventory_backdate_log_views.xml',
        'views/inventory_past_count_views.xml',
        'wizard/inventory_backdate_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}
