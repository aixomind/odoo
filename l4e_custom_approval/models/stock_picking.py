# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2026 Links4Engg Private Limited.
# All Rights Reserved.
#
# This software is proprietary and confidential.
#
# Unauthorized copying, modification, redistribution,
# reverse engineering, decompilation, sublicensing,
# or commercial use of this software is strictly prohibited
# without prior written permission from
# Links4Engg Private Limited.
#
# Licensed under the Odoo Proprietary License v1.0 (OPL-1).
#
# Links4Engg Private Limited
# Website : https://links4engg.com
# Email   : info@links4engg.com
# Phone   : +91 471 3592209 | +91 7306889096
#
##############################################################################
from odoo import models


class StockPicking(models.Model):
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
