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
from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied

class ResUsers(models.Model):
    _inherit = 'res.users'

    access_management_ids = fields.Many2many(
        'access.management',
        'access_management_users_rel',
        'user_id',
        'access_id',
        string='Access Management Rules'
    )

    def _check_credentials(self, *args, **kwargs):
        """Override _check_credentials to enforce Disable User Login access rule."""
        res = super()._check_credentials(*args, **kwargs)
        for user in self:
            if not user._is_superuser() and not user.has_group('base.group_system'):
                rules = self.env['access.management'].sudo()._get_user_rules(user)
                if any(rule.disable_login for rule in rules):
                    raise AccessDenied(_('Your account access has been restricted by System Administrator.'))
        return res

    @classmethod
    def _login(cls, db, login, password, user_agent_env=None):
        """Override _login to enforce Disable User Login access rule."""
        auth_info = super()._login(db, login, password, user_agent_env=user_agent_env)
        if auth_info:
            uid = auth_info.get('uid') if isinstance(auth_info, dict) else auth_info
            if uid:
                from odoo import registry
                with registry(db).cursor() as cr:
                    env = api.Environment(cr, uid, {})
                    user = env['res.users'].browse(uid)
                    if not user._is_superuser() and not user.has_group('base.group_system'):
                        rules = env['access.management'].sudo()._get_user_rules(user)
                        if any(rule.disable_login for rule in rules):
                            raise AccessDenied(_('Your account access has been restricted by System Administrator.'))
        return auth_info
