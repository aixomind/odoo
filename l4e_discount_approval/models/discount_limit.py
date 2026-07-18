# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L4eDiscountLimit(models.Model):
    """
    Per-salesperson discount limits.
    Falls back to company-level defaults from Settings if not set per user.
    """
    _name = 'l4e.discount.limit'
    _description = 'Salesperson Discount Limit'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users', string='Salesperson',
        required=True, ondelete='cascade', index=True,
        domain=[('share', '=', False)],
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    global_discount_limit = fields.Float(
        string='Global Discount Limit (%)',
        digits=(5, 2), default=0.0,
        help='Maximum overall (header-level) discount % this salesperson can apply without approval.',
    )
    line_discount_limit = fields.Float(
        string='Per-Line Discount Limit (%)',
        digits=(5, 2), default=0.0,
        help='Maximum per-line discount % this salesperson can apply without approval.',
    )
    approver_ids = fields.Many2many(
        'res.users',
        relation='l4e_discount_limit_approver_rel',
        column1='limit_id', column2='user_id',
        string='Approvers',
        domain=[('share', '=', False)],
        help='If set, these users are used as approvers instead of the discount tier approvers.',
    )
    approval_mode = fields.Selection(
        [('any', 'Any one approver'), ('all', 'All approvers required')],
        string='Approval Mode', default='any',
    )
    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_user_company', 'UNIQUE(user_id, company_id)', 'A discount limit record already exists for this salesperson and company.'),
    ]

    @api.constrains('global_discount_limit', 'line_discount_limit')
    def _check_limits(self):
        for rec in self:
            if rec.global_discount_limit < 0 or rec.global_discount_limit > 100:
                raise ValidationError(_('Global Discount Limit must be between 0 and 100.'))
            if rec.line_discount_limit < 0 or rec.line_discount_limit > 100:
                raise ValidationError(_('Per-Line Discount Limit must be between 0 and 100.'))
