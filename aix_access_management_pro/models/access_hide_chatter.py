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

class AccessHideChatter(models.Model):
    _name = 'access.hide.chatter'
    _description = 'Chatter Component Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)

    hide_chatter = fields.Boolean(string='Hide Chatter Completely', default=False)
    hide_send_message = fields.Boolean(string='Hide Send Message', default=False)
    hide_log_note = fields.Boolean(string='Hide Log Note', default=False)
    hide_schedule_activity = fields.Boolean(string='Hide Schedule Activity', default=False)
    hide_followers = fields.Boolean(string='Hide Followers', default=False)
    hide_attachments = fields.Boolean(string='Hide Attachments', default=False)
