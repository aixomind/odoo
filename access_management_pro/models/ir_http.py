# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_debug(cls):
        """Extend core debug-mode handling to enforce Access Management Pro's
        'Disable Developer (Debug) Mode' rule.
        """
        super()._handle_debug()
        cls._access_management_enforce_debug_restriction()

    @classmethod
    def _access_management_enforce_debug_restriction(cls):
        if not request or not getattr(request, 'session', None) or not request.session.uid:
            return
        if not request.session.debug:
            return

        try:
            from odoo import api
            uid = request.session.uid
            env = api.Environment(request.cr, uid, request.context or {})
            user = env.user
        except Exception as e:
            _logger.warning("AMP DEBUG CHECK: failed to create env: %s", e)
            return

        if not user or not user.exists():
            return

        if user._is_superuser():
            return

        Access = env['access.management'].sudo()
        rules = Access._get_user_rules(user)
        if any(r.disable_debug_mode for r in rules):
            request.session.debug = ''

    def session_info(self):
        """Inject Access Management rules into session so JS can read them
        synchronously without async RPC calls."""
        res = super().session_info()
        try:
            user = self.env.user
            if user and not user._is_superuser():
                Access = self.env['access.management'].sudo()
                rules = Access._get_user_rules(user)

                if any(r.disable_debug_mode for r in rules):
                    res['debug'] = ''
                res['disable_export'] = any(r.disable_export for r in rules)

                # Build per-model chatter rules dict so JS can read synchronously
                chatter_rules_by_model = {}
                for rule in rules:
                    for hc in rule.hide_chatter_ids:
                        model_name = hc.model_name
                        if not model_name:
                            continue
                        existing = chatter_rules_by_model.get(model_name, {})
                        chatter_rules_by_model[model_name] = {
                            'hide_chatter':           existing.get('hide_chatter', False) or hc.hide_chatter,
                            'hide_send_message':      existing.get('hide_send_message', False) or hc.hide_send_message or hc.hide_chatter,
                            'hide_log_note':          existing.get('hide_log_note', False) or hc.hide_log_note or hc.hide_chatter,
                            'hide_schedule_activity': existing.get('hide_schedule_activity', False) or hc.hide_schedule_activity or hc.hide_chatter,
                            'hide_followers':         existing.get('hide_followers', False) or hc.hide_followers or hc.hide_chatter,
                            'hide_attachments':       existing.get('hide_attachments', False) or hc.hide_attachments or hc.hide_chatter,
                        }
                res['amp_chatter_rules'] = chatter_rules_by_model
            else:
                res['amp_chatter_rules'] = {}
        except Exception as e:
            _logger.warning("AMP session_info error: %s", e)
            res['amp_chatter_rules'] = {}
        return res

