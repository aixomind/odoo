# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccessHideFilters(models.Model):
    _name = 'access.hide.filters'
    _description = 'Search Filter and Group By Restrictions'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)
    filter_name = fields.Char(string='Filter / Group By / Search Panel Name', required=True, help='Name, string, or domain of the filter to hide.')
    filter_type = fields.Selection([
        ('filter', 'Filter Option'),
        ('groupby', 'Group By Option'),
        ('search_panel', 'Search Panel Section/Item'),
    ], string='Type', default='filter', required=True)
