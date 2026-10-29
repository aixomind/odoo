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
