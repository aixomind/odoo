# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccessButtonTab(models.Model):
    _name = 'access.button.tab'
    _description = 'Button and Notebook Tab Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)
    element_type = fields.Selection([
        ('button', 'Button'),
        ('tab', 'Notebook Tab / Page'),
    ], string='Element Type', required=True, default='button')
    element_identifier = fields.Char(
        string='Element Name / String / XPath',
        required=True,
        help='Technical button name (e.g. action_confirm), string (e.g. Confirm), or tab name.'
    )
    element_description = fields.Char(string='Label / Notes')
    restriction_type = fields.Selection([
        ('hide', 'Hide / Invisible'),
        ('readonly', 'Disable / Read-Only'),
    ], string='Restriction Type', required=True, default='hide')
    domain = fields.Char(string='Conditional Domain', help='Evaluation domain for conditional button/tab access rules.')
