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


class MailTrackingValue(models.Model):
    _inherit = 'mail.tracking.value'

    def _tracking_value_format_model(self, model):
        formatted_values = super()._tracking_value_format_model(model)
        if not model:
            return formatted_values

        ir_model = self.env['ir.model'].sudo().search([('model', '=', model)], limit=1)
        config = self.env['tracking.config'].sudo().search([('model_id', '=', ir_model.id)], limit=1) if ir_model else False
        use_custom_card = bool(config and config.tracking_enable and not config.remove_tracking)

        for values in formatted_values:
            values['fieldInfo']['useCustomTrackingCard'] = use_custom_card

        return formatted_values
