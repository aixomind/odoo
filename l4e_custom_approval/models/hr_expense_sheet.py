# -*- coding: utf-8 -*-
from odoo import models

class HrExpenseSheet(models.Model):
    """Expense Report — L4E Dynamic Approval."""
    _name = 'hr.expense.sheet'
    _inherit = ['hr.expense.sheet', 'l4e.approval.mixin']
