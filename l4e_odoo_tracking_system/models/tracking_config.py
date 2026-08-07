# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TrackingConfig(models.Model):
    _name = 'tracking.config'
    _description = 'Tracking Configuration'
    _rec_name = 'model_id'

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="Select the model to configure chatter tracking and dust bin options."
    )
    tracking_enable = fields.Boolean(
        string='Tracking Enable',
        default=False,
        help="Enable dynamic field tracking on chatter for all fields in this model."
    )
    remove_tracking = fields.Boolean(
        string='Remove Tracking',
        default=False,
        help="Disable field tracking on chatter for this model."
    )
    tracking_days = fields.Integer(
        string='Tracking Days',
        default=0,
        help="Number of days to keep deleted records in Dust Bin. 0 or empty means unlimited."
    )

    _sql_constraints = [
        ('model_uniq', 'unique(model_id)', 'Tracking configuration for this model already exists!')
    ]

    @api.constrains('tracking_days')
    def _check_tracking_days(self):
        for rec in self:
            if rec.tracking_days < 0:
                raise ValidationError(_("Tracking Days cannot be negative."))

    @api.constrains('tracking_enable', 'remove_tracking')
    def _check_tracking_fields(self):
        for rec in self:
            if rec.tracking_enable and rec.remove_tracking:
                raise ValidationError(_("You cannot enable both 'Tracking Enable' and 'Remove Tracking' at the same time."))

    @api.onchange('tracking_enable')
    def _onchange_tracking_enable(self):
        if self.tracking_enable:
            self.remove_tracking = False

    @api.onchange('remove_tracking')
    def _onchange_remove_tracking(self):
        if self.remove_tracking:
            self.tracking_enable = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tracking_enable'):
                vals['remove_tracking'] = False
            elif vals.get('remove_tracking'):
                vals['tracking_enable'] = False
        return super(TrackingConfig, self).create(vals_list)

    def write(self, vals):
        if vals.get('tracking_enable'):
            vals['remove_tracking'] = False
        elif vals.get('remove_tracking'):
            vals['tracking_enable'] = False
        return super(TrackingConfig, self).write(vals)


