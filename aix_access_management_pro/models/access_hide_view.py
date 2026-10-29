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

class AccessHideView(models.Model):
    _name = 'access.hide.view'
    _description = 'Hide View Mode Access Rights'

    access_management_id = fields.Many2one('access.management', string='Access Rule', ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', store=True)
    view_mode = fields.Selection([
        ('tree', 'List / Tree'),
        ('form', 'Form'),
        ('kanban', 'Kanban'),
        ('pivot', 'Pivot'),
        ('graph', 'Graph'),
        ('calendar', 'Calendar'),
        ('activity', 'Activity'),
        ('gantt', 'Gantt'),
        ('map', 'Map'),
    ], string='Restricted View Mode', required=True)


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def read(self, fields=None, load='_classic_read'):
        """Override read on act_window to strip restricted view modes for current user."""
        res = super().read(fields=fields, load=load)

        user = self.env.user
        if user._is_superuser():
            return res

        rules = self.env['access.management']._get_user_rules(user)
        if not rules or not rules.mapped('hide_view_ids'):
            return res

        hide_view_records = rules.mapped('hide_view_ids')
        hidden_by_model = {}
        for hv in hide_view_records:
            mname = hv.model_name
            if mname:
                hidden_by_model.setdefault(mname, set()).add(hv.view_mode)
                if hv.view_mode == 'tree':
                    hidden_by_model[mname].add('list')
                elif hv.view_mode == 'list':
                    hidden_by_model[mname].add('tree')

        for act in res:
            if isinstance(act, dict) and act.get('res_model'):
                mname = act['res_model']
                if mname in hidden_by_model:
                    bad_modes = hidden_by_model[mname]

                    # Filter view_mode string
                    if act.get('view_mode'):
                        modes = [m.strip() for m in act['view_mode'].split(',') if m.strip()]
                        valid_modes = [m for m in modes if m not in bad_modes]
                        act['view_mode'] = ','.join(valid_modes)

                    # Filter views list
                    if act.get('views'):
                        filtered_views = []
                        for v in act['views']:
                            if isinstance(v, (list, tuple)) and len(v) > 1:
                                v_type = v[1]
                                if v_type not in bad_modes:
                                    filtered_views.append(v)
                            else:
                                filtered_views.append(v)
                        act['views'] = filtered_views

        return res
