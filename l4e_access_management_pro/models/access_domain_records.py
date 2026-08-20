# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccessDomainRecords(models.Model):
    _name = 'access.domain.records'
    _description = 'Record Level Domain Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)

    domain = fields.Text(string='Domain Filter', required=True, default='[]', help='Domain expression to limit accessible records.')

    perm_read = fields.Boolean(string='Read', default=True)
    perm_write = fields.Boolean(string='Write / Edit', default=True)
    perm_create = fields.Boolean(string='Create', default=True)
    perm_unlink = fields.Boolean(string='Delete', default=True)

    restriction_mode = fields.Selection([
        ('hard', 'Hard Restriction (Strict Filter)'),
        ('soft', 'Soft Restriction (Advisory / Warning)'),
    ], string='Restriction Mode', default='hard', required=True)
