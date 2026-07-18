# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'l4e.approval.mixin']

    def button_validate(self):
        """
        On approval, _finalize_approve() calls button_validate() with
        l4e_bypass_approval=True in context. That must go straight to
        super() so the transfer actually moves to 'done'.

        Without bypass: Odoo's button_validate() internally calls
        _action_done() which writes state='done'.  That write() is
        intercepted by l4e.approval.mixin.write() → triggers the rule →
        creates the approval request → blocks the state change. ✅

        With bypass (called from _finalize_approve): goes straight to
        super() → state becomes 'done'. ✅
        """
        if self.env.context.get('l4e_bypass_approval'):
            return super().button_validate()

        # No bypass → let Odoo run normally.
        # The mixin's write() interceptor will catch state → 'done'
        # and create the approval request automatically.
        return super().button_validate()
