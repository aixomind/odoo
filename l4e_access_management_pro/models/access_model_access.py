# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccessModelAccess(models.Model):
    _name = 'access.model.access'
    _description = 'Model Level Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)

    perm_read = fields.Boolean(string='Read', default=True)
    perm_create = fields.Boolean(string='Create', default=True)
    perm_write = fields.Boolean(string='Write / Edit', default=True)
    perm_unlink = fields.Boolean(string='Delete', default=True)
    perm_archive = fields.Boolean(string='Archive / Unarchive', default=True)
    perm_duplicate = fields.Boolean(string='Duplicate', default=True)
    perm_export = fields.Boolean(string='Export Data', default=True)
