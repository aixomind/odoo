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
import json
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class TrackingDustBin(models.Model):
    _name = 'tracking.dust.bin'
    _description = 'Dust Bin Data'
    _order = 'deletion_date desc'

    name = fields.Char(
        string='Record Name',
        required=True
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade'
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Technical Model Name',
        store=True
    )
    res_id = fields.Integer(
        string='Original Record ID'
    )
    record_data = fields.Text(
        string='Serialized Record Data',
        required=True
    )
    deletion_date = fields.Datetime(
        string='Deleted On',
        default=fields.Datetime.now,
        required=True
    )

    def action_restore(self):
        """ Restores the selected deleted record(s) back into the target Odoo model. Restricted to Admins. """
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only System Administrators are allowed to restore deleted records."))

        restored_count = 0
        for rec in self:
            if not rec.model_id or not rec.record_data:
                continue

            target_model_name = rec.model_id.model
            if target_model_name not in self.env:
                raise UserError(_("Target model %s does not exist in the system.", target_model_name))

            target_model = self.env[target_model_name]
            try:
                data = json.loads(rec.record_data)
            except Exception as e:
                _logger.error("Failed to parse record data JSON for restore: %s", str(e))
                continue

            # Clean stored dictionary keys to only keep writable fields
            valid_fields = target_model._fields
            clean_vals = {}
            skip_comodels = {'mail.followers', 'mail.message', 'mail.activity', 'mail.tracking.value', 'mail.notification', 'tracking.dust.bin', 'tracking.config'}
            for fname, val in data.items():
                if fname not in valid_fields or fname in ('id', 'create_date', 'create_uid', 'write_date', 'write_uid', '__last_update'):
                    continue
                if fname.startswith(('message_', 'activity_')) or getattr(valid_fields[fname], 'comodel_name', None) in skip_comodels:
                    continue
                field = valid_fields[fname]

                # Skip compute fields unless they are stored AND writable/inverse, EXCEPT 'state'
                if field.compute and not field.inverse and fname != 'state':
                    continue

                # Skip readonly fields UNLESS field is 'state' or field is stored
                if field.readonly and fname != 'state' and not field.store:
                    continue

                if field.type == 'many2one':
                    m2o_id = val[0] if isinstance(val, (list, tuple)) else val
                    if m2o_id and self.env[field.comodel_name].browse(m2o_id).exists():
                        clean_vals[fname] = m2o_id
                    else:
                        clean_vals[fname] = False

                elif field.type == 'many2many':
                    if isinstance(val, list):
                        existing_m2m = self.env[field.comodel_name].browse(val).exists().ids
                        clean_vals[fname] = [(6, 0, existing_m2m)]

                elif field.type == 'one2many':
                    if isinstance(val, list) and val:
                        comodel = self.env[field.comodel_name]
                        comodel_fields = comodel._fields
                        clean_lines = []
                        for line_item in val:
                            if isinstance(line_item, (list, tuple)) and len(line_item) == 3:
                                line_dict = line_item[2]
                            elif isinstance(line_item, dict):
                                line_dict = line_item
                            else:
                                continue

                            clean_line_vals = {}
                            for l_fname, l_val in line_dict.items():
                                if l_fname not in comodel_fields or l_fname in ('id', 'create_date', 'create_uid', 'write_date', 'write_uid', '__last_update'):
                                    continue
                                l_field = comodel_fields[l_fname]
                                if l_field.compute and not l_field.store and not l_field.inverse:
                                    continue
                                if l_field.type == 'many2one':
                                    m2o_id = l_val[0] if isinstance(l_val, (list, tuple)) else l_val
                                    if m2o_id and self.env[l_field.comodel_name].browse(m2o_id).exists():
                                        clean_line_vals[l_fname] = m2o_id
                                    else:
                                        clean_line_vals[l_fname] = False
                                elif l_field.type == 'many2many':
                                    if isinstance(l_val, list):
                                        existing_m2m = self.env[l_field.comodel_name].browse(l_val).exists().ids
                                        clean_line_vals[l_fname] = [(6, 0, existing_m2m)]
                                else:
                                    clean_line_vals[l_fname] = l_val

                            if clean_line_vals:
                                clean_lines.append((0, 0, clean_line_vals))

                        if clean_lines:
                            clean_vals[fname] = clean_lines

                else:
                    clean_vals[fname] = val

            # Bypass delete tracking during restoration to avoid loop
            context = dict(self.env.context, bypass_dust_bin=True, bypass_chatter_tracking=True)
            restored_rec = target_model.with_context(context).create(clean_vals)

            # GUARANTEE STATE RESTORATION:
            # If original data had a 'state' field and restored_rec's state doesn't match, force state update
            original_state = data.get('state')
            if restored_rec and original_state and hasattr(restored_rec, 'state') and restored_rec.state != original_state:
                _logger.info("Restoring state for %s (%s) to '%s'", target_model_name, restored_rec.id, original_state)
                try:
                    restored_rec.sudo().with_context(context).write({'state': original_state})
                except Exception as e:
                    _logger.warning("Standard write failed for state restoration (%s), using low-level write: %s", original_state, str(e))
                    try:
                        restored_rec.sudo()._write({'state': original_state})
                    except Exception as e2:
                        _logger.error("Low-level _write failed for state restoration: %s", str(e2))

            if restored_rec:
                rec.unlink()
                restored_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Restored'),
                'message': _('Successfully restored %s record(s).', restored_count),
                'sticky': False,
                'type': 'success',
            }
        }

    @api.model
    def _cron_cleanup_dust_bin(self):
        """ Cleanup dust bin records that exceeded configured tracking days """
        dust_records = self.search([])
        now = fields.Datetime.now()
        to_remove = self.env['tracking.dust.bin']

        for rec in dust_records:
            config = self.env['tracking.config'].search([('model_id', '=', rec.model_id.id)], limit=1)
            if config and config.tracking_days > 0:
                expiry_date = rec.deletion_date + timedelta(days=config.tracking_days)
                if now >= expiry_date:
                    to_remove |= rec

        if to_remove:
            _logger.info("Auto-deleting %s expired record(s) from Dust Bin Data.", len(to_remove))
            to_remove.unlink()
