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
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

class BaseModelOverride(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_views(self, views, options=None):
        """Override BaseModel.get_views to manipulate view XML architectures and toolbars based on Access Management Pro rules."""
        res = super().get_views(views, options=options)

        user = self.env.user
        if user._is_superuser() or user.has_group('base.group_system'):
            return res

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return res

        model_name = self._name

        # Global Toggles
        disable_export = any(r.disable_export for r in rules)
        disable_import = any(r.disable_import for r in rules)
        readonly_user = any(r.readonly_user for r in rules)

        # Model Specific Rules
        model_access = rules.mapped('model_access_ids').filtered(lambda ma: ma.model_name == model_name)
        field_rules = rules.mapped('field_access_ids').filtered(lambda fa: fa.model_name == model_name)
        button_tab_rules = rules.mapped('button_tab_access_ids').filtered(lambda bt: bt.model_name == model_name)
        filter_rules = rules.mapped('hide_filters_ids').filtered(lambda hf: hf.model_name == model_name)
        chatter_rules = rules.mapped('hide_chatter_ids').filtered(lambda hc: hc.model_name == model_name)
        hide_report_ids = set(rules.mapped('hide_report_ids.report_id.id'))

        perm_create = all(ma.perm_create for ma in model_access) if model_access else True
        perm_write = all(ma.perm_write for ma in model_access) if model_access else True
        perm_unlink = all(ma.perm_unlink for ma in model_access) if model_access else True
        perm_archive = all(ma.perm_archive for ma in model_access) if model_access else True
        perm_duplicate = all(ma.perm_duplicate for ma in model_access) if model_access else True
        perm_export = all(ma.perm_export for ma in model_access) if model_access else True

        if readonly_user:
            perm_create = perm_write = perm_unlink = perm_archive = perm_duplicate = perm_export = False

        # 1. Filter View-Level XML & Toolbars
        for view_type, view_info in res.get('views', {}).items():
            # A. Toolbar Filtering (Print Reports & Action Dropdown Options)
            toolbar = view_info.get('toolbar')
            if toolbar:
                # Filter Print Reports
                if 'print' in toolbar and hide_report_ids:
                    toolbar['print'] = [rpt for rpt in toolbar['print'] if rpt.get('id') not in hide_report_ids]

                # Filter Action Dropdown Items (Delete, Archive, Duplicate, Export)
                if 'action' in toolbar:
                    filtered_actions = []
                    for act in toolbar['action']:
                        act_name = str(act.get('name', '')).lower()
                        act_key = str(act.get('key', '')).lower()
                        if not perm_unlink and ('delete' in act_name or 'unlink' in act_key):
                            continue
                        if not perm_duplicate and ('duplicate' in act_name or 'copy' in act_key):
                            continue
                        if not perm_archive and ('archive' in act_name or 'unarchive' in act_name):
                            continue
                        if (disable_export or not perm_export) and ('export' in act_name or 'export' in act_key):
                            continue
                        filtered_actions.append(act)
                    toolbar['action'] = filtered_actions

            if 'arch' not in view_info:
                continue

            try:
                doc = etree.fromstring(view_info['arch'])
            except Exception as e:
                _logger.warning("Access Management Pro: Failed to parse XML for %s: %s", model_name, e)
                continue

            root_changed = False

            # B. Root Node Attributes Modification
            if not perm_create:
                doc.set('create', 'false')
                root_changed = True
            if not perm_write:
                doc.set('edit', 'false')
                root_changed = True
            if not perm_unlink:
                doc.set('delete', 'false')
                root_changed = True
            if disable_import:
                doc.set('import', 'false')
                root_changed = True
            if disable_export or not perm_export:
                doc.set('export_xlsx', 'false')
                root_changed = True

            # C. Field Rules Application (Field & Associated Labels)
            for fr in field_rules:
                fname = fr.field_name
                if not fname:
                    continue

                field_nodes = doc.xpath("//field[@name='%s']" % fname)
                label_nodes = doc.xpath("//label[@for='%s']" % fname)

                for node in field_nodes:
                    if fr.restriction_type == 'invisible':
                        node.set('invisible', '1')
                        parent = node.getparent()
                        if parent is not None and parent.tag in ('div', 'span') and parent.get('class'):
                            p_cls = parent.get('class', '')
                            if 'o_td_label' in p_cls and len(parent) <= 1:
                                parent.set('invisible', '1')
                    elif fr.restriction_type == 'readonly':
                        node.set('readonly', '1')
                    elif fr.restriction_type == 'required':
                        node.set('required', '1')
                    root_changed = True

                for lnode in label_nodes:
                    if fr.restriction_type == 'invisible':
                        lnode.set('invisible', '1')
                        parent = lnode.getparent()
                        if parent is not None and parent.tag in ('div', 'span') and parent.get('class'):
                            p_cls = parent.get('class', '')
                            if 'o_td_label' in p_cls and len(parent) <= 1:
                                parent.set('invisible', '1')
                    elif fr.restriction_type == 'readonly':
                        lnode.set('readonly', '1')
                    root_changed = True

            # D. Button & Tab Rules Application
            for btr in button_tab_rules:
                identifier = btr.element_identifier
                if not identifier:
                    continue
                ident_lower = identifier.lower()
                if btr.element_type == 'button':
                    xpath_expr = "//button[@name='%s'] | //button[contains(translate(@string, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')]" % (identifier, ident_lower)
                    for btn_node in doc.xpath(xpath_expr):
                        if btr.restriction_type == 'hide':
                            btn_node.set('invisible', '1')
                        elif btr.restriction_type == 'readonly':
                            btn_node.set('disabled', '1')
                        root_changed = True
                elif btr.element_type == 'tab':
                    xpath_expr = "//page[@name='%s'] | //page[contains(translate(@string, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')]" % (identifier, ident_lower)
                    for tab_node in doc.xpath(xpath_expr):
                        if btr.restriction_type == 'hide':
                            tab_node.set('invisible', '1')
                        root_changed = True

            # E. Search Filter & Group By & Search Panel Restrictions
            if view_type == 'search':
                for fltr in filter_rules:
                    fname = (fltr.filter_name or '').strip().lower()
                    if not fname:
                        continue

                    if fname in ('custom filter', 'custom filter...', 'custom_filter', 'add custom filter'):
                        doc.set('hide_custom_filter', '1')
                        root_changed = True

                    if fname in ('custom group', 'custom_group', 'add custom group'):
                        doc.set('hide_custom_group', '1')
                        root_changed = True

                    xpath_expr = (
                        "//filter[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')] | "
                        "//filter[contains(translate(@string, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')] | "
                        "//filter[contains(translate(@domain, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')] | "
                        "//filter[contains(translate(@context, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')] | "
                        "//searchpanel//section[contains(translate(@string, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')] | "
                        "//searchpanel//field[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')]"
                        % (fname, fname, fname, fname, fname, fname)
                    )
                    for filter_node in doc.xpath(xpath_expr):
                        parent = filter_node.getparent()
                        if parent is not None:
                            parent.remove(filter_node)
                            root_changed = True

            # F. Chatter Restrictions Application in Form View XML
            if view_type == 'form' and chatter_rules:
                for cr in chatter_rules:
                    chatter_nodes = doc.xpath("//chatter | //div[contains(@class, 'oe_chatter')]")
                    for cnode in chatter_nodes:
                        if cr.hide_chatter:
                            cnode.set('invisible', '1')
                            root_changed = True
                        else:
                            if cr.hide_followers:
                                cnode.set('has_followers', '0')
                                root_changed = True
                            if cr.hide_attachments:
                                cnode.set('has_files', '0')
                                root_changed = True

                    if cr.hide_chatter or cr.hide_followers:
                        for fn in doc.xpath("//field[@name='message_follower_ids']"):
                            fn.set('invisible', '1')
                            root_changed = True
                    if cr.hide_chatter:
                        for fn in doc.xpath("//field[@name='message_ids'] | //field[@name='activity_ids']"):
                            fn.set('invisible', '1')
                            root_changed = True

            if root_changed:
                view_info['arch'] = etree.tostring(doc, encoding='unicode')

        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Legacy view modification hook for Odoo 16 fallback."""
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        user = self.env.user
        if user._is_superuser() or user.has_group('base.group_system'):
            return res

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return res

        model_name = self._name
        field_rules = rules.mapped('field_access_ids').filtered(lambda fa: fa.model_name == model_name)
        if field_rules and 'arch' in res:
            try:
                doc = etree.fromstring(res['arch'])
                changed = False
                for fr in field_rules:
                    if fr.field_name:
                        for node in doc.xpath("//field[@name='%s']" % fr.field_name):
                            if fr.restriction_type == 'invisible':
                                node.set('invisible', '1')
                            elif fr.restriction_type == 'readonly':
                                node.set('readonly', '1')
                            elif fr.restriction_type == 'required':
                                node.set('required', '1')
                            changed = True
                if changed:
                    res['arch'] = etree.tostring(doc, encoding='unicode')
            except Exception:
                pass
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override fields_get to inject readonly/invisible flags directly into field definitions."""
        res = super().fields_get(allfields=allfields, attributes=attributes)

        user = self.env.user
        if user._is_superuser() or user.has_group('base.group_system'):
            return res

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return res

        field_rules = rules.mapped('field_access_ids').filtered(lambda fa: fa.model_name == self._name)
        readonly_user = any(r.readonly_user for r in rules)

        for fname, fdict in res.items():
            if readonly_user:
                fdict['readonly'] = True

            matching_rules = field_rules.filtered(lambda fr: fr.field_name == fname)
            for fr in matching_rules:
                if fr.restriction_type == 'invisible':
                    fdict['searchable'] = False
                elif fr.restriction_type == 'readonly':
                    fdict['readonly'] = True
                elif fr.restriction_type == 'required':
                    fdict['required'] = True

        return res
