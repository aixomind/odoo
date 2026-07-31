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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L4eApprovalRecordRequest(models.Model):
    """
    Per-record approval request created by l4e.approval.mixin when a trigger fires.
    Tracks approver lines, status, and replays the blocked write on full approval.
    """
    _name = 'l4e.approval.record.request'
    _description = 'Dynamic Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'

    name = fields.Char(string='Request', required=True, readonly=True)
    rule_id = fields.Many2one(
        'l4e.approval.rule', string='Rule', required=True,
        ondelete='restrict', readonly=True,
    )
    # Target record (generic reference)
    res_model = fields.Char(string='Model', required=True, readonly=True)
    res_id = fields.Integer(string='Record ID', required=True, readonly=True)
    res_name = fields.Char(string='Record', compute='_compute_res_name', store=False)

    state = fields.Selection(
        [
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status', default='pending', required=True,
        tracking=True,
    )

    # The blocked write values stored as JSON, replayed on approval
    pending_values = fields.Text(string='Pending Values', readonly=True)
    # Original field values captured BEFORE the pending state was written
    # Used to restore the record before calling finalize_method
    original_values = fields.Text(string='Original Values', readonly=True)

    # Requester
    requester_id = fields.Many2one(
        'res.users', string='Requested By', readonly=True,
        default=lambda self: self.env.user,
    )
    date_request = fields.Datetime(
        string='Requested On', readonly=True,
        default=fields.Datetime.now,
    )

    # Approver lines
    approver_ids = fields.One2many(
        'l4e.approval.record.approver', 'request_id', string='Approvers',
    )

    # Summary counts
    approved_count = fields.Integer(compute='_compute_counts', string='Approved')
    refused_count = fields.Integer(compute='_compute_counts', string='Refused')
    pending_count = fields.Integer(compute='_compute_counts', string='Pending')
    waiting_count = fields.Integer(compute='_compute_counts', string='Waiting')

    # Current user's approver line (for button visibility)
    my_approver_id = fields.Many2one(
        'l4e.approval.record.approver', string='My Approver Line',
        compute='_compute_my_approver_id', store=False,
    )
    can_approve = fields.Boolean(compute='_compute_my_approver_id', store=False)
    is_admin = fields.Boolean(compute='_compute_my_approver_id', store=False)

    # Rule config mirrors for display
    approval_mode = fields.Selection(related='rule_id.approval_mode', string='Mode', readonly=True)
    rule_note = fields.Html(related='rule_id.note', string='Approval Instructions', readonly=True)

    query_sale_comment = fields.Text(
        string="Approver Query",
        readonly=True
    )

    def _compute_res_name(self):
        for rec in self:
            try:
                obj = self.env[rec.res_model].browse(rec.res_id)
                rec.res_name = obj.display_name if obj.exists() else f'#{rec.res_id}'
            except Exception:
                rec.res_name = f'#{rec.res_id}'

    @api.depends('approver_ids.status')
    def _compute_counts(self):
        for rec in self:
            rec.approved_count = len(rec.approver_ids.filtered(lambda a: a.status == 'approved'))
            rec.refused_count = len(rec.approver_ids.filtered(lambda a: a.status == 'refused'))
            rec.pending_count = len(rec.approver_ids.filtered(lambda a: a.status == 'pending'))
            rec.waiting_count = len(rec.approver_ids.filtered(lambda a: a.status == 'waiting'))

    @api.depends('approver_ids.user_id', 'approver_ids.status', 'state')
    def _compute_my_approver_id(self):
        is_admin = self.env.user.has_group('base.group_system')
        for rec in self:
            line = rec.approver_ids.filtered(
                lambda a: a.user_id == self.env.user and a.status == 'pending'
            )[:1]
            rec.my_approver_id = line
            rec.is_admin = is_admin
            rec.can_approve = bool(line or is_admin) and rec.state == 'pending'

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('This request is no longer pending.'))
        is_admin = self.env.user.has_group('base.group_system')
        line = self.approver_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )[:1]
        if not line and not is_admin:
            raise UserError(_(
                'You are not a pending approver for this request, '
                'or it is not yet your turn.'
            ))
        if line:
            line.write({'status': 'approved', 'date': fields.Datetime.now()})
        else:
            # Admin override: approve all remaining pending/waiting approver lines
            override_lines = self.approver_ids.filtered(
                lambda a: a.status in ('pending', 'waiting')
            )
            override_lines.write({'status': 'approved', 'date': fields.Datetime.now()})
        self._check_completion()
        return True

    def action_refuse(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('This request is no longer pending.'))
        is_admin = self.env.user.has_group('base.group_system')
        line = self.approver_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )[:1]
        if not line and not is_admin:
            raise UserError(_(
                'You are not a pending approver for this request, '
                'or it is not yet your turn.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Approval'),
            'res_model': 'l4e.approval.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_cancel(self):
        self.ensure_one()
        if self.state not in ('pending',):
            raise UserError(_('Only pending requests can be cancelled.'))
        self.write({'state': 'cancelled'})
        self._post_to_record_chatter(_('Approval request cancelled.'))

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
        }

    def action_custom_view_record(self):
        self.ensure_one()

        #  If always sale.order
        if self.res_model == 'sale.order':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.res_id,
                'target': 'current',
            }

        # Dynamic support (BEST)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Record',
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
            'target': 'current',
        }
    
    def action_query(self):
        self.ensure_one()
        #if not self.approver_ids:
        #    raise UserError("Please select an approval record first.")

        # approval = self.approver_ids[0]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Raise Query',
            'res_model': 'sale.custom.raise.query',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'l4e.approval.record.request',
            }
        }

    # ── Completion logic ──────────────────────────────────────────────────────

    def _check_completion(self):
        """Called after any approver votes. Checks if the request is fully approved."""
        self.ensure_one()
        mode = self.rule_id.approval_mode
        approvers = self.approver_ids

        if mode == 'any':
            if approvers.filtered(lambda a: a.status == 'approved'):
                self._finalize_approve()
            elif all(a.status in ('refused', 'waiting') for a in approvers):
                self._finalize_refuse()

        elif mode == 'all':
            if all(a.status == 'approved' for a in approvers):
                self._finalize_approve()
            elif approvers.filtered(lambda a: a.status == 'refused'):
                self._finalize_refuse()

        elif mode == 'sequential':
            pending_lines = approvers.filtered(lambda a: a.status == 'pending')
            approved_lines = approvers.filtered(lambda a: a.status == 'approved')
            refused_lines = approvers.filtered(lambda a: a.status == 'refused')
            waiting_lines = approvers.filtered(lambda a: a.status == 'waiting')

            if refused_lines:
                self._finalize_refuse()
                return

            if not pending_lines:
                # Current level fully approved — activate next level
                if waiting_lines:
                    next_seq = min(waiting_lines.mapped('sequence'))
                    next_level = waiting_lines.filtered(lambda a: a.sequence == next_seq)
                    next_level.write({'status': 'pending'})
                    self._notify_approvers(next_level.mapped('user_id'))
                else:
                    # All levels done
                    if all(a.status == 'approved' for a in approvers):
                        self._finalize_approve()

    def _finalize_approve(self):
        """All required approvals received — replay the blocked write or call the configured method."""
        self.ensure_one()
        self.write({'state': 'approved'})

        rule = self.rule_id.sudo()

        if rule.finalize_action == 'method' and rule.finalize_method:
            # Call the configured method on the record instead of replaying the write
            try:
                record = self.env[self.res_model].browse(self.res_id)
                if record.exists():
                    # Build context: start with l4e bypass, then merge any extra context from rule
                    ctx = {'l4e_bypass_approval': True}
                    if rule.finalize_method_context:
                        try:
                            extra_ctx = json.loads(rule.finalize_method_context)
                            if isinstance(extra_ctx, dict):
                                ctx.update(extra_ctx)
                        except (json.JSONDecodeError, ValueError):
                            _logger.warning(
                                'L4E Approval: invalid JSON in finalize_method_context for rule %s, ignoring.',
                                rule.name,
                            )

                    # Restore the record to its original state BEFORE the pending state was set.
                    # This ensures the method (e.g. action_confirm) sees the record in the
                    # correct initial state (e.g. 'draft') so its internal flow runs completely —
                    # including delivery/procurement creation which Odoo skips when state != 'draft'.
                    if self.original_values:
                        try:
                            orig_vals = json.loads(self.original_values)
                            if orig_vals:
                                record.with_context(l4e_bypass_approval=True).write(orig_vals)
                        except Exception as e:
                            _logger.warning(
                                'L4E Approval: could not restore original values before method call: %s', e
                            )

                    method = getattr(record.with_context(**ctx), rule.finalize_method, None)
                    if callable(method):
                        method()
                    else:
                        _logger.error(
                            'L4E Approval: method "%s" not found or not callable on %s',
                            rule.finalize_method, self.res_model,
                        )
            except Exception as e:
                _logger.error('L4E Approval: failed to call method "%s": %s', rule.finalize_method, e)
        else:
            # Default: replay the blocked field write
            if self.pending_values:
                try:
                    vals = json.loads(self.pending_values)
                    record = self.env[self.res_model].browse(self.res_id)
                    if record.exists():
                        record.with_context(l4e_bypass_approval=True).write(vals)
                except Exception as e:
                    _logger.error('L4E Approval: failed to replay approved values: %s', e)

        if rule.notify_requester:
            self._notify_requester(approved=True)
        self._post_to_record_chatter(_('✅ Approval granted. Action has been applied.'))

    def _finalize_refuse(self, note=''):
        """Request refused — apply refused state if configured."""
        self.ensure_one()
        self.write({'state': 'refused'})

        # sudo() to access pending_field_id (Many2one → ir.model.fields)
        rule = self.rule_id.sudo()
        if rule.pending_field_id and rule.refused_value is not False:
            try:
                record = self.env[self.res_model].browse(self.res_id)
                if record.exists():
                    record.with_context(l4e_bypass_approval=True).write(
                        {rule.pending_field_id.name: rule.refused_value or False}
                    )
            except Exception as e:
                _logger.error('L4E Approval: failed to apply refused state: %s', e)

        if rule.notify_requester:
            self._notify_requester(approved=False, note=note)
        msg = _('❌ Approval refused.')
        if note:
            msg = f'{msg} <em>{note}</em>'
        self._post_to_record_chatter(msg)

    # ── Notifications ─────────────────────────────────────────────────────────

    def _notify_approvers(self, users=None):
        """
        Notify pending approvers via:
        1. Chatter inbox notification (always)
        2. Direct email via mail.mail (when send_email=True)
        3. In-app DM via discuss.channel (when send_dm=True)
        Extra users in notify_extra_request_ids also receive notifications.
        """
        self.ensure_one()
        rule = self.rule_id
        if users is None:
            users = self.approver_ids.filtered(
                lambda a: a.status == 'pending'
            ).mapped('user_id')

        all_users = users | rule.notify_extra_request_ids
        if not all_users:
            return

        body = Markup(self._build_request_message_html())

        # 1. Chatter notification (inbox for all partners)
        self.message_post(
            body=body,
            message_type='notification',
            partner_ids=all_users.mapped('partner_id').ids,
            subtype_xmlid='mail.mt_note',
        )

        # 2. Direct email (bypasses notification_type preference)
        if rule.send_email:
            self._send_email_to_users(
                users=all_users,
                subject=_('Approval Required: %(record)s', record=self.res_name),
                body=body,
            )

        # 3. In-app DM to actual approvers only
        if rule.send_dm:
            for user in users:
                try:
                    self._send_dm_to_user(user, body)
                except Exception as e:
                    _logger.warning('L4E Approval: DM failed for %s: %s', user.name, e)

    def _notify_requester(self, approved=True, note=''):
        """
        Notify the requester (and extra decision users) of the decision
        via inbox notification, direct email, and optional DM.
        """
        self.ensure_one()
        rule = self.rule_id
        if not self.requester_id:
            return

        body = Markup(self._build_decision_message_html(approved=approved, note=note))
        notify_users = self.requester_id | rule.notify_extra_decision_ids

        # 1. Chatter notification
        self.message_post(
            body=body,
            message_type='notification',
            partner_ids=notify_users.mapped('partner_id').ids,
            subtype_xmlid='mail.mt_note',
        )

        # 2. Direct email
        if rule.send_email:
            decision = _('Approved') if approved else _('Refused')
            self._send_email_to_users(
                users=notify_users,
                subject=_('Approval %(decision)s: %(record)s', decision=decision, record=self.res_name),
                body=body,
            )

        # 3. DM to requester
        if rule.send_dm:
            try:
                self._send_dm_to_user(self.requester_id, body)
            except Exception as e:
                _logger.warning('L4E Approval: DM to requester failed: %s', e)

    # ── Message builders ──────────────────────────────────────────────────────

    def _build_request_message_html(self):
        """Build HTML body for the approval request notification to approvers."""
        self.ensure_one()
        rule = self.rule_id
        tmpl = (rule.request_message_tmpl or '').strip()
        rule_note = rule.note or ''

        if tmpl:
            try:
                plain = tmpl.format(
                    record_name=self.res_name or '',
                    rule_name=rule.name or '',
                    requester_name=self.requester_id.name or '',
                    model_name=self.res_model or '',
                )
            except (KeyError, ValueError):
                plain = tmpl
            lines = [f'<p>{line}</p>' for line in plain.splitlines() if line.strip()]
            body = ''.join(lines)
        else:
            body = _(
                '<p>Your approval is required for <b>%(record)s</b>.</p>'
                '<p><b>Rule:</b> %(rule)s | <b>Requested by:</b> %(user)s</p>',
                record=self.res_name,
                rule=rule.name,
                user=self.requester_id.name or '',
            )

        if rule_note:
            body += f'<hr/><p><em>{rule_note}</em></p>'
        return body

    def _build_decision_message_html(self, approved=True, note=''):
        """Build HTML body for the decision notification to requester."""
        self.ensure_one()
        rule = self.rule_id
        tmpl = (rule.decision_message_tmpl or '').strip()
        decision = 'Approved ✅' if approved else 'Refused ❌'

        if tmpl:
            try:
                plain = tmpl.format(
                    record_name=self.res_name or '',
                    rule_name=rule.name or '',
                    decision=decision,
                    approver_name=self.env.user.name or '',
                    note=note or '',
                )
            except (KeyError, ValueError):
                plain = tmpl
            lines = [f'<p>{line}</p>' for line in plain.splitlines() if line.strip()]
            return ''.join(lines)

        body = _(
            '<p>Your approval request for <b>%(record)s</b> has been <b>%(decision)s</b>.</p>'
            '<p><b>Rule:</b> %(rule)s | <b>By:</b> %(approver)s</p>',
            record=self.res_name,
            decision=decision,
            rule=rule.name,
            approver=self.env.user.name or '',
        )
        if note:
            body += f'<p><b>Note:</b> <em>{note}</em></p>'
        return body

    # ── Email helper ──────────────────────────────────────────────────────────

    def _send_email_to_users(self, users, subject, body):
        """
        Send a direct email via mail.mail — bypasses user notification_type
        preferences so email is always delivered regardless of inbox/email setting.
        """
        Mail = self.env['mail.mail'].sudo()
        for user in users:
            if not user.email:
                continue
            Mail.create({
                'subject': subject,
                'body_html': Markup(body),
                'email_to': user.email,
                'auto_delete': True,
                'state': 'outgoing',
            }).send()

    # ── Direct Message (DM) ───────────────────────────────────────────────────

    def _send_dm_to_user(self, user, message):
        """Send an in-app Direct Message to a user via discuss.channel (chat)."""
        if not user or not user.partner_id:
            return
        bot = self.env.user
        Channel = self.env['discuss.channel'].sudo()

        # Find existing 1-to-1 chat channel
        channel = Channel.search([
            ('channel_type', '=', 'chat'),
            ('channel_partner_ids', 'in', user.partner_id.id),
            ('channel_partner_ids', 'in', bot.partner_id.id),
        ], limit=1)

        if not channel:
            channel = Channel.create({
                'name': f'{bot.name}, {user.name}',
                'channel_type': 'chat',
                'channel_partner_ids': [
                    (4, user.partner_id.id),
                    (4, bot.partner_id.id),
                ],
            })

        # Markup() ensures HTML renders correctly in Discuss (prevents tag escaping)
        channel.sudo().message_post(
            body=Markup(message),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    def _post_to_record_chatter(self, message):
        """Post a status message to the linked record's chatter."""
        self.ensure_one()
        try:
            record = self.env[self.res_model].browse(self.res_id)
            if record.exists() and hasattr(record, 'message_post'):
                record.message_post(
                    body=Markup(message),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
        except Exception:
            pass


class L4eApprovalRecordApprover(models.Model):
    """Individual approver line on an approval request."""
    _name = 'l4e.approval.record.approver'
    _description = 'Approval Request Approver Line'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'l4e.approval.record.request', ondelete='cascade', required=True,
    )
    sequence = fields.Integer(string='Level', default=10)
    user_id = fields.Many2one('res.users', string='Approver', required=True)

    status = fields.Selection(
        [
            ('waiting', 'Waiting (not yet turn)'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
        ],
        string='Status', default='pending', required=True, tracking=True,
    )
    date = fields.Datetime(string='Decision Date', readonly=True)
    note = fields.Text(string='Note')
