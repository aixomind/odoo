# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2026 Links4Engg Private Limited.
# All Rights Reserved.
#
# This software is proprietary and confidential.
#
# Unauthorized copying, modification, redistribution,
# reverse engineering, decompilation, sublicensing,
# or commercial use of this software is strictly prohibited
# without prior written permission from
# Links4Engg Private Limited.
#
# Licensed under the Odoo Proprietary License v1.0 (OPL-1).
#
# Links4Engg Private Limited
# Website : https://links4engg.com
# Email   : info@links4engg.com
# Phone   : +91 471 3592209 | +91 7306889096
#
##############################################################################
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
