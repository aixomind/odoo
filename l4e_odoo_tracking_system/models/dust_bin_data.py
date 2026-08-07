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
            for fname, val in data.items():
                if fname not in valid_fields or fname in ('id', 'create_date', 'create_uid', 'write_date', 'write_uid'):
                    continue
                field = valid_fields[fname]
                # Skip compute/readonly fields unless they are explicitly store/writable
                if field.readonly and not getattr(field, 'states', None):
                    continue
                if field.type in ('one2many', 'many2many'):
                    continue
                if field.type == 'many2one' and isinstance(val, (list, tuple)):
                    val = val[0]
                clean_vals[fname] = val

            # Bypass delete tracking during restoration to avoid loop
            context = dict(self.env.context, bypass_dust_bin=True)
            restored_rec = target_model.with_context(context).create(clean_vals)
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
