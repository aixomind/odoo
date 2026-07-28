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
from odoo import models, api, fields
from datetime import datetime, timedelta, date
import pytz
import logging

_logger = logging.getLogger(__name__)

class L4eInventoryDashboard(models.TransientModel):
    _name = 'l4e.inventory.dashboard'
    _description = 'Inventory Dashboard'

    def _get_name_sql(self):
        try:
            self.env.cr.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'product_template' AND column_name = 'name'")
            res = self.env.cr.fetchone()
            if res and res[0] in ('jsonb', 'json'):
                lang = (self.env.lang or 'en_US').replace("'", "''")
                return f"COALESCE(pt.name->>'{lang}', pt.name->>'en_US', pt.name::text)"
        except Exception:
            pass
        return "pt.name::text"

    def _get_move_qty_sql(self):
        try:
            self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_move' AND column_name IN ('quantity', 'product_uom_qty')")
            cols = [r[0] for r in self.env.cr.fetchall()]
            if 'quantity' in cols:
                return "sm.quantity"
        except Exception:
            pass
        return "sm.product_uom_qty"

    def _get_location_name_sql(self):
        try:
            self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_location' AND column_name = 'complete_name'")
            if self.env.cr.fetchone():
                return "sl.complete_name"
        except Exception:
            pass
        return "sl.name"

    def _table_exists(self, table_name):
        try:
            self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (table_name,))
            return bool(self.env.cr.fetchone())
        except Exception:
            return False

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, product_id=None):
        try:
            company_id = self.env.company.id
            _logger.info("=== L4E INVENTORY DASHBOARD get_dashboard_data CALLED ===")
            _logger.info("Params: date_from=%s, date_to=%s, product_id=%s, company_id=%s", date_from, date_to, product_id, company_id)

            lang = self.env.lang or 'en_US'
            user_tz = self.env.user.tz or 'UTC'
            tz = pytz.timezone(user_tz)

            name_sql = self._get_name_sql()
            move_qty_sql = self._get_move_qty_sql()
            loc_name_sql = self._get_location_name_sql()
            has_svl = self._table_exists('stock_valuation_layer')

            if product_id:
                try:
                    product_id = int(product_id)
                except (ValueError, TypeError):
                    product_id = None

            if date_from:
                df = datetime.strptime(date_from, "%Y-%m-%d").date()
            else:
                df = date.today().replace(day=1)

            if date_to:
                dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            else:
                dt = date.today()

            dt_from_local = datetime.combine(df, datetime.min.time())
            dt_to_local = datetime.combine(dt, datetime.max.time())

            dt_from_utc = tz.localize(dt_from_local).astimezone(pytz.utc).replace(tzinfo=None)
            dt_to_utc = tz.localize(dt_to_local).astimezone(pytz.utc).replace(tzinfo=None)

            delta = dt - df + timedelta(days=1)
            prev_df = df - delta
            prev_dt = dt - delta

            prev_dt_from_local = datetime.combine(prev_df, datetime.min.time())
            prev_dt_to_local = datetime.combine(prev_dt, datetime.max.time())

            prev_dt_from_utc = tz.localize(prev_dt_from_local).astimezone(pytz.utc).replace(tzinfo=None)
            prev_dt_to_utc = tz.localize(prev_dt_to_local).astimezone(pytz.utc).replace(tzinfo=None)

            prod_cond = " AND pp.id = %s " if product_id else ""

            # 1. Total Valuation
            total_value = 0.0
            if has_svl:
                val_params = [company_id, dt_to_utc]
                if product_id:
                    val_params.append(product_id)
                self.env.cr.execute(f"""
                    SELECT COALESCE(SUM(svl.value), 0.0)
                    FROM stock_valuation_layer svl
                    JOIN product_product pp ON pp.id = svl.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN product_category pc ON pc.id = pt.categ_id
                    WHERE (svl.company_id = %s OR svl.company_id IS NULL)
                      AND svl.create_date <= %s
                      AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                      {prod_cond}
                """, tuple(val_params))
                total_value = self.env.cr.fetchone()[0] or 0.0

            if total_value == 0.0:
                p_dom = [('active', '=', True)]
                if product_id:
                    p_dom.append(('id', '=', product_id))
                prods = self.env['product.product'].search(p_dom)
                total_value = sum(p.with_context(company_id=company_id).qty_available * p.standard_price for p in prods if getattr(p.categ_id, 'show_in_dashboard', True) is not False)

            prev_total_value = 0.0
            if has_svl:
                prev_val_params = [company_id, prev_dt_to_utc]
                if product_id:
                    prev_val_params.append(product_id)
                self.env.cr.execute(f"""
                    SELECT COALESCE(SUM(svl.value), 0.0)
                    FROM stock_valuation_layer svl
                    JOIN product_product pp ON pp.id = svl.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN product_category pc ON pc.id = pt.categ_id
                    WHERE (svl.company_id = %s OR svl.company_id IS NULL)
                      AND svl.create_date <= %s
                      AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                      {prod_cond}
                """, tuple(prev_val_params))
                prev_total_value = self.env.cr.fetchone()[0] or 0.0

            if prev_total_value == 0.0:
                p_dom = [('active', '=', True)]
                if product_id:
                    p_dom.append(('id', '=', product_id))
                prods = self.env['product.product'].search(p_dom)
                prev_total_value = sum(p.with_context(company_id=company_id).qty_available * p.standard_price for p in prods if getattr(p.categ_id, 'show_in_dashboard', True) is not False)

            # 2. Total Products
            prod_count_domain = [('active', '=', True)]
            if product_id:
                prod_count_domain.append(('id', '=', product_id))

            total_products = self.env['product.product'].search_count(prod_count_domain)
            prev_total_products = total_products

            # 3. Stock Moves
            move_domain = [('state', '=', 'done'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]
            if product_id:
                move_domain.append(('product_id', '=', product_id))

            stock_moves = self.env['stock.move'].search_count(move_domain + [('date', '>=', fields.Datetime.to_string(dt_from_utc)), ('date', '<=', fields.Datetime.to_string(dt_to_utc))])
            prev_stock_moves = self.env['stock.move'].search_count(move_domain + [('date', '>=', fields.Datetime.to_string(prev_dt_from_utc)), ('date', '<=', fields.Datetime.to_string(prev_dt_to_utc))])

            _logger.info("Calculated total_value=%s, prev_total_value=%s", total_value, prev_total_value)
            _logger.info("Calculated total_products=%s, prev_total_products=%s", total_products, prev_total_products)
            _logger.info("Calculated stock_moves=%s, prev_stock_moves=%s", stock_moves, prev_stock_moves)

            # 4. Low Stock Products
            low_stock_domain = [('active', '=', True)]
            if product_id:
                low_stock_domain.append(('id', '=', product_id))

            products = self.env['product.product'].search(low_stock_domain)
            orderpoints = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', 'in', products.ids),
                '|', ('company_id', '=', company_id), ('company_id', '=', False)
            ])
            min_qty_map = {}
            for op in orderpoints:
                min_qty_map[op.product_id.id] = min_qty_map.get(op.product_id.id, 0.0) + op.product_min_qty

            low_stock_count = 0
            low_stock_product_ids = []
            for p in products:
                qty = p.with_context(company_id=company_id).qty_available
                min_qty = min_qty_map.get(p.id, 5.0)
                if qty < min_qty:
                    low_stock_count += 1
                    low_stock_product_ids.append(p.id)

            _logger.info("Calculated low_stock_count=%s", low_stock_count)

            # In/Out
            in_out_domain = [('state', '=', 'done'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]
            if product_id:
                in_out_domain.append(('product_id', '=', product_id))

            inc_moves = self.env['stock.move'].search(in_out_domain + [
                ('date', '>=', fields.Datetime.to_string(dt_from_utc)),
                ('date', '<=', fields.Datetime.to_string(dt_to_utc)),
                ('location_id.usage', '!=', 'internal'),
                ('location_dest_id.usage', '=', 'internal')
            ])
            current_in = sum(inc_moves.mapped(lambda m: getattr(m, 'quantity', m.product_uom_qty)))

            out_moves = self.env['stock.move'].search(in_out_domain + [
                ('date', '>=', fields.Datetime.to_string(dt_from_utc)),
                ('date', '<=', fields.Datetime.to_string(dt_to_utc)),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '!=', 'internal')
            ])
            current_out = sum(out_moves.mapped(lambda m: getattr(m, 'quantity', m.product_uom_qty)))

            prev_inc_moves = self.env['stock.move'].search(in_out_domain + [
                ('date', '>=', fields.Datetime.to_string(prev_dt_from_utc)),
                ('date', '<=', fields.Datetime.to_string(prev_dt_to_utc)),
                ('location_id.usage', '!=', 'internal'),
                ('location_dest_id.usage', '=', 'internal')
            ])
            prev_in = sum(prev_inc_moves.mapped(lambda m: getattr(m, 'quantity', m.product_uom_qty)))

            prev_out_moves = self.env['stock.move'].search(in_out_domain + [
                ('date', '>=', fields.Datetime.to_string(prev_dt_from_utc)),
                ('date', '<=', fields.Datetime.to_string(prev_dt_to_utc)),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '!=', 'internal')
            ])
            prev_out = sum(prev_out_moves.mapped(lambda m: getattr(m, 'quantity', m.product_uom_qty)))

            # Chart values over time
            months_list = []
            curr_m = df.replace(day=1)
            end_m = dt.replace(day=1)
            while curr_m <= end_m:
                months_list.append(curr_m)
                if curr_m.month == 12:
                    curr_m = date(curr_m.year + 1, 1, 1)
                else:
                    curr_m = date(curr_m.year, curr_m.month + 1, 1)

            values_over_time = []
            for m_date in months_list:
                values_over_time.append({
                    'date': m_date.strftime("%b %Y"),
                    'value': round(total_value, 2)
                })

            # Categories (ORM computed to avoid SQL numeric * jsonb type errors)
            cat_map = {}
            quant_domain = [('location_id.usage', '=', 'internal'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]
            if product_id:
                quant_domain.append(('product_id', '=', product_id))

            quants = self.env['stock.quant'].search(quant_domain)
            for q in quants:
                cat = q.product_id.categ_id
                if getattr(cat, 'show_in_dashboard', True) is not False:
                    v = q.quantity * q.product_id.with_context(company_id=company_id).standard_price
                    cat_map[cat.id] = cat_map.get(cat.id, {'id': cat.id, 'name': cat.name or 'Category', 'value': 0.0})
                    cat_map[cat.id]['value'] += v

            category_vals = [v for v in cat_map.values() if v['value'] > 0]
            category_vals.sort(key=lambda x: x['value'], reverse=True)

            # Top 5 products (ORM computed)
            top_prods = self.env['product.product'].search([('active', '=', True)] + ([('id', '=', product_id)] if product_id else []), limit=5)
            top_products = [{
                'id': p.id,
                'name': p.display_name,
                'qty_on_hand': round(p.with_context(company_id=company_id).qty_available, 2),
                'value': round(p.with_context(company_id=company_id).qty_available * p.standard_price, 2),
                'tmpl_id': p.product_tmpl_id.id
            } for p in top_prods]

            # Locations (ORM computed)
            loc_map = {}
            for q in quants:
                loc = q.location_id
                v = q.quantity * q.product_id.with_context(company_id=company_id).standard_price
                loc_name = loc.complete_name if hasattr(loc, 'complete_name') else loc.name
                loc_map[loc.id] = loc_map.get(loc.id, {'id': loc.id, 'name': loc_name or 'Location', 'qty': 0.0, 'value': 0.0})
                loc_map[loc.id]['qty'] += q.quantity
                loc_map[loc.id]['value'] += v

            location_vals = [v for v in loc_map.values() if v['qty'] > 0 or v['value'] > 0][:5]
            location_vals.sort(key=lambda x: x['value'], reverse=True)

            # Product Moves (ORM computed)
            move_recs = self.env['stock.move'].search([('state', '=', 'done')] + ([('product_id', '=', product_id)] if product_id else []), limit=5)
            product_moves = [{
                'id': m.product_id.id,
                'name': m.product_id.display_name,
                'in': round(getattr(m, 'quantity', m.product_uom_qty), 2) if m.location_dest_id.usage == 'internal' else 0.0,
                'out': round(getattr(m, 'quantity', m.product_uom_qty), 2) if m.location_id.usage == 'internal' else 0.0,
                'net': round(getattr(m, 'quantity', m.product_uom_qty), 2)
            } for m in move_recs]

            def get_trend(curr, prev):
                if not prev:
                    return 100.0 if curr else 0.0
                return round(((curr - prev) / prev) * 100.0, 1)

            _logger.info("=== SUCCESSFUL EXIT L4E INVENTORY DASHBOARD get_dashboard_data ===")
            return {
                'kpis': {
                    'total_value': {
                        'value': round(total_value, 2),
                        'trend': get_trend(total_value, prev_total_value)
                    },
                    'total_products': {
                        'value': total_products,
                        'trend': get_trend(total_products, prev_total_products)
                    },
                    'stock_moves': {
                        'value': stock_moves,
                        'trend': get_trend(stock_moves, prev_stock_moves)
                    },
                    'low_stock': {
                        'value': low_stock_count,
                        'trend': get_trend(low_stock_count, low_stock_count),
                        'product_ids': low_stock_product_ids
                    },
                    'in_out': {
                        'in': round(current_in, 2),
                        'out': round(current_out, 2),
                        'prev_in': round(prev_in, 2),
                        'prev_out': round(prev_out, 2),
                        'in_trend': get_trend(current_in, prev_in),
                        'out_trend': get_trend(current_out, prev_out)
                    }
                },
                'currency_symbol': self.env.company.currency_id.symbol or '$',
                'currency_code': self.env.company.currency_id.name or 'USD',
                'currency_position': self.env.company.currency_id.position or 'before',
                'currency_id': self.env.company.currency_id.id,
                'values_over_time': values_over_time,
                'categories': category_vals,
                'top_products': top_products,
                'locations': location_vals,
                'product_moves': product_moves
            }

        except Exception as e:
            _logger.error("!!! ERROR IN L4E INVENTORY DASHBOARD get_dashboard_data: %s", e, exc_info=True)
            return {
                'currency_symbol': '$',
                'currency_code': 'USD',
                'currency_position': 'before',
                'currency_id': False,
                'kpis': {
                    'total_value': {'value': 0.0, 'trend': 0.0},
                    'total_products': {'value': 0, 'trend': 0.0},
                    'stock_moves': {'value': 0, 'trend': 0.0},
                    'low_stock': {'value': 0, 'trend': 0.0, 'product_ids': []},
                    'in_out': {'in': 0.0, 'out': 0.0, 'prev_in': 0.0, 'prev_out': 0.0, 'in_trend': 0.0, 'out_trend': 0.0}
                },
                'values_over_time': [],
                'categories': [],
                'top_products': [],
                'locations': [],
                'product_moves': []
            }

    @api.model
    def get_products(self):
        try:
            domain = [('active', '=', True)]
            products = self.env['product.product'].search_read(
                domain=domain,
                fields=['id', 'display_name'],
                order='display_name asc'
            )
            return products
        except Exception as e:
            _logger.error("Error in L4eInventoryDashboard get_products: %s", e, exc_info=True)
            return []
