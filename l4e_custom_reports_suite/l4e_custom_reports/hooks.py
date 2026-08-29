# -*- coding: utf-8 -*-

def pre_init_hook(env):
    """Pre-init hook to safely create res_company columns before module install searching."""
    env.cr.execute("""
        ALTER TABLE res_company 
        ADD COLUMN IF NOT EXISTS header_footer_type varchar,
        ADD COLUMN IF NOT EXISTS report_header_image bytea,
        ADD COLUMN IF NOT EXISTS report_footer_image bytea,
        ADD COLUMN IF NOT EXISTS report_footer_text text;
    """)
