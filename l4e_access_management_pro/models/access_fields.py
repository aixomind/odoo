# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccessFields(models.Model):
    _name = 'access.fields'
    _description = 'Field Level Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id)]"
    )
    field_name = fields.Char(related='field_id.name', string='Field Technical Name', store=True)
    restriction_type = fields.Selection([
        ('invisible', 'Hide / Invisible'),
        ('readonly', 'Read-Only'),
        ('required', 'Required'),
    ], string='Restriction Type', required=True, default='invisible')
    domain = fields.Char(string='Conditional Domain', help='Evaluation domain for conditional field access rules.')
