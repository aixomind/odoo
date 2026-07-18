# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class UniversalFieldUpdater(models.TransientModel):
    _name = 'universal.field.updater'
    _description = 'Universal Field Updater'

    name = fields.Char(default="Universal Field Transfer")

    allowed_model_ids = fields.Many2many('ir.model', string="Allowed Models")
    model_id = fields.Many2one('ir.model', string='Model')
    model_name = fields.Char(related='model_id.model', string="Technical Model", readonly=True)
    
    update_all = fields.Boolean(string="All", default=False)

    force_bypass = fields.Boolean(
        string="Force Update (Bypass ORM Restrictions)",
        default=False,
        help="Writes directly via SQL instead of record.write(), skipping any "
             "Python-level constraints (e.g. locked/posted document guards). "
             "Use with caution: model-level Python constraints, workflow "
             "triggers and field-level business logic (onchange/compute "
             "cascades, tracking, mail followers, etc.) will NOT run."
    )

    is_global = fields.Boolean(
        string="Global",
        help="Instead of picking one model/field, pick a reference record "
             "(e.g. a Partner or a User) and scan every module for any "
             "record that points to it, so you can replace it everywhere "
             "in one shot."
    )
    global_model_id = fields.Many2one('ir.model', string="Reference Type", domain=[('transient', '=', False)])
    global_model_name = fields.Char(related='global_model_id.model', string="Reference Technical Model", readonly=True)

    global_old_value_m2o = fields.Char(string="Current Value")  # dynamic_record_selector, relation_field=global_model_name
    global_new_value_m2o = fields.Char(string="Replace With")   # dynamic_record_selector, relation_field=global_model_name

    global_line_ids = fields.One2many('universal.field.updater.global.line', 'wizard_id', string="Global Matches")
    global_selected_count = fields.Integer(string="Models Selected", compute="_compute_global_selected_count")
    
    field_id = fields.Many2one('ir.model.fields', string='Field')
    field_name = fields.Char(related='field_id.name', string="Technical Field", readonly=True)
    field_label = fields.Char(related='field_id.field_description', string="Field Label", readonly=True)
    field_type = fields.Char(string="Field Type", compute="_compute_field_type", store=True)
    relation_model = fields.Char(related='field_id.relation', string="Related Model", readonly=True)

    # Current value fields for different types
    old_value_char = fields.Char(string="Current Value (Text/Numeric)")
    old_value_bool = fields.Selection([('true', 'True'), ('false', 'False')], string="Current Value (Boolean)")
    old_value_selection_id = fields.Many2one('universal.field.selection.option', string="Current Value (Selection)", domain="[('wizard_id', '=', id), ('is_filter_option', '=', False)]")
    old_value_m2o = fields.Char(string="Current Value (Relational)") # Used with dynamic_record_selector widget
    old_value_date = fields.Date(string="Current Value (Date)")
    old_value_datetime = fields.Datetime(string="Current Value (Datetime)")

    # Replace with fields
    new_value_char = fields.Char(string="Replace With (Text/Numeric)")
    new_value_bool = fields.Selection([('true', 'True'), ('false', 'False')], string="Replace With (Boolean)")
    new_value_selection_id = fields.Many2one('universal.field.selection.option', string="Replace With (Selection)", domain="[('wizard_id', '=', id), ('is_filter_option', '=', False)]")
    new_value_m2o = fields.Char(string="Replace With (Relational)") # Used with dynamic_record_selector widget
    new_value_date = fields.Date(string="Replace With (Date)")
    new_value_datetime = fields.Datetime(string="Replace With (Datetime)")

    # Optional filter — narrows the records found by field_id/old_value to a
    # smaller subset (or a single record) matching a second field/value.
    filter_field_id = fields.Many2one('ir.model.fields', string='Filter By Field')
    filter_field_name = fields.Char(related='filter_field_id.name', string="Filter Technical Field", readonly=True)
    filter_field_label = fields.Char(related='filter_field_id.field_description', string="Filter Field Label", readonly=True)
    filter_field_type = fields.Char(string="Filter Field Type", compute="_compute_filter_field_type", store=True)
    filter_relation_model = fields.Char(related='filter_field_id.relation', string="Filter Related Model", readonly=True)

    filter_value_char = fields.Char(string="Filter Value (Text/Numeric)")
    filter_value_bool = fields.Selection([('true', 'True'), ('false', 'False')], string="Filter Value (Boolean)")
    filter_value_selection_id = fields.Many2one('universal.field.selection.option', string="Filter Value (Selection)", domain="[('wizard_id', '=', id), ('is_filter_option', '=', True)]")
    filter_value_m2o = fields.Char(string="Filter Value (Relational)")  # Used with dynamic_record_selector widget
    filter_value_date = fields.Date(string="Filter Value (Date)")
    filter_value_datetime = fields.Datetime(string="Filter Value (Datetime)")

    line_ids = fields.One2many('universal.field.updater.line', 'wizard_id', string="Target Records")
    
    record_count = fields.Integer(string="Records Found", compute="_compute_counts", store=True)
    selected_count = fields.Integer(string="Records Selected", compute="_compute_counts", store=True)
    warning_message = fields.Char(string="Limit Warning", readonly=True)

    @api.constrains('is_global', 'model_id', 'field_id')
    def _check_required_by_mode(self):
        for rec in self:
            if rec.is_global:
                continue
            # Only enforce once single-field mode has actually been touched —
            # a blank new wizard shouldn't block itself from being saved/discarded.
            if not rec.model_id and not rec.field_id:
                continue
            if not rec.model_id:
                raise ValidationError(_("Model is required."))
            if not rec.field_id:
                raise ValidationError(_("Field is required."))

    @api.model
    def _referencable_models(self):
        models = self.env['ir.model'].search([('transient', '=', False)])
        return [(model.model, model.name) for model in models]

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_id = False
        self.filter_field_id = False
        self._clear_value_fields()
        self._clear_filter_value_fields()
        self.line_ids = [(5, 0, 0)]
        self.warning_message = False
        if self.model_id:
            domain = [
                ('model_id', '=', self.model_id.id),
                ('store', '=', True),
                ('readonly', '=', False),
                ('name', 'not in', ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update']),
                ('ttype', 'in', ['char', 'text', 'integer', 'float', 'monetary', 'boolean', 'selection', 'date', 'datetime', 'many2one'])
            ]
            fields_data = self.env['ir.model.fields'].search(domain)
            return {'domain': {'field_id': [('id', 'in', fields_data.ids)]}}
        return {'domain': {'field_id': [('id', '=', 0)]}}

    @api.onchange('field_id')
    def _onchange_field_id(self):
        self._clear_value_fields()
        self.line_ids = [(5, 0, 0)]
        self.warning_message = False
        
        if not self.field_id:
            return
            
        self._validate_selected_field()
        
        if self.field_type == 'selection':
            # Clean old options for this wizard (leave filter options alone)
            self.env['universal.field.selection.option'].search([
                ('wizard_id', '=', self._origin.id or self.id),
                ('is_filter_option', '=', False),
            ]).unlink()
            
            model_class = self.env[self.model_name]
            field_obj = model_class._fields.get(self.field_name)
            if field_obj and hasattr(field_obj, 'selection'):
                selection_list = []
                if callable(field_obj.selection):
                    selection_list = field_obj.selection(self.env)
                elif isinstance(field_obj.selection, list):
                    selection_list = field_obj.selection
                
                options_to_create = []
                for item in selection_list:
                    options_to_create.append((0, 0, {
                        'key': str(item[0]),
                        'value': str(item[1]),
                    }))
                if options_to_create:
                    self.write({'old_value_selection_id': False, 'new_value_selection_id': False})
                    # Use standard format for updates in active view context
                    return {'value': {'old_value_selection_id': False, 'new_value_selection_id': False},
                            'domain': {'old_value_selection_id': [('wizard_id', '=', self.id), ('is_filter_option', '=', False)],
                                       'new_value_selection_id': [('wizard_id', '=', self.id), ('is_filter_option', '=', False)]}}

    @api.onchange('filter_field_id')
    def _onchange_filter_field_id(self):
        self._clear_filter_value_fields()
        self.line_ids = [(5, 0, 0)]
        self.warning_message = False

        if not self.filter_field_id:
            return

        self._validate_selected_filter_field()

        if self.filter_field_type == 'selection':
            self.env['universal.field.selection.option'].search([
                ('wizard_id', '=', self._origin.id or self.id),
                ('is_filter_option', '=', True),
            ]).unlink()

            model_class = self.env[self.model_name]
            field_obj = model_class._fields.get(self.filter_field_name)
            if field_obj and hasattr(field_obj, 'selection'):
                selection_list = []
                if callable(field_obj.selection):
                    selection_list = field_obj.selection(self.env)
                elif isinstance(field_obj.selection, list):
                    selection_list = field_obj.selection

                for item in selection_list:
                    self.env['universal.field.selection.option'].create({
                        'wizard_id': self._origin.id or self.id,
                        'key': str(item[0]),
                        'value': str(item[1]),
                        'is_filter_option': True,
                    })

                return {'domain': {'filter_value_selection_id': [
                    ('wizard_id', '=', self.id), ('is_filter_option', '=', True)
                ]}}
                
    @api.depends('global_line_ids.selected')
    def _compute_global_selected_count(self):
        for rec in self:
            rec.global_selected_count = len(rec.global_line_ids.filtered('selected'))
            
    

    @api.onchange('is_global')
    def _onchange_is_global(self):
        # The two modes are mutually exclusive — reset the other one so
        # stale selections can't leak into apply().
        if self.is_global:
            self.model_id = False
            self.field_id = False
            self.line_ids = [(5, 0, 0)]
        else:
            self.global_model_id = False
            self.global_old_value_m2o = False
            self.global_new_value_m2o = False
            self.global_line_ids = [(5, 0, 0)]

    @api.onchange('global_model_id', 'global_old_value_m2o')
    def _onchange_global_reset(self):
        self.global_line_ids = [(5, 0, 0)]

    def _clear_value_fields(self):
        self.old_value_char = False
        self.new_value_char = False
        self.old_value_bool = False
        self.new_value_bool = False
        self.old_value_selection_id = False
        self.new_value_selection_id = False
        self.old_value_m2o = False
        self.new_value_m2o = False
        self.old_value_date = False
        self.new_value_date = False
        self.old_value_datetime = False
        self.new_value_datetime = False
        
    def _clear_filter_value_fields(self):
        self.filter_value_char = False
        self.filter_value_bool = False
        self.filter_value_selection_id = False
        self.filter_value_m2o = False
        self.filter_value_date = False
        self.filter_value_datetime = False

    def _validate_selected_field(self):
        self.ensure_one()
        if not self.field_id:
            return
        unsafe_fields = ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update']
        if self.field_id.name in unsafe_fields:
            raise UserError(_("Modifying the field '%s' is not allowed for security reasons.") % self.field_id.name)
        if self.field_id.model_id.model != self.model_id.model:
            raise UserError(_("The selected field does not belong to the selected model."))
        supported_types = ['char', 'text', 'integer', 'float', 'monetary', 'boolean', 'selection', 'date', 'datetime', 'many2one']
        if self.field_type not in supported_types:
            raise UserError(_("Field type '%s' is not supported.") % self.field_type)
        
    def _validate_selected_filter_field(self):
        self.ensure_one()
        if not self.filter_field_id:
            return
        if self.filter_field_id.model_id.model != self.model_id.model:
            raise UserError(_("The filter field does not belong to the selected model."))
        supported_types = ['char', 'text', 'integer', 'float', 'monetary', 'boolean', 'selection', 'date', 'datetime', 'many2one']
        if self.filter_field_type not in supported_types:
            raise UserError(_("Filter field type '%s' is not supported.") % self.filter_field_type)

    @api.model
    def default_get(self, fields_list):
        res = super(UniversalFieldUpdater, self).default_get(fields_list)
        active_models = list(self.env.registry.keys())
        domain_models = self.env['ir.model'].search([
            ('model', 'in', active_models),
            ('transient', '=', False)
        ])
        res['allowed_model_ids'] = [(6, 0, domain_models.ids)]
        return res

    @api.depends('field_id')
    def _compute_field_type(self):
        for rec in self:
            rec.field_type = rec.field_id.ttype if rec.field_id else False
            
    @api.depends('filter_field_id')
    def _compute_filter_field_type(self):
        for rec in self:
            rec.filter_field_type = rec.filter_field_id.ttype if rec.filter_field_id else False

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_counts(self):
        for rec in self:
            rec.record_count = len(rec.line_ids)
            rec.selected_count = len(rec.line_ids.filtered(lambda l: l.selected))

    def _get_current_value(self):
        self.ensure_one()
        if self.update_all:
            return False
        ftype = self.field_type
        if ftype in ('char', 'text'):
            return self.old_value_char or ""
        elif ftype == 'integer':
            if not self.old_value_char:
                raise UserError(_("Please specify a Current Value."))
            try:
                return int(self.old_value_char)
            except ValueError:
                raise UserError(_("Current Value is not a valid integer."))
        elif ftype in ('float', 'monetary'):
            if not self.old_value_char:
                raise UserError(_("Please specify a Current Value."))
            try:
                return float(self.old_value_char)
            except ValueError:
                raise UserError(_("Current Value is not a valid float."))
        elif ftype == 'boolean':
            if not self.old_value_bool:
                raise UserError(_("Please select a Current Value (Boolean)."))
            return self.old_value_bool == 'true'
        elif ftype == 'selection':
            if not self.old_value_selection_id:
                raise UserError(_("Please select a Current Value option."))
            return self.old_value_selection_id.key
        elif ftype == 'many2one':
            if not self.old_value_m2o:
                raise UserError(_("Please search and select a Current Value record."))
            try:
                return int(self.old_value_m2o)
            except ValueError:
                raise UserError(_("Invalid relational record selected."))
        elif ftype == 'date':
            if not self.old_value_date:
                raise UserError(_("Please select a Current Value date."))
            return self.old_value_date
        elif ftype == 'datetime':
            if not self.old_value_datetime:
                raise UserError(_("Please select a Current Value datetime."))
            return self.old_value_datetime
        raise UserError(_("Unsupported field type."))

    def _get_new_value(self):
        self.ensure_one()
        ftype = self.field_type
        if ftype in ('char', 'text'):
            return self.new_value_char or False
        elif ftype == 'integer':
            if not self.new_value_char:
                return False
            try:
                return int(self.new_value_char)
            except ValueError:
                raise UserError(_("Replace With value is not a valid integer."))
        elif ftype in ('float', 'monetary'):
            if not self.new_value_char:
                return False
            try:
                return float(self.new_value_char)
            except ValueError:
                raise UserError(_("Replace With value is not a valid float."))
        elif ftype == 'boolean':
            if not self.new_value_bool:
                raise UserError(_("Please select a Replace With value (Boolean)."))
            return self.new_value_bool == 'true'
        elif ftype == 'selection':
            if not self.new_value_selection_id:
                return False
            return self.new_value_selection_id.key
        elif ftype == 'many2one':
            if not self.new_value_m2o:
                return False
            try:
                return int(self.new_value_m2o)
            except ValueError:
                raise UserError(_("Invalid relational record selected."))
        elif ftype == 'date':
            if not self.new_value_date:
                return False
            return self.new_value_date
        elif ftype == 'datetime':
            if not self.new_value_datetime:
                return False
            return self.new_value_datetime
        raise UserError(_("Unsupported field type."))
    
    def _get_filter_value(self):
        self.ensure_one()
        if not self.filter_field_id:
            return None
        ftype = self.filter_field_type
        if ftype in ('char', 'text'):
            return self.filter_value_char or ""
        elif ftype == 'integer':
            if not self.filter_value_char:
                raise UserError(_("Please specify a Filter Value."))
            try:
                return int(self.filter_value_char)
            except ValueError:
                raise UserError(_("Filter Value is not a valid integer."))
        elif ftype in ('float', 'monetary'):
            if not self.filter_value_char:
                raise UserError(_("Please specify a Filter Value."))
            try:
                return float(self.filter_value_char)
            except ValueError:
                raise UserError(_("Filter Value is not a valid float."))
        elif ftype == 'boolean':
            if not self.filter_value_bool:
                raise UserError(_("Please select a Filter Value (Boolean)."))
            return self.filter_value_bool == 'true'
        elif ftype == 'selection':
            if not self.filter_value_selection_id:
                raise UserError(_("Please select a Filter Value option."))
            return self.filter_value_selection_id.key
        elif ftype == 'many2one':
            if not self.filter_value_m2o:
                raise UserError(_("Please search and select a Filter Value record."))
            try:
                return int(self.filter_value_m2o)
            except ValueError:
                raise UserError(_("Invalid relational record selected for Filter Value."))
        elif ftype == 'date':
            if not self.filter_value_date:
                raise UserError(_("Please select a Filter Value date."))
            return self.filter_value_date
        elif ftype == 'datetime':
            if not self.filter_value_datetime:
                raise UserError(_("Please select a Filter Value datetime."))
            return self.filter_value_datetime
        raise UserError(_("Unsupported field type for filter."))

    def _get_display_value(self, val, ftype):
        if val is False or val is None or val == '':
            return ""
        if ftype == 'boolean':
            return "True" if val else "False"
        if ftype == 'selection':
            option = self.env['universal.field.selection.option'].search([
                ('wizard_id', '=', self.id),
                ('key', '=', str(val))
            ], limit=1)
            if option:
                return option.value
            return str(val)
        if ftype == 'many2one':
            try:
                rec = self.env[self.relation_model].browse(int(val))
                if rec.exists():
                    return rec.display_name or f"ID: {val}"
            except Exception:
                pass
            return f"ID: {val}"
        return str(val)

    def action_find_records(self):
        self.ensure_one()
        self.line_ids = [(5, 0, 0)]
        self.warning_message = False
        
        self._validate_selected_field()
        self._validate_selected_filter_field()
        old_val = self._get_current_value()
        new_val = self._get_new_value()
        
        model_name = self.model_name
        field_name = self.field_name
        
        domain = [] if self.update_all else [(field_name, '=', old_val)]

        if self.filter_field_id:
            filter_val = self._get_filter_value()
            domain.append((self.filter_field_id.name, '=', filter_val))
        
        # Verify read access
        if not self.env[model_name].check_access_rights('read', raise_exception=False):
            raise AccessError(_("You do not have read access to model: %s") % self.model_id.name)
            
        total_count = self.env[model_name].search_count(domain)
        
        if total_count == 0:
            raise UserError(_("No records found in %s matching the criteria.") % self.model_id.name)
            
        records = self.env[model_name].search(domain)
            
        lines = []
        for record in records:
            # For each record, read its actual current value dynamically
            db_val = record[field_name]
            if self.field_type == 'many2one':
                db_val = db_val.id if db_val else False
            lines.append((0, 0, {
                'res_id': record.id,
                'res_name': record.display_name or f"ID: {record.id}",
                'current_value_display': self._get_display_value(db_val, self.field_type),
                'new_value_display': self._get_display_value(new_val, self.field_type),
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'universal.field.updater',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _sql_write(self, record, field_name, new_val):
        """Raw-SQL fallback used when `force_bypass` is enabled.

        record.write() enforces Python-level guards (e.g. account.move's
        posted/locked entry restriction). Every field this wizard allows
        is a plain stored column — including many2one, which stores the
        related id directly — so a direct UPDATE is safe here. This
        mirrors the approach used by l4e_change_journal_item for posted
        journal entries.
        """
        table = record._table
        column = field_name  # ir.model.fields name == DB column for all ttypes this wizard allows
        self.env.cr.execute(
            'UPDATE "%s" SET "%s" = %%s WHERE id = %%s' % (table, column),
            (new_val, record.id),
        )
        # Drop the cached value(s) so the ORM/UI reflect the DB change immediately.
        record.invalidate_recordset([field_name])
        
    def _sql_write_m2m(self, record, field_name, old_id, new_id):
        """Raw-SQL fallback for many2many fields (force_bypass mode).
        Many2many values live in a separate pivot table, not a column on
        the record's own table, so this can't reuse _sql_write."""
        f = record._fields[field_name]
        table, col1, col2 = f.relation, f.column1, f.column2
        self.env.cr.execute(
            'DELETE FROM "%s" WHERE "%s" = %%s AND "%s" = %%s' % (table, col1, col2),
            (record.id, old_id),
        )
        self.env.cr.execute(
            'INSERT INTO "%s" ("%s", "%s") VALUES (%%s, %%s) ON CONFLICT DO NOTHING' % (table, col1, col2),
            (record.id, new_id),
        )
        record.invalidate_recordset([field_name])

    def action_apply_update(self):
        self.ensure_one()
        # Security validation
        if not self.env.user.has_group('l4e_universal_field_update.group_universal_field_update_manager'):
            raise AccessError(_("Only Managers can apply universal field updates."))

        self._validate_selected_field()
        
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError(_("No records selected for update."))

        model_name = self.model_name
        field_name = self.field_name
        ftype = self.field_type
        
        # Access validation on target model
        TargetModel = self.env[model_name]
        if not TargetModel.check_access_rights('write', raise_exception=False):
            raise AccessError(_("You do not have write access to model: %s") % self.model_id.name)

        old_val = self._get_current_value()
        new_val = self._get_new_value()
        
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        
        log_lines_data = []
        
        LogModel = self.env['universal.field.update.log']

        for line in selected_lines:
            record = TargetModel.browse(line.res_id)
            # 1. Verify existence
            if not record.exists():
                failed_count += 1
                log_lines_data.append((0, 0, {
                    'res_id': line.res_id,
                    'res_name': line.res_name,
                    'status': 'failed',
                    'old_value_display': line.current_value_display,
                    'new_value_display': line.new_value_display,
                    'error_message': _("Record was deleted in the database.")
                }))
                continue

            # 2. Fetch the actual current value — needed both for the concurrency
            # check AND to support reverting later (even in "Update All" mode,
            # where each record's original value can differ).
            current_db_val = record[field_name]
            if ftype == 'many2one':
                current_db_val = current_db_val.id if current_db_val else False

            # 3. Concurrency Check: re-verify current value
            if not self.update_all and current_db_val != old_val:
                skipped_count += 1
                log_lines_data.append((0, 0, {
                    'res_id': line.res_id,
                    'res_name': line.res_name,
                    'status': 'skipped',
                    'old_value_display': self._get_display_value(current_db_val, ftype),
                    'new_value_display': line.new_value_display,
                    'error_message': _("Value was modified by another user before update.")
                }))
                continue

            # 4. Perform write
            try:
                if self.force_bypass:
                    self._sql_write(record.sudo(), field_name, new_val)
                else:
                    record.sudo().write({field_name: new_val})
                updated_count += 1
                log_lines_data.append((0, 0, {
                    'res_id': line.res_id,
                    'res_name': line.res_name,
                    'status': 'updated',
                    'old_value_display': line.current_value_display,
                    'new_value_display': line.new_value_display,
                    'old_value_raw': LogModel._serialize_value(current_db_val, ftype),
                    'new_value_raw': LogModel._serialize_value(new_val, ftype),
                    'was_forced': self.force_bypass,
                }))
            except Exception as e:
                failed_count += 1
                log_lines_data.append((0, 0, {
                    'res_id': line.res_id,
                    'res_name': line.res_name,
                    'status': 'failed',
                    'old_value_display': line.current_value_display,
                    'new_value_display': line.new_value_display,
                    'error_message': str(e)
                }))

        # Create history log
        log_rec = self.env['universal.field.update.log'].create({
            'model_name': model_name,
            'model_label': self.model_id.name,
            'field_name': field_name,
            'field_label': self.field_id.field_description,
            'field_type': ftype,
            'relation_model': self.relation_model,
            'old_value_display': self._get_display_value(old_val, ftype),
            'new_value_display': self._get_display_value(new_val, ftype),
            'old_value_raw': str(old_val),
            'new_value_raw': str(new_val),
            'requested_count': len(selected_lines),
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'failed_count': failed_count,
            'line_ids': log_lines_data,
        })
        
        # Display Success view with redirect to log
        message = _("%(updated)s records updated, %(skipped)s skipped, %(failed)s failed.") % {
            'updated': updated_count,
            'skipped': skipped_count,
            'failed': failed_count
        }
        
        return {
            'name': _('Success'),
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Field Update Completed'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'universal.field.update.log',
                    'res_id': log_rec.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }
        
    def _global_display_value(self, model_name, val):
        if not val:
            return ""
        try:
            rec = self.env[model_name].sudo().browse(int(val))
            if rec.exists():
                return rec.display_name or f"ID: {val}"
        except Exception:
            pass
        return f"ID: {val}"

    def action_global_scan(self):
        self.ensure_one()
        if not self.global_model_id or not self.global_old_value_m2o:
            raise UserError(_("Select a reference type and a current value first."))

        old_id = int(self.global_old_value_m2o)
        ref_model = self.global_model_name
        self.global_line_ids = [(5, 0, 0)]

        # Every stored many2one/many2many field, on any non-transient model,
        # pointing at the reference model (per the client's spec: match both).
        candidate_fields = self.env['ir.model.fields'].sudo().search([
            ('relation', '=', ref_model),
            ('ttype', 'in', ('many2one', 'many2many')),
            ('store', '=', True),
            ('model_id.transient', '=', False),
        ])

        lines_data = []
        seen = set()
        for f in candidate_fields:
            key = (f.model, f.name)
            if key in seen:
                continue
            seen.add(key)

            Model = self.env.get(f.model)
            if Model is None:
                continue
            if not Model.check_access_rights('read', raise_exception=False):
                continue

            # A savepoint isolates each field's query: if one field's search
            # blows up (broken SQL view, missing table, etc.) it rolls back
            # only that savepoint instead of poisoning the whole transaction
            # (which is what was causing InFailedSqlTransaction afterwards).
            count = None
            try:
                with self.env.cr.savepoint():
                    if f.ttype == 'many2one':
                        count = Model.sudo().search_count([(f.name, '=', old_id)])
                    else:  # many2many
                        count = Model.sudo().search_count([(f.name, 'in', [old_id])])
            except Exception:
                _logger.warning(
                    "Global scan: skipping %s.%s (query failed)", f.model, f.name, exc_info=True
                )
                continue

            if count:
                lines_data.append((0, 0, {
                    'model_name': f.model,
                    'model_label': f.model_id.name,
                    'field_name': f.name,
                    'field_label': f.field_description,
                    'field_ttype': f.ttype,
                    'record_count': count,
                    'selected': True,
                }))

        if not lines_data:
            raise UserError(_("No records reference this value anywhere in the database."))

        self.global_line_ids = lines_data
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'universal.field.updater',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_global_apply(self):
        self.ensure_one()
        if not self.env.user.has_group('l4e_universal_field_update.group_universal_field_update_manager'):
            raise AccessError(_("Only Managers can apply universal field updates."))

        if not self.global_old_value_m2o or not self.global_new_value_m2o:
            raise UserError(_("Select both a current value and a replacement value."))
        if self.global_old_value_m2o == self.global_new_value_m2o:
            raise UserError(_("Current value and replacement value are the same."))

        old_id = int(self.global_old_value_m2o)
        new_id = int(self.global_new_value_m2o)

        selected_lines = self.global_line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_("No models selected to update."))

        LogModel = self.env['universal.field.update.log']
        old_display = self._global_display_value(self.global_model_name, old_id)
        new_display = self._global_display_value(self.global_model_name, new_id)

        total_updated = total_failed = 0
        log_ids = []

        for gline in selected_lines:
            Model = self.env.get(gline.model_name)
            if Model is None:
                continue

            if gline.records_fetched:
                # User drilled into this model and hand-picked records —
                # honor exactly that selection (may be a subset, or none).
                chosen_ids = gline.record_ids.filtered('selected').mapped('res_id')
                records = Model.sudo().browse(chosen_ids).exists()
            else:
                # Never inspected individually — update every matching
                # record, same as before this feature existed.
                domain = [(gline.field_name, '=', old_id)] if gline.field_ttype == 'many2one' \
                    else [(gline.field_name, 'in', [old_id])]
                records = Model.sudo().search(domain)

            updated_count = failed_count = 0
            log_lines_data = []

            for record in records:
                try:
                    # Each record gets its own savepoint so one bad record
                    # (e.g. a genuine constraint violation) can't poison the
                    # transaction and silently kill the rest of the batch.
                    with self.env.cr.savepoint():
                        if gline.field_ttype == 'many2one':
                            if self.force_bypass:
                                self._sql_write(record, gline.field_name, new_id)
                            else:
                                record.write({gline.field_name: new_id})
                        else:  # many2many
                            if self.force_bypass:
                                self._sql_write_m2m(record, gline.field_name, old_id, new_id)
                            else:
                                record.write({gline.field_name: [(3, old_id, 0), (4, new_id, 0)]})
                    updated_count += 1
                    log_lines_data.append((0, 0, {
                        'res_id': record.id,
                        'res_name': record.display_name,
                        'status': 'updated',
                        'old_value_display': old_display,
                        'new_value_display': new_display,
                        'old_value_raw': LogModel._serialize_value(old_id, 'many2one'),
                        'new_value_raw': LogModel._serialize_value(new_id, 'many2one'),
                        'was_forced': self.force_bypass,
                    }))
                except Exception as e:
                    failed_count += 1
                    log_lines_data.append((0, 0, {
                        'res_id': record.id,
                        'res_name': record.display_name,
                        'status': 'failed',
                        'old_value_display': old_display,
                        'new_value_display': new_display,
                        'error_message': str(e),
                    }))

            log_rec = LogModel.create({
                'model_name': gline.model_name,
                'model_label': gline.model_label,
                'field_name': gline.field_name,
                'field_label': gline.field_label,
                'field_type': gline.field_ttype,
                'relation_model': self.global_model_name,
                'old_value_display': old_display,
                'new_value_display': new_display,
                'old_value_raw': str(old_id),
                'new_value_raw': str(new_id),
                'requested_count': len(records),
                'updated_count': updated_count,
                'skipped_count': 0,
                'failed_count': failed_count,
                'line_ids': log_lines_data,
            })
            log_ids.append(log_rec.id)
            total_updated += updated_count
            total_failed += failed_count

        message = _("%(updated)s record(s) updated across %(models)s model(s), %(failed)s failed.") % {
            'updated': total_updated,
            'models': len(selected_lines),
            'failed': total_failed,
        }

        return {
            'name': _('Global Update Completed'),
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Global Field Update Completed'),
                'message': message,
                'type': 'success' if total_failed == 0 else 'warning',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'universal.field.update.log',
                    'domain': [('id', 'in', log_ids)],
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                    'target': 'current',
                }
            }
        }

class UniversalFieldUpdaterLine(models.TransientModel):
    _name = 'universal.field.updater.line'
    _description = 'Universal Field Updater Target Record Line'

    wizard_id = fields.Many2one('universal.field.updater', string="Wizard")
    selected = fields.Boolean(string="Update", default=True)
    res_id = fields.Integer(string="Record ID")
    res_name = fields.Char(string="Record")
    current_value_display = fields.Char(string="Current Value")
    new_value_display = fields.Char(string="New Value")
    target_model_name = fields.Char(related='wizard_id.model_name', string="Target Model", readonly=True)

    def action_open_record(self):
        self.ensure_one()
        if not self.target_model_name or not self.res_id:
            return False
        record = self.env[self.target_model_name].browse(self.res_id)
        if not record.exists():
            raise UserError(_("This record no longer exists."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.target_model_name,
            'res_id': self.res_id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

class UniversalFieldSelectionOption(models.TransientModel):
    _name = 'universal.field.selection.option'
    _description = 'Universal Field Selection Option Helper'
    _rec_name = 'value'

    wizard_id = fields.Many2one('universal.field.updater', string="Wizard")
    key = fields.Char(string="Key", required=True)
    value = fields.Char(string="Value", required=True)
    is_filter_option = fields.Boolean(string="Is Filter Option", default=False)
    
class UniversalFieldUpdaterGlobalLine(models.TransientModel):
    _name = 'universal.field.updater.global.line'
    _description = 'Universal Field Updater Global Scan Line'

    wizard_id = fields.Many2one('universal.field.updater', string="Wizard")
    selected = fields.Boolean(string="Include", default=True)
    model_name = fields.Char(string="Technical Model")
    model_label = fields.Char(string="Model")
    field_name = fields.Char(string="Technical Field")
    field_label = fields.Char(string="Field")
    field_ttype = fields.Selection([
        ('many2one', 'Many2one'),
        ('many2many', 'Many2many'),
    ], string="Field Type")
    record_count = fields.Integer(string="Records Found")

    record_ids = fields.One2many(
        'universal.field.updater.global.record.line', 'global_line_id',
        string="Matching Records")
    records_fetched = fields.Boolean(
        string="Records Loaded", default=False,
        help="Set once the user has drilled into this model and picked "
             "individual records. Until then, applying the update falls "
             "back to every matching record (previous behaviour).")
    selected_record_count = fields.Integer(
        string="Selected", compute='_compute_selected_record_count')

    @api.depends('record_ids.selected')
    def _compute_selected_record_count(self):
        for rec in self:
            rec.selected_record_count = len(rec.record_ids.filtered('selected'))

    def action_view_records(self):
        self.ensure_one()
        old_val = self.wizard_id.global_old_value_m2o
        if not old_val or not self.model_name or not self.field_name:
            return False
        old_id = int(old_val)

        Model = self.env.get(self.model_name)
        if Model is None:
            raise UserError(_("The target model '%s' no longer exists.") % self.model_name)

        domain = [(self.field_name, '=', old_id)] if self.field_ttype == 'many2one' \
            else [(self.field_name, 'in', [old_id])]

        return {
            'name': _("%(model)s — %(field)s") % {'model': self.model_label, 'field': self.field_label},
            'type': 'ir.actions.act_window',
            'res_model': self.model_name,
            'domain': domain,
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'target': 'current',
        }

    def action_select_records(self):
        """Open a popup listing every matching record for this model/field
        so the user can check/uncheck exactly which ones should be updated,
        instead of the whole model being all-or-nothing."""
        self.ensure_one()
        wizard = self.wizard_id
        old_val = wizard.global_old_value_m2o
        if not old_val or not self.model_name or not self.field_name:
            raise UserError(_("Select a current value first."))
        old_id = int(old_val)

        Model = self.env.get(self.model_name)
        if Model is None:
            raise UserError(_("The target model '%s' no longer exists.") % self.model_name)

        domain = [(self.field_name, '=', old_id)] if self.field_ttype == 'many2one' \
            else [(self.field_name, 'in', [old_id])]
        records = Model.sudo().search(domain)

        # Preserve any selections already made if this is being reopened.
        previous = {line.res_id: line.selected for line in self.record_ids}

        lines = [(5, 0, 0)]
        for record in records:
            lines.append((0, 0, {
                'res_id': record.id,
                'res_name': record.display_name or f"ID: {record.id}",
                'selected': previous.get(record.id, True),
            }))
        self.record_ids = lines
        self.records_fetched = True

        return {
            'name': _("%(model)s — %(field)s") % {'model': self.model_label, 'field': self.field_label},
            'type': 'ir.actions.act_window',
            'res_model': 'universal.field.updater.global.line',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }
        
    def action_select_all_records(self):
        self.ensure_one()
        self.record_ids.write({'selected': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'universal.field.updater.global.line',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_deselect_all_records(self):
        self.ensure_one()
        self.record_ids.write({'selected': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'universal.field.updater.global.line',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_close_selection(self):
        return {'type': 'ir.actions.act_window_close'}


class UniversalFieldUpdaterGlobalRecordLine(models.TransientModel):
    _name = 'universal.field.updater.global.record.line'
    _description = 'Universal Field Updater Global Scan - Individual Record'

    global_line_id = fields.Many2one(
        'universal.field.updater.global.line', string="Global Match Line",
        ondelete='cascade')
    selected = fields.Boolean(string="Update", default=True)
    res_id = fields.Integer(string="Record ID")
    res_name = fields.Char(string="Record")
    target_model_name = fields.Char(
        related='global_line_id.model_name', string="Target Model", readonly=True)

    def action_open_record(self):
        self.ensure_one()
        if not self.target_model_name or not self.res_id:
            return False
        record = self.env[self.target_model_name].browse(self.res_id)
        if not record.exists():
            raise UserError(_("This record no longer exists."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.target_model_name,
            'res_id': self.res_id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }
