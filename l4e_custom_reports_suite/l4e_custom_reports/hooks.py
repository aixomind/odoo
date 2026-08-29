# -*- coding: utf-8 -*-

def pre_init_hook(cr_or_env):
    """Pre-init hook to safely create res_company columns before module install searching."""
    cr = cr_or_env.cr if hasattr(cr_or_env, 'cr') else cr_or_env
    cr.execute("""
        ALTER TABLE res_company 
        ADD COLUMN IF NOT EXISTS header_footer_type varchar,
        ADD COLUMN IF NOT EXISTS report_header_image bytea,
        ADD COLUMN IF NOT EXISTS report_footer_image bytea,
        ADD COLUMN IF NOT EXISTS report_footer_text text,
        ADD COLUMN IF NOT EXISTS report_text_color varchar,
        ADD COLUMN IF NOT EXISTS report_table_color varchar,
        ADD COLUMN IF NOT EXISTS report_text_bg_color varchar;
    """)
