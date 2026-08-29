# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_company_stamp = fields.Boolean(
        string="Enable Company Stamp/Seal",
        default=True,
        help="Master switch to allow printing company stamp on reports across documents."
    )
    company_stamp_image = fields.Binary(
        string="Company Stamp / Seal Image",
        help="Upload or draw the default company stamp or seal image to print on reports."
    )
