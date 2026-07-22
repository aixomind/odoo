
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class FinancialDashboard extends Component {
    static template = "l4e_dashboard_collection.FinancialDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.periods = [
            { key: "today", label: "Today" },
            { key: "this_week", label: "This Week" },
            { key: "this_month", label: "This Month" },
            { key: "this_quarter", label: "This Quarter" },
            { key: "this_year", label: "This Year" },
            { key: "all", label: "All" },
        ];

        const savedState = sessionStorage.getItem("financial_dashboard_state");
        let initialState = {
            loading: true,
            period: "all",
            metricPeriod: "this_year",
            category: "profitability",
            data: { cards: [], categories: [], metrics: [] },
            options: { years: [], customers: [], vendors: [], users: [], employees: [], departments: [] },
            metricFilters: {
                date_from: "",
                date_to: "",
            },
            filters: {
                sale: {
                    customer_id: "",
                    user_id: "",
                    date_from: "",
                    date_to: "",
                },
                salary: {
                    employee_id: "",
                    department_id: "",
                    date_from: "",
                    date_to: "",
                },
                purchase: {
                    vendor_id: "",
                    user_id: "",
                    date_from: "",
                    date_to: "",
                },
            },
        };

        if (savedState) {
            try {
                const parsed = JSON.parse(savedState);
                initialState.period = parsed.period ?? "all";
                initialState.metricPeriod = parsed.metricPeriod ?? "this_year";
                initialState.category = parsed.category ?? "profitability";
                initialState.metricFilters = parsed.metricFilters ?? initialState.metricFilters;
                initialState.filters = parsed.filters ?? initialState.filters;
            } catch (e) {
                console.error("Failed to parse saved financial dashboard state", e);
            }
        }

        this.state = useState(initialState);

        onWillStart(async () => {
            await Promise.all([this.loadOptions(), this.loadDashboard()]);
        });
    }

    async loadOptions() {
        this.state.options = await this.orm.call("financial.dashboard", "get_filter_options", []);
    }

    async loadDashboard() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "financial.dashboard",
                "get_dashboard_data",
                [],
                {
                    period: this.state.period,
                    category: this.state.category,
                    filters: this.rpcFilters,
                }
            );
        } catch (error) {
            console.error("Financial dashboard error:", error);
            this.notification.add("Failed to load Financial Dashboard", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async loadCard(cardType) {
        try {
            const cardData = await this.orm.call(
                "financial.dashboard",
                "get_card_data",
                [],
                {
                    card_type: cardType,
                    period: this.state.period,
                    filters: this.rpcFilters,
                }
            );
            if (cardData) {
                const index = this.state.data.cards.findIndex(c => c.type === cardType);
                if (index !== -1) {
                    this.state.data.cards[index] = cardData;
                }
            }
        } catch (error) {
            console.error(`Failed to load card ${cardType}:`, error);
            this.notification.add("Failed to load card data", { type: "danger" });
        }
    }

    async loadMetricCards() {
        try {
            const result = await this.orm.call(
                "financial.dashboard",
                "get_dashboard_data",
                [],
                {
                    period: this.state.period,
                    metric_period: this.state.metricPeriod,
                    category: this.state.category,
                    metric_date_from: this.state.metricFilters.date_from,
                    metric_date_to:this.state.metricFilters.date_to,
                    filters: this.rpcFilters,
                }
            );
            this.state.data.metrics = result.metrics;
        } catch (error) {
            console.error("Metric error:", error);
            this.notification.add("Failed to load metrics", { type: "danger" });
        }
    }

    async updateMetricDate(key, ev) {
        this.state.metricFilters[key] = ev.target.value;
        const filters = this.state.metricFilters;
        if (
            (filters.date_from && filters.date_to) ||
            (!filters.date_from && !filters.date_to)
        ) {
            this.saveState();
            await this.loadMetricCards();
        }
    }

    get rpcFilters() {
        const filters = { cards: {} };
        for (const [cardType, cardFilters] of Object.entries(this.state.filters)) {
            filters.cards[cardType] = this.rpcFiltersFor(cardType);
        }
        return filters;
    }

    rpcFiltersFor(cardType) {
        const filters = {};
        for (const [key, value] of Object.entries(this.cardFilters(cardType))) {
            filters[key] = value || false;
        }
        return filters;
    }

    get selectedCategory() {
        return (this.state.data.categories || []).find((category) => category.key === this.state.category) || {};
    }

    get periodLabel() {
        const found = this.periods.find((period) => period.key === this.state.period);
        return found ? found.label : String(this.state.period || "All");
    }

    cardFilters(cardType) {
        return this.state.filters[cardType] || {};
    }

    getSelectValue(cardType, key) {
        return this.cardFilters(cardType)[key] || "";
    }

    isSelected(cardType, key, value) {
        return String(this.cardFilters(cardType)[key] || "") === String(value || "");
    }

    isPeriodSelected(periodKey) {
        return String(this.state.period) === String(periodKey);
    }

    async onPeriodChange(ev) {
        this.state.metricPeriod = ev.target.value;
        this.saveState();
        await this.loadMetricCards();
    }

    async onDashboardPeriodChange(ev) {
        this.state.period = ev.target.value;
        this.saveState();
        await Promise.all([
            this.loadCard("sale"),
            this.loadCard("salary"),
            this.loadCard("purchase")
        ]);
    }

    async onCategoryChange(ev) {
        this.state.category = ev.target.value;
        this.saveState();
        await this.loadMetricCards();
    }

    async selectCategory(key) {
        this.state.category = key;
        this.saveState();
        await this.loadMetricCards();
    }

    async updateFilter(cardType, key, ev) {
        this.state.filters[cardType][key] = ev.target.value;
        this.saveState();
        await this.loadCard(cardType);
    }

    async updateDateFilter(cardType, key, ev) {
        const cardFilters = this.state.filters[cardType];
        cardFilters[key] = ev.target.value;
        if (
            (cardFilters.date_from && cardFilters.date_to) ||
            (!cardFilters.date_from && !cardFilters.date_to)
        ) {
            this.saveState();
            await this.loadCard(cardType);
        }
    }

    async clearDates(cardType) {
        this.state.filters[cardType].date_from = "";
        this.state.filters[cardType].date_to = "";
        this.saveState();
        await this.loadCard(cardType);
    }

    async openInvoiceCard(cardType, statKey) {
        const action = await this.orm.call(
            "financial.dashboard",
            "action_open_invoice_records",
            [],
            {
                journal_type: cardType,
                status_key: statKey,
                period: this.state.period,
                filters: this.rpcFiltersFor(cardType),
            }
        );
        await this.action.doAction(action);
    }

    async openSalaryCard(statKey) {
        const action = await this.orm.call(
            "financial.dashboard",
            "action_open_salary_records",
            [],
            {
                status_key: statKey,
                period: this.state.period,
                filters: this.rpcFiltersFor("salary"),
            }
        );
        await this.action.doAction(action);
    }

    async openCard(card, stat) {
        if (card.type === "salary") {
            await this.openSalaryCard(stat.key);
        } else {
            await this.openInvoiceCard(card.type, stat.key);
        }
    }

    documentLabel(card, count) {
        if (card.type === "salary") {
            return count === 1 ? (card.stats.find((stat) => stat.key === "total_net") ? "Employee" : "Payslip") : "Payslips";
        }
        return count === 1 ? card.document_label : `${card.document_label}s`;
    }

    saveState() {
        sessionStorage.setItem("financial_dashboard_state", JSON.stringify({
            period: this.state.period,
            metricPeriod: this.state.metricPeriod,
            category: this.state.category,
            metricFilters: this.state.metricFilters,
            filters: this.state.filters,
        }));
    }

    async resetAllFilters() {
        sessionStorage.removeItem("financial_dashboard_state");

        this.state.period = "all";
        this.state.metricPeriod = "this_year";
        this.state.category = "profitability";

        this.state.metricFilters = {
            date_from: "",
            date_to: "",
        };

        this.state.filters = {
            sale: {
                customer_id: "",
                user_id: "",
                date_from: "",
                date_to: "",
            },
            salary: {
                employee_id: "",
                department_id: "",
                date_from: "",
                date_to: "",
            },
            purchase: {
                vendor_id: "",
                user_id: "",
                date_from: "",
                date_to: "",
            },
        };

        await this.loadDashboard();
    }
}

registry.category("actions").add("l4e_dashboard_collection.financial_dashboard", FinancialDashboard);
export { FinancialDashboard };

