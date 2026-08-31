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
from odoo import models, _
from odoo.exceptions import AccessError


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _access_management_check_module_operation(self, operation):
        """Block module install/upgrade/uninstall for restricted users."""

        user = self.env.user

        if not user or user._is_superuser():
            return

        rules = self.env['access.management']._get_user_rules(user)

        if any(rule.disable_module_install for rule in rules):
            operation_names = {
                'install': _('installation'),
                'upgrade': _('upgrade'),
                'uninstall': _('uninstallation'),
            }

            operation_name = operation_names.get(
                operation,
                _('module operation')
            )

            raise AccessError(
                _(
                    'Access Management Restriction:\n\n'
                    'You are not allowed to perform module %s.'
                ) % operation_name
            )

    def button_immediate_install(self):
        self._access_management_check_module_operation('install')
        return super().button_immediate_install()

    def button_immediate_upgrade(self):
        self._access_management_check_module_operation('upgrade')
        return super().button_immediate_upgrade()

    def button_immediate_uninstall(self):
        self._access_management_check_module_operation('uninstall')
        return super().button_immediate_uninstall()
