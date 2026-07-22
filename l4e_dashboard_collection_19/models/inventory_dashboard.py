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
                return "COALESCE(pt.name->>%s, pt.name->>'en_US', pt.name::text)"
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

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, product_id=None):
        try:
            company_id = self.env.company.id
            lang = self.env.lang or 'en_US'
            user_tz = self.env.user.tz or 'UTC'
            tz = pytz.timezone(user_tz)

            name_sql = self._get_name_sql()
            move_qty_sql = self._get_move_qty_sql()
            loc_name_sql = self._get_location_name_sql()
            is_name_json = '%s' in name_sql

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

            val_params = [company_id, dt_to_utc]
            if product_id:
                val_params.append(product_id)
            self.env.cr.execute(f"""
                SELECT COALESCE(SUM(svl.value), 0.0)
                FROM stock_valuation_layer svl
                JOIN product_product pp ON pp.id = svl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                WHERE svl.company_id = %s
                  AND svl.create_date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  {prod_cond}
            """, tuple(val_params))
            total_value = self.env.cr.fetchone()[0] or 0.0

            prev_val_params = [company_id, prev_dt_to_utc]
            if product_id:
                prev_val_params.append(product_id)
            self.env.cr.execute(f"""
                SELECT COALESCE(SUM(svl.value), 0.0)
                FROM stock_valuation_layer svl
                JOIN product_product pp ON pp.id = svl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                WHERE svl.company_id = %s
                  AND svl.create_date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  {prod_cond}
            """, tuple(prev_val_params))
            prev_total_value = self.env.cr.fetchone()[0] or 0.0

            prod_count_domain = [('active', '=', True)]
            if product_id:
                prod_count_domain.append(('id', '=', product_id))

            total_products = self.env['product.product'].search_count(prod_count_domain + [('create_date', '<=', dt_to_utc)])
            prev_total_products = self.env['product.product'].search_count(prod_count_domain + [('create_date', '<=', prev_dt_to_utc)])

            move_domain = [('state', '=', 'done'), ('company_id', '=', company_id)]
            if product_id:
                move_domain.append(('product_id', '=', product_id))

            stock_moves = self.env['stock.move'].search_count(move_domain + [('date', '>=', dt_from_utc), ('date', '<=', dt_to_utc)])
            prev_stock_moves = self.env['stock.move'].search_count(move_domain + [('date', '>=', prev_dt_from_utc), ('date', '<=', prev_dt_to_utc)])

            low_stock_domain = [('active', '=', True)]
            if product_id:
                low_stock_domain.append(('id', '=', product_id))

            products = self.env['product.product'].search(low_stock_domain)
            orderpoints = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', 'in', products.ids),
                ('company_id', '=', company_id)
            ])
            min_qty_map = {}
            for op in orderpoints:
                min_qty_map[op.product_id.id] = min_qty_map.get(op.product_id.id, 0.0) + op.product_min_qty

            cs_params = [company_id]
            if product_id:
                cs_params.append(product_id)

            im_params = [company_id, dt_to_utc]
            if product_id:
                im_params.append(product_id)

            om_params = [company_id, dt_to_utc]
            if product_id:
                om_params.append(product_id)

            main_params = []
            if product_id:
                main_params.append(product_id)

            qtys_params = cs_params + im_params + om_params + main_params

            self.env.cr.execute(f"""
                WITH current_stock AS (
                    SELECT sq.product_id, COALESCE(SUM(sq.quantity), 0.0) as qty
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sl.usage = 'internal' AND sq.company_id = %s
                      {"AND sq.product_id = %s" if product_id else ""}
                    GROUP BY sq.product_id
                ),
                incoming_moves AS (
                    SELECT sm.product_id, COALESCE(SUM({move_qty_sql}), 0.0) as qty
                    FROM stock_move sm
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dest ON dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND sm.company_id = %s
                      AND sm.date > %s
                      AND src.usage != 'internal'
                      AND dest.usage = 'internal'
                      {"AND sm.product_id = %s" if product_id else ""}
                    GROUP BY sm.product_id
                ),
                outgoing_moves AS (
                    SELECT sm.product_id, COALESCE(SUM({move_qty_sql}), 0.0) as qty
                    FROM stock_move sm
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dest ON dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND sm.company_id = %s
                      AND sm.date > %s
                      AND src.usage = 'internal'
                      AND dest.usage != 'internal'
                      {"AND sm.product_id = %s" if product_id else ""}
                    GROUP BY sm.product_id
                )
                SELECT pp.id,
                       COALESCE(cs.qty, 0.0) - COALESCE(im.qty, 0.0) + COALESCE(om.qty, 0.0) AS qty_at_date
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                LEFT JOIN current_stock cs ON cs.product_id = pp.id
                LEFT JOIN incoming_moves im ON im.product_id = pp.id
                LEFT JOIN outgoing_moves om ON om.product_id = pp.id
                WHERE (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL) AND pp.active = TRUE
                  {"AND pp.id = %s" if product_id else ""}
            """, tuple(qtys_params))
            curr_qtys = {row[0]: row[1] for row in self.env.cr.fetchall()}

            low_stock_count = 0
            low_stock_product_ids = []
            for pid, qty in curr_qtys.items():
                min_qty = min_qty_map.get(pid, 5.0)
                if qty < min_qty:
                    low_stock_count += 1
                    low_stock_product_ids.append(pid)

            cs_params_prev = [company_id]
            if product_id:
                cs_params_prev.append(product_id)

            im_params_prev = [company_id, prev_dt_to_utc]
            if product_id:
                im_params_prev.append(product_id)

            om_params_prev = [company_id, prev_dt_to_utc]
            if product_id:
                om_params_prev.append(product_id)

            main_params_prev = []
            if product_id:
                main_params_prev.append(product_id)

            prev_qtys_params = cs_params_prev + im_params_prev + om_params_prev + main_params_prev

            self.env.cr.execute(f"""
                WITH current_stock AS (
                    SELECT sq.product_id, COALESCE(SUM(sq.quantity), 0.0) as qty
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sl.usage = 'internal' AND sq.company_id = %s
                      {"AND sq.product_id = %s" if product_id else ""}
                    GROUP BY sq.product_id
                ),
                incoming_moves AS (
                    SELECT sm.product_id, COALESCE(SUM({move_qty_sql}), 0.0) as qty
                    FROM stock_move sm
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dest ON dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND sm.company_id = %s
                      AND sm.date > %s
                      AND src.usage != 'internal'
                      AND dest.usage = 'internal'
                      {"AND sm.product_id = %s" if product_id else ""}
                    GROUP BY sm.product_id
                ),
                outgoing_moves AS (
                    SELECT sm.product_id, COALESCE(SUM({move_qty_sql}), 0.0) as qty
                    FROM stock_move sm
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dest ON dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND sm.company_id = %s
                      AND sm.date > %s
                      AND src.usage = 'internal'
                      AND dest.usage != 'internal'
                      {"AND sm.product_id = %s" if product_id else ""}
                    GROUP BY sm.product_id
                )
                SELECT pp.id,
                       COALESCE(cs.qty, 0.0) - COALESCE(im.qty, 0.0) + COALESCE(om.qty, 0.0) AS qty_at_date
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                LEFT JOIN current_stock cs ON cs.product_id = pp.id
                LEFT JOIN incoming_moves im ON im.product_id = pp.id
                LEFT JOIN outgoing_moves om ON om.product_id = pp.id
                WHERE (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL) AND pp.active = TRUE
                  {"AND pp.id = %s" if product_id else ""}
            """, tuple(prev_qtys_params))
            prev_qtys = {row[0]: row[1] for row in self.env.cr.fetchall()}

            prev_low_stock_count = 0
            for pid, qty in prev_qtys.items():
                min_qty = min_qty_map.get(pid, 5.0)
                if qty < min_qty:
                    prev_low_stock_count += 1

            in_out_params = [company_id, dt_from_utc, dt_to_utc]
            if product_id:
                in_out_params.append(product_id)

            self.env.cr.execute(f"""
                SELECT COALESCE(SUM({move_qty_sql}), 0.0)
                FROM stock_move sm
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dest ON dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND sm.company_id = %s
                  AND sm.date >= %s AND sm.date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  AND src.usage != 'internal' AND dest.usage = 'internal'
                  {prod_cond}
            """, tuple(in_out_params))
            current_in = self.env.cr.fetchone()[0] or 0.0

            self.env.cr.execute(f"""
                SELECT COALESCE(SUM({move_qty_sql}), 0.0)
                FROM stock_move sm
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dest ON dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND sm.company_id = %s
                  AND sm.date >= %s AND sm.date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  AND src.usage = 'internal' AND dest.usage != 'internal'
                  {prod_cond}
            """, tuple(in_out_params))
            current_out = self.env.cr.fetchone()[0] or 0.0

            prev_in_out_params = [company_id, prev_dt_from_utc, prev_dt_to_utc]
            if product_id:
                prev_in_out_params.append(product_id)

            self.env.cr.execute(f"""
                SELECT COALESCE(SUM({move_qty_sql}), 0.0)
                FROM stock_move sm
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dest ON dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND sm.company_id = %s
                  AND sm.date >= %s AND sm.date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  AND src.usage != 'internal' AND dest.usage = 'internal'
                  {prod_cond}
            """, tuple(prev_in_out_params))
            prev_in = self.env.cr.fetchone()[0] or 0.0

            self.env.cr.execute(f"""
                SELECT COALESCE(SUM({move_qty_sql}), 0.0)
                FROM stock_move sm
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dest ON dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND sm.company_id = %s
                  AND sm.date >= %s AND sm.date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  AND src.usage = 'internal' AND dest.usage != 'internal'
                  {prod_cond}
            """, tuple(prev_in_out_params))
            prev_out = self.env.cr.fetchone()[0] or 0.0

            ot_base_params = [company_id, dt_from_utc]
            if product_id:
                ot_base_params.append(product_id)
            self.env.cr.execute(f"""
                SELECT COALESCE(SUM(svl.value), 0.0)
                FROM stock_valuation_layer svl
                JOIN product_product pp ON pp.id = svl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                WHERE svl.company_id = %s
                  AND svl.create_date < %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  {prod_cond}
            """, tuple(ot_base_params))
            running_val = self.env.cr.fetchone()[0] or 0.0

            ot_changes_params = [user_tz, company_id, dt_from_utc, dt_to_utc]
            if product_id:
                ot_changes_params.append(product_id)
            ot_changes_params.append(user_tz)
            self.env.cr.execute(f"""
                SELECT DATE(svl.create_date AT TIME ZONE 'UTC' AT TIME ZONE %s) AS day,
                       COALESCE(SUM(svl.value), 0.0) AS change
                FROM stock_valuation_layer svl
                JOIN product_product pp ON pp.id = svl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                WHERE svl.company_id = %s
                  AND svl.create_date >= %s
                  AND svl.create_date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  {prod_cond}
                GROUP BY DATE(svl.create_date AT TIME ZONE 'UTC' AT TIME ZONE %s)
                ORDER BY day
            """, tuple(ot_changes_params))
            changes = {row[0]: row[1] for row in self.env.cr.fetchall()}

            values_over_time = []
            curr_day = df
            while curr_day <= dt:
                running_val += changes.get(curr_day, 0.0)
                values_over_time.append({
                    'date': curr_day.strftime("%b %d"),
                    'value': round(running_val, 2)
                })
                curr_day += timedelta(days=1)

            cat_params = [company_id, dt_to_utc]
            if product_id:
                cat_params.append(product_id)
            self.env.cr.execute(f"""
                SELECT pc.id, pc.name, COALESCE(SUM(svl.value), 0.0) AS val
                FROM stock_valuation_layer svl
                JOIN product_product pp ON pp.id = svl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                WHERE svl.company_id = %s
                  AND svl.create_date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  {prod_cond}
                GROUP BY pc.id, pc.name
                HAVING SUM(svl.value) > 0
                ORDER BY val DESC
            """, tuple(cat_params))
            category_vals = [{'id': row[0], 'name': row[1] or 'Category', 'value': round(row[2], 2)} for row in self.env.cr.fetchall()]

            top_prod_params = []
            if is_name_json:
                top_prod_params.append(lang)
            top_prod_params.extend([company_id, dt_to_utc])
            if product_id:
                top_prod_params.append(product_id)

            self.env.cr.execute(f"""
                SELECT pp.id, {name_sql} AS name, COALESCE(SUM(svl.value), 0.0) AS val, pt.id AS tmpl_id
                FROM stock_valuation_layer svl
                JOIN product_product pp ON pp.id = svl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                WHERE svl.company_id = %s
                  AND svl.create_date <= %s
                  AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                  {prod_cond}
                GROUP BY pp.id, pt.id
                HAVING SUM(svl.value) > 0
                ORDER BY val DESC
                LIMIT 5
            """, tuple(top_prod_params))
            top_products_res = self.env.cr.fetchall()

            top_products = []
            for row in top_products_res:
                top_products.append({
                    'id': row[0],
                    'name': row[1] if isinstance(row[1], str) else str(row[1] or 'Product'),
                    'qty_on_hand': round(curr_qtys.get(row[0], 0.0), 2),
                    'value': round(row[2], 2),
                    'tmpl_id': row[3]
                })

            loc_params = []
            loc_params.append(company_id)
            if product_id:
                loc_params.append(product_id)
            loc_params.append(company_id)
            if product_id:
                loc_params.append(product_id)

            self.env.cr.execute(f"""
                SELECT sl.id, {loc_name_sql} AS name, COALESCE(SUM(sq.quantity), 0.0) AS qty,
                       COALESCE(SUM(sq.quantity * COALESCE(svl_cost.avg_cost, 0.0)), 0.0) AS val
                FROM stock_quant sq
                JOIN stock_location sl ON sl.id = sq.location_id
                JOIN product_product pp ON pp.id = sq.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                LEFT JOIN (
                    SELECT product_id,
                           SUM(value) / NULLIF(SUM(quantity), 0) AS avg_cost
                    FROM stock_valuation_layer
                    WHERE company_id = %s
                      {"AND product_id = %s" if product_id else ""}
                    GROUP BY product_id
                ) svl_cost ON svl_cost.product_id = pp.id
                WHERE sl.usage = 'internal'
                  AND sq.company_id = %s
                  {"AND sq.product_id = %s" if product_id else ""}
                GROUP BY sl.id, {loc_name_sql}
                HAVING SUM(sq.quantity) > 0 OR SUM(sq.quantity * COALESCE(svl_cost.avg_cost, 0.0)) > 0
                ORDER BY val DESC
                LIMIT 5
            """, tuple(loc_params))
            location_vals = [{'id': row[0], 'name': row[1] or 'Location', 'qty': round(row[2], 2), 'value': round(row[3], 2)} for row in self.env.cr.fetchall()]

            moves_params = []
            moves_params.extend([company_id, dt_from_utc, dt_to_utc])
            if product_id:
                moves_params.append(product_id)
            moves_params.extend([company_id, dt_from_utc, dt_to_utc])
            if product_id:
                moves_params.append(product_id)
            if is_name_json:
                moves_params.append(lang)

            self.env.cr.execute(f"""
                WITH incoming AS (
                    SELECT sm.product_id, SUM({move_qty_sql}) AS qty
                    FROM stock_move sm
                    JOIN product_product pp ON pp.id = sm.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN product_category pc ON pc.id = pt.categ_id
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dest ON dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND sm.company_id = %s
                      AND sm.date >= %s AND sm.date <= %s
                      AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                      AND src.usage != 'internal' AND dest.usage = 'internal'
                      {"AND sm.product_id = %s" if product_id else ""}
                    GROUP BY sm.product_id
                ),
                outgoing AS (
                    SELECT sm.product_id, SUM({move_qty_sql}) AS qty
                    FROM stock_move sm
                    JOIN product_product pp ON pp.id = sm.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN product_category pc ON pc.id = pt.categ_id
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dest ON dest.id = sm.location_dest_id
                    WHERE sm.state = 'done'
                      AND sm.company_id = %s
                      AND sm.date >= %s AND sm.date <= %s
                      AND (pc.show_in_dashboard IS TRUE OR pc.show_in_dashboard IS NULL)
                      AND src.usage = 'internal' AND dest.usage != 'internal'
                      {"AND sm.product_id = %s" if product_id else ""}
                    GROUP BY sm.product_id
                )
                SELECT pp.id, {name_sql} AS name,
                       COALESCE(inc.qty, 0.0) AS inc_qty,
                       COALESCE(outg.qty, 0.0) AS outg_qty,
                       COALESCE(inc.qty, 0.0) - COALESCE(outg.qty, 0.0) AS net_qty
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN incoming inc ON inc.product_id = pp.id
                LEFT JOIN outgoing outg ON outg.product_id = pp.id
                WHERE inc.qty > 0 OR outg.qty > 0
                ORDER BY (COALESCE(inc.qty, 0.0) + COALESCE(outg.qty, 0.0)) DESC
                LIMIT 5
            """, tuple(moves_params))
            product_moves = [{
                'id': row[0],
                'name': row[1] if isinstance(row[1], str) else str(row[1] or 'Product'),
                'in': round(row[2], 2),
                'out': round(row[3], 2),
                'net': round(row[4], 2)
            } for row in self.env.cr.fetchall()]

            def get_trend(curr, prev):
                if not prev:
                    return 100.0 if curr else 0.0
                return round(((curr - prev) / prev) * 100.0, 1)

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
                        'trend': get_trend(low_stock_count, prev_low_stock_count),
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
            _logger.exception("Error in L4eInventoryDashboard get_dashboard_data: %s", e)
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
            _logger.exception("Error in L4eInventoryDashboard get_products: %s", e)
            return []
