# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'L4E Sale Update Product',
    'version': '16.0.1.0.0',
    'summary': 'Update product on confirmed sale orders without altering price or quantity',
    'description': """
L4E Sale Update Product (Odoo 16.0)
===================================
* Author: Krishnaraj
* Allows updating the product on confirmed sales orders that have not yet been delivered.
* Preserves order line quantity, unit price, taxes, and discounts untouched.
* Synchronizes open stock moves (delivery orders) and unreserves/re-reserves stock.
* Updates invoice lines linked to the sale order line.
* Accessible via a line-level button or form action menu.
    """,
    'category': 'Sales/Sales',
    'author': 'Links4Engg Pvt. Ltd',
    'website': 'https://links4engg.com',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'sale_stock',
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/update_sale_product_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'images': [
        'static/description/banner_screenshot.gif',
        'static/description/screenshot_1_line_action.png',
        'static/description/screenshot_2_single_wizard.png',
        'static/description/screenshot_3_multi_wizard.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
