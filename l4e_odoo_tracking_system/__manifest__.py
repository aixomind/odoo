{
    'name': 'L4E Tracking System',
    'version': '17.0.1.0.0',
    'category': 'All Modules',
    'summary': 'All Modules to set a Tracking Automatically and store it for Deleted Records / Restore it',
    'description': """
             Configuration for L4E Tracking System & Dust Bin Data
    """,
    'author': 'Harishbalaji',
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
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
