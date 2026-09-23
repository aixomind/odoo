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
def pre_init_hook(env):
    """Pre-init hook to safely create res_company columns before module install searching."""
    env.cr.execute("""
        ALTER TABLE res_company 
        ADD COLUMN IF NOT EXISTS header_footer_type varchar,
        ADD COLUMN IF NOT EXISTS report_header_image bytea,
        ADD COLUMN IF NOT EXISTS report_footer_image bytea,
        ADD COLUMN IF NOT EXISTS report_footer_text text;
    """)
