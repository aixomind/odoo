# -*- coding: utf-8 -*-
from odoo import models


class PurchaseOrder(models.Model):
    """Inherit purchase.order with the L4E dynamic approval mixin.

    Admin can now create an l4e.approval.rule:
        Model       : Purchase Order
        Trigger Field : State
        Trigger Value : purchase
        Conditions  : (e.g.) Amount Total >= 50000
        Approvers   : (any user / group / field on record)
    """
    _inherit = ['purchase.order', 'l4e.approval.mixin']
