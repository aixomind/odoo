# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """This class inherits 'res.config.settings' model and adds fields
    to the settings"""
    _inherit = 'res.config.settings'

