# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.export import Export
from odoo.exceptions import AccessError

class AccessManagementController(http.Controller):

    @http.route('/access_management/get_model_rules', type='json', auth="user")
    def get_model_rules(self, model=None):
        """Return computed access rules summary for specified model and current user."""
        user = request.env.user
        if user._is_superuser():
            return {
                'is_admin': True,
                'hide_chatter': False,
                'hide_send_message': False,
                'hide_log_note': False,
                'hide_schedule_activity': False,
                'hide_followers': False,
                'hide_attachments': False,
                'disable_export': False,
                'hidden_filters': [],
            }

        rules = request.env['access.management']._get_user_rules(user)
        if not rules:
            return {
                'is_admin': False,
                'hide_chatter': False,
                'hide_send_message': False,
                'hide_log_note': False,
                'hide_schedule_activity': False,
                'hide_followers': False,
                'hide_attachments': False,
                'disable_export': False,
                'hidden_filters': [],
            }

        disable_export = any(r.disable_export for r in rules)
        
        all_chatter = rules.mapped('hide_chatter_ids')
        if model:
            chatter_rules = all_chatter.filtered(lambda hc: not hc.model_id or hc.model_name == model)
        else:
            chatter_rules = all_chatter

        all_filters = rules.mapped('hide_filters_ids')
        if model:
            filter_rules = all_filters.filtered(lambda hf: not hf.model_id or hf.model_name == model)
        else:
            filter_rules = all_filters

        hidden_filters = list(set(hf.filter_name.strip().lower() for hf in filter_rules if hf.filter_name))

        return {
            'is_admin': False,
            'hide_chatter': any(cr.hide_chatter for cr in chatter_rules),
            'hide_send_message': any(cr.hide_send_message or cr.hide_chatter for cr in chatter_rules),
            'hide_log_note': any(cr.hide_log_note or cr.hide_chatter for cr in chatter_rules),
            'hide_schedule_activity': any(cr.hide_schedule_activity or cr.hide_chatter for cr in chatter_rules),
            'hide_followers': any(cr.hide_followers or cr.hide_chatter for cr in chatter_rules),
            'hide_attachments': any(cr.hide_attachments or cr.hide_chatter for cr in chatter_rules),
            'disable_export': disable_export,
            'hidden_filters': hidden_filters,
        }


class AccessManagementExportController(Export):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        user = request.env.user
        if not user._is_superuser():
            rules = request.env['access.management']._get_user_rules(user)
            if any(r.disable_export for r in rules):
                return []
        return super().formats()

    @http.route('/web/export/xlsx', type='http', auth="user")
    def index(self, data):
        user = request.env.user
        if not user._is_superuser():
            rules = request.env['access.management']._get_user_rules(user)
            if any(r.disable_export for r in rules):
                raise AccessError(_("Export data feature is disabled for your user account."))
        return super().index(data)
