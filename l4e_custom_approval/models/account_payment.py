# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    """Payment — L4E Dynamic Approval."""
    _inherit = ['account.payment', 'l4e.approval.mixin']
