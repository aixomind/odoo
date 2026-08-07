# -*- coding: utf-8 -*-

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
            values['useCustomTrackingCard'] = use_custom_card

        return formatted_values
