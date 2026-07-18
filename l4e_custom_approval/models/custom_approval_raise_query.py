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



