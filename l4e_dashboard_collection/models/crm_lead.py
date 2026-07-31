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
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_set_lost(self, **kwargs):
        res = super().action_set_lost(**kwargs)
        lost_stage = self.env["crm.stage"].search([("name", "ilike", "lost")], limit=1)
        if lost_stage:
            self.write({"stage_id": lost_stage.id})
        return res

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            lost_stage = self.env["crm.stage"].search([("name", "ilike", "lost")], limit=1)
            if lost_stage:
                to_update = self.filtered(lambda l: l.stage_id != lost_stage)
                if to_update:
                    super(CrmLead, to_update).write({"stage_id": lost_stage.id})
        return res
