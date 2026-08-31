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

class AccessHideMenu(models.Model):
    _name = 'access.hide.menu'
    _description = 'Hide Menu Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    menu_id = fields.Many2one('ir.ui.menu', string='Menu Item', required=True, ondelete='cascade')
