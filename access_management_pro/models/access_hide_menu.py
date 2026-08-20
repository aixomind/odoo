# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccessHideMenu(models.Model):
    _name = 'access.hide.menu'
    _description = 'Hide Menu Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    menu_id = fields.Many2one('ir.ui.menu', string='Menu Item', required=True, ondelete='cascade')
