# -*- coding: utf-8 -*-
from odoo import models

class ProjectTask(models.Model):
    """Project Task — L4E Dynamic Approval."""
    _inherit = ['project.task', 'l4e.approval.mixin']
