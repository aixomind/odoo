/** @odoo-module **/
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function checkIsDarkMode() {
    try {
        const matchCookie = document.cookie.split("; ").find(r => r.startsWith("color_scheme="));
        const cookieScheme = matchCookie ? decodeURIComponent(matchCookie.split("=")[1]) : "";
        if (cookieScheme === "dark") return true;
        if (cookieScheme === "light") return false;
        if (document.documentElement.getAttribute("data-color-scheme") === "dark") return true;
        if (document.documentElement.getAttribute("data-bs-theme") === "dark") return true;
        if (document.body.classList.contains("o_dark_user")) return true;
        return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    } catch (e) {
        return false;
    }
}

function saveFilters(filters) {
    const jsonStr = JSON.stringify(filters || {});
    try { sessionStorage.setItem("l4e_dashboard_collection_filters", jsonStr); } catch (e) {}
    try {
        const expires = new Date(Date.now() + 7 * 864e5).toUTCString();
        document.cookie = "l4e_dashboard_collection_filters=" + encodeURIComponent(jsonStr) + "; expires=" + expires + "; path=/;";
    } catch (e) {}
}

function clearSavedFilters() {
    try { sessionStorage.removeItem("l4e_dashboard_collection_filters"); } catch (e) {}
    try { document.cookie = "l4e_dashboard_collection_filters=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"; } catch (e) {}
}

function loadSavedFilters() {
    let raw = "";
    const currentYear = String(new Date().getFullYear());
    const currentMonthNum = String(new Date().getMonth() + 1);
    try { raw = sessionStorage.getItem("l4e_dashboard_collection_filters") || ""; } catch (e) {}
    if (!raw) {
        try {
            const match = document.cookie.split("; ").find(r => r.startsWith("l4e_dashboard_collection_filters="));
            if (match) raw = decodeURIComponent(match.split("=")[1]);
        } catch (e) {}
    }
    if (raw) {
        try {
            const f = JSON.parse(raw);
            if (!f.year_filter) {
                f.year_filter = currentYear;
            }
            if (!f.month_filter) {
                f.month_filter = currentMonthNum;
            }
            if (f.date_from && !/^\d{4}-\d{2}-\d{2}$/.test(f.date_from)) delete f.date_from;
            if (f.date_to && !/^\d{4}-\d{2}-\d{2}$/.test(f.date_to)) delete f.date_to;
            return f;
        } catch (e) {}
    }
    return { year_filter: currentYear };
}

