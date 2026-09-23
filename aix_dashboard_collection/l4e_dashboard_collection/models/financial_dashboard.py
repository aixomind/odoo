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
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class FinancialDashboard(models.TransientModel):
    _name = "financial.dashboard"
    _description = "Financial Dashboard"

    INVOICE_STATUS_CONFIG = [
        ("not_paid", "Not Paid", True, "#fff1f2", "#dc3545", "fa-clock-o"),
        ("in_payment", "In Payment", True, "#fff8e7", "#f59f00", "fa-hourglass-half"),
        ("paid", "Paid", False, "#edfdf3", "#0f9d58", "fa-check-circle-o"),
        ("partial", "Partially Paid", True, "#eefcff", "#128c7e", "fa-user-o"),
        ("reversed", "Reversed", False, "#f8fafc", "#334155", "fa-refresh"),
        ("blocked", "Blocked", True, "#f8fafc", "#111827", "fa-lock"),
        ("released", "Payment Released", True, "#f5efff", "#6d4aff", "fa-paper-plane-o"),
    ]

    SALARY_STATE_CONFIG = [
        ("draft", "Draft", "#fff8e7", "#f59f00", "fa-file-text-o"),
        ("verify", "Waiting", "#fff4ed", "#f97316", "fa-clock-o"),
        ("paid", "Paid", "#edfdf3", "#0f9d58", "fa-check-circle-o"),
        ("cancel", "Cancelled", "#f8fafc", "#334155", "fa-times-circle-o"),
    ]

    CATEGORY_CONFIG = {
        "profitability": {
            "label": "Profitability",
            "icon": "fa-bar-chart",
            "color": "#16a163",
            "description": "Measures the ability of the business to generate earnings from its operations",
        },
        "liquidity": {
            "label": "Liquidity",
            "icon": "fa-tint",
            "color": "#2563eb",
            "description": "Tracks cash strength and short-term obligations",
        },
        "solvency": {
            "label": "Solvency",
            "icon": "fa-shield",
            "color": "#6d4aff",
            "description": "Compares debt, equity, and long-term financial stability",
        },
        "efficiency": {
            "label": "Efficiency Metrics",
            "icon": "fa-cogs",
            "color": "#f59f00",
            "description": "Evaluates how effectively resources generate turnover",
        },
        "valuation": {
            "label": "Valuation Metrics",
            "icon": "fa-line-chart",
            "color": "#0284c7",
            "description": "Summarizes overall financial scale and asset backing",
        },
        "cash_flow": {
            "label": "Cash Flow Metrics",
            "icon": "fa-money",
            "color": "#d97706",
            "description": "Shows cash received, spent, and closing bank position",
        },
        "returns": {
            "label": "Return Metrics",
            "icon": "fa-area-chart",
            "color": "#e11d48",
            "description": "Measures returns compared with assets, equity, and revenue",
        },
    }

    @api.model
    def get_dashboard_data(self, period="this_year", category="profitability", filters=None, metric_period=None, metric_date_from=False, metric_date_to=False, **kwargs):
        filters = filters or {}
        company = self.env.company
        sale_filters = self._get_card_filters(filters, "sale")
        salary_filters = self._get_card_filters(filters, "salary")
        purchase_filters = self._get_card_filters(filters, "purchase")

        sale_date_from, sale_date_to = self._get_date_range(period, sale_filters.get("date_from"), sale_filters.get("date_to"))
        salary_date_from, salary_date_to = self._get_date_range(period, salary_filters.get("date_from"), salary_filters.get("date_to"))
        purchase_date_from, purchase_date_to = self._get_date_range(period, purchase_filters.get("date_from"), purchase_filters.get("date_to"))

        m_date_from, m_date_to = self._get_date_range(metric_period or period, metric_date_from, metric_date_to)
        category = category if category in self.CATEGORY_CONFIG else "profitability"

        cards = [
            self._get_invoice_summary("sale", sale_date_from, sale_date_to, sale_filters),
            self._get_salary_summary(salary_date_from, salary_date_to, salary_filters),
            self._get_invoice_summary("purchase", purchase_date_from, purchase_date_to, purchase_filters),
        ]

        return {
            "cards": cards,
            "categories": self._get_categories(),
            "selected_category": category,
            "metrics": self._get_financial_metrics(category, m_date_from, m_date_to),
            "period": {
                "key": period,
                "date_from": fields.Date.to_string(m_date_from) if m_date_from else False,
                "date_to": fields.Date.to_string(m_date_to) if m_date_to else False,
            },
            "currency": {
                "symbol": company.currency_id.symbol or "$",
                "code": company.currency_id.name or "USD",
                "position": company.currency_id.position or "before",
            },
            "currency_symbol": company.currency_id.symbol or "$",
            "currency_code": company.currency_id.name or "USD",
        }

    @api.model
    def get_card_data(self, card_type, period, filters=None):
        filters = filters or {}
        card_filters = self._get_card_filters(filters, card_type)
        date_from, date_to = self._get_date_range(period, card_filters.get("date_from"), card_filters.get("date_to"))
        if card_type == "sale":
            return self._get_invoice_summary("sale", date_from, date_to, card_filters)
        elif card_type == "purchase":
            return self._get_invoice_summary("purchase", date_from, date_to, card_filters)
        elif card_type == "salary":
            return self._get_salary_summary(date_from, date_to, card_filters)
        return False

    @api.model
    def get_filter_options(self):
        partners = self.env["res.partner"].sudo()
        current_year = date.today().year
        years = [str(y) for y in range(current_year, current_year - 5, -1)]

        return {
            "years": years,
            "customers": partners.search_read(
                [("parent_id", "=", False), ("active", "=", True)],
                ["id", "name"],
                limit=250,
                order="name asc",
            ),
            "vendors": partners.search_read(
                [("parent_id", "=", False), ("active", "=", True)],
                ["id", "name"],
                limit=250,
                order="name asc",
            ),
            "users": self.env["res.users"].search_read(
                [("share", "=", False), ("active", "=", True)],
                ["id", "name"],
                limit=200,
                order="name asc",
            ),
            "employees": self.env["hr.employee"].search_read(
                [("active", "=", True)],
                ["id", "name"],
                limit=300,
                order="name asc",
            ) if "hr.employee" in self.env else [],
            "departments": self.env["hr.department"].search_read(
                [("active", "=", True)],
                ["id", "name"],
                limit=100,
                order="name asc",
            ) if "hr.department" in self.env else [],
        }

    @api.model
    def action_open_invoice_records(self, journal_type, status_key=False, period="this_year", filters=None):
        filters = filters or {}
        card_type = "sale" if journal_type in ("sale", "out_invoice") else "purchase"
        card_filters = self._get_card_filters(filters, card_type)
        date_from, date_to = self._get_date_range(period, card_filters.get("date_from"), card_filters.get("date_to"))
        
        move_types = ["out_invoice", "out_refund"] if journal_type in ("sale", "out_invoice") else ["in_invoice", "in_refund"]
        domain = [
            ("move_type", "in", move_types),
            ("state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
        ] + self._invoice_domain_filters(card_type, date_from, date_to, card_filters)

        if status_key and status_key not in ("total", "total_invoices", "total_expenses"):
            domain.append(("payment_state", "=", status_key))

        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoices") if journal_type in ("sale", "out_invoice") else _("Vendor Bills"),
            "res_model": "account.move",
            "views": [(False, "list"), (False, "form")],
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_move_type": "out_invoice" if journal_type in ("sale", "out_invoice") else "in_invoice"},
        }

    @api.model
    def action_open_salary_records(self, status_key=False, period="this_year", filters=None):
        filters = filters or {}
        card_filters = self._get_card_filters(filters, "salary")
        date_from, date_to = self._get_date_range(period, card_filters.get("date_from"), card_filters.get("date_to"))
        domain = self._salary_domain(date_from, date_to, card_filters)

        if isinstance(status_key, str) and status_key.startswith("rule_"):
            rule_code = status_key[5:]
            slips = self.env["hr.payslip"].search(domain + [("state", "!=", "cancel")])
            return {
                "type": "ir.actions.act_window",
                "name": _("Payslip Lines - %s") % rule_code,
                "res_model": "hr.payslip.line",
                "views": [(False, "list"), (False, "form")],
                "view_mode": "list,form",
                "domain": [
                    ("slip_id", "in", slips.ids),
                    ("salary_rule_id.code", "=", rule_code),
                ],
            }
        if status_key == "total_net":
            domain.append(("state", "in", ["draft", "verify", "done", "paid"]))
        elif status_key in ("verify", "waiting", "done"):
            domain.append(("state", "in", ["verify", "done", "waiting", "validated"]))
        elif status_key:
            domain.append(("state", "=", status_key))

        return {
            "type": "ir.actions.act_window",
            "name": _("Salaries"),
            "res_model": "hr.payslip",
            "views": [(False, "list"), (False, "form")],
            "view_mode": "list,form",
            "domain": domain,
        }

    def _get_categories(self):
        return [{"key": key, **value} for key, value in self.CATEGORY_CONFIG.items()]

    def _get_card_filters(self, filters, card_type):
        card_filters = filters.get("cards", {}).get(card_type) if isinstance(filters.get("cards"), dict) else None
        return card_filters or filters

    def _get_date_range(self, period, date_from=None, date_to=None):
        today = date.today()
        if date_from or date_to:
            return (fields.Date.to_date(date_from) if date_from else False,
                    fields.Date.to_date(date_to) if date_to else False)
        if not period or period == "all":
            return False, False
        if str(period).isdigit():
            y = int(period)
            return date(y, 1, 1), date(y, 12, 31)
        if period == "today":
            return today, today
        if period == "this_week":
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=6)
        if period == "this_month":
            start = today.replace(day=1)
            return start, today
        if period == "this_quarter":
            qm = ((today.month - 1) // 3) * 3 + 1
            start = today.replace(month=qm, day=1)
            return start, today
        if period == "this_year":
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        return False, False

    def _invoice_domain_filters(self, journal_type, date_from, date_to, filters):
        domain = []
        if date_from:
            domain.append(("invoice_date", ">=", fields.Date.to_string(date_from)))
        if date_to:
            domain.append(("invoice_date", "<=", fields.Date.to_string(date_to)))
        if journal_type in ("sale", "out_invoice") and filters.get("customer_id"):
            domain.append(("partner_id", "=", int(filters["customer_id"])))
        if journal_type in ("purchase", "in_invoice") and filters.get("vendor_id"):
            domain.append(("partner_id", "=", int(filters["vendor_id"])))
        if filters.get("user_id"):
            domain.append(("invoice_user_id", "=", int(filters["user_id"])))
        return domain

    def _get_invoice_summary(self, journal_type, date_from, date_to, filters):
        Move = self.env["account.move"]
        move_types = ["out_invoice", "out_refund"] if journal_type in ("sale", "out_invoice") else ["in_invoice", "in_refund"]
        base_domain = [
            ("state", "=", "posted"),
            ("move_type", "in", move_types),
            ("company_id", "=", self.env.company.id),
        ] + self._invoice_domain_filters(journal_type, date_from, date_to, filters)
        currency = self.env.company.currency_id

        stats = []
        for key, label, use_residual, background, color, icon in self.INVOICE_STATUS_CONFIG:
            records = Move.search(base_domain + [("payment_state", "=", key)])
            amount = sum(records.mapped("amount_residual" if use_residual else "amount_total")) if records else 0.0
            stats.append({
                "key": key,
                "label": label,
                "count": len(records),
                "amount": abs(amount),
                "amount_formatted": self._format_amount(abs(amount), currency),
                "background": background,
                "color": color,
                "icon": icon,
            })

        all_moves = Move.search(base_domain)
        tot_amount = sum(all_moves.mapped("amount_total")) if all_moves else 0.0
        tot_label = "Total Invoices" if journal_type in ("sale", "out_invoice") else "Total Expenses"
        stats.append({
            "key": "total",
            "label": tot_label,
            "count": len(all_moves),
            "amount": abs(tot_amount),
            "amount_formatted": self._format_amount(abs(tot_amount), currency),
            "background": "#f8fafc",
            "color": "#334155",
            "icon": "fa-file-text-o",
        })

        return {
            "type": "sale" if journal_type in ("sale", "out_invoice") else "purchase",
            "title": "Customer Invoices" if journal_type in ("sale", "out_invoice") else "Vendor Bills",
            "icon": "fa-arrow-down" if journal_type in ("sale", "out_invoice") else "fa-arrow-up",
            "accent": "#16a163" if journal_type in ("sale", "out_invoice") else "#2563eb",
            "stats": stats,
            "document_label": "Invoice" if journal_type in ("sale", "out_invoice") else "Bill",
        }

    def _salary_domain(self, date_from, date_to, filters):
        domain = ['|', ("company_id", "=", self.env.company.id), ("company_id", "=", False)]
        if date_from:
            domain.append(("date_to", ">=", fields.Date.to_string(date_from)))
        if date_to:
            domain.append(("date_from", "<=", fields.Date.to_string(date_to)))
        if filters and filters.get("employee_id"):
            try:
                emp_id = int(filters["employee_id"])
                domain.append(("employee_id", "=", emp_id))
            except (ValueError, TypeError):
                pass
        if filters and filters.get("department_id"):
            try:
                dept_id = int(filters["department_id"])
                domain.append(("department_id", "=", dept_id))
            except (ValueError, TypeError):
                pass
        return domain

    def _get_salary_summary(self, date_from, date_to, filters):
        if "hr.payslip" not in self.env:
            return {"type": "salary", "title": "Salaries", "icon": "fa-user-o", "accent": "#6d4aff", "stats": []}

        Payslip = self.env["hr.payslip"]
        PayslipLine = self.env["hr.payslip.line"]
        slips = Payslip.search(self._salary_domain(date_from, date_to, filters))
        currency = self.env.company.currency_id

        net_slips = slips.filtered(lambda slip: slip.state in ("draft", "verify", "done", "paid"))
        net_total = 0.0
        for slip in net_slips:
            net_lines = PayslipLine.search([
                ("zip_id", "=", slip.id) if "zip_id" in PayslipLine._fields else ("slip_id", "=", slip.id),
                ("salary_rule_id.category_id.code", "=", "NET"),
            ])
            if net_lines:
                net_total += sum(net_lines.mapped("total"))
            elif hasattr(slip, 'net_wage') and slip.net_wage:
                net_total += slip.net_wage
            elif hasattr(slip, 'basic_wage') and slip.basic_wage:
                net_total += slip.basic_wage
            elif slip.line_ids:
                net_total += sum(slip.line_ids.mapped("total"))
            elif hasattr(slip, 'contract_id') and slip.contract_id and hasattr(slip.contract_id, 'wage'):
                net_total += slip.contract_id.wage

        stats = [{
            "key": "total_net",
            "label": "Net Salary",
            "count": len(net_slips.mapped("employee_id")),
            "amount": abs(net_total),
            "amount_formatted": self._format_amount(abs(net_total), currency),
            "background": "#edfdf3",
            "color": "#0f9d58",
            "icon": "fa-money",
            "sub_label": "Employees",
        }]

        for key, label, background, color, icon in self.SALARY_STATE_CONFIG:
            state_slips = slips.filtered(lambda slip, target=key: slip.state in ("verify", "done", "waiting", "validated") if target in ("verify", "waiting") else slip.state == target)
            total = 0.0
            for slip in state_slips:
                lines = PayslipLine.search([
                    ("zip_id", "=", slip.id) if "zip_id" in PayslipLine._fields else ("slip_id", "=", slip.id),
                    ("salary_rule_id.category_id.code", "=", "NET"),
                ])
                if lines:
                    total += sum(lines.mapped("total"))
                elif hasattr(slip, 'net_wage') and slip.net_wage:
                    total += slip.net_wage
                elif hasattr(slip, 'basic_wage') and slip.basic_wage:
                    total += slip.basic_wage
                elif slip.line_ids:
                    total += sum(slip.line_ids.mapped("total"))
                elif hasattr(slip, 'contract_id') and slip.contract_id and hasattr(slip.contract_id, 'wage'):
                    total += slip.contract_id.wage

            stats.append({
                "key": key,
                "label": label,
                "count": len(state_slips),
                "amount": abs(total),
                "amount_formatted": self._format_amount(abs(total), currency),
                "background": background,
                "color": color,
                "icon": icon,
                "sub_label": "Payslips",
            })

        SalaryRule = self.env["hr.salary.rule"]
        if "show_on_salary_card" in SalaryRule._fields:
            active_slips = slips.filtered(lambda slip: slip.state != "cancel")
            rules = SalaryRule.search([("show_on_salary_card", "=", True)], order="sequence asc")
            for rule in rules:
                lines = PayslipLine.search([
                    ("zip_id", "in", active_slips.ids) if "zip_id" in PayslipLine._fields else ("slip_id", "in", active_slips.ids),
                    ("salary_rule_id", "=", rule.id),
                ])
                if not lines:
                    continue
                total = sum(lines.mapped("total"))
                stats.append({
                    "key": f"rule_{rule.code}",
                    "label": rule.name,
                    "count": len(lines.mapped("slip_id.employee_id" if "slip_id" in PayslipLine._fields else "zip_id.employee_id")),
                    "amount": abs(total),
                    "amount_formatted": self._format_amount(abs(total), currency),
                    "background": self._lighten_hex_color(rule.card_color) if rule.card_color else "#f0fdf4",
                    "color": "#334155",
                    "icon": "fa-calculator",
                    "sub_label": "Employees",
                })
        return {
            "type": "salary",
            "title": "Salaries",
            "icon": "fa-user-o",
            "accent": "#6d4aff",
            "stats": stats,
            "document_label": "Payslip",
        }

    def _get_indicators(self, sums, base_sums=None):
        revenue = abs(sums["income"])
        cogs = abs(sums["cogs"])
        expenses = abs(sums["expenses"])
        gross_profit = revenue - cogs
        net_profit = gross_profit - expenses
        ebitda = net_profit + abs(sums["depreciation"])

        current_assets = sums["current_assets"]
        current_liabilities = sums["current_liabilities"]
        current_ratio = self._ratio(current_assets, current_liabilities)
        quick_ratio = self._ratio(sums["cash"] + sums["receivables"], current_liabilities)
        working_capital = current_assets - current_liabilities

        debt_to_equity = self._ratio(sums["liabilities"], sums["equity"])
        debt_ratio = self._ratio(sums["liabilities"], sums["assets"])
        equity_ratio = self._ratio(sums["equity"], sums["assets"])
        net_assets = sums["assets"] - sums["liabilities"]

        asset_turnover = self._ratio(revenue, sums["assets"])
        receivables_turnover = self._ratio(revenue, sums["receivables"])
        payables_coverage = self._ratio(cogs + expenses, sums["payables"])
        operating_expense_ratio = self._percent(expenses, revenue)

        roa = self._percent(net_profit, sums["assets"])
        roe = self._percent(net_profit, sums["equity"])
        ror = self._percent(net_profit, revenue)
        gross_return = self._percent(gross_profit, revenue)

        revenue_growth = 0.0
        if base_sums and base_sums.get("income"):
            revenue_growth = self._percent(sums["income"], base_sums["income"], growth=True)

        return {
            "revenue": revenue,
            "cogs": cogs,
            "expenses": expenses,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "ebitda": ebitda,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "cash": sums["cash"],
            "working_capital": working_capital,
            "debt_to_equity": debt_to_equity,
            "debt_ratio": debt_ratio,
            "equity_ratio": equity_ratio,
            "net_assets": net_assets,
            "asset_turnover": asset_turnover,
            "receivables_turnover": receivables_turnover,
            "payables_coverage": payables_coverage,
            "operating_expense_ratio": operating_expense_ratio,
            "cash_received": sums["cash_received"],
            "cash_spent": sums["cash_spent"],
            "cash_surplus": sums["cash_received"] - sums["cash_spent"],
            "roa": roa,
            "roe": roe,
            "ror": ror,
            "gross_return": gross_return,
            "revenue_growth": revenue_growth,
        }

    def _get_financial_metrics(self, category, date_from, date_to):
        current_sums = self._ledger_sums(date_from, date_to)
        previous_from = previous_to = None
        if date_from and date_to:
            span = (date_to - date_from).days + 1
            previous_to = date_from - timedelta(days=1)
            previous_from = previous_to - timedelta(days=span - 1)
        previous_sums = self._ledger_sums(previous_from, previous_to)

        current = self._get_indicators(current_sums, previous_sums)
        previous = self._get_indicators(previous_sums)

        metric_map = {
            "profitability": [
                self._metric("Revenue Growth Rate", current["revenue_growth"], "(Current Period Revenue - Prior Period Revenue) / Prior Period Revenue x 100", current["revenue_growth"], "%"),
                self._metric("Gross Profit Margin", current["gross_return"], "(Revenue - COGS) / Revenue x 100", self._percent(current["gross_return"], previous["gross_return"], growth=True), "%"),
                self._metric("Net Profit Margin", current["ror"], "Net Profit / Revenue x 100", self._percent(current["ror"], previous["ror"], growth=True), "%"),
                self._metric("EBITDA", current["ebitda"], "Net Income + Interest + Taxes + Depreciation + Amortization", self._percent(current["ebitda"], previous["ebitda"], growth=True), "money"),
            ],
            "liquidity": [
                self._metric("Current Ratio", current["current_ratio"], "Current Assets / Current Liabilities", self._percent(current["current_ratio"], previous["current_ratio"], growth=True), "number"),
                self._metric("Quick Ratio", current["quick_ratio"], "(Cash + Receivables) / Current Liabilities", self._percent(current["quick_ratio"], previous["quick_ratio"], growth=True), "number"),
                self._metric("Cash Balance", current["cash"], "Posted cash and bank account balance", self._percent(current["cash"], previous["cash"], growth=True), "money"),
                self._metric("Working Capital", current["working_capital"], "Current Assets - Current Liabilities", self._percent(current["working_capital"], previous["working_capital"], growth=True), "money"),
            ],
            "solvency": [
                self._metric("Debt to Equity", current["debt_to_equity"], "Total Liabilities / Equity", self._percent(current["debt_to_equity"], previous["debt_to_equity"], growth=True), "number"),
                self._metric("Debt Ratio", current["debt_ratio"], "Total Liabilities / Total Assets", self._percent(current["debt_ratio"], previous["debt_ratio"], growth=True), "number"),
                self._metric("Equity Ratio", current["equity_ratio"], "Equity / Total Assets", self._percent(current["equity_ratio"], previous["equity_ratio"], growth=True), "number"),
                self._metric("Net Assets", current["net_assets"], "Assets - Liabilities", self._percent(current["net_assets"], previous["net_assets"], growth=True), "money"),
            ],
            "efficiency": [
                self._metric("Asset Turnover", current["asset_turnover"], "Revenue / Total Assets", self._percent(current["asset_turnover"], previous["asset_turnover"], growth=True), "number"),
                self._metric("Receivables Turnover", current["receivables_turnover"], "Revenue / Receivables", self._percent(current["receivables_turnover"], previous["receivables_turnover"], growth=True), "number"),
                self._metric("Payables Coverage", current["payables_coverage"], "(COGS + Expenses) / Payables", self._percent(current["payables_coverage"], previous["payables_coverage"], growth=True), "number"),
                self._metric("Operating Expense Ratio", current["operating_expense_ratio"], "Expenses / Revenue x 100", self._percent(current["operating_expense_ratio"], previous["operating_expense_ratio"], growth=True), "%"),
            ],
            "valuation": [
                self._metric("Revenue", current["revenue"], "Income posted for the selected period", self._percent(current["revenue"], previous["revenue"], growth=True), "money"),
                self._metric("Gross Profit", current["gross_profit"], "Revenue - Cost of Goods Sold", self._percent(current["gross_profit"], previous["gross_profit"], growth=True), "money"),
                self._metric("Net Assets", current["net_assets"], "Assets - Liabilities", self._percent(current["net_assets"], previous["net_assets"], growth=True), "money"),
                self._metric("Cash Position", current["cash"], "Cash and bank balances", self._percent(current["cash"], previous["cash"], growth=True), "money"),
            ],
            "cash_flow": [
                self._metric("Cash Received", current["cash_received"], "Debit movement on bank and cash accounts", self._percent(current["cash_received"], previous["cash_received"], growth=True), "money"),
                self._metric("Cash Spent", current["cash_spent"], "Credit movement on bank and cash accounts", self._percent(current["cash_spent"], previous["cash_spent"], growth=True), "money"),
                self._metric("Cash Surplus", current["cash_surplus"], "Cash Received - Cash Spent", self._percent(current["cash_surplus"], previous["cash_surplus"], growth=True), "money"),
                self._metric("Closing Bank Balance", current["cash"], "Posted cash and bank balance", self._percent(current["cash"], previous["cash"], growth=True), "money"),
            ],
            "returns": [
                self._metric("Return on Assets", current["roa"], "Net Profit / Total Assets x 100", self._percent(current["roa"], previous["roa"], growth=True), "%"),
                self._metric("Return on Equity", current["roe"], "Net Profit / Equity x 100", self._percent(current["roe"], previous["roe"], growth=True), "%"),
                self._metric("Return on Revenue", current["ror"], "Net Profit / Revenue x 100", self._percent(current["ror"], previous["ror"], growth=True), "%"),
                self._metric("Gross Return", current["gross_return"], "Gross Profit / Revenue x 100", self._percent(current["gross_return"], previous["gross_return"], growth=True), "%"),
            ],
        }
        return metric_map[category]

    def _ledger_sums(self, date_from, date_to):
        domain = [("move_id.state", "=", "posted"), ("company_id", "=", self.env.company.id)]
        if date_from:
            domain.append(("date", ">=", fields.Date.to_string(date_from)))
        if date_to:
            domain.append(("date", "<=", fields.Date.to_string(date_to)))

        grouped = self.env["account.move.line"].read_group(
            domain,
            ["balance:sum", "debit:sum", "credit:sum"],
            ["account_id"],
            lazy=False,
        )
        values = {
            "income": 0.0,
            "cogs": 0.0,
            "expenses": 0.0,
            "depreciation": 0.0,
            "assets": 0.0,
            "liabilities": 0.0,
            "equity": 0.0,
            "current_assets": 0.0,
            "current_liabilities": 0.0,
            "receivables": 0.0,
            "payables": 0.0,
            "cash": 0.0,
            "cash_received": 0.0,
            "cash_spent": 0.0,
        }
        for row in grouped:
            account_id = row.get("account_id") and row["account_id"][0]
            account_type = self.env["account.account"].browse(account_id).account_type if account_id else False
            balance = row.get("balance", 0.0)
            debit = row.get("debit", 0.0)
            credit = row.get("credit", 0.0)
            if account_type in ("income", "income_other"):
                values["income"] += balance
            elif account_type == "expense_direct_cost":
                values["cogs"] += balance
            elif account_type == "expense_depreciation":
                values["expenses"] += balance
                values["depreciation"] += balance
            elif account_type == "expense":
                values["expenses"] += balance

            if account_type and account_type.startswith("asset"):
                values["assets"] += balance
            if account_type and account_type.startswith("liability"):
                values["liabilities"] += abs(balance)
            if account_type and account_type.startswith("equity"):
                values["equity"] += abs(balance)
            if account_type in ("asset_current", "asset_receivable", "asset_cash"):
                values["current_assets"] += balance
            if account_type in ("liability_current", "liability_payable"):
                values["current_liabilities"] += abs(balance)
            if account_type == "asset_receivable":
                values["receivables"] += balance
            if account_type == "liability_payable":
                values["payables"] += abs(balance)
            if account_type == "asset_cash":
                values["cash"] += balance
                values["cash_received"] += debit
                values["cash_spent"] += credit
        return values

    def _metric(self, label, value, formula, delta, value_type):
        currency = self.env.company.currency_id
        formatted = self._format_amount(value, currency) if value_type == "money" else self._format_number(value, value_type)
        return {
            "label": label,
            "value": value,
            "formatted": formatted,
            "formula": formula,
            "delta": delta,
            "delta_formatted": self._format_number(abs(delta), "%") if isinstance(delta, (int, float)) else "",
            "trend": "down" if delta < 0 else "up",
            "value_type": value_type,
        }

    def _percent(self, numerator, denominator, growth=False):
        if not denominator:
            return 0.0
        if growth:
            return ((numerator - denominator) / abs(denominator)) * 100
        return (numerator / abs(denominator)) * 100

    def _ratio(self, numerator, denominator):
        if not denominator:
            return 0.0
        return numerator / abs(denominator)

    def _format_number(self, value, value_type):
        if value_type == "%":
            return f"{value:.2f}%"
        return f"{value:.2f}"

    def _format_amount(self, amount, currency):
        symbol = currency.symbol or ""
        sign = "-" if amount < 0 else ""
        amount = abs(amount)
        if amount >= 1_000_000:
            value = f"{amount / 1_000_000:.2f}M"
        elif amount >= 1_000:
            value = f"{amount / 1_000:.1f}K"
        else:
            value = f"{amount:,.2f}"
        return f"{sign}{symbol}{value}"

    def _lighten_hex_color(self, color):
        if not color or not isinstance(color, str):
            return "#f0fdf4"
        color = color.strip().lstrip("#")
        if len(color) != 6:
            return "#f0fdf4"
        try:
            red = int(color[0:2], 16)
            green = int(color[2:4], 16)
            blue = int(color[4:6], 16)
        except ValueError:
            return "#f0fdf4"
        red = round(red + (255 - red) * 0.68)
        green = round(green + (255 - green) * 0.68)
        blue = round(blue + (255 - blue) * 0.68)
        return f"#{red:02x}{green:02x}{blue:02x}"
