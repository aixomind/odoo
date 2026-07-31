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
from odoo.exceptions import UserError


class ApprovalRaiseQuery(models.Model):
    _name = 'approval.raise.query'
    _description = 'Raise Query'

    approval_id = fields.Many2one('l4e.approval.record.request',string="Approvals")
    sale_raise_comment = fields.Text(string="Query Comment For Approvals", required=True)

    def action_send_raise_query(self):
        approvals = self.approval_id

        if not approvals:
            raise UserError("No approvals selected.")

        for approval in approvals:
            if not approval.exists():
                continue  # skip deleted record

            approval.message_post(
                body=f"Query Raised: {self.sale_raise_comment}",
                partner_ids=[approval.requester_id.partner_id.id]
            )

            approval.state = 'pending'
            approval.query_sale_comment = self.sale_raise_comment

            approval.message_notify(
                body=f"Query raised by approver: {self.sale_raise_comment}",
                partner_ids=[approval.requester_id.partner_id.id],
                subject="Sale Approval Query",
            )

        return {'type': 'ir.actions.act_window_close'}



