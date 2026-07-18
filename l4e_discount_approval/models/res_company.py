# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """This class inherits 'res.company' and adds so_double_validation,
    so_double_validation_limit to add validation limits"""
    _inherit = 'res.company'

