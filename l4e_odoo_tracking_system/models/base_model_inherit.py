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
from odoo import models, api, _
from markupsafe import Markup

_logger = logging.getLogger(__name__)


def _format_tracking_message(field_name, old_val, new_val):
    """ Formats tracking messages into clean HTML matching standard Odoo chatter tracking boxes """
    old_str = f"<span class='o_l4e_tracking_old'>{old_val}</span>" if old_val else "<span class='o_l4e_tracking_empty'>empty</span>"
    new_str = f"<span class='o_l4e_tracking_new'>{new_val}</span>" if new_val else "<span class='o_l4e_tracking_empty'>empty</span>"

    raw_html = f"""<div class="o_custom_tracking_card">
        <span class="o_l4e_tracking_title">{field_name} updated.</span> 
        <span>The {field_name.lower()} has been changed from {old_str} to {new_str}.</span>
    </div>"""
    return Markup(raw_html)


def _format_relational_change(field_name, added_ids, removed_ids, new_records, old_name_map, unchanged_count):
    """Formats many2many/one2many changes as a meaningful diff — only added/removed items,
    no repetition of unchanged lines."""
    parts = []

    if added_ids:
        added_records = new_records.filtered(lambda r: r.id in added_ids)
        added_str = ', '.join(
            f"<span class='o_l4e_tracking_new'>{r.display_name}</span>"
            for r in added_records
        )
        parts.append(f"Added: {added_str}")

    if removed_ids:
        removed_str = ', '.join(
            f"<span class='o_l4e_tracking_old'>{old_name_map[rid]}</span>"
            for rid in removed_ids if rid in old_name_map
        )
        if removed_str:
            parts.append(f"Removed: {removed_str}")

    if unchanged_count > 0:
        item_label = f"item{'s' if unchanged_count != 1 else ''}"
        parts.append(f"<span class='o_l4e_tracking_empty'>{unchanged_count} {item_label} unchanged</span>")

    if not parts:
        return None

    body = '. '.join(parts)
    raw_html = f"""<div class="o_custom_tracking_card">
        <span class="o_l4e_tracking_title">{field_name} updated.</span>
        <span> {body}.</span>
    </div>"""
    return Markup(raw_html)


class MailThreadInherit(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_post_after_hook(self, message, msg_vals):
        res = super(MailThreadInherit, self)._message_post_after_hook(message, msg_vals)
        if self.env.context.get('bypass_chatter_tracking') or message.message_type == 'email':
            return res

        ir_model = self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1)
        config = self.env['tracking.config'].sudo().search([('model_id', '=', ir_model.id)], limit=1) if ir_model else False
        if config and config.tracking_enable and not config.remove_tracking:
            body = str(message.body or '').strip()
            if (
                'o_custom_tracking_card' not in body
                and (
                    message.tracking_value_ids
                    or not body
                    or body.endswith(' created')
                    or body == _('Document created')
                )
            ):
                message.sudo().unlink()
        return res

    def _track_post_template(self):
        ir_model = self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1)
        if ir_model:
            config = self.env['tracking.config'].sudo().search([('model_id', '=', ir_model.id)], limit=1)
            if config and config.tracking_enable and not config.remove_tracking:
                return {}
        return super(MailThreadInherit, self)._track_post_template()


