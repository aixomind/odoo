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
from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _l4e_use_custom_tracking_card(self):
        self.ensure_one()
        if not self.model:
            return False

        ir_model = self.env['ir.model'].sudo().search([('model', '=', self.model)], limit=1)
        config = self.env['tracking.config'].sudo().search([('model_id', '=', ir_model.id)], limit=1) if ir_model else False
        return bool(config and config.tracking_enable and not config.remove_tracking)

    def message_format(self):
        res = super(MailMessage, self).message_format()
        for message_dict in res:
            message = self.browse(message_dict.get('id'))
            message_dict['useCustomTrackingCard'] = message._l4e_use_custom_tracking_card()
        return res
