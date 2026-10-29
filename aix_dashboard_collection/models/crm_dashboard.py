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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

class CrmDashboard(models.TransientModel):
    _name = "crm.dashboard"
    _description = "Sales Office Dashboard Provider"

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}
        today = fields.Date.context_today(self)
        year = today.year
        current_month_str = str(today.month)
        card_filters = filters.get("card_filters") or {}

        # Global year and month filters
        year_filter = filters.get("year_filter") or str(today.year)
        filters["year_filter"] = year_filter
        year = int(year_filter)

        m_filter = filters.get("month_filter") or current_month_str
        filters["month_filter"] = m_filter

        def _get_date_range(m_val):
            if not m_val or m_val == "all":
                return None, None
            try:
                m_num = int(m_val)
                if 1 <= m_num <= 12:
                    first_day = datetime(year, m_num, 1).date()
                    if m_num == 12:
                        last_day = datetime(year, 12, 31).date()
                    else:
                        last_day = (datetime(year, m_num + 1, 1) - timedelta(days=1)).date()
                    return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass
            return None, None

        global_df, global_dt = f"{year}-01-01", f"{year}-12-31"

        if not filters.get("date_from"):
            filters["date_from"] = global_df
        if not filters.get("date_to"):
            filters["date_to"] = global_dt

        lead_domain, sale_domain, lead_domain_base, sale_domain_base = self._domains(filters)

        Lead = self.env["crm.lead"]
        Lead_all = Lead.with_context(active_test=False)
        Sale = self.env["sale.order"]
        Stage = self.env["crm.stage"]
        Activity = self.env["mail.activity"]
        allowed_companies = self.env.context.get("allowed_company_ids") or [self.env.company.id]

        currency = self.env.company.currency_id
        symbol = currency.symbol or "$"
        if symbol == "S$":
            symbol = "$"
        currency_info = {
            "symbol": symbol,
            "position": currency.position or "before",
            "name": currency.name or "USD",
        }

        month_labels = {
            "1": "January", "2": "February", "3": "March", "4": "April",
            "5": "May", "6": "June", "7": "July", "8": "August",
            "9": "September", "10": "October", "11": "November", "12": "December",
            "this_year": "This Year", "all": "All Time"
        }
        selected_month_label = month_labels.get(str(m_filter), today.strftime("%B"))

        def _smart_fmt(val):
            if val is None:
                val = 0.0
            s = currency_info["symbol"] or ""
            pos = currency_info["position"] or "before"
            code = (currency_info["name"] or "").upper()
            is_inr = (code == "INR" or s == "₹")
            abs_v = abs(val)

            if is_inr:
                if abs_v >= 10000000:
                    num = val / 10000000
                    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
                    txt = f"{num_str}Cr"
                elif abs_v >= 100000:
                    num = val / 100000
                    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
                    txt = f"{num_str}L"
                elif abs_v >= 1000:
                    num = val / 1000
                    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
                    txt = f"{num_str}K"
                else:
                    txt = f"{int(val)}" if val == int(val) else f"{val:,.2f}"
            else:
                # All International Currencies (EUR, USD, GBP, CAD, AUD, JPY, AED, SAR, etc.)
                if abs_v >= 1000000000:
                    num = val / 1000000000
                    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
                    txt = f"{num_str}B"
                elif abs_v >= 1000000:
                    num = val / 1000000
                    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
                    txt = f"{num_str}M"
                elif abs_v >= 1000:
                    num = val / 1000
                    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
                    txt = f"{num_str}K"
                else:
                    txt = f"{int(val)}" if val == int(val) else f"{val:,.2f}"

            if pos == "after":
                return f"{txt} {s}".strip()
            else:
                return f"{s}{txt}".strip()

        _fmt = _smart_fmt
        _short_fmt = _smart_fmt

        def _build_specific_domains(card_key):
            spec_month = card_filters.get(card_key)
            if not spec_month or spec_month == m_filter:
                return lead_domain, sale_domain
            df, dt = _get_date_range(spec_month)
            ld = list(lead_domain_base)
            sd = list(sale_domain_base)
            for k, fld in (("team_id", "team_id"), ("user_id", "user_id")):
                if filters.get(k):
                    try:
                        ld.append((fld, int(filters[k])))
                        sd.append((fld, int(filters[k])))
                    except Exception:
                        pass
            if df:
                ld.append(("create_date", ">=", df))
                sd.append(("date_order", ">=", df))
            if dt:
                ld.append(("create_date", "<=", dt))
                sd.append(("date_order", "<=", dt))
            return ld, sd

        # -------------------------------------------------------------
        # Real Dynamic Trend Calculation (Current vs Prior Calendar Period)
        # -------------------------------------------------------------
        def _get_prior_dates(d_from_str, d_to_str):
            if not d_from_str or not d_to_str:
                d_from = today.replace(day=1)
                d_to = today
            else:
                try:
                    d_from = fields.Date.from_string(d_from_str)
                    d_to = fields.Date.from_string(d_to_str)
                except Exception:
                    d_from = today.replace(day=1)
                    d_to = today

            next_day_after_to = d_to + timedelta(days=1)
            if d_from.day == 1 and next_day_after_to.day == 1:
                prior_from = d_from - relativedelta(months=1)
                prior_to = d_from - timedelta(days=1)
            else:
                delta = (d_to - d_from).days + 1
                prior_to = d_from - timedelta(days=1)
                prior_from = prior_to - timedelta(days=delta - 1)
            return prior_from.strftime("%Y-%m-%d"), prior_to.strftime("%Y-%m-%d")

        prior_from, prior_to = _get_prior_dates(filters.get("date_from"), filters.get("date_to"))
        prior_lead_domain = lead_domain_base + [("create_date", ">=", prior_from), ("create_date", "<=", prior_to), "|", ("active", "=", True), ("active", "=", False)]
        prior_sale_domain = sale_domain_base + [("date_order", ">=", prior_from), ("date_order", "<=", prior_to)]

        def _kpi_domains(kpi_key):
            """Build lead/sale domains for a specific KPI using its card_filters month."""
            kpi_m = card_filters.get(kpi_key) or current_month_str
            kdf, kdt = _get_date_range(kpi_m)
            ld = list(lead_domain_base)
            sd = list(sale_domain_base)
            for k, fld in (("team_id", "team_id"), ("user_id", "user_id")):
                if filters.get(k):
                    try:
                        ld.append((fld, "=", int(filters[k])))
                        sd.append((fld, "=", int(filters[k])))
                    except Exception:
                        pass
            if kdf:
                ld += [("create_date", ">=", kdf), ("create_date", "<=", kdt)]
                sd += [("date_order", ">=", kdf), ("date_order", "<=", kdt)]
            return ld, sd

        # KPI: Total Leads
        kpi_total_ld, _ = _kpi_domains("kpi_total")
        kpi_total_ld_all = kpi_total_ld + ["|", ("active", "=", True), ("active", "=", False)]
        total_leads = Lead_all.search_count(kpi_total_ld_all)

        # KPI: Won Revenue
        _, kpi_won_sd = _kpi_domains("kpi_won")
        won_orders = Sale.search(kpi_won_sd + [("state", "in", ["sale", "done"])])
        won_revenue = sum(won_orders.mapped("amount_total"))

        # KPI: Lost Revenue
        kpi_lost_ld, _ = _kpi_domains("kpi_lost")
        lost_domain = kpi_lost_ld + ["|", ("active", "=", False), ("stage_id.name", "ilike", "lost")]
        lost_leads = Lead_all.search(lost_domain)
        lost_revenue = sum(lost_leads.mapped("expected_revenue"))

        # KPI: Quotation Pending
        _, kpi_quotes_sd = _kpi_domains("kpi_quotes")
        quotes_pending_orders = Sale.search(kpi_quotes_sd + [("state", "in", ["draft", "sent"])])
        quotes_pending_count = len(quotes_pending_orders)
        quotes_pending_value = sum(quotes_pending_orders.mapped("amount_total"))

        # KPI: Overdue & Today Activities (use kpi month to filter deadline)
        kpi_overdue_m = card_filters.get("kpi_overdue") or current_month_str
        kpi_today_m = card_filters.get("kpi_today") or current_month_str
        overdue_df, overdue_dt = _get_date_range(kpi_overdue_m)
        today_df, today_dt = _get_date_range(kpi_today_m)

        activity_base_domain = [("res_model", "=", "crm.lead")]
        allowed_lead_ids = Lead_all.search([("company_id", "in", allowed_companies)]).ids
        activity_base_domain.append(("res_id", "in", allowed_lead_ids))
        if filters.get("user_id"):
            try:
                activity_base_domain.append(("user_id", "=", int(filters["user_id"])))
            except Exception:
                pass

        overdue_domain = activity_base_domain[:]
        if overdue_df:
            overdue_domain += [("date_deadline", ">=", overdue_df), ("date_deadline", "<=", overdue_dt)]
        overdue_activities_count = Activity.search_count(overdue_domain + [("date_deadline", "<", today)])

        today_domain = activity_base_domain[:]
        if today_df:
            today_domain += [("date_deadline", ">=", today_df), ("date_deadline", "<=", today_dt)]
        today_activities_count = Activity.search_count(today_domain + [("date_deadline", "=", today)])

        # Prior period for global trend (not used in display but kept for future use)
        prior_from, prior_to = _get_prior_dates(filters.get("date_from"), filters.get("date_to"))

        kpis = {
            "company_name": self.env.company.name,
            "total_leads": total_leads,
            "total_leads_formatted": f"{total_leads:,}",
            "won_revenue": won_revenue,
            "won_revenue_formatted": _fmt(won_revenue),
            "lost_revenue": lost_revenue,
            "lost_revenue_formatted": _fmt(lost_revenue),
            "quotes_pending": quotes_pending_count,
            "quotes_pending_formatted": _fmt(quotes_pending_value),
            "overdue_activities": overdue_activities_count,
            "overdue_activities_formatted": f"{overdue_activities_count:,}",
            "today_activities": today_activities_count,
            "today_activities_formatted": f"{today_activities_count:,}",
            "total_trend": "0%",
            "won_trend": "0%",
            "lost_trend": "0%",
            "quotes_trend": "0%",
            "overdue_trend": "0%",
            "today_trend": "0%",
        }

        # -------------------------------------------------------------
        # 1. Month Sales Trend (Card Specific Filter)
        # -------------------------------------------------------------
        trend_m = card_filters.get("sales_trend") or m_filter
        t_df, t_dt = _get_date_range(trend_m)
        if t_df and t_dt:
            d_start = fields.Date.from_string(t_df)
            d_end = fields.Date.from_string(t_dt)
        else:
            d_start = today.replace(day=1)
            next_m = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            d_end = next_m - timedelta(days=1)

        total_days = max(1, (d_end - d_start).days + 1)
        step = max(1, total_days // 5)

        sales_trend_points = []
        for i in range(5):
            p_start = d_start + timedelta(days=i * step)
            if i == 4:
                p_end = d_end
            else:
                p_end = p_start + timedelta(days=step - 1)
                if p_end > d_end:
                    p_end = d_end

            p_start_str = p_start.strftime("%Y-%m-%d")
            p_end_str = p_end.strftime("%Y-%m-%d")
            label = f"{p_start.strftime('%b %d')} - {p_end.strftime('%d')}"

            interval_so = Sale.search(sale_domain_base + [
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", p_start_str),
                ("date_order", "<=", p_end_str + " 23:59:59")
            ])
            rev = sum(interval_so.mapped("amount_total"))
            sales_trend_points.append({
                "label": label,
                "revenue": rev,
                "date_from": p_start_str,
                "date_to": p_end_str,
            })

        max_trend_rev = max([p["revenue"] for p in sales_trend_points] + [1])
        for p in sales_trend_points:
            p["revenue_formatted"] = _short_fmt(p["revenue"])
            p["height_pct"] = round((p["revenue"] / max_trend_rev) * 100) if max_trend_rev else 0

        chart_w, chart_h = 500, 180
        coords = []
        n_points = len(sales_trend_points)
        for idx, pt in enumerate(sales_trend_points):
            x = round(30 + idx * ((chart_w - 60) / (n_points - 1)))
            y = round((chart_h - 30) - (pt["height_pct"] / 100.0) * (chart_h - 50))
            coords.append((x, y))
            pt["x"] = x
            pt["y"] = y

        line_path = "M " + " L ".join([f"{c[0]},{c[1]}" for c in coords])
        area_path = line_path + f" L {coords[-1][0]},{chart_h-20} L {coords[0][0]},{chart_h-20} Z"

        month_sales_trend = {
            "points": sales_trend_points,
            "line_path": line_path,
            "area_path": area_path,
            "max_formatted": _short_fmt(max_trend_rev),
        }

        # -------------------------------------------------------------
        # 2. Pipeline Details Table (Card Specific Filter)
        # -------------------------------------------------------------
        pipe_lead_domain, pipe_sale_domain = _build_specific_domains("pipeline")
        pipe_won_orders = Sale.search(pipe_sale_domain + [("state", "in", ["sale", "done"])])
        pipe_won_revenue = sum(pipe_won_orders.mapped("amount_total"))

        pipe_won_domain = pipe_lead_domain + ["|", ("probability", "=", 100), ("stage_id.is_won", "=", True)]
        pipe_lost_domain = pipe_lead_domain + ["|", ("active", "=", False), ("stage_id.name", "ilike", "lost")]

        stages = Stage.search([], order="sequence asc")
        stage_colors = ["#2563eb", "#16a34a", "#ea580c", "#9333ea", "#059669", "#dc2626"]
        pipeline_rows = []
        total_opps = 0
        total_pipe_val = 0
        total_exp_rev = 0

        for idx, stg in enumerate(stages):
            s_name = (stg.name or "").lower()
            is_won = getattr(stg, "is_won", False) or ("won" in s_name)
            if "lost" in s_name:
                leads_in_stage = Lead_all.search(pipe_lost_domain)
            elif is_won:
                leads_in_stage = Lead_all.search(pipe_won_domain)
            else:
                leads_in_stage = Lead.search(pipe_lead_domain + [("active", "=", True), ("stage_id", "=", stg.id)])

            count = len(leads_in_stage)
            pipe_val = sum(leads_in_stage.mapped("expected_revenue"))

            if is_won:
                pipe_val = max(pipe_won_revenue, pipe_val)

            stg_prob = getattr(stg, "probability", None)
            if stg_prob is not None:
                prob = stg_prob
            elif count:
                prob = sum(leads_in_stage.mapped("probability")) / count
            else:
                prob = 100.0 if is_won else (0.0 if "lost" in s_name else 25.0)

            exp_rev = pipe_val
            total_opps += count
            total_pipe_val += pipe_val
            total_exp_rev += exp_rev

            pipeline_rows.append({
                "id": stg.id,
                "name": stg.name,
                "color": stage_colors[idx % len(stage_colors)],
                "count": count,
                "is_won": is_won,
                "is_lost": "lost" in s_name,
                "expected_revenue": _fmt(exp_rev),
            })

        pipeline_details = {
            "rows": pipeline_rows,
            "total_count": total_opps,
            "total_pipeline_value": _fmt(total_pipe_val),
            "total_expected_revenue": _fmt(total_exp_rev),
        }

        # -------------------------------------------------------------
        # 3. Sales Team Performance (Card Specific Filter)
        # -------------------------------------------------------------
        team_lead_domain, team_sale_domain = _build_specific_domains("team_perf")
        team_lead_all = team_lead_domain + ["|", ("active", "=", True), ("active", "=", False)]
        user_groups = Lead_all.read_group(team_lead_all, ["user_id"], ["user_id"], limit=20)
        team_perf_rows = []
        seen_user_ids = set()

        for row in user_groups:
            if not row["user_id"]:
                continue
            u_id, u_name = row["user_id"]
            if u_id in seen_user_ids:
                continue
            seen_user_ids.add(u_id)

            u_won_orders = Sale.search(team_sale_domain + [("user_id", "=", u_id), ("state", "in", ["sale", "done"])])
            u_rev = sum(u_won_orders.mapped("amount_total"))

            team_perf_rows.append({
                "id": u_id,
                "name": u_name,
                "revenue": u_rev,
                "revenue_formatted": _short_fmt(u_rev),
            })

        team_perf_rows.sort(key=lambda x: x["revenue"], reverse=True)
        team_perf_rows = team_perf_rows[:9]
        max_user_rev = team_perf_rows[0]["revenue"] if team_perf_rows and team_perf_rows[0]["revenue"] > 0 else 1

        n_users = len(team_perf_rows)
        bar_colors = ["#818cf8", "#34d399", "#fb923c", "#60a5fa", "#f472b6", "#a78bfa", "#2dd4bf", "#fbbf24"]

        # Horizontal bar chart layout
        bar_h = 24
        bar_gap = 8
        name_col_w = 120
        chart_left = name_col_w + 8
        chart_right_pad = 70
        chart_w = 500
        bar_area_w = chart_w - chart_left - chart_right_pad
        chart_total_h = n_users * (bar_h + bar_gap) + 16

        for idx, row in enumerate(team_perf_rows):
            val_pct = row["revenue"] / max_user_rev if max_user_rev > 0 else 0
            bw = max(6, round(val_pct * bar_area_w))
            by = 10 + idx * (bar_h + bar_gap)

            row["bar_x"] = chart_left
            row["bar_y"] = by
            row["bar_w"] = bw
            row["bar_h"] = bar_h
            row["name_x"] = name_col_w
            row["name_y"] = by + bar_h / 2 + 5
            row["val_x"] = chart_left + bw + 8
            row["val_y"] = by + bar_h / 2 + 5
            row["color"] = bar_colors[idx % len(bar_colors)]
            row["revenue_fmt"] = _fmt(row["revenue"])
            row["revenue_short"] = _smart_fmt(row["revenue"])
            row["name_short"] = row["name"][:18] + '..' if len(row["name"]) > 20 else row["name"]
            row["rank"] = idx + 1

        line_path = ""
        chart_svg_viewbox = f"0 0 {chart_w} {chart_total_h}" 

        # -------------------------------------------------------------
        # 4. Recent Won Orders (Card Specific Filter)
        # -------------------------------------------------------------
        _, won_sale_domain = _build_specific_domains("recent_won")
        recent_won_raw = Sale.search(won_sale_domain + [("state", "in", ["sale", "done"])], order="date_order desc", limit=5)
        recent_won_orders = []
        for so in recent_won_raw:
            recent_won_orders.append({
                "id": so.id,
                "name": so.name,
                "customer": so.partner_id.name if so.partner_id else "—",
                "salesperson": so.user_id.name if so.user_id else "Unassigned",
                "revenue": _fmt(so.amount_total),
                "date": so.date_order.strftime("%b %d, %Y") if so.date_order else "—",
            })

        # -------------------------------------------------------------
        # 5. Top Sales Person (Card Specific Filter)
        # -------------------------------------------------------------
        top_sp_lead_domain, top_sp_sale_domain = _build_specific_domains("top_sp")
        top_sp_lead_all = top_sp_lead_domain + ["|", ("active", "=", True), ("active", "=", False)]
        
        user_groups_sp = Lead_all.read_group(top_sp_lead_all, ["user_id"], ["user_id"], limit=20)
        sp_perf_rows = []
        seen_sp_ids = set()

        for row in user_groups_sp:
            if not row["user_id"]:
                continue
            u_id, u_name = row["user_id"]
            if u_id in seen_sp_ids:
                continue
            seen_sp_ids.add(u_id)

            u_won_orders = Sale.search(top_sp_sale_domain + [("user_id", "=", u_id), ("state", "in", ["sale", "done"])])
            u_rev = sum(u_won_orders.mapped("amount_total"))

            sp_perf_rows.append({
                "id": u_id,
                "name": u_name,
                "revenue": u_rev,
                "revenue_formatted": _short_fmt(u_rev),
            })

        sp_perf_rows.sort(key=lambda x: x["revenue"], reverse=True)

        top_sp_rows = []
        for idx, row in enumerate(sp_perf_rows[:10]):
            u_id = row["id"]
            u_lead_domain = top_sp_lead_all + [("user_id", "=", u_id)]
            u_total = Lead_all.search_count(u_lead_domain)
            u_won = Lead_all.search_count(u_lead_domain + ["|", ("probability", "=", 100), ("stage_id.is_won", "=", True)])
            win_rate_val = round((u_won * 100.0 / u_total), 1) if u_total else 0.0
            rate_color = "win-high" if win_rate_val >= 30 else ("win-med" if win_rate_val >= 15 else "win-low")

            top_sp_rows.append({
                "rank": idx + 1,
                "id": u_id,
                "name": row["name"],
                "avatar": f"/web/image?model=res.users&id={u_id}&field=avatar_128",
                "revenue": row["revenue_formatted"],
                "won_revenue": _fmt(row["revenue"]),
                "deals_won": u_won,
                "win_rate": f"{win_rate_val}%",
                "rate_color": rate_color,
            })

        # -------------------------------------------------------------
        # 6. Top Customers (Card Specific Filter)
        # -------------------------------------------------------------
        _, top_cust_sale_domain = _build_specific_domains("top_cust")
        partner_groups = Sale.read_group(top_cust_sale_domain + [("state", "in", ["sale", "done"])], ["partner_id", "amount_total:sum"], ["partner_id"], orderby="amount_total desc", limit=10)
        top_customers = []
        for idx, row in enumerate(partner_groups):
            if not row["partner_id"]:
                continue
            p_id, p_name = row["partner_id"]
            rev = row["amount_total"]
            deals_count = row["partner_id_count"]

            top_customers.append({
                "rank": idx + 1,
                "id": p_id,
                "name": p_name,
                "revenue": _fmt(rev),
                "deals": deals_count,
                "won_revenue": _fmt(rev),
            })

        # -------------------------------------------------------------
        # 7. Upcoming Activities (Card Specific Filter)
        # -------------------------------------------------------------
        act_dom = list(activity_base_domain)
        act_m = card_filters.get("activities")
        if act_m and act_m != "all":
            adf, adt = _get_date_range(act_m)
            if adf:
                act_dom.append(("date_deadline", ">=", adf))
            if adt:
                act_dom.append(("date_deadline", "<=", adt))

        activities_raw = Activity.search(act_dom, order="date_deadline asc, id desc", limit=10)
        upcoming_activities = []

        for act in activities_raw:
            customer = ""
            record = False
            if act.res_model and act.res_id:
                try:
                    record = self.env[act.res_model].sudo().browse(act.res_id).exists()
                    if record:
                        if hasattr(record, "partner_id") and record.partner_id:
                            customer = record.partner_id.name
                        elif hasattr(record, "contact_name") and record.contact_name:
                            customer = record.contact_name
                        elif hasattr(record, "name"):
                            customer = record.name
                except Exception:
                    pass
            if not customer:
                customer = act.res_name or "—"

            act_type = act.activity_type_id.name if act.activity_type_id else "Activity"
            is_overdue = act.date_deadline and act.date_deadline < today
            days_diff = (act.date_deadline - today).days if act.date_deadline else 999

            if is_overdue or days_diff == 0:
                prio = "High"
                prio_cls = "badge-high"
            elif 1 <= days_diff <= 7:
                prio = "Medium"
                prio_cls = "badge-med"
            else:
                prio = "Low"
                prio_cls = "badge-low"

            upcoming_activities.append({
                "id": act.id,
                "res_model": act.res_model,
                "res_id": act.res_id,
                "activity": act.summary or act_type,
                "customer": customer,
                "salesperson": act.user_id.name if act.user_id else "Unassigned",
                "type": act_type,
                "date": act.date_deadline.strftime("%b %d, %Y") if act.date_deadline else "—",
                "time": "10:00 AM",
                "priority": prio,
                "priority_class": prio_cls,
                "status": "Overdue" if is_overdue else ("Today" if days_diff == 0 else "Not Done"),
                "status_class": "badge-high" if is_overdue else ("status-done" if days_diff == 0 else "status-not-done"),
            })

        team_domain = ["|", ("company_id", "=", False), ("company_id", "in", allowed_companies)]
        teams = self.env["crm.team"].search_read(team_domain, ["name"])

        user_ids = set()
        if filters.get("team_id"):
            try:
                selected_team = self.env["crm.team"].browse(int(filters["team_id"])).exists()
                if selected_team:
                    if hasattr(selected_team, "member_ids") and selected_team.member_ids:
                        user_ids.update(selected_team.member_ids.ids)
                    if hasattr(selected_team, "crm_team_member_ids") and selected_team.crm_team_member_ids:
                        user_ids.update(selected_team.crm_team_member_ids.mapped("user_id").ids)
                    if selected_team.user_id:
                        user_ids.add(selected_team.user_id.id)
            except Exception:
                pass

        if user_ids:
            user_domain = [("id", "in", list(user_ids)), ("share", "=", False), ("company_ids", "in", allowed_companies)]
        else:
            user_domain = [("share", "=", False), ("company_ids", "in", allowed_companies)]
        users = self.env["res.users"].search_read(user_domain, ["name"], order="name asc")

        self.env.cr.execute("""
            SELECT DISTINCT EXTRACT(YEAR FROM create_date)::integer as yr 
            FROM crm_lead 
            WHERE create_date IS NOT NULL
            UNION
            SELECT DISTINCT EXTRACT(YEAR FROM date_order)::integer as yr 
            FROM sale_order 
            WHERE date_order IS NOT NULL
            ORDER BY yr DESC
        """)
        years_list = [r[0] for r in self.env.cr.fetchall() if r[0]]
        current_yr = today.year
        required_years = {current_yr, current_yr - 1, current_yr - 2}
        all_years = set(years_list).union(required_years)
        years_list = sorted(list(all_years), reverse=True)

        self.env.cr.execute("""
            SELECT DISTINCT EXTRACT(MONTH FROM create_date)::integer as mth 
            FROM crm_lead 
            WHERE create_date IS NOT NULL AND EXTRACT(YEAR FROM create_date) = %s
            UNION
            SELECT DISTINCT EXTRACT(MONTH FROM date_order)::integer as mth 
            FROM sale_order 
            WHERE date_order IS NOT NULL AND EXTRACT(YEAR FROM date_order) = %s
            ORDER BY mth ASC
        """, (year, year))
        months_list = [r[0] for r in self.env.cr.fetchall() if r[0]]
        if year == today.year and today.month not in months_list:
            months_list.append(today.month)
            months_list.sort()
        if not months_list:
            months_list = [today.month]

        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        months_data = [{"value": str(m), "name": month_names[m]} for m in months_list]

        return {
            "kpis": kpis,
            "month_label": selected_month_label,
            "month_sales_trend": month_sales_trend,
            "pipeline_details": pipeline_details,
            "sales_team_performance": team_perf_rows,
            "sales_team_performance_line_path": line_path,
            "sales_team_performance_chart_w": chart_w,
            "chart_svg_viewbox": chart_svg_viewbox,
            "sales_team_performance_max_fmt": _smart_fmt(max_user_rev) if team_perf_rows else "0",
            "recent_won_orders": recent_won_orders,
            "top_salespersons": top_sp_rows,
            "top_customers": top_customers,
            "upcoming_activities": upcoming_activities,
            "teams": teams,
            "users": users,
            "years": [str(y) for y in years_list],
            "months": months_data,
            "currency": currency_info,
        }

    def _domains(self, filters):
        allowed_companies = self.env.context.get("allowed_company_ids") or [self.env.company.id]
        lead_domain_base = ["|", ("company_id", "=", False), ("company_id", "in", allowed_companies)]
        sale_domain_base = [("company_id", "in", allowed_companies), ("opportunity_id", "!=", False)]

        lead_domain = list(lead_domain_base)
        sale_domain = list(sale_domain_base)

        for key, field in (("team_id", "team_id"), ("user_id", "user_id")):
            if filters.get(key):
                try:
                    lead_domain.append((field, "=", int(filters[key])))
                    sale_domain.append((field, "=", int(filters[key])))
                except (ValueError, TypeError):
                    pass

        def _is_valid_date(val):
            if not val or not isinstance(val, str):
                return False
            parts = val.split("-")
            return len(parts) == 3 and all(p.isdigit() for p in parts)

        if _is_valid_date(filters.get("date_from")):
            lead_domain.append(("create_date", ">=", filters["date_from"]))
            sale_domain.append(("date_order", ">=", filters["date_from"]))

        if _is_valid_date(filters.get("date_to")):
            lead_domain.append(("create_date", "<=", filters["date_to"]))
            sale_domain.append(("date_order", "<=", filters["date_to"]))

        return lead_domain, sale_domain, lead_domain_base, sale_domain_base
