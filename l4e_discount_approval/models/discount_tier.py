# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L4eDiscountTier(models.Model):
    """
    Discount Approval Tier.
    Defines which approvers are required for each discount range.

    Example:
      Tier 1:  0% – 20%  → Sales Manager
      Tier 2: 20% – 40%  → Sales Director
      Tier 3: 40% – 100% → VP / CEO
    """
    _name = 'l4e.discount.tier'
    _description = 'Discount Approval Tier'
    _order = 'discount_min asc'

    name = fields.Char(string='Tier Name', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )
    discount_min = fields.Float(
        string='From (%)', required=True, digits=(5, 2),
        help='Discount strictly greater than this % triggers this tier.',
    )
    discount_max = fields.Float(
        string='To (%)', required=True, digits=(5, 2),
        help='Discount up to and including this % triggers this tier.',
    )
    approver_ids = fields.Many2many(
        'res.users',
        relation='l4e_discount_tier_approver_rel',
        column1='tier_id', column2='user_id',
        string='Approvers',
        domain=[('share', '=', False)],
        help='Users who must approve when the discount falls in this range.',
    )
    approval_mode = fields.Selection(
        [('any', 'Any one approver'), ('all', 'All approvers required')],
        string='Approval Mode', default='any', required=True,
    )
    description = fields.Text(string='Description / Policy')

    @api.constrains('discount_min', 'discount_max')
    def _check_range(self):
        for rec in self:
            if rec.discount_min < 0 or rec.discount_max > 100:
                raise ValidationError(_('Discount range must be between 0 and 100.'))
            if rec.discount_min >= rec.discount_max:
                raise ValidationError(_('From (%) must be less than To (%).'))

    def _match_discount(self, discount_pct):
        """Return True if the given discount % falls in this tier's range."""
        self.ensure_one()
        return self.discount_min < discount_pct <= self.discount_max
