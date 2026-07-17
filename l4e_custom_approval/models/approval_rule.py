# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class L4eApprovalRule(models.Model):
    """
    Dynamic Approval Rule — admin configures which model, which field trigger,
    what value, optional conditions, and who must approve. Zero code needed to
    add a new model: just add a rule and make that model inherit l4e.approval.mixin.
    """
    _name = 'l4e.approval.rule'
    _description = 'Dynamic Approval Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to apply to all companies.',
    )
    code = fields.Char(string="Tech Code")

    # ── Target Model ──────────────────────────────────────────────────────────
    model_id = fields.Many2one(
        'ir.model', string='Model', required=True, ondelete='cascade',
        domain=[('transient', '=', False)],
        help='The Odoo model this rule applies to (e.g. Sale Order, Purchase Order).',
    )
    model_name = fields.Char(related='model_id.model', store=True, readonly=True)

    # ── Trigger ───────────────────────────────────────────────────────────────
    trigger_field_id = fields.Many2one(
        'ir.model.fields', string='Trigger Field',
        ondelete='set null',
        domain="[('model_id', '=', model_id), ('ttype', 'not in', ['one2many', 'html'])]",
        help='When this field is written with the Trigger Value, approval is required.',
    )
    trigger_field_name = fields.Char(related='trigger_field_id.name', store=True, readonly=True)
    trigger_field_ttype = fields.Char(compute='_compute_trigger_field_ttype', store=True)

    trigger_value = fields.Char(
        string='Trigger Value',
        help=(
            'For Selection/Char: technical value (e.g. "sale", "purchase", "posted")\n'
            'For Boolean: True or False\n'
            'For Float/Integer: numeric value (e.g. 50000)\n'
            'For Many2one: use the Record picker below instead.'
        ),
    )
    # Record picker for Many2one trigger fields — user-friendly alternative to typing an ID
    trigger_value_ref = fields.Reference(
        selection='_selection_trigger_value_ref',
        string='Trigger Record',
        ondelete='set null',
        help='For Many2one trigger fields: select the record directly instead of typing an ID.\n'
             'Example: Trigger Field = Stage → select "Won" stage here.',
    )

    @api.depends('trigger_field_id')
    def _compute_trigger_field_ttype(self):
        for rec in self:
            rec.trigger_field_ttype = rec.trigger_field_id.ttype or False

    @api.model
    def _selection_trigger_value_ref(self):
        return [(m.model, m.name) for m in self.env['ir.model'].search(
            [('transient', '=', False)], order='name'
        )]

    @api.onchange('trigger_field_id')
    def _onchange_trigger_field_clear_value(self):
        """Clear value fields when trigger field changes."""
        self.trigger_value = False
        self.trigger_value_ref = False

    # ── On-Approval Action ────────────────────────────────────────────────────
    finalize_action = fields.Selection(
        [
            ('write', 'Update Field (default) — replay the blocked field write'),
            ('method', 'Call Method on Record — invoke a method instead'),
        ],
        string='On Approval', default='write', required=True,
        help=(
            'What happens when the approval is granted:\n'
            '• Update Field: replays the original field write (e.g. state → sale)\n'
            '• Call Method: calls a method on the record (e.g. action_confirm) '
            'so the full default business flow runs (delivery creation, etc.)'
        ),
    )
    finalize_method = fields.Char(
        string='Method to Call',
        help=(
            'Python method name to call on the record when approved.\n'
            'Example: action_confirm  →  record.action_confirm()\n'
            'The method is called with no arguments and with l4e_bypass_approval=True context.'
        ),
    )
    finalize_method_context = fields.Char(
        string='Method Context (JSON)',
        help=(
            'Optional extra context to pass when calling the method.\n'
            'Must be valid JSON. Example: {"validate_analytic": true}\n'
            'This is merged with l4e_bypass_approval=True automatically.'
        ),
    )

    # ── Pending / Refused state tracking (optional) ───────────────────────────
    pending_field_id = fields.Many2one(
        'ir.model.fields', string='Pending State Field',
        ondelete='set null',
        domain="[('model_id', '=', model_id), ('ttype', '=', 'selection')]",
        help='Optional. A selection field on the record to write a "pending" value while waiting.',
    )
    pending_value = fields.Char(
        string='Pending Value',
        help='Value written to Pending State Field while approval is pending.',
    )
    refused_value = fields.Char(
        string='Refused Value',
        help='Value written to Pending State Field when the request is refused. Leave empty to keep current.',
    )

    # ── Conditions ────────────────────────────────────────────────────────────
    condition_ids = fields.One2many(
        'l4e.approval.rule.condition', 'rule_id', string='Conditions',
        help='Additional conditions. If none, the rule triggers for all records.',
    )
    condition_logic = fields.Selection(
        [('and', 'All conditions must match (AND)'), ('or', 'Any condition matches (OR)')],
        string='Condition Logic', default='and', required=True,
    )

    # ── Approvers ─────────────────────────────────────────────────────────────
    approver_ids = fields.One2many(
        'l4e.approval.rule.approver', 'rule_id', string='Approvers',
    )
    approval_mode = fields.Selection(
        [
            ('any', 'Any one approver is enough'),
            ('all', 'All approvers must approve'),
            ('sequential', 'Sequential — level by level (use Sequence)'),
        ],
        string='Approval Mode', default='all', required=True,
    )

    # ── Notifications ─────────────────────────────────────────────────────────
    notify_requester = fields.Boolean(
        string='Notify Requester on Decision', default=True,
    )
    send_dm = fields.Boolean(
        string='Send Direct Message (DM)', default=True,
        help='Send an in-app chat DM to approvers and requester.',
    )
    send_email = fields.Boolean(
        string='Send Email', default=True,
        help='Send an email notification to approvers and requester.',
    )

    # Extra notification users
    notify_extra_request_ids = fields.Many2many(
        'res.users',
        relation='l4e_approval_rule_notify_req_rel',
        column1='rule_id', column2='user_id',
        string='Also Notify on Request',
        help='Additional users notified when a new approval request is created.',
    )
    notify_extra_decision_ids = fields.Many2many(
        'res.users',
        relation='l4e_approval_rule_notify_dec_rel',
        column1='rule_id', column2='user_id',
        string='Also Notify on Decision',
        help='Additional users notified when the request is approved or refused.',
    )

    # Configurable message templates (support {record_name}, {rule_name}, etc.)
    request_message_tmpl = fields.Text(
        string='Request Notification Message',
        default=(
            'Your approval is required for: {record_name}\n'
            'Rule: {rule_name}\n'
            'Requested by: {requester_name}\n\n'
            'Please open the approval request and take action.'
        ),
        help=(
            'Message sent to approvers when a request is created.\n'
            'Placeholders: {record_name}, {rule_name}, {requester_name}, {model_name}'
        ),
    )
    decision_message_tmpl = fields.Text(
        string='Decision Notification Message',
        default=(
            'Your approval request for: {record_name}\n'
            'Rule: {rule_name}\n'
            'Decision: {decision}\n'
            'By: {approver_name}\n'
            '{note}'
        ),
        help=(
            'Message sent to the requester after approve/refuse.\n'
            'Placeholders: {record_name}, {rule_name}, {decision}, {approver_name}, {note}'
        ),
    )

    note = fields.Html(
        string='Note for Approvers',
        help='Optional note shown inside the approval request (instructions, policy, etc.).',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Business logic
    # ─────────────────────────────────────────────────────────────────────────

    def _match_record(self, record, incoming_value):
        """
        Return True if this rule should trigger for the given record and
        incoming trigger-field value.
        """
        self.ensure_one()

        # Company filter
        if self.company_id and hasattr(record, 'company_id') and record.company_id:
            if record.company_id != self.company_id:
                return False

        # Trigger value must match
        # If trigger_value_ref is set (Many2one record picker), use its ID
        ttype = self.trigger_field_id.ttype
        if self.trigger_value_ref:
            expected = self.trigger_value_ref.id
            incoming = self._cast_value(incoming_value, 'many2one')
        else:
            expected = self._cast_value(self.trigger_value, ttype)
            incoming = self._cast_value(incoming_value, ttype)
        if incoming != expected:
            return False

        # Evaluate conditions
        conditions = self.condition_ids
        if not conditions:
            return True

        results = [cond._evaluate(record) for cond in conditions]
        return all(results) if self.condition_logic == 'and' else any(results)

    @staticmethod
    def _cast_value(value, ttype):
        """Cast a string representation to the native Python type for comparison."""
        if value is None:
            return None
        try:
            if ttype in ('integer', 'many2one'):
                return int(value)
            if ttype in ('float', 'monetary'):
                return float(value)
            if ttype == 'boolean':
                return str(value).strip().lower() in ('true', '1', 'yes')
            return str(value)
        except (ValueError, TypeError):
            return str(value)

    def resolve_approvers(self, record):
        """
        Return a sorted list of (sequence, res.users recordset) representing
        each approval level for the given record.
        """
        self.ensure_one()
        levels = {}
        for cfg in self.approver_ids.sorted('sequence'):
            users = cfg.resolve_users(record)
            if users:
                levels.setdefault(cfg.sequence, self.env['res.users'])
                levels[cfg.sequence] |= users
        return sorted(levels.items())


class L4eApprovalRuleCondition(models.Model):
    """
    A single condition line on a Dynamic Approval Rule.

    Supports two evaluation modes:
    1. Direct field:  record.amount_total >= 50000
    2. Dotted path:  record.opportunity_id.po_date  (traverse one Many2one hop)

    For Many2one value comparison, use value_ref (record picker) instead of
    typing an ID manually in the value field.
    """
    _name = 'l4e.approval.rule.condition'
    _description = 'Approval Rule Condition'
    _order = 'sequence, id'

    rule_id = fields.Many2one('l4e.approval.rule', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)

    # ── Level 1: field on the main model ──────────────────────────────────────
    field_id = fields.Many2one(
        'ir.model.fields', string='Field',
        ondelete='set null',
        domain="[('model_id', '=', parent.model_id), ('ttype', 'not in', ['one2many', 'html'])]",
    )
    field_name = fields.Char(related='field_id.name', store=True, readonly=True)
    # Stored as Char (computed, not related) to avoid Selection type-mismatch
    field_ttype = fields.Char(string='Field Type', compute='_compute_field_ttype', store=True)

    # ── Level 2: sub-field on the related model (dotted path) ─────────────────
    related_model_id = fields.Many2one(
        'ir.model', string='Related Model',
        compute='_compute_related_model', store=True, readonly=True,
        help='Automatically set when Field is a Many2one.',
    )
    related_field_id = fields.Many2one(
        'ir.model.fields', string='Sub-Field',
        ondelete='set null',
        domain="[('model_id', '=', related_model_id), ('ttype', 'not in', ['one2many', 'html'])]",
        help='Optional. Pick a field from the related model to create a dotted path condition.\n'
             'Example: Field = Opportunity, Sub-Field = PO Date',
    )
    related_field_name = fields.Char(related='related_field_id.name', store=True, readonly=True)
    related_field_ttype = fields.Char(
        string='Sub-Field Type', compute='_compute_related_field_ttype', store=True,
    )

    # ── Operator ──────────────────────────────────────────────────────────────
    operator = fields.Selection(
        [
            ('=', '= (equals)'),
            ('!=', '≠ (not equals)'),
            ('>', '> (greater than)'),
            ('<', '< (less than)'),
            ('>=', '≥ (greater or equal)'),
            ('<=', '≤ (less or equal)'),
            ('in', 'in (comma-separated values)'),
            ('not_in', 'not in (comma-separated values)'),
            ('set', 'is set'),
            ('not_set', 'is not set'),
        ],
        string='Operator', required=True, default='=',
    )

    # ── Value: plain text for simple types ────────────────────────────────────
    value = fields.Char(
        string='Value',
        help=(
            'For simple types (char, int, float, bool, selection).\n'
            '• in / not in: comma-separated (e.g. draft,sent  or  1,2,3)\n'
            '• Boolean: True or False\n'
            'For Many2one fields: use the Record picker below instead.'
        ),
    )

    # ── Value: record picker for Many2one fields ──────────────────────────────
    value_ref = fields.Reference(
        selection='_selection_value_ref',
        string='Record',
        ondelete='set null',
        help='Pick a record for Many2one field comparisons. '
             'Select the model first, then the record.',
    )

    # ── Computes ──────────────────────────────────────────────────────────────

    @api.depends('field_id')
    def _compute_field_ttype(self):
        for rec in self:
            rec.field_ttype = rec.field_id.ttype or False

    @api.depends('field_id', 'field_id.ttype', 'field_id.relation')
    def _compute_related_model(self):
        IrModel = self.env['ir.model']
        for rec in self:
            if rec.field_id and rec.field_id.ttype == 'many2one' and rec.field_id.relation:
                rec.related_model_id = IrModel.search(
                    [('model', '=', rec.field_id.relation)], limit=1
                )
            else:
                rec.related_model_id = False

    @api.depends('related_field_id')
    def _compute_related_field_ttype(self):
        for rec in self:
            rec.related_field_ttype = rec.related_field_id.ttype or False

    @api.model
    def _selection_value_ref(self):
        """All non-transient models available as reference targets."""
        models = self.env['ir.model'].search(
            [('transient', '=', False)], order='name'
        )
        return [(m.model, m.name) for m in models]

    @api.onchange('field_id')
    def _onchange_field_id_clear(self):
        """Clear sub-field and value_ref when the primary field changes."""
        self.related_field_id = False
        self.value_ref = False

    @api.onchange('related_field_id')
    def _onchange_related_field_clear(self):
        self.value_ref = False

    # ── Evaluation engine ─────────────────────────────────────────────────────

    def _evaluate(self, record):
        """Evaluate this condition against a single record. Returns bool."""
        self.ensure_one()
        if not self.field_name:
            return True

        # --- Read value from record (direct or dotted path) ---
        rec_val = getattr(record, self.field_name, None)

        if self.related_field_id and self.related_field_name:
            # Dotted path: traverse the Many2one to the related record
            if not rec_val or (hasattr(rec_val, 'id') and not rec_val.id):
                rec_val = False
            else:
                rec_val = getattr(rec_val, self.related_field_name, None)
            ttype = self.related_field_ttype or 'char'
        else:
            ttype = self.field_ttype or 'char'

        # Normalize Many2one/recordset → id
        if hasattr(rec_val, '_name'):
            # Many2one: single record → get id
            # Many2many/One2many: multiple records → get list of ids
            _ids = getattr(rec_val, '_ids', ())
            if len(_ids) > 1:
                rec_val = list(_ids)   # [1, 2, 3] — use is_set/not_set/in/not_in
            else:
                rec_val = _ids[0] if _ids else False

        op = self.operator
        if op == 'set':
            return bool(rec_val)
        if op == 'not_set':
            return not bool(rec_val)

        # --- Determine comparison value ---
        if self.value_ref:
            # Record picker: use the selected record's ID
            raw = str(self.value_ref.id)
            ttype = 'many2one'
        else:
            raw = self.value or ''

        if op in ('in', 'not_in'):
            items = [v.strip() for v in raw.split(',') if v.strip()]
            if ttype in ('integer', 'many2one'):
                try:
                    items = [int(v) for v in items]
                except ValueError:
                    pass
            elif ttype in ('float', 'monetary'):
                try:
                    items = [float(v) for v in items]
                except ValueError:
                    pass
            return (rec_val in items) if op == 'in' else (rec_val not in items)

        cond_val = L4eApprovalRule._cast_value(raw, ttype)
        try:
            if op == '=':
                return rec_val == cond_val
            if op == '!=':
                return rec_val != cond_val
            rv = rec_val or 0
            if op == '>':
                return rv > cond_val
            if op == '<':
                return rv < cond_val
            if op == '>=':
                return rv >= cond_val
            if op == '<=':
                return rv <= cond_val
        except TypeError:
            pass
        return False


class L4eApprovalRuleApprover(models.Model):
    """Approver configuration line on a Dynamic Approval Rule."""
    _name = 'l4e.approval.rule.approver'
    _description = 'Approval Rule Approver'
    _order = 'sequence, id'

    rule_id = fields.Many2one('l4e.approval.rule', ondelete='cascade', required=True)
    sequence = fields.Integer(
        string='Level', default=10,
        help='Lower = first to approve. Same sequence = same level (parallel).',
    )

    approver_type = fields.Selection(
        [
            ('user', 'Specific User'),
            ('group', 'User Group (any member)'),
            ('field', 'Field on Record → User'),
        ],
        string='Approver Type', required=True, default='user',
    )

    user_id = fields.Many2one(
        'res.users', string='User', domain=[('share', '=', False)],
    )
    group_id = fields.Many2one('res.groups', string='Group')
    field_id = fields.Many2one(
        'ir.model.fields', string='User Field on Record',
        ondelete='set null',
        domain="[('model_id', '=', parent.model_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.users')]",
        help='A Many2one → res.users field on the record. Resolved at runtime.',
    )

    label = fields.Char(string='Approver', compute='_compute_label', store=True)

    @api.depends('approver_type', 'user_id', 'group_id', 'field_id')
    def _compute_label(self):
        for rec in self:
            if rec.approver_type == 'user':
                rec.label = rec.user_id.name or ''
            elif rec.approver_type == 'group':
                rec.label = rec.group_id.full_name or ''
            elif rec.approver_type == 'field':
                rec.label = rec.field_id.field_description or ''
            else:
                rec.label = ''

    def resolve_users(self, record):
        """Return the actual res.users recordset for this approver config."""
        self.ensure_one()
        Users = self.env['res.users']
        if self.approver_type == 'user' and self.user_id:
            return self.user_id
        if self.approver_type == 'group' and self.group_id:
            return self.group_id.users.filtered(lambda u: not u.share)
        if self.approver_type == 'field' and self.field_id:
            val = getattr(record, self.field_id.name, None)
            if val and hasattr(val, '_name') and val._name == 'res.users':
                return val
        return Users
