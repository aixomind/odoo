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
        """Ensure the client never sees debug=truthy in session_info for a
        restricted user."""
        res = super().session_info()
        try:
            user = self.env.user
            if user and not user._is_superuser():
                Access = self.env['access.management'].sudo()
                rules = Access._get_user_rules(user)
                if any(r.disable_debug_mode for r in rules):
                    res['debug'] = ''
                res['disable_export'] = any(r.disable_export for r in rules)
        except Exception:
            pass
        return res
