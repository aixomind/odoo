# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    def _register_hook(self):
        res = super()._register_hook()
        try:
            self.env.cr.execute("""
                ALTER TABLE res_company 
                ADD COLUMN IF NOT EXISTS header_footer_type varchar,
                ADD COLUMN IF NOT EXISTS report_header_image bytea,
                ADD COLUMN IF NOT EXISTS report_footer_image bytea,
                ADD COLUMN IF NOT EXISTS report_footer_text text,
                ADD COLUMN IF NOT EXISTS report_text_color varchar,
                ADD COLUMN IF NOT EXISTS report_table_color varchar,
                ADD COLUMN IF NOT EXISTS report_text_bg_color varchar;
            """)
        except Exception:
            pass
        return res

    header_footer_type = fields.Selection([
        ('standard', 'Standard Odoo Layout'),
        ('custom_image', 'Custom Header & Footer Banner Images'),
    ], string="Report Header & Footer Type", default='standard',
       help="Select whether reports should use default Odoo company layout or custom uploaded header/footer images.")

    report_header_image = fields.Image(
        string="Report Header Banner Image",
        help="Upload a banner image to be displayed at the header of all reports for this company."
    )
    report_footer_image = fields.Image(
        string="Report Footer Banner Image",
        help="Upload a banner image to be displayed at the footer of all reports for this company."
    )
    report_footer_text = fields.Text(
        string="Custom Report Footer Text",
        help="Custom footer text to be rendered below or alongside the footer banner."
    )

    report_text_color = fields.Char(
        string="Report Text Color",
        default='#000000',
        help="Custom text color for PDF report text and labels (e.g. #000000)."
    )
    report_table_color = fields.Char(
        string="Report Table Header Color",
        default='#dcdcdc',
        help="Custom background color for table headers in PDF reports (e.g. #dcdcdc)."
    )
    report_text_bg_color = fields.Char(
        string="Report Text Background / Banner Color",
        default='#dcdcdc',
        help="Custom background color for title badges and summary total banners in PDF reports (e.g. #dcdcdc)."
    )

    def action_reset_report_colors(self):
        """Reset report color customization fields to system defaults."""
        self.write({
            'report_text_color': '#000000',
            'report_table_color': '#dcdcdc',
            'report_text_bg_color': '#dcdcdc',
        })

