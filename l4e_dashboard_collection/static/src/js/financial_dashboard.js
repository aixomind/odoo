/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState , xml } from "@odoo/owl";

export class FinancialDashboard extends Component {
    static template = xml`
<div class="o_financial_dashboard h-100 overflow-auto">
            <div class="o_fd_header">
                <div>
                    <h1>Dashboard</h1>
                    <p>Overview of key financial metrics and performance indicators</p>
                </div>
                 <div class="o_fd_toolbar">
                    <label>
                        <span>Card Period Filter</span>
                        <select t-att-value="state.period" t-on-change="onDashboardPeriodChange">
                            <t t-foreach="state.options.years" t-as="year" t-key="year">
                                <option t-att-value="year" t-att-selected="isPeriodSelected(year)">
                                    <t t-out="year"/>
                                </option>
                            </t>
                            <option value="all" t-att-selected="isPeriodSelected('all')">All</option>
                        </select>
                    </label>
                    <button class="o_fd_reset_btn" t-on-click="resetAllFilters">
                        <i class="fa fa-refresh"/> Reset
                    </button>
                </div>
            </div>

            <t t-if="state.loading">
                <div class="o_fd_loading">Loading...</div>
            </t>
            <t t-else="">
                <div class="o_fd_cards">
                    <t t-foreach="state.data.cards" t-as="card" t-key="card.type">
                        <section class="o_fd_summary" t-att-class="{ 'o_fd_summary_salary': card.type === 'salary' }">
                            <div class="o_fd_summary_title" t-att-style="'--accent:' + card.accent">
                                <i t-attf-class="fa {{ card.icon }}"/>
                                <h2 t-out="card.title"/>
                            </div>

                            <div class="o_fd_filter_grid">
                                <t t-if="card.type === 'sale'">
                                    <select t-att-value="getSelectValue(card.type, 'customer_id')" t-on-change="(ev) => this.updateFilter(card.type, 'customer_id', ev)">
                                        <option value="" t-att-selected="isSelected(card.type, 'customer_id', '')">All Customers</option>
                                        <t t-foreach="state.options.customers" t-as="customer" t-key="customer.id">
                                            <option t-att-value="customer.id" t-att-selected="isSelected(card.type, 'customer_id', customer.id)">
                                                <t t-out="customer.name"/>
                                            </option>
                                        </t>
                                    </select>
                                    <select t-att-value="getSelectValue(card.type, 'user_id')" t-on-change="(ev) => this.updateFilter(card.type, 'user_id', ev)">
                                        <option value="" t-att-selected="isSelected(card.type, 'user_id', '')">All Users</option>
                                        <t t-foreach="state.options.users" t-as="user" t-key="user.id">
                                            <option t-att-value="user.id" t-att-selected="isSelected(card.type, 'user_id', user.id)">
                                                <t t-out="user.name"/>
                                            </option>
                                        </t>
                                    </select>
                                </t>
                                <t t-elif="card.type === 'purchase'">
                                    <select t-att-value="getSelectValue(card.type, 'vendor_id')" t-on-change="(ev) => this.updateFilter(card.type, 'vendor_id', ev)">
                                        <option value="" t-att-selected="isSelected(card.type, 'vendor_id', '')">All Vendors</option>
                                        <t t-foreach="state.options.vendors" t-as="vendor" t-key="vendor.id">
                                            <option t-att-value="vendor.id" t-att-selected="isSelected(card.type, 'vendor_id', vendor.id)">
                                                <t t-out="vendor.name"/>
                                            </option>
                                        </t>
                                    </select>
                                    <select t-att-value="getSelectValue(card.type, 'user_id')" t-on-change="(ev) => this.updateFilter(card.type, 'user_id', ev)">
                                        <option value="" t-att-selected="isSelected(card.type, 'user_id', '')">All Users</option>
                                        <t t-foreach="state.options.users" t-as="user" t-key="user.id">
                                            <option t-att-value="user.id" t-att-selected="isSelected(card.type, 'user_id', user.id)">
                                                <t t-out="user.name"/>
                                            </option>
                                        </t>
                                    </select>
                                </t>
                                <t t-else="">
                                    <select t-att-value="getSelectValue(card.type, 'department_id')" t-on-change="(ev) => this.updateFilter(card.type, 'department_id', ev)">
                                        <option value="" t-att-selected="isSelected(card.type, 'department_id', '')">All Departments</option>
                                        <t t-foreach="state.options.departments" t-as="department" t-key="department.id">
                                            <option t-att-value="department.id" t-att-selected="isSelected(card.type, 'department_id', department.id)">
                                                <t t-out="department.name"/>
                                            </option>
                                        </t>
                                    </select>
                                    <select t-att-value="getSelectValue(card.type, 'employee_id')" t-on-change="(ev) => this.updateFilter(card.type, 'employee_id', ev)">
                                        <option value="" t-att-selected="isSelected(card.type, 'employee_id', '')">All Employees</option>
                                        <t t-foreach="state.options.employees" t-as="employee" t-key="employee.id">
                                            <option t-att-value="employee.id" t-att-selected="isSelected(card.type, 'employee_id', employee.id)">
                                                <t t-out="employee.name"/>
                                            </option>
                                        </t>
                                    </select>
                                </t>
                                <input type="date" t-att-value="getSelectValue(card.type, 'date_from')" t-on-change="(ev) => this.updateDateFilter(card.type, 'date_from', ev)"/>
                                <input type="date" t-att-value="getSelectValue(card.type, 'date_to')" t-on-change="(ev) => this.updateDateFilter(card.type, 'date_to', ev)"/>
                            </div>

                            <div class="o_fd_stat_grid">
                                <t t-foreach="card.stats" t-as="stat" t-key="stat.key">
                                    <button class="o_fd_stat_card"
                                            t-att-style="'--stat-bg:' + stat.background + '; --stat-color:' + stat.color"
                                            t-on-click="() => this.openCard(card, stat)">
                                        <div class="o_fd_stat_label">
                                            <i t-attf-class="fa {{ stat.icon }}"/>
                                            <span t-out="stat.label"/>
                                        </div>
                                        <strong>
                                            <t t-if="stat.key === 'total_net' or card.type === 'salary'">
                                                <t t-out="stat.amount_formatted"/>
                                            </t>
                                            <t t-else="">
                                                <t t-out="stat.count"/>
                                            </t>
                                        </strong>
                                        <small>
                                            <t t-if="card.type === 'salary'">
                                                <t t-out="stat.count"/> <t t-out="stat.sub_label"/>
                                            </t>
                                            <t t-else="">
                                                <t t-out="stat.amount_formatted"/>
                                            </t>
                                        </small>
                                    </button>
                                </t>
                            </div>
                        </section>
                    </t>
                </div>

                <div class="o_fd_bottom">
                    <aside class="o_fd_category_panel">
                        <h2>Financial Category</h2>
                        <t t-foreach="state.data.categories" t-as="category" t-key="category.key">
                            <button class="o_fd_category_item"
                                    t-att-class="{ 'active': state.category === category.key }"
                                    t-att-style="'--category-color:' + category.color"
                                    t-on-click="() => this.selectCategory(category.key)">
                                <i t-attf-class="fa {{ category.icon }}"/>
                                <span t-out="category.label"/>
                                <i class="fa fa-chevron-right"/>
                            </button>
                        </t>
                    </aside>

                    <section class="o_fd_metric_panel">
                        <div class="o_fd_metric_header" t-att-style="'--category-color:' + selectedCategory.color">
                            <div>
                                <i t-attf-class="fa {{ selectedCategory.icon }}"/>
                                <h2>Showing: <t t-out="selectedCategory.label"/><t t-if="!selectedCategory.label.includes('Metrics')"> Metrics</t></h2>
                            </div>
                            <p t-out="selectedCategory.description"/>
                            <div class="o_fd_toolbar">
                                <label>
                                    <span>Metric Period Filter</span>
                                    <select t-att-value="state.metricPeriod" t-on-change="onPeriodChange">
                                        <t t-foreach="periods" t-as="period" t-key="period.key">
                                            <option t-att-value="period.key" t-att-selected="period.key === state.metricPeriod">
                                                <t t-out="period.label"/>
                                            </option>
                                        </t>
                                    </select>
                                </label>
                            </div>
                            <div class="o_fd_metric_dates">
                                <input type="date"
                                    t-att-value="state.metricFilters.date_from"
                                    t-on-change="(ev) => this.updateMetricDate('date_from', ev)"/>

                                <input type="date"
                                    t-att-value="state.metricFilters.date_to"
                                    t-on-change="(ev) => this.updateMetricDate('date_to', ev)"/>
                            </div>
                        </div>
                        <div class="o_fd_metric_grid">
                            <t t-foreach="state.data.metrics" t-as="metric" t-key="metric.label">
                                <article class="o_fd_metric_card">
                                    <div class="o_fd_metric_title">
                                        <h3 t-out="metric.label"/>
                                        <i class="fa fa-info-circle"/>
                                    </div>
                                    <strong t-out="metric.formatted"/>
                                    <p t-out="metric.formula"/>
                                    <div class="o_fd_metric_delta">
                                        <span>vs Previous Period</span>
                                        <em t-att-class="metric.trend">
                                            <i t-attf-class="fa {{ metric.trend === 'down' ? 'fa-arrow-down' : 'fa-arrow-up' }}"/>
                                            <t t-out="metric.delta_formatted"/>
                                        </em>
                                    </div>
                                </article>
                            </t>
                        </div>
                    </section>
                </div>
            </t>
        </div>
`;
    static props = ["*"];

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

