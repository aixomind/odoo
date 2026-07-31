/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount, onWillStart , xml } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const AVATAR_COLORS = ['#1976d2', '#388e3c', '#f57c00', '#7b1fa2', '#0097a7', '#d32f2f', '#5d4037', '#455a64'];
const FILTER_STORAGE_KEY = 'l4e_amc_dashboard_filters';
const DONUT_STATUS_KEYS = ['completed', 'ongoing', 'not_started', 'overdue'];
const DONUT_STATUS_TITLES = {
    completed: 'Completed Services',
    ongoing: 'Ongoing Services',
    not_started: 'Not Started Services',
    overdue: 'Overdue Services',
};

function getAvatarColor(name) {
    if (!name) return AVATAR_COLORS[0];
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
    return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0][0].toUpperCase();
}

function getStatusClass(status) {
    const map = {
        Done: 'done',
        'In Progress': 'in-progress',
        New: 'new',
        Overdue: 'overdue',
        'Due Soon': 'due-soon',
        Scheduled: 'scheduled',
    };
    return map[status] || 'new';
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr.replace(' ', 'T'));
    if (isNaN(d)) return dateStr;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

class AmcDashboard extends Component {
    static template = xml`
<div class="amc_dashboard">

        <div class="amc-dashboard-header">
            <div class="amc-header-left">
                <h1>&#9881; AMC Management Dashboard</h1>
                <p>Overview of Annual Maintenance Contract services</p>
            </div>
            <div class="amc-header-right">
                <div class="amc-date-picker">
                    <span>&#128197;</span>
                    <input type="date" t-att-value="state.dateFrom" t-att-max="state.dateTo" t-on-change="onDateFromChange"/>
                    <span>-</span>
                    <input type="date" t-att-value="state.dateTo" t-att-min="state.dateFrom" t-on-change="onDateToChange"/>
                </div>
                <button class="amc-btn-new" t-on-click="onFilter">Apply</button>
            </div>
        </div>

        <div class="amc-filters-bar">
            <div class="amc-filter-group">
                <label>Employee</label>
                <select class="amc-select" t-att-value="state.employeeId" t-on-change="onEmployeeChange">
                    <option value="">All Employees</option>
                    <t t-foreach="state.employees" t-as="emp" t-key="emp.id">
                        <option t-att-value="emp.id" t-esc="emp.name"/>
                    </t>
                </select>
            </div>
            <div class="amc-filter-group">
                <label>Customer</label>
                <select class="amc-select" t-att-value="state.customerId" t-on-change="onCustomerChange">
                    <option value="">All Customers</option>
                    <t t-foreach="state.customers" t-as="customer" t-key="customer.id">
                        <option t-att-value="customer.id" t-esc="customer.name"/>
                    </t>
                </select>
            </div>
            <button class="amc-btn-clear" t-on-click="onClearFilters">
                &#8635; Clear Filters
            </button>
        </div>

        <div class="amc-dashboard-body">

            <t t-if="state.loading">
                <div class="amc-loading">
                    <div class="amc-spinner"/>
                    Loading dashboard data...
                </div>
            </t>

            <t t-if="!state.loading and state.data">

                <div class="amc-kpi-row">
                    <div class="amc-kpi-card" t-on-click="() => this.openKpi('projects')" role="button" tabindex="0">
                        <div class="amc-kpi-icon blue">&#128193;</div>
                        <div class="amc-kpi-info">
                            <span class="amc-kpi-label">Projects</span>
                            <span class="amc-kpi-value" t-esc="state.data.projects"/>
                            <span class="amc-kpi-trend">&#8599; vs last month</span>
                        </div>
                    </div>
                    <div class="amc-kpi-card" t-on-click="() => this.openKpi('services')" role="button" tabindex="0">
                        <div class="amc-kpi-icon purple">&#9776;</div>
                        <div class="amc-kpi-info">
                            <span class="amc-kpi-label">Services</span>
                            <span class="amc-kpi-value" t-esc="state.data.services"/>
                            <span class="amc-kpi-trend">&#8599; vs last month</span>
                        </div>
                    </div>
                    <div class="amc-kpi-card" t-on-click="() => this.openKpi('completed')" role="button" tabindex="0">
                        <div class="amc-kpi-icon green">&#10003;</div>
                        <div class="amc-kpi-info">
                            <span class="amc-kpi-label">Completed</span>
                            <span class="amc-kpi-value" t-esc="state.data.completed"/>
                            <span class="amc-kpi-trend">&#8599; vs last month</span>
                        </div>
                    </div>
                    <div class="amc-kpi-card" t-on-click="() => this.openKpi('ongoing')" role="button" tabindex="0">
                        <div class="amc-kpi-icon orange">&#8635;</div>
                        <div class="amc-kpi-info">
                            <span class="amc-kpi-label">Ongoing</span>
                            <span class="amc-kpi-value" t-esc="state.data.ongoing"/>
                            <span class="amc-kpi-trend">&#8599; vs last month</span>
                        </div>
                    </div>
                    <div class="amc-kpi-card" t-on-click="() => this.openKpi('not_started')" role="button" tabindex="0">
                        <div class="amc-kpi-icon gray">&#128337;</div>
                        <div class="amc-kpi-info">
                            <span class="amc-kpi-label">Not Started</span>
                            <span class="amc-kpi-value" t-esc="state.data.not_started"/>
                            <span class="amc-kpi-trend">&#8599; vs last month</span>
                        </div>
                    </div>
                    <div class="amc-kpi-card" t-on-click="() => this.openKpi('overdue')" role="button" tabindex="0">
                        <div class="amc-kpi-icon red">&#9888;</div>
                        <div class="amc-kpi-info">
                            <span class="amc-kpi-label">Overdue</span>
                            <span class="amc-kpi-value" t-esc="state.data.overdue"/>
                            <span class="amc-kpi-trend down">&#8599; vs last month</span>
                        </div>
                    </div>
                </div>

                <div class="amc-charts-row">
                    <div class="amc-chart-card">
                        <div class="amc-chart-card-header">
                            <span class="amc-chart-title">Service Status Distribution</span>
                            <select class="amc-chart-period" t-att-value="state.statusPeriod" t-on-change="onStatusPeriodChange">
                                <option value="custom" t-if="state.statusPeriod === 'custom'">Custom</option>
                                <option value="month">This Month</option>
                                <option value="quarter">This Quarter</option>
                                <option value="year">This Year</option>
                            </select>
                        </div>
                        <div class="amc-donut-wrapper">
                            <div class="amc-donut-chart">
                                <canvas id="amcDonutCanvas" width="180" height="180"/>
                                <div class="amc-donut-center">
                                    <span class="amc-donut-center-value" t-esc="state.data.status_chart.total"/>
                                    <span class="amc-donut-center-label">Total</span>
                                </div>
                            </div>
                            <div class="amc-donut-legend">
                                <div class="amc-legend-item" t-on-click="() => this.openStatusSlice(0)" role="button" tabindex="0">
                                    <div class="amc-legend-dot" style="background:#4caf50"/>
                                    <span>Completed</span>
                                    <span class="amc-legend-count" t-esc="state.data.status_chart.completed + ' (' + getDonutPct(state.data.status_chart.completed) + ')'"/>
                                </div>
                                <div class="amc-legend-item" t-on-click="() => this.openStatusSlice(1)" role="button" tabindex="0">
                                    <div class="amc-legend-dot" style="background:#2196f3"/>
                                    <span>Ongoing</span>
                                    <span class="amc-legend-count" t-esc="state.data.status_chart.ongoing + ' (' + getDonutPct(state.data.status_chart.ongoing) + ')'"/>
                                </div>
                                <div class="amc-legend-item" t-on-click="() => this.openStatusSlice(2)" role="button" tabindex="0">
                                    <div class="amc-legend-dot" style="background:#ff9800"/>
                                    <span>Not Started</span>
                                    <span class="amc-legend-count" t-esc="state.data.status_chart.not_started + ' (' + getDonutPct(state.data.status_chart.not_started) + ')'"/>
                                </div>
                                <div class="amc-legend-item" t-on-click="() => this.openStatusSlice(3)" role="button" tabindex="0">
                                    <div class="amc-legend-dot" style="background:#f44336"/>
                                    <span>Overdue</span>
                                    <span class="amc-legend-count" t-esc="state.data.status_chart.overdue + ' (' + getDonutPct(state.data.status_chart.overdue) + ')'"/>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="amc-chart-card">
                        <div class="amc-chart-card-header">
                            <span class="amc-chart-title">Services Scheduled Per Month</span>
                            <select class="amc-chart-period" t-att-value="state.schedulePeriod" t-on-change="onSchedulePeriodChange">
                                <option value="custom" t-if="state.schedulePeriod === 'custom'">Custom</option>
                                <option value="month">This Month</option>
                                <option value="quarter">This Quarter</option>
                                <option value="year">This Year</option>
                            </select>
                        </div>
                        <div class="amc-bar-chart-wrapper" style="height:220px;">
                            <canvas id="amcBarCanvas"/>
                        </div>
                    </div>
                </div>

                <div class="amc-table-card">
                    <div class="amc-table-header">Upcoming Scheduled Services</div>
                    <div class="amc-table-wrapper">
                        <table class="amc-table">
                            <thead>
                                <tr>
                                    <th>Customer Name</th>
                                    <th>AMC Reference</th>
                                    <th>Scheduled Date &#9660;</th>
                                    <th>Product / Asset</th>
                                    <th>Employee</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-if="state.data.scheduled_services.length === 0">
                                    <tr>
                                        <td colspan="6" style="text-align:center;color:#718096;padding:32px;">
                                            No services found for the selected period.
                                        </td>
                                    </tr>
                                </t>
                                <t t-foreach="state.data.scheduled_services" t-as="svc" t-key="svc.id">
                                    <tr class="amc-service-row" t-on-click="() => this.openService(svc.id)">
                                        <td t-esc="svc.customer"/>
                                        <td t-esc="svc.amc_reference"/>
                                        <td>
                                            <span style="display:flex;align-items:center;gap:6px;">
                                                <t t-esc="formatDate(svc.scheduled_date)"/>
                                            </span>
                                        </td>
                                        <td t-esc="svc.product"/>
                                        <td>
                                            <div class="d-flex flex-wrap gap-1">
                                                <t t-foreach="svc.employees" t-as="emp" t-key="emp.id">
                                                    <div class="amc-employee-chip">
                                                        <div class="amc-employee-avatar"
                                                            t-att-style="'background:' + getAvatarColor(emp.name)"
                                                            t-esc="getInitials(emp.name)"/>
                                                        <span t-esc="emp.name"/>
                                                    </div>
                                                </t>
                                            </div>
                                        </td>
                                        <td>
                                            <span t-att-class="'amc-status-badge ' + getStatusClass(svc.status)"
                                                  t-esc="svc.status"/>
                                        </td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>
                    </div>
                </div>

            </t>

        </div>
    </div>
`;
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const savedFilters = this._getSavedFilters();
        this.state = useState({
            loading: true,
            data: null,
            dateFrom: savedFilters.dateFrom || this._defaultDateFrom(),
            dateTo: savedFilters.dateTo || this._defaultDateTo(),
            employeeId: savedFilters.employeeId || '',
            customerId: savedFilters.customerId || '',
            statusPeriod: savedFilters.statusPeriod || 'month',
            schedulePeriod: savedFilters.schedulePeriod || 'year',
            employees: [],
            customers: [],
        });
        this._donutChart = null;
        this._barChart = null;
        this._loadSeq = 0;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
        });

        onMounted(async () => {
            await this._loadEmployees();
            await this._loadCustomers();
            await this._loadData();
        });

        onWillUnmount(() => {
            if (this._donutChart) this._donutChart.destroy();
            if (this._barChart) this._barChart.destroy();
        });
    }

    _defaultDateFrom() {
        const d = new Date();
        d.setDate(1);
        return d.toISOString().split('T')[0];
    }

    _defaultDateTo() {
        const d = new Date();
        d.setMonth(d.getMonth() + 1);
        d.setDate(0);
        return d.toISOString().split('T')[0];
    }

    _formatInputDate(date) {
        return date.toISOString().split('T')[0];
    }

    _getPeriodRange(period) {
        if (period === 'custom') {
            return {
                dateFrom: this.state.dateFrom || false,
                dateTo: this.state.dateTo || false,
            };
        }
        const today = new Date();
        const start = new Date(today);
        const end = new Date(today);

        if (period === 'year') {
            start.setMonth(0, 1);
            end.setMonth(11, 31);
        } else if (period === 'quarter') {
            const quarterStartMonth = Math.floor(today.getMonth() / 3) * 3;
            start.setMonth(quarterStartMonth, 1);
            end.setMonth(quarterStartMonth + 3, 0);
        } else {
            start.setDate(1);
            end.setMonth(today.getMonth() + 1, 0);
        }

        return {
            dateFrom: this._formatInputDate(start),
            dateTo: this._formatInputDate(end),
        };
    }

    _getSavedFilters() {
        try {
            return JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY)) || {};
        } catch {
            return {};
        }
    }

    _saveFilters() {
        try {
            localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify({
                dateFrom: this.state.dateFrom,
                dateTo: this.state.dateTo,
                employeeId: this.state.employeeId,
                customerId: this.state.customerId,
                statusPeriod: this.state.statusPeriod,
                schedulePeriod: this.state.schedulePeriod,
            }));
        } catch {
        }
    }

    async _loadEmployees() {
        const employees = await this.orm.call("amc.dashboard", "get_employees", [], {});
        this.state.employees = employees;
    }

    async _loadCustomers() {
        const customers = await this.orm.call("amc.dashboard", "get_customers", [], {});
        this.state.customers = customers;
    }

    async _loadData() {
        const loadSeq = ++this._loadSeq;
        this.state.loading = true;
        const statusRange = this._getPeriodRange(this.state.statusPeriod);
        const scheduleRange = this._getPeriodRange(this.state.schedulePeriod);
        try {
            const result = await this.orm.call("amc.dashboard", "get_dashboard_data", [], {
                date_from: this.state.dateFrom || false,
                date_to: this.state.dateTo || false,
                employee_id: this.state.employeeId ? parseInt(this.state.employeeId, 10) : false,
                customer_id: this.state.customerId ? parseInt(this.state.customerId, 10) : false,
                status_date_from: statusRange.dateFrom || false,
                status_date_to: statusRange.dateTo || false,
                schedule_date_from: scheduleRange.dateFrom || false,
                schedule_date_to: scheduleRange.dateTo || false,
            });
            if (loadSeq !== this._loadSeq) return;
            this.state.data = result;
            setTimeout(() => {
                if (loadSeq !== this._loadSeq) return;
                this._renderDonut();
                this._renderBar();
            }, 100);
        } finally {
            if (loadSeq === this._loadSeq) {
                this.state.loading = false;
            }
        }
    }

    _renderDonut() {
        const canvas = document.getElementById('amcDonutCanvas');
        if (!canvas || !this.state.data) return;
        if (this._donutChart) this._donutChart.destroy();
        const d = this.state.data;
        const Chart = window.Chart;
        if (!Chart) return;

        const hasData = (d.status_chart.completed + d.status_chart.ongoing + d.status_chart.not_started + d.status_chart.overdue) > 0;
        const chartData = hasData ? [
            d.status_chart.completed,
            d.status_chart.ongoing,
            d.status_chart.not_started,
            d.status_chart.overdue,
        ] : [1];
        const bgColors = hasData ? ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'] : ['#e2e8f0'];

        this._donutChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Ongoing', 'Not Started', 'Overdue'],
                datasets: [{
                    data: chartData,
                    backgroundColor: bgColors,
                    borderWidth: 0,
                    hoverOffset: hasData ? 6 : 0,
                }],
            },
            options: {
                cutoutPercentage: 75,
                cutout: '75%',
                responsive: true,
                maintainAspectRatio: false,
                legend: {
                    display: false
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: hasData,
                        backgroundColor: '#0f172a',
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => {
                                const total = d.status_chart.total || 0;
                                const val = ctx.raw !== undefined ? ctx.raw : ctx.y;
                                return ` ${ctx.label}: ${val} (${total ? Math.round(val / total * 100) : 0}%)`;
                            },
                        },
                    },
                },
                onClick: (_event, elements) => {
                    if (!elements || !elements.length || !hasData) return;
                    this.openStatusSlice(elements[0].index);
                },
                onHover: (evt, activeElements) => {
                    const target = evt?.native?.target || evt?.target || (evt?.chart && evt.chart.canvas);
                    if (target && target.style) {
                        target.style.cursor = (activeElements && activeElements.length) ? 'pointer' : 'default';
                    }
                },
            },
        });
    }

    _renderBar() {
        const canvas = document.getElementById('amcBarCanvas');
        if (!canvas || !this.state.data) return;
        if (this._barChart) this._barChart.destroy();
        const Chart = window.Chart;
        if (!Chart) return;
        this._barChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: MONTHS,
                datasets: [{
                    label: 'Services',
                    data: this.state.data.monthly_data,
                    backgroundColor: '#3b82f6',
                    hoverBackgroundColor: '#2563eb',
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 32,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (_event, elements) => {
                    if (!elements.length) return;
                    this.openMonthlySlice(elements[0].index);
                },
                onHover: (evt, activeElements) => {
                    const target = evt?.native?.target || evt?.target || (evt?.chart && evt.chart.canvas);
                    if (target && target.style) {
                        target.style.cursor = (activeElements && activeElements.length) ? 'pointer' : 'default';
                    }
                },
                legend: {
                    display: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        padding: 10,
                        cornerRadius: 8,
                        mode: 'index',
                        intersect: false
                    },
                },
                scales: {
                    yAxes: [{
                        ticks: {
                            beginAtZero: true,
                            min: 0,
                            suggestedMax: 5,
                            stepSize: 1,
                            precision: 0,
                            fontColor: '#64748b',
                            fontSize: 11,
                        },
                        gridLines: {
                            color: '#f1f5f9',
                            zeroLineColor: '#cbd5e1',
                        }
                    }],
                    xAxes: [{
                        gridLines: {
                            display: false
                        },
                        ticks: {
                            fontColor: '#64748b',
                            fontSize: 11,
                        }
                    }],
                    y: {
                        beginAtZero: true,
                        min: 0,
                        suggestedMax: 5,
                        grid: { color: '#f1f5f9' },
                        ticks: { stepSize: 1, precision: 0, font: { size: 11 } }
                    },
                    x: { grid: { display: false }, ticks: { font: { size: 11 } } },
                },
            },
        });
    }

    onDateFromChange(ev) {
        const val = ev.target.value;
        this.state.dateFrom = val;
        if (this.state.dateTo && val > this.state.dateTo) {
            this.state.dateTo = val;
        }
    }

    onDateToChange(ev) {
        const val = ev.target.value;
        this.state.dateTo = val;
        if (this.state.dateFrom && val < this.state.dateFrom) {
            this.state.dateFrom = val;
        }
    }

    async onEmployeeChange(ev) {
        this.state.employeeId = ev.target.value;
        this._saveFilters();
        await this._loadData();
    }

    async onCustomerChange(ev) {
        this.state.customerId = ev.target.value;
        this._saveFilters();
        await this._loadData();
    }

    async onFilter() {
        if (this.state.dateFrom || this.state.dateTo) {
            this.state.statusPeriod = 'custom';
            this.state.schedulePeriod = 'custom';
        }
        this._saveFilters();
        await this._loadData();
    }

    async onStatusPeriodChange(ev) {
        this.state.statusPeriod = ev.target.value;
        this._saveFilters();
        await this._loadData();
    }

    async onSchedulePeriodChange(ev) {
        this.state.schedulePeriod = ev.target.value;
        this._saveFilters();
        await this._loadData();
    }

    async onClearFilters() {
        this.state.dateFrom = this._defaultDateFrom();
        this.state.dateTo = this._defaultDateTo();
        this.state.employeeId = '';
        this.state.customerId = '';
        this.state.statusPeriod = 'month';
        this.state.schedulePeriod = 'year';
        this._saveFilters();
        await this._loadData();
    }

    openKpi(type) {
        const actionData = this.state.data?.actions?.[type];
        if (!actionData) return;
        const titles = {
            projects: 'Field Service Projects',
            services: 'Services',
            completed: 'Completed Services',
            ongoing: 'Ongoing Services',
            not_started: 'Not Started Services',
            overdue: 'Overdue Services',
        };
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: titles[type] || 'AMC Records',
            res_model: actionData.model,
            views: [[false, 'list'], [false, 'form']],
            domain: [['id', 'in', actionData.ids || []]],
            target: 'current',
        });
    }

    openTaskList(name, ids) {
        if (!ids || !ids.length) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            name,
            res_model: 'project.task',
            views: [[false, 'list'], [false, 'form']],
            domain: [['id', 'in', ids]],
            target: 'current',
        });
    }

    openStatusSlice(index) {
        const key = DONUT_STATUS_KEYS[index];
        if (!key) return;
        const ids = this.state.data?.status_actions?.[key] || [];
        this.openTaskList(DONUT_STATUS_TITLES[key] || 'AMC Services', ids);
    }

    openMonthlySlice(index) {
        const monthName = MONTHS[index];
        if (!monthName) return;
        const ids = this.state.data?.monthly_actions?.[index] || [];
        this.openTaskList(`${monthName} Scheduled Services`, ids);
    }

    openService(serviceId) {
        if (!serviceId) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Service',
            res_model: 'project.task',
            views: [[false, 'form']],
            res_id: serviceId,
            target: 'current',
        });
    }

    getStatusClass(status) { return getStatusClass(status); }
    getInitials(name) { return getInitials(name); }
    getAvatarColor(name) { return getAvatarColor(name); }
    formatDate(d) { return formatDate(d); }

    getDonutPct(val) {
        const total = this.state.data?.status_chart?.total || 0;
        if (!total) return '0%';
        return Math.round(val / total * 100) + '%';
    }
}

registry.category("actions").add("l4e_dashboard_collection.amc_dashboard", AmcDashboard);
export { AmcDashboard };

