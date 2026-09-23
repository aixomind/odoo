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
from odoo.exceptions import AccessError

class AccessHideReport(models.Model):
    _name = 'access.hide.report'
    _description = 'Hide Report Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model')
    report_id = fields.Many2one('ir.actions.report', string='Report Action', required=True, ondelete='cascade')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render(self, report_ref, res_ids, data=None):
        """Override _render to prevent rendering hidden reports."""
        user = self.env.user
        if not user._is_superuser():
            rules = self.env['access.management']._get_user_rules(user)
            if rules:
                hide_report_ids = set(rules.mapped('hide_report_ids.report_id.id'))
                report = self._get_report(report_ref)
                if report and report.id in hide_report_ids:
                    raise AccessError(_("Access Management Restriction: You are not allowed to print or view report '%s'.") % report.name)

        return super()._render(report_ref, res_ids, data=data)
