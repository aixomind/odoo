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
"""Helpers shared by the backdating wizard and the past-count import."""

from datetime import datetime, time as datetime_time

import pytz

from odoo import _
from odoo.exceptions import UserError

# Company lock dates that block a plain miscellaneous entry. ``tax_lock_date``
# and the sale/purchase lock dates are deliberately not checked: a stock
# valuation entry carries no tax and belongs to no sale or purchase journal.
COMPANY_LOCK_DATE_FIELDS = (
    ('hard_lock_date', 'Hard Lock Date'),
    ('fiscalyear_lock_date', 'Fiscal Year Lock Date'),
    ('period_lock_date', 'Period Lock Date'),
)


def local_to_utc(env, naive_local):
    """Read a naive datetime as the user's wall clock and return naive UTC."""
    timezone = pytz.timezone(env.user.tz or env.context.get('tz') or 'UTC')
    return timezone.localize(naive_local).astimezone(pytz.utc).replace(tzinfo=None)


def combine_local(env, date_value, float_time):
    """Combine a date with an HH:MM float, in the user's timezone, as naive UTC."""
    hours = int(float_time or 0.0)
    minutes = int(round(((float_time or 0.0) - hours) * 60))
    if minutes >= 60:
        hours, minutes = hours + 1, 0
    if hours > 23:
        hours, minutes = 23, 59
    return local_to_utc(env, datetime.combine(date_value, datetime_time(hours, minutes)))


def day_bounds_utc(env, date_from, date_to):
    """UTC datetime bounds covering whole local days, inclusive."""
    return (
        local_to_utc(env, datetime.combine(date_from, datetime_time.min)),
        local_to_utc(env, datetime.combine(date_to, datetime_time.max)),
    )


def check_lock_dates(companies, target_date):
    """Refuse to write into a period the accountant has closed.

    Raw SQL and freshly posted entries both bypass the check Odoo would
    normally make, so it has to be made explicitly before anything is written.
    """
    for company in companies:
        company_sudo = company.sudo()
        for field_name, label in COMPANY_LOCK_DATE_FIELDS:
            if field_name not in company_sudo._fields:
                continue
            lock_date = company_sudo[field_name]
            if lock_date and target_date <= lock_date:
                raise UserError(_(
                    "%(new_date)s falls inside a locked period of %(company)s "
                    "(%(label)s: %(lock)s).",
                    new_date=target_date, company=company.display_name,
                    label=label, lock=lock_date,
                ))
