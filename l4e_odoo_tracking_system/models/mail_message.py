# -*- coding: utf-8 -*-

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

    def message_format(self, *args, **kwargs):
        res = super(MailMessage, self).message_format(*args, **kwargs)
        for message_dict in res:
            message = self.browse(message_dict.get('id'))
            message_dict['useCustomTrackingCard'] = message._l4e_use_custom_tracking_card()
        return res
