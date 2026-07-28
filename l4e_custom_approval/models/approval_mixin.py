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
from markupsafe import Markup
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class L4eApprovalMixin(models.AbstractModel):
    """
    Abstract mixin to be inherited by any model that needs dynamic approvals.
    Overrides write() to intercept trigger fields and route through the approval
    engine (l4e.approval.rule).

    Usage:
        class SaleOrder(models.Model):
            _name = 'sale.order'
            _inherit = ['sale.order', 'l4e.approval.mixin']

    That's all. No other code needed per model.
    """
    _name = 'l4e.approval.mixin'
    _description = 'L4E Dynamic Approval Mixin'

    # ── Computed approval fields added to every mixin model ───────────────────
    l4e_approval_count = fields.Integer(
        string='Approvals', compute='_compute_l4e_approval_count',
    )
    l4e_approval_state = fields.Char(
        string='Approval Status', compute='_compute_l4e_approval_state',
    )

    def _compute_l4e_approval_count(self):
        Req = self.env['l4e.approval.record.request']
        for record in self:
            record.l4e_approval_count = Req.search_count([
                ('res_model', '=', record._name),
                ('res_id', '=', record.id),
                ('state', '=', 'pending'),
            ])

    def _compute_l4e_approval_state(self):
        Req = self.env['l4e.approval.record.request']
        for record in self:
            req = Req.search([
                ('res_model', '=', record._name),
                ('res_id', '=', record.id),
            ], order='id desc', limit=1)
            record.l4e_approval_state = req.state if req else False

    # ── write() interceptor ───────────────────────────────────────────────────

    def write(self, vals):
        # Bypass flag set internally when replaying approved values
        if self.env.context.get('l4e_bypass_approval'):
            return super().write(vals)

        normal_records = self.env[self._name]

        for record in self:
            triggered_rules = record._l4e_find_triggered_rules(vals)

            if not triggered_rules:
                normal_records |= record
                continue

            # First matching rule wins (lowest sequence)
            rule = triggered_rules[0]
            trigger_field = rule.trigger_field_name

            # --- Write all non-trigger fields immediately ---
            passthrough = {k: v for k, v in vals.items() if k != trigger_field}
            if passthrough:
                super(L4eApprovalMixin, record).write(passthrough)

            # --- Capture original value BEFORE setting pending state ---
            # Used to restore the record to its pre-pending state when finalizing
            # via method call (e.g. action_confirm needs state='draft', not 'pending_approval')
            original_vals = {}
            if rule.pending_field_id:
                field_name = rule.pending_field_id.name
                orig_val = getattr(record, field_name, None)
                # Normalize Many2one recordset → id
                if hasattr(orig_val, 'id'):
                    orig_val = orig_val.id
                original_vals[field_name] = orig_val

            # --- Write pending state field if configured ---
            if rule.pending_field_id and rule.pending_value is not False:
                super(L4eApprovalMixin, record).write(
                    {rule.pending_field_id.name: rule.pending_value or False}
                )

            # --- Create approval request, blocking the trigger write ---
            blocked = {trigger_field: vals[trigger_field]}
            record._l4e_create_approval_request(rule, blocked, original_vals=original_vals)

        # --- Records with no triggered rule get the full normal write ---
        if normal_records:
            super(L4eApprovalMixin, normal_records).write(vals)

        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _l4e_find_triggered_rules(self, vals):
        """Return sorted l4e.approval.rule records that match this record + vals."""
        self.ensure_one()
        # sudo() required: rules reference ir.model.fields (trigger_field_id)
        # which is restricted to Access Rights group.
        # Keep sudo on matched so downstream access to .trigger_field_id.ttype works.
        rules = self.env['l4e.approval.rule'].sudo().search([
            ('model_name', '=', self._name),
            ('active', '=', True),
        ])
        matched = self.env['l4e.approval.rule'].sudo()
        for rule in rules:
            fname = rule.trigger_field_name
            if fname and fname in vals and rule._match_record(self, vals[fname]):
                matched |= rule
        return matched.sorted('sequence')

    def _l4e_create_approval_request(self, rule, blocked_vals, original_vals=None):
        """
        Create an l4e.approval.record.request for this record.
        blocked_vals is a dict of {field: value} that will be replayed on approval.
        original_vals is a dict of field values captured BEFORE the pending state was written,
        used to restore the record to its original state when finalize_action='method'.
        """
        self.ensure_one()

        # sudo() required: salesperson has no create on l4e.approval.record.request
        # and no create on l4e.approval.record.approver (system creates on their behalf)
        RequestModel = self.env['l4e.approval.record.request'].sudo()

        # Don't create duplicate pending requests for the same rule+record
        existing = RequestModel.search([
            ('rule_id', '=', rule.id),
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('state', '=', 'pending'),
        ], limit=1)
        if existing:
            return existing

        levels = rule.resolve_approvers(self)

        # No approvers configured → warn and auto-apply
        if not levels:
            _logger.warning(
                'L4E Approval: Rule "%s" has no approvers. Auto-applying without approval.',
                rule.name,
            )
            return super(L4eApprovalMixin, self).write(
                dict(blocked_vals,
                     **(({rule.pending_field_id.name: rule.trigger_value} if rule.pending_field_id else {})))
            )

        first_seq = levels[0][0]
        approver_lines = []
        for seq, users in levels:
            for user in users:
                approver_lines.append((0, 0, {
                    'user_id': user.id,
                    'sequence': seq,
                    'status': 'pending' if seq == first_seq else 'waiting',
                }))

        request = RequestModel.create({
            'name': f'{rule.name} — {self.display_name}',
            'rule_id': rule.id,
            'res_model': self._name,
            'res_id': self.id,
            'pending_values': json.dumps(blocked_vals),
            'original_values': json.dumps(original_vals) if original_vals else False,
            'requester_id': self.env.uid,
            'approver_ids': approver_lines,
        })

        request._notify_approvers()

        # Post to record chatter if it has mail.thread
        if hasattr(self, 'message_post'):
            self.message_post(
                body=Markup(
                    '<p>⏳ Approval required: <b>%(rule)s</b><br/>'
                    'Requested by: %(user)s</p>'
                ) % {'rule': rule.name, 'user': self.env.user.name},
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

        return request

    # ── Smart button action ───────────────────────────────────────────────────

    def action_view_l4e_approvals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Requests'),
            'res_model': 'l4e.approval.record.request',
            'view_mode': 'tree,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }
