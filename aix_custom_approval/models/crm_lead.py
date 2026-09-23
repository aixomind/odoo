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


class CrmLead(models.Model):
    """CRM Lead/Opportunity — L4E Dynamic Approval.

    Example rule:
        Model         : CRM Lead (crm.lead)
        Trigger Field : Stage (stage_id) or Probability or any field
        Trigger Value : <stage id or probability value>
        Conditions    : e.g. Expected Revenue >= 100000
        Approvers     : Sales Manager group / specific user
    """
    _inherit = ['crm.lead', 'l4e.approval.mixin']
