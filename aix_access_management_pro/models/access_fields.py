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
