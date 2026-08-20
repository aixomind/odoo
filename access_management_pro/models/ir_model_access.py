# -*- coding: utf-8 -*-
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
        if not user or user._is_superuser():
            return res

        # Bypass security rules on access management models and system infrastructure models to prevent loops
        if model and (model.startswith('access.') or model in ('ir.model.access', 'ir.rule', 'ir.ui.menu', 'res.users', 'res.groups', 'res.company', 'res.lang', 'website', 'mail.activity', 'mail.message', 'mail.thread', 'mail.channel', 'mail.followers')):
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
