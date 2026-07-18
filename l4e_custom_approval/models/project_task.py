# -*- coding: utf-8 -*-
from odoo import models

class ProjectTask(models.Model):
    """Project Task — L4E Dynamic Approval."""
    _name = 'project.task'
    _inherit = ['project.task', 'l4e.approval.mixin']
