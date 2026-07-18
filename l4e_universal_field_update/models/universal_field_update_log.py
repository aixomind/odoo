# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class UniversalFieldUpdateLog(models.Model):
    _name = 'universal.field.update.log'
    _description = 'Universal Field Update Log'
    _order = 'create_date desc'

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: '/')
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, readonly=True)
    date = fields.Datetime(string="Execution Date", default=fields.Datetime.now, readonly=True)

    model_name = fields.Char(string="Technical Model", readonly=True)
    model_label = fields.Char(string="Model", readonly=True)
    field_name = fields.Char(string="Technical Field", readonly=True)
    field_label = fields.Char(string="Field", readonly=True)
    field_type = fields.Char(string="Field Type", readonly=True)
    relation_model = fields.Char(string="Related Model", readonly=True)

    old_value_display = fields.Char(string="Current Value", readonly=True)
    new_value_display = fields.Char(string="Replace With", readonly=True)
    old_value_raw = fields.Text(string="Old Value (Raw)", readonly=True)
    new_value_raw = fields.Text(string="New Value (Raw)", readonly=True)

    requested_count = fields.Integer(string="Requested", readonly=True)
    updated_count = fields.Integer(string="Updated", readonly=True)
    skipped_count = fields.Integer(string="Skipped", readonly=True)
    failed_count = fields.Integer(string="Failed", readonly=True)

    line_ids = fields.One2many('universal.field.update.log.line', 'log_id', string="Lines", readonly=True)

    is_revert = fields.Boolean(string="Is Revert Entry", default=False, readonly=True, copy=False)
    state = fields.Selection([
        ('completed', 'Completed'),
        ('reverted', 'Reverted'),
    ], string="Status", default='completed', readonly=True, copy=False, tracking=True)
    reverted_log_id = fields.Many2one(
        'universal.field.update.log', string="Reverted From", readonly=True, copy=False)
    revert_log_id = fields.Many2one(
        'universal.field.update.log', string="Revert Entry", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('universal.field.update.log') or '/'
        return super(UniversalFieldUpdateLog, self).create(vals_list)

    # ---------------------------------------------------------
    # Raw value (de)serialization — shared by wizard apply + revert
    # ---------------------------------------------------------
    @staticmethod
    def _serialize_value(val, ftype):
        if val is False or val is None:
            return json.dumps(None)
        if ftype == 'date':
            return json.dumps(fields.Date.to_string(val))
        if ftype == 'datetime':
            return json.dumps(fields.Datetime.to_string(val))
        if ftype == 'many2one':
            return json.dumps(val if isinstance(val, int) else val.id)
        return json.dumps(val)

    def _deserialize_value(self, raw, ftype):
        val = json.loads(raw) if raw else None
        if val is None:
            return False
        if ftype == 'date':
            return fields.Date.to_date(val)
        if ftype == 'datetime':
            return fields.Datetime.to_datetime(val)
        if ftype == 'many2one':
            return int(val)
        return val
    
    @staticmethod
    def _sql_write(record, field_name, new_val):
        """Raw-SQL fallback for reverting a value that was originally
        written via force_bypass. Mirrors wizard._sql_write / the
        approach used by l4e_change_journal_item."""
        table = record._table
        column = field_name
        record.env.cr.execute(
            'UPDATE "%s" SET "%s" = %%s WHERE id = %%s' % (table, column),
            (new_val, record.id),
        )
        record.invalidate_recordset([field_name])
        
    @staticmethod
    def _sql_write_m2m(record, field_name, old_id, new_id):
        f = record._fields[field_name]
        table, col1, col2 = f.relation, f.column1, f.column2
        record.env.cr.execute(
            'DELETE FROM "%s" WHERE "%s" = %%s AND "%s" = %%s' % (table, col1, col2),
            (record.id, old_id),
        )
        record.env.cr.execute(
            'INSERT INTO "%s" ("%s", "%s") VALUES (%%s, %%s) ON CONFLICT DO NOTHING' % (table, col1, col2),
            (record.id, new_id),
        )
        record.invalidate_recordset([field_name])

    # ---------------------------------------------------------
    # Revert
    # ---------------------------------------------------------
    def action_revert_update(self):
        self.ensure_one()

        if self.is_revert:
            raise UserError(_("A revert entry cannot itself be reverted."))
        if self.state == 'reverted':
            raise UserError(_("This update has already been reverted."))

        lines_to_revert = self.line_ids.filtered(lambda l: l.status == 'updated' and not l.reverted)
        if not lines_to_revert:
            raise UserError(_("There are no updated records to revert."))

        Model = self.env.get(self.model_name)
        if Model is None:
            raise UserError(_("The target model '%s' no longer exists.") % self.model_name)
        if not Model.check_access_rights('write', raise_exception=False):
            raise AccessError(_("You do not have write access to model: %s") % self.model_label)

        reverted_count = 0
        failed_count = 0

        for line in lines_to_revert:
            record = Model.browse(line.res_id)
            if not record.exists():
                failed_count += 1
                line.sudo().write({'error_message': _("Record no longer exists.")})
                continue

            try:
                old_val = self._deserialize_value(line.old_value_raw, self.field_type)
                new_val = self._deserialize_value(line.new_value_raw, self.field_type)
                if self.field_type == 'many2many':
                    if line.was_forced:
                        self._sql_write_m2m(record.sudo(), self.field_name, new_val, old_val)
                    else:
                        record.write({self.field_name: [(3, new_val, 0), (4, old_val, 0)]})
                elif line.was_forced:
                    self._sql_write(record.sudo(), self.field_name, old_val)
                else:
                    record.write({self.field_name: old_val})
                reverted_count += 1
                # Flip the line's own old/new values so it now reflects the reverted state
                line.sudo().write({
                    'old_value_display': line.new_value_display,
                    'new_value_display': line.old_value_display,
                    'old_value_raw': line.new_value_raw,
                    'new_value_raw': line.old_value_raw,
                    'reverted': True,
                })
            except Exception as e:
                failed_count += 1
                line.sudo().write({'error_message': str(e)})

        vals = {'failed_count': self.failed_count + failed_count}
        if reverted_count:
            # Flip the header's own old/new values so "Current Value" now shows
            # the value the records were actually reverted back to.
            vals.update({
                'old_value_display': self.new_value_display,
                'new_value_display': self.old_value_display,
                'old_value_raw': self.new_value_raw,
                'new_value_raw': self.old_value_raw,
            })
        if failed_count == 0:
            vals['state'] = 'reverted'

        self.sudo().write(vals)

        message = _("%(reverted)s record(s) reverted, %(failed)s failed.") % {
            'reverted': reverted_count,
            'failed': failed_count,
        }

        return {
            'name': _('Reverted'),
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Revert Completed'),
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'universal.field.update.log',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }


class UniversalFieldUpdateLogLine(models.Model):
    _name = 'universal.field.update.log.line'
    _description = 'Universal Field Update Log Line'

    log_id = fields.Many2one('universal.field.update.log', string="Log", ondelete='cascade', readonly=True)
    was_forced = fields.Boolean(
        string="Forced (SQL Bypass)", readonly=True, default=False,
        help="This line was written via raw SQL, bypassing ORM constraints. "
             "Reverting it will also use raw SQL, for the same reason."
    )
    res_id = fields.Integer(string="Record ID", readonly=True)
    res_name = fields.Char(string="Record Name", readonly=True)
    status = fields.Selection([
        ('updated', 'Updated'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed')
    ], string="Status", readonly=True)
    old_value_display = fields.Char(string="Old Value Display", readonly=True)
    new_value_display = fields.Char(string="New Value Display", readonly=True)
    old_value_raw = fields.Text(string="Old Value (Raw)", readonly=True)
    new_value_raw = fields.Text(string="New Value (Raw)", readonly=True)
    error_message = fields.Char(string="Error Details", readonly=True)
    reverted = fields.Boolean(string="Reverted", default=False, readonly=True, copy=False)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def _compute_display_name(self):
        if self.env.context.get('show_tech_name'):
            for rec in self:
                rec.display_name = f"{rec.field_description} ({rec.name})"
        else:
            super(IrModelFields, self)._compute_display_name()