# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    l4e_discount_limit_ids = fields.One2many(
        'l4e.discount.limit', 'user_id', string='Discount Limits',
    )
