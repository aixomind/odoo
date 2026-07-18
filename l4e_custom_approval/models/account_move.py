# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    """Inherit account.move with the L4E dynamic approval mixin.

    Admin can now create an l4e.approval.rule:
        Model       : Journal Entry (account.move)
        Trigger Field : State
        Trigger Value : posted
        Conditions  : (e.g.) Move Type = out_invoice, Amount Total >= 100000
        Approvers   : (any user / group / field on record)
    """
    _name = 'account.move'
    _inherit = ['account.move', 'l4e.approval.mixin']
