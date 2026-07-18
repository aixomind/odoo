# -*- coding: utf-8 -*-
# ── Dynamic Approval Engine (new) ─────────────────────────────────────────────
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