class BaseModelInherit(models.AbstractModel):
    _inherit = 'base'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(BaseModelInherit, self).create(vals_list)

        if not self.env.context.get('bypass_chatter_tracking'):
            model_name = self._name
            ir_model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)

            if ir_model:
                config = self.env['tracking.config'].sudo().search([('model_id', '=', ir_model.id)], limit=1)
                if config:
                    # STRICT CONDITIONAL CHECK:
                    # ONLY generate custom green cards and purge default logs IF tracking_enable is True AND remove_tracking is False
                    if config.tracking_enable and not config.remove_tracking:
                        for record in records:
                            # Post custom green card
                            if hasattr(record, 'message_post'):
                                rec_name = record.display_name or record._name
                                msg = _format_tracking_message("Record", "none", f"{rec_name} created")
                                record.with_context(bypass_chatter_tracking=True).message_post(body=msg)

                            # Purge default plain text creation logs
                            default_msgs = self.env['mail.message'].sudo().search([
                                ('model', '=', model_name),
                                ('res_id', '=', record.id),
                                ('message_type', '!=', 'email'),
                            ]).filtered(lambda m: (
                                'o_custom_tracking_card' not in str(m.body)
                                and (
                                    m.tracking_value_ids
                                    or not m.body
                                    or str(m.body).strip() in {
                                        f'{record._description} created',
                                        f'{record._name} created',
                                        f'{record.display_name} created',
                                        _('Document created'),
                                    }
                                    or str(m.body).strip().endswith(' created')
                                )
                            ))
                            if default_msgs:
                                default_msgs.sudo().unlink()

        return records

    def write(self, vals):
        old_values = {}
        model_name = self._name
        ir_model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        config = self.env['tracking.config'].sudo().search([('model_id', '=', ir_model.id)], limit=1) if ir_model else False

        if config and config.tracking_enable and not config.remove_tracking:
            for record in self:
                old_values[record.id] = {}
                for fname in vals.keys():
                    if fname in record._fields:
                        field = record._fields[fname]
                        val = record[fname]
                        if field.type == 'many2one':
                            old_values[record.id][fname] = val.display_name if val else False
                        elif field.type in ('many2many', 'one2many'):
                            # Store as {id: display_name} dict so deleted records
                            # still have their names available after the write
                            old_values[record.id][fname] = {r.id: r.display_name for r in val}
                        else:
                            old_values[record.id][fname] = str(val) if val is not False and val is not None else False

        res = super(BaseModelInherit, self).write(vals)

        if not self.env.context.get('bypass_chatter_tracking') and self and hasattr(self, 'message_post'):
            # STRICT CONDITIONAL CHECK:
            if config and config.tracking_enable and not config.remove_tracking:
                for record in self:
                    rec_old_vals = old_values.get(record.id, {})
                    for fname in vals.keys():
                        if fname in record._fields:
                            field = record._fields[fname]
                            new_val = record[fname]
                            field_string = field.string or fname

                            if field.type in ('many2many', 'one2many'):
                                # Diff-based: show only added/removed, no repetition
                                old_name_map = rec_old_vals.get(fname, {})
                                if not isinstance(old_name_map, dict):
                                    old_name_map = {}
                                old_ids = frozenset(old_name_map.keys())
                                new_ids = frozenset(new_val.ids)
                                if old_ids != new_ids:
                                    added_ids = new_ids - old_ids
                                    removed_ids = old_ids - new_ids
                                    unchanged_count = len(old_ids & new_ids)
                                    msg = _format_relational_change(
                                        field_string, added_ids, removed_ids,
                                        new_val, old_name_map, unchanged_count
                                    )
                                    if msg:
                                        record.with_context(bypass_chatter_tracking=True).message_post(body=msg)
                                continue  # Skip generic scalar logic below

                            if field.type == 'many2one':
                                new_val_str = new_val.display_name if new_val else False
                            else:
                                new_val_str = str(new_val) if new_val is not False and new_val is not None else False

                            old_val_str = rec_old_vals.get(fname, False)
                            if old_val_str != new_val_str:
                                msg = _format_tracking_message(field_string, old_val_str, new_val_str)
                                record.with_context(bypass_chatter_tracking=True).message_post(body=msg)

                    default_msgs = self.env['mail.message'].sudo().search([
                        ('model', '=', model_name),
                        ('res_id', '=', record.id),
                        ('message_type', '!=', 'email'),
                    ]).filtered(lambda m: (
                        'o_custom_tracking_card' not in str(m.body)
                        and (m.tracking_value_ids or not m.body)
                    ))
                    if default_msgs:
                        default_msgs.sudo().unlink()

        return res

    def unlink(self):
        """ Intercept record deletion to store snapshot in Dust Bin if tracking is enabled """
        if not self.env.context.get('bypass_dust_bin') and self:
            model_name = self._name
            ir_model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)

            if ir_model:
                config = self.env['tracking.config'].sudo().search([
                    ('model_id', '=', ir_model.id),
                    ('tracking_enable', '=', True)
                ], limit=1)

                if config:
                    DustBin = self.env['tracking.dust.bin'].sudo()
                    for record in self:
                        try:
                            rec_vals = {}
                            for fname, field in record._fields.items():
                                if field.type in ('binary', 'one2many', 'many2many', 'serialized'):
                                    continue
                                val = record[fname]
                                if field.type == 'many2one':
                                    val = val.id if val else False
                                elif field.type in ('date', 'datetime'):
                                    val = str(val) if val else False
                                rec_vals[fname] = val

                            display_name = record.display_name or f"{model_name},{record.id}"
                            DustBin.create({
                                'name': display_name,
                                'model_id': ir_model.id,
                                'res_id': record.id,
                                'record_data': json.dumps(rec_vals, default=str),
                            })
                        except Exception as e:
                            _logger.error("Error creating Dust Bin entry for record %s of model %s: %s", record.id, model_name, str(e))

        return super(BaseModelInherit, self).unlink()
