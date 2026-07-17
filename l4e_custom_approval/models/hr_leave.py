# -*- coding: utf-8 -*-
from odoo import models

class HrLeave(models.Model):
    """Time Off Request — L4E Dynamic Approval."""
    _inherit = ['hr.leave', 'l4e.approval.mixin']