class SalesOfficeDashboard extends Component {
    static template = "l4e_dashboard_collection.crm_dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const currentMonthNum = String(new Date().getMonth() + 1);
        this.state = useState({
            filters: loadSavedFilters(),
            card_filters: {
                sales_trend: currentMonthNum,
                pipeline: currentMonthNum,
                team_perf: currentMonthNum,
                recent_won: currentMonthNum,
                top_sp: currentMonthNum,
                top_cust: currentMonthNum,
                activities: currentMonthNum,
                kpi_total: currentMonthNum,
                kpi_won: currentMonthNum,
                kpi_lost: currentMonthNum,
                kpi_quotes: currentMonthNum,
                kpi_overdue: currentMonthNum,
                kpi_today: currentMonthNum,
            },
            dropdowns: { year: false, team: false, user: false, kpi_month: false },
            data: { kpis: {}, offices: [], teams: [], users: [], performance: [], pipeline: [], lost_reasons: [], people: [] }
        });
        onWillStart(() => this.load());
        onMounted(() => {
            this.updateThemeAttribute();
            if (window.matchMedia) {
                const mq = window.matchMedia("(prefers-color-scheme: dark)");
                const listener = () => this.updateThemeAttribute();
                if (mq.addEventListener) {
                    mq.addEventListener("change", listener);
                } else if (mq.addListener) {
                    mq.addListener(listener);
                }
            }
        });
    }

    updateThemeAttribute() {
        const isDark = checkIsDarkMode();
        const container = document.querySelector(".l4e-dashboard-container");
        if (container) {
            container.setAttribute("data-theme", isDark ? "dark" : "light");
        }
    }

    async load() {
        this.state.data = await this.orm.call("crm.dashboard", "get_dashboard_data", [], {
            filters: {
                ...this.state.filters,
                card_filters: this.state.card_filters,
            }
        });
    }

    resetFilters() {
        const currentYear = String(new Date().getFullYear());
        const currentMonthNum = String(new Date().getMonth() + 1);
        this.state.filters = { year_filter: currentYear };
        this.state.card_filters = {
            sales_trend: currentMonthNum,
            pipeline: currentMonthNum,
            team_perf: currentMonthNum,
            recent_won: currentMonthNum,
            top_sp: currentMonthNum,
            top_cust: currentMonthNum,
            activities: currentMonthNum,
            kpi_total: currentMonthNum,
            kpi_won: currentMonthNum,
            kpi_lost: currentMonthNum,
            kpi_quotes: currentMonthNum,
            kpi_overdue: currentMonthNum,
            kpi_today: currentMonthNum,
        };
        this.state.dropdowns = { year: false, team: false, user: false, kpi_month: false };
        clearSavedFilters();
        this.load();
    }

    toggleDropdown(name) {
        for (const k in this.state.dropdowns) {
            if (k === name) {
                this.state.dropdowns[k] = !this.state.dropdowns[k];
            } else {
                this.state.dropdowns[k] = false;
            }
        }
    }

    closeDropdown(name) {
        this.state.dropdowns[name] = false;
    }

    selectFilter(name, val) {
        if (val) {
            this.state.filters[name] = val;
        } else {
            delete this.state.filters[name];
        }
        if (name === "team_id") {
            delete this.state.filters.user_id;
        }
        this.state.dropdowns.year = false;
        this.state.dropdowns.team = false;
        this.state.dropdowns.user = false;
        saveFilters(this.state.filters);
        this.load();
    }

    setKpiMonthAll(month) {
        this.state.card_filters.kpi_total = month;
        this.state.card_filters.kpi_won = month;
        this.state.card_filters.kpi_lost = month;
        this.state.card_filters.kpi_quotes = month;
        this.state.card_filters.kpi_overdue = month;
        this.state.card_filters.kpi_today = month;
        this.load();
    }

    setKpiMonth(kpiKey, e) {
        const v = e.target.value;
        if (v) {
            this.state.card_filters[kpiKey] = v;
        } else {
            delete this.state.card_filters[kpiKey];
        }
        this.load();
    }

    get kpiMonthLabel() {
        const months = {
            "1": "January", "2": "February", "3": "March", "4": "April",
            "5": "May", "6": "June", "7": "July", "8": "August",
            "9": "September", "10": "October", "11": "November", "12": "December"
        };
        return months[this.state.card_filters.kpi_total] || "Select Month";
    }

    get monthLabel() {
        const months = {
            "1": "January", "2": "February", "3": "March", "4": "April",
            "5": "May", "6": "June", "7": "July", "8": "August",
            "9": "September", "10": "October", "11": "November", "12": "December",
            "all": "All Year"
        };
        return months[this.state.filters.month_filter] || "Select Month";
    }

    setFilter(e) {
        const v = e.target.value;
        if (v) {
            this.state.filters[e.target.name] = v;
        } else {
            delete this.state.filters[e.target.name];
        }
        if (e.target.name === "year_filter") {
            this.state.card_filters = {};
        }
        if (e.target.name === "team_id") {
            delete this.state.filters.user_id;
        }
        saveFilters(this.state.filters);
        this.load();
    }

    setCardFilter(cardKey, e) {
        const v = e.target.value;
        if (v) {
            this.state.card_filters[cardKey] = v;
        } else {
            delete this.state.card_filters[cardKey];
        }
        this.load();
    }

    openActivityRecord(act) {
        if (act.res_model && act.res_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: act.res_model,
                res_id: act.res_id,
                views: [[false, "form"]],
                target: "current"
            });
        }
    }

    open(model, domain, name, context = {}) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain,
            context,
            target: "current"
        });
    }

    kpiDomain(model) {
        const d = [];
        if (model === "sale.order") {
            d.push(["opportunity_id", "!=", false]);
        }
        for (const [key, field] of [["team_id", "team_id"], ["user_id", "user_id"]]) {
            if (this.state.filters[key]) d.push([field, "=", Number(this.state.filters[key])]);
        }
        if (this.state.filters.date_from) d.push([model === "sale.order" ? "date_order" : "create_date", ">=", this.state.filters.date_from]);
        if (this.state.filters.date_to) d.push([model === "sale.order" ? "date_order" : "create_date", "<=", this.state.filters.date_to]);
        return d;
    }

    openKpi(kind) {
        let model = "crm.lead", title = "Total Leads", domain = this.kpiDomain(model), context = { group_by: ["user_id", "company_id"] };
        const todayStr = new Date().toISOString().split('T')[0];

        if (kind === "total") {
            title = "All Leads";
            context = { active_test: false, group_by: ["user_id", "company_id"] };
        } else if (kind === "quotes") {
            model = "sale.order";
            title = "Active Quotations";
            domain = this.kpiDomain(model).concat([["state", "in", ["draft", "sent"]]]);
            context = { group_by: ["user_id", "company_id"] };
        } else if (kind === "won") {
            model = "crm.lead";
            title = "Won Opportunities";
            domain = this.kpiDomain(model).concat([["active", "=", true], "|", ["probability", "=", 100], ["stage_id.is_won", "=", true]]);
            context = { group_by: ["user_id", "company_id"] };
        } else if (kind === "lost") {
            title = "Lost Opportunities";
            domain = domain.concat(["|", ["active", "=", false], ["stage_id.name", "ilike", "lost"]]);
            context = { active_test: false, search_default_inactive: 1, group_by: ["user_id", "company_id"] };
        } else if (kind === "overdue") {
            model = "mail.activity";
            title = "Overdue CRM Activities";
            domain = [["res_model", "=", "crm.lead"], ["date_deadline", "<", todayStr]];
            if (this.state.filters.user_id) {
                domain.push(["user_id", "=", Number(this.state.filters.user_id)]);
            }
            context = {};
        } else if (kind === "today") {
            model = "mail.activity";
            title = "CRM Activities Due Today";
            domain = [["res_model", "=", "crm.lead"], ["date_deadline", "=", todayStr]];
            if (this.state.filters.user_id) {
                domain.push(["user_id", "=", Number(this.state.filters.user_id)]);
            }
            context = {};
        }
        this.open(model, domain, title, context);
    }

    openPipelineStage(row) {
        let model = "crm.lead";
        let domain = this.kpiDomain(model);
        let context = {};

        if (row.is_lost) {
            domain = domain.concat(["|", ["active", "=", false], ["stage_id.name", "ilike", "lost"]]);
            context = { active_test: false, search_default_inactive: 1 };
        } else if (row.is_won) {
            domain = domain.concat([["active", "=", true], "|", ["probability", "=", 100], ["stage_id.is_won", "=", true]]);
        } else {
            domain.push(["stage_id", "=", row.id], ["active", "=", true]);
        }

        this.open(model, domain, `${row.name} Opportunities`, context);
    }

    openSalesPersonDetail(user) {
        if (user.id) {
            const domain = [
                ["opportunity_id", "!=", false],
                ["state", "in", ["sale", "done"]],
                ["user_id", "=", user.id]
            ];
            if (this.state.filters.date_from) {
                domain.push(["date_order", ">=", this.state.filters.date_from]);
            }
            if (this.state.filters.date_to) {
                domain.push(["date_order", "<=", this.state.filters.date_to]);
            }
            this.open("sale.order", domain, `Won Orders: ${user.name}`);
        }
    }

    openSalesTrendPoint(pt) {
        if (pt.date_from && pt.date_to) {
            const domain = [
                ["opportunity_id", "!=", false],
                ["state", "in", ["sale", "done"]],
                ["date_order", ">=", pt.date_from],
                ["date_order", "<=", pt.date_to + " 23:59:59"]
            ];
            for (const [key, field] of [["team_id", "team_id"], ["user_id", "user_id"]]) {
                if (this.state.filters[key]) {
                    domain.push([field, "=", Number(this.state.filters[key])]);
                }
            }
            this.open("sale.order", domain, `Sales Orders (${pt.label})`);
        }
    }
}



registry.category("actions").add("l4e_dashboard_collection.crm_dashboard", SalesOfficeDashboard);
