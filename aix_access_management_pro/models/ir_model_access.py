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
from odoo import models, api, _
from odoo.exceptions import AccessError

class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    def check(self, model, mode='read', raise_exception=True):
        """Override ir.model.access check to enforce Access Management Pro model-level rules."""
        res = super().check(model, mode=mode, raise_exception=False)

        if self.env.context.get('access_management_skip') or self.env.su:
            return res

        user = self.env.user
        if not user or user._is_superuser() or user.has_group('base.group_system'):
            return res

        # Bypass security rules on internal system models to prevent blocking core Odoo operations.
        # We bypass entire model families by prefix to avoid whack-a-mole with individual models.
        BYPASS_PREFIXES = ('access.', 'discuss.', 'bus.', 'mail.', 'ir.', 'base_setup.',)
        BYPASS_MODELS = {
            'res.users', 'res.users.log', 'res.groups', 'res.company', 'res.lang', 'res.partner',
            'res.currency', 'res.country', 'res.device.log', 'website', 'rating.rating',
        }
        if model and (
            any(model.startswith(p) for p in BYPASS_PREFIXES)
            or model in BYPASS_MODELS
        ):
            return res

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return res

        # 1. Global Disable Login Rule
        if any(r.disable_login for r in rules):
            if raise_exception:
                raise AccessError(_("Your user account login access has been disabled by System Administrator."))
            return False

        # 2. Global Read-Only User rule
        if mode in ('write', 'create', 'unlink') and any(r.readonly_user for r in rules):
            if raise_exception:
                raise AccessError(_("You are configured as a Read-Only user. Operation '%s' on '%s' is prohibited.") % (mode, model))
            return False

        # 3. Specific Model Access Rules
        model_rules = rules.mapped('model_access_ids').filtered(lambda ma: ma.model_name == model)
        if model_rules:
            allowed = True
            for mr in model_rules:
                if mode == 'read' and not mr.perm_read:
                    allowed = False
                elif mode == 'create' and not mr.perm_create:
                    allowed = False
                elif mode == 'write' and not mr.perm_write:
                    allowed = False
                elif mode == 'unlink' and not mr.perm_unlink:
                    allowed = False

            if not allowed:
                if raise_exception:
                    raise AccessError(_("Access Management Restriction: You are not allowed to '%s' records of model '%s'.") % (mode, model))
                return False

        return res
