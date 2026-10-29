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
from . import approval_rule            # l4e.approval.rule + condition + approver config
from . import approval_mixin           # abstract mixin — must load before models that use it
from . import approval_record_request  # l4e.approval.record.request + approver lines

# ── Model integrations (inherit mixin) ────────────────────────────────────────
from . import sale_order
from . import purchase_order
from . import account_move
from . import crm_lead
from . import stock_picking
from . import account_payment     # Payments (account always installed)
from . import custom_approval_raise_query
# stock_picking, project_task, hr_expense_sheet, hr_leave
# are in bridge modules: l4e_approval_inventory, l4e_approval_project, l4e_approval_hr
