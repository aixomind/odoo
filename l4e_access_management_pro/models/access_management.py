# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccessManagement(models.Model):
    _name = 'access.management'
    _description = 'Access Management Configuration'
    _order = 'priority asc, id desc'

    name = fields.Char(string='Title', required=True)
    active = fields.Boolean(string='Active', default=True)
    priority = fields.Integer(string='Priority', default=10, help='Lower numbers indicate higher priority.')

    user_ids = fields.Many2many(
        'res.users',
        'access_management_users_rel',
        'access_id',
        'user_id',
        string='Users'
    )
    group_ids = fields.Many2many(
        'res.groups',
        'access_management_groups_rel',
        'access_id',
        'group_id',
        string='User Groups'
    )
    company_ids = fields.Many2many(
        'res.company',
        'access_management_companies_rel',
        'access_id',
        'company_id',
        string='Companies'
    )

    # Global System Toggles
    readonly_user = fields.Boolean(string='Global Read-Only User', help='Makes all models and fields read-only for targeted users.')
    disable_debug_mode = fields.Boolean(string='Disable Developer (Debug) Mode', help='Blocks targeted users from activating or using developer mode.')
    disable_export = fields.Boolean(string='Disable Export Data', help='Disables the export feature across all list views.')
    disable_import = fields.Boolean(string='Disable Import Data', help='Disables the import feature across all views.')
    disable_login = fields.Boolean(string='Disable User Login', help='Prevents targeted users from logging into the system.')
    disable_module_install = fields.Boolean(string='Disable Module Install/Uninstall', help='Prevents users from installing, upgrading, or uninstalling modules.')

    # Detailed Rule Relations
    model_access_ids = fields.One2many('access.model.access', 'access_management_id', string='Model Access Rights', copy=True)
    field_access_ids = fields.One2many('access.fields', 'access_management_id', string='Field Access Rights', copy=True)
    button_tab_access_ids = fields.One2many('access.button.tab', 'access_management_id', string='Button & Tab Restrictions', copy=True)
    domain_access_ids = fields.One2many('access.domain.records', 'access_management_id', string='Domain & Record Restrictions', copy=True)
    hide_menu_ids = fields.One2many('access.hide.menu', 'access_management_id', string='Hide Menus', copy=True)
    hide_report_ids = fields.One2many('access.hide.report', 'access_management_id', string='Hide Reports', copy=True)
    hide_view_ids = fields.One2many('access.hide.view', 'access_management_id', string='Hide View Modes', copy=True)
    hide_chatter_ids = fields.One2many('access.hide.chatter', 'access_management_id', string='Chatter Restrictions', copy=True)
    hide_filters_ids = fields.One2many('access.hide.filters', 'access_management_id', string='Search Filter Restrictions', copy=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_caches()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_caches()
        return res

    @api.model
    def _get_user_rules(self, user=None):
        """Retrieve active access rules applicable to the specified or current user."""
        if user is None:
            user = self.env.user

        if not user or user._is_superuser():
            return self.browse()

        if self.env.context.get('access_management_skip'):
            return self.browse()

        # Query rules using sudo and skip context to prevent recursive ORM checks
        sudo_self = self.sudo().with_context(access_management_skip=True)
        domain = [('active', '=', True)]

        user_groups = set()
        if hasattr(user, 'groups_id') and user.groups_id:
            user_groups = set(user.groups_id.ids)
        elif hasattr(user, 'group_ids') and user.group_ids:
            user_groups = set(user.group_ids.ids)

        user_companies = set()
        if hasattr(user, 'company_ids') and user.company_ids:
            user_companies.update(user.company_ids.ids)
        if hasattr(user, 'company_id') and user.company_id:
            user_companies.add(user.company_id.id)
        if hasattr(self.env, 'company') and self.env.company:
            user_companies.add(self.env.company.id)

        rules = sudo_self.search(domain)
        if not rules:
            return self.browse()

        matched_ids = []
        for rule in rules:
            # Check Company Match
            if rule.company_ids and not any(cid in user_companies for cid in rule.company_ids.ids):
                continue

            # Check User or Group Match
            user_match = user.id in rule.user_ids.ids if rule.user_ids else False
            group_match = any(gid in user_groups for gid in rule.group_ids.ids) if rule.group_ids else False

            if (rule.user_ids or rule.group_ids):
                if user_match or group_match:
                    matched_ids.append(rule.id)
            else:
                matched_ids.append(rule.id)

        return self.browse(matched_ids)
