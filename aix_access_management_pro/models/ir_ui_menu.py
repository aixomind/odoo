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
from odoo import models, api

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        """Override _visible_menu_ids to exclude hidden menu IDs from the visible set."""
        visible_ids = super()._visible_menu_ids(debug=debug)

        user = self.env.user
        if user._is_superuser() or user.has_group('base.group_system'):
            return visible_ids

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return visible_ids

        hidden_menu_ids = set(rules.mapped('hide_menu_ids.menu_id.id'))
        if hidden_menu_ids:
            visible_ids = visible_ids - hidden_menu_ids

        return visible_ids

    @api.model
    def load_menus(self, debug=False):
        """Override load_menus to filter out hidden menus per access management rules."""
        menu_roots = super().load_menus(debug=debug)

        user = self.env.user
        if user._is_superuser() or user.has_group('base.group_system'):
            return menu_roots

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return menu_roots

        hidden_menu_ids = set(rules.mapped('hide_menu_ids.menu_id.id'))
        if not hidden_menu_ids:
            return menu_roots

        def filter_menu_dict(menu):
            if menu.get('id') in hidden_menu_ids:
                return None
            if 'childrenTree' in menu and menu['childrenTree']:
                menu['childrenTree'] = [
                    filter_menu_dict(child) for child in menu['childrenTree']
                    if child.get('id') not in hidden_menu_ids
                ]
                menu['childrenTree'] = [c for c in menu['childrenTree'] if c is not None]
            return menu

        if isinstance(menu_roots, dict):
            keys_to_remove = [k for k in menu_roots if k in hidden_menu_ids]
            for k in keys_to_remove:
                del menu_roots[k]
            if 'childrenTree' in menu_roots:
                menu_roots['childrenTree'] = [
                    filter_menu_dict(child) for child in menu_roots['childrenTree']
                    if child.get('id') not in hidden_menu_ids
                ]
                menu_roots['childrenTree'] = [c for c in menu_roots['childrenTree'] if c is not None]

        return menu_roots
