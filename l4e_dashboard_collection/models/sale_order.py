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
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection(
        selection=[
            ('project', 'Project'),
            ('amc', 'AMC'),
            ('trading', 'Trading'),
            ('cold_rooms_amc', 'Cold Rooms AMC'),
            ('on_call_maintenance', 'On Call Maintenance'),
            ('cold_room_on_call', 'Cold Room On Call Maintenance'),
            ('fast_moving', 'Fast Moving'),
        ],
        string="Order Type",
        store=True,
    )

    def _sdash_fmt(self, amount, symbol):
        amount = abs(amount)
        if amount >= 1_000_000:
            return f"{symbol}{amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"{symbol}{amount / 1_000:.1f}K"
        return f"{symbol}{amount:,.2f}"

    @api.model
    def get_sale_dashboard_stats(self, partner_id=None, team_id=None, user_id=None, date_from=None, date_to=None):
        currency = self.env.company.currency_id
        symbol   = currency.symbol or ''

        base = [('company_id', '=', self.env.company.id)]
        if partner_id:
            base.append(('partner_id', '=', int(partner_id)))
        if team_id:
            base.append(('team_id', '=', int(team_id)))
        if user_id:
            base.append(('user_id', '=', int(user_id)))
        if date_from:
            base.append(('date_order', '>=', date_from + ' 00:00:00'))
        if date_to:
            base.append(('date_order', '<=', date_to + ' 23:59:59'))

        Order = self.env['sale.order']
        fmt   = lambda a: self._sdash_fmt(a, symbol)

        quot  = Order.search(base + [('state', 'in', ('draft', 'sent'))])
        q_cnt = len(quot)
        q_amt = sum(quot.mapped('amount_total'))

        conf  = Order.search(base + [('state', 'in', ('sale', 'done'))])
        c_cnt = len(conf)
        c_amt = sum(conf.mapped('amount_total'))

        to_inv = Order.search(
            base + [('state', 'in', ('sale', 'done')),
                    ('invoice_status', '=', 'to invoice')]
        )
        ti_cnt = len(to_inv)
        ti_amt = sum(to_inv.mapped('amount_total'))

        partial = Order.search(
            base + [('state', 'in', ('sale', 'done')),
                    ('invoice_status', '=', 'partially_invoiced')]
        )
        pa_cnt = len(partial)
        if 'invoiced_total' in Order._fields:
            pa_amt = sum(partial.mapped('amount_total')) - sum(partial.mapped('invoiced_total'))
        else:
            pa_amt = 0.0
            for order in partial:
                invoiced = sum(inv.amount_total for inv in order.invoice_ids if inv.state == 'posted')
                pa_amt += (order.amount_total - invoiced)

        full_inv = Order.search(
            base + [('state', 'in', ('sale', 'done')),
                    ('invoice_status', '=', 'invoiced')]
        )
        fp_cnt = len(full_inv)
        fp_amt = sum(full_inv.mapped('amount_total'))
        total_docs = c_cnt + q_cnt
        outstanding_amt = ti_amt + pa_amt
        avg_order_value = c_amt / c_cnt if c_cnt else 0.0
        conversion_rate = (c_cnt / total_docs * 100.0) if total_docs else 0.0

        chart_year = fields.Date.today().year
        if date_from:
            try:
                chart_year = fields.Date.from_string(date_from).year
            except Exception:
                chart_year = fields.Date.today().year
        month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_revenue = []
        for month in range(1, 13):
            start = f'{chart_year}-{month:02d}-01 00:00:00'
            if month == 12:
                end = f'{chart_year}-12-31 23:59:59'
            else:
                end = f'{chart_year}-{month + 1:02d}-01 00:00:00'
            month_domain = base + [('state', 'in', ('sale', 'done')), ('date_order', '>=', start)]
            if month == 12:
                month_domain.append(('date_order', '<=', end))
            else:
                month_domain.append(('date_order', '<', end))
            amount = sum(Order.search(month_domain).mapped('amount_total'))
            monthly_revenue.append({
                'label': f'{month_labels[month - 1]} {chart_year}',
                'short_label': month_labels[month - 1],
                'value': amount,
                'formatted': fmt(amount),
                'date_from': start[:10],
                'date_to': end[:10],
            })

        recent_orders = Order.search(base, order='date_order desc, id desc', limit=5)
        recent_activities = []
        for order in recent_orders:
            if order.state in ('draft', 'sent'):
                title = f'Quotation {order.name} sent'
                icon = 'fa-file-text-o'
                tone = 'orange'
            elif order.invoice_status == 'invoiced':
                title = f'Sales Order {order.name} fully invoiced'
                icon = 'fa-check'
                tone = 'green'
            elif order.invoice_status in ('to invoice', 'partially_invoiced'):
                title = f'Invoice pending for {order.name}'
                icon = 'fa-clock-o'
                tone = 'pink'
            else:
                title = f'Sales Order {order.name} confirmed'
                icon = 'fa-shopping-bag'
                tone = 'blue'
            recent_activities.append({
                'id': order.id,
                'title': title,
                'customer': order.partner_id.display_name,
                'time_label': fields.Datetime.context_timestamp(self, order.date_order).strftime('%d %b %Y'),
                'icon': icon,
                'tone': tone,
            })

        return {
            'cards': [
                {
                    'key':              'total',
                    'label':            'Total Sale Orders',
                    'count':            c_cnt,
                    'amount':           c_amt,
                    'amount_formatted': fmt(c_amt),
                    'color':            '#5B8DEF',
                    'icon':             'fa-shopping-cart',
                    'sub_label':        'Confirmed Orders',
                },
                {
                    'key':              'to_invoice',
                    'label':            'To Invoice',
                    'count':            ti_cnt,
                    'amount':           ti_amt,
                    'amount_formatted': fmt(ti_amt),
                    'color':            '#EBA7A7',
                    'icon':             'fa-file-text-o',
                    'sub_label':        'Awaiting Invoice',
                },
                {
                    'key':              'partial',
                    'label':            'Partially Invoiced',
                    'count':            pa_cnt,
                    'amount':           pa_amt,
                    'amount_formatted': fmt(pa_amt),
                    'color':            '#AFEDE4',
                    'icon':             'fa-adjust',
                    'sub_label':        'Outstanding Balance',
                },
                {
                    'key':              'fully_invoiced',
                    'label':            'Fully Invoiced',
                    'count':            fp_cnt,
                    'amount':           fp_amt,
                    'amount_formatted': fmt(fp_amt),
                    'color':            '#8ADB90',
                    'icon':             'fa-check-circle',
                    'sub_label':        'Paid & Closed',
                },
                {
                    'key':              'quotations',
                    'label':            'Quotations',
                    'count':            q_cnt,
                    'amount':           q_amt,
                    'amount_formatted': fmt(q_amt),
                    'color':            '#E0B294',
                    'icon':             'fa-clock-o',
                    'sub_label':        'Draft / Sent',
                },
            ],
            'summary': {
                'total_revenue': fmt(c_amt),
                'avg_order_value': fmt(avg_order_value),
                'conversion_rate': f'{conversion_rate:.1f}%',
                'avg_delivery_time': '0 Days',
                'outstanding': fmt(outstanding_amt),
                'outstanding_orders': ti_cnt + pa_cnt,
            },
            'monthly_revenue': monthly_revenue,
            'recent_activities': recent_activities,
            'teams': [{'id': team.id, 'name': team.name} for team in self.env['crm.team'].search([])],
            'users': [{'id': user.id, 'name': user.name} for user in self.env['res.users'].search([('share', '=', False)])],
            'currency_symbol': symbol,
        }

    @api.model
    def action_open_sale_orders_by_status(self, status_key, partner_id=None, team_id=None, user_id=None, date_from=None, date_to=None):
        base = [('company_id', '=', self.env.company.id)]
        if partner_id:
            base.append(('partner_id', '=', int(partner_id)))
        if team_id:
            base.append(('team_id', '=', int(team_id)))
        if user_id:
            base.append(('user_id', '=', int(user_id)))
        if date_from:
            base.append(('date_order', '>=', date_from + ' 00:00:00'))
        if date_to:
            base.append(('date_order', '<=', date_to + ' 23:59:59'))

        STATUS = {
            'total':          ([('state', 'in', ('sale', 'done'))], 'Confirmed Orders'),
            'to_invoice':     ([('state', 'in', ('sale', 'done')), ('invoice_status', '=', 'to invoice')], 'To Invoice'),
            'partial':        ([('state', 'in', ('sale', 'done')), ('invoice_status', '=', 'partially_invoiced')], 'Partially Invoiced'),
            'fully_invoiced': ([('state', 'in', ('sale', 'done')), ('invoice_status', '=', 'invoiced')], 'Fully Invoiced'),
            'quotations':     ([('state', 'in', ('draft', 'sent'))], 'Quotations'),
        }
        extra, label = STATUS.get(status_key, ([], status_key))

        return {
            'type': 'ir.actions.act_window',
            'name': f'Sale Orders - {label}',
            'res_model': 'sale.order',
            'views': [
                (self.env.ref('sale.sale_order_tree').id, 'list'),
                (False, 'form')
            ],
            'view_mode': 'list,form',
            'domain': base + extra,
        }
