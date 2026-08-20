# -*- coding: utf-8 -*-
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
