# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    """Inherit sale.order with the L4E dynamic approval mixin.

    Admin can now create an l4e.approval.rule:
        Model         : Sales Order
        Trigger Field : State
        Trigger Value : sale
        Conditions    : (e.g.) Amount Total >= 100000
        Approvers     : (any user / group / field on record)

    The existing discount approval workflow (approval.category / approval.request)
    is preserved in approval_request.py for backward compatibility.
    """
    _name = 'sale.order'
    _inherit = ['sale.order', 'l4e.approval.mixin']
