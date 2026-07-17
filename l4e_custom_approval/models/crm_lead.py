# -*- coding: utf-8 -*-
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
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'l4e.approval.mixin']
