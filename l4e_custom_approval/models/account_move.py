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
