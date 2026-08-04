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
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_admin_id_2 = fields.Boolean(compute='_compute_is_admin_id_2')

    l4e_show_crm_dashboard = fields.Boolean(
        string="CRM Dashboard",
        config_parameter="l4e_dashboard_collection.show_crm_dashboard",
    )
    l4e_show_sales_dashboard = fields.Boolean(
        string="Sales Dashboard",
        config_parameter="l4e_dashboard_collection.show_sales_dashboard",
    )
    l4e_show_inventory_dashboard = fields.Boolean(
        string="Inventory Dashboard",
        config_parameter="l4e_dashboard_collection.show_inventory_dashboard",
    )
    l4e_show_account_dashboard = fields.Boolean(
        string="Account Dashboard",
        config_parameter="l4e_dashboard_collection.show_account_dashboard",
    )
    l4e_show_amc_dashboard = fields.Boolean(
        string="AMC Dashboard",
        config_parameter="l4e_dashboard_collection.show_amc_dashboard",
    )

    @api.depends_context('uid')
    def _compute_is_admin_id_2(self):
        for record in self:
            record.is_admin_id_2 = (self.env.user.id in (1, 2) or self.env.user.has_group('base.group_system'))

    def _register_hook(self):
        """Runs immediately after module upgrade to re-enforce saved menu visibility from ir.config_parameter."""
        res = super()._register_hook()
        ICP = self.env['ir.config_parameter'].sudo()

        def _sync_menu(param_name, xml_id):
            is_active = ICP.get_param(param_name, 'False').lower() == 'true'
            menu = self.env.ref(xml_id, raise_if_not_found=False)
            if menu and menu.active != is_active:
                menu.sudo().write({'active': is_active})

        _sync_menu('l4e_dashboard_collection.show_crm_dashboard', 'l4e_dashboard_collection.menu_crm_dashboard')
        _sync_menu('l4e_dashboard_collection.show_sales_dashboard', 'l4e_dashboard_collection.menu_sale_dashboard')
        _sync_menu('l4e_dashboard_collection.show_inventory_dashboard', 'l4e_dashboard_collection.menu_l4e_inventory_dashboard')
        _sync_menu('l4e_dashboard_collection.show_account_dashboard', 'l4e_dashboard_collection.menu_financial_dashboard')
        _sync_menu('l4e_dashboard_collection.show_amc_dashboard', 'l4e_dashboard_collection.menu_amc_dashboard')
        return res

    def set_values(self):
        super().set_values()

        def _update_menu(xml_id, is_active):
            menu = self.env.ref(xml_id, raise_if_not_found=False)
            if menu and menu.active != is_active:
                menu.sudo().write({'active': is_active})

        _update_menu('l4e_dashboard_collection.menu_crm_dashboard', bool(self.l4e_show_crm_dashboard))
        _update_menu('l4e_dashboard_collection.menu_sale_dashboard', bool(self.l4e_show_sales_dashboard))
        _update_menu('l4e_dashboard_collection.menu_l4e_inventory_dashboard', bool(self.l4e_show_inventory_dashboard))
        _update_menu('l4e_dashboard_collection.menu_financial_dashboard', bool(self.l4e_show_account_dashboard))
        _update_menu('l4e_dashboard_collection.menu_amc_dashboard', bool(self.l4e_show_amc_dashboard))
