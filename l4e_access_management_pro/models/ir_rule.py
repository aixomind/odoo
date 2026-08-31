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
from odoo.osv import expression
from ast import literal_eval

class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _compute_domain(self, model_name, mode='read'):
        """Override ir.rule _compute_domain to merge access.domain.records domain rules."""
        domain = super()._compute_domain(model_name, mode=mode)

        if self.env.context.get('access_management_skip') or self.env.su:
            return domain

        user = self.env.user
        if not user or user._is_superuser() or user.has_group('base.group_system'):
            return domain

        if model_name and (model_name.startswith('access.') or model_name in ('ir.model.access', 'ir.rule', 'ir.ui.menu', 'res.users', 'res.groups', 'res.company', 'res.lang', 'website', 'mail.activity', 'mail.message', 'mail.thread', 'mail.channel', 'mail.followers')):
            return domain

        rules = self.env['access.management']._get_user_rules(user)
        if not rules:
            return domain

        domain_records = rules.mapped('domain_access_ids').filtered(
            lambda dr: dr.model_name == model_name and dr.restriction_mode == 'hard'
        )

        custom_domains = []
        for dr in domain_records:
            if mode == 'read' and not dr.perm_read:
                continue
            if mode == 'write' and not dr.perm_write:
                continue
            if mode == 'create' and not dr.perm_create:
                continue
            if mode == 'unlink' and not dr.perm_unlink:
                continue

            if dr.domain:
                try:
                    eval_domain = literal_eval(dr.domain)
                    if isinstance(eval_domain, list):
                        custom_domains.append(eval_domain)
                except Exception:
                    pass

        if custom_domains:
            combined_custom = expression.AND(custom_domains)
            domain = expression.AND([domain, combined_custom]) if domain else combined_custom

        return domain
