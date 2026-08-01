/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount, onWillStart, xml } from "@odoo/owl";
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
    static template = "l4e_dashboard_collection.AmcDashboard";

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
        this._themeCleanup = null;
        this._loadSeq = 0;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
        });

        onMounted(async () => {
            if (window.l4eDashboardTheme) {
                this._themeCleanup = window.l4eDashboardTheme.subscribe(() => {
                    this._renderDonut();
                    this._renderBar();
                });
            }
            await this._loadEmployees();
            await this._loadCustomers();
            await this._loadData();
        });

        onWillUnmount(() => {
            if (this._donutChart) this._donutChart.destroy();
            if (this._barChart) this._barChart.destroy();
            if (this._themeCleanup) this._themeCleanup();
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

    _chartTheme() {
        const isDark = Boolean(window.l4eDashboardTheme && window.l4eDashboardTheme.isDark());
        return {
            axis: isDark ? '#cbd5e1' : '#4a5568',
            grid: isDark ? '#334155' : '#f0f2f5',
            legend: isDark ? '#e2e8f0' : '#374151',
            tooltipBg: isDark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(33, 37, 41, 0.95)',
            donutBorder: isDark ? '#1e293b' : '#fff',
        };
    }

    _renderDonut() {
        const canvas = document.getElementById('amcDonutCanvas');
        if (!canvas || !this.state.data) return;
        if (this._donutChart) this._donutChart.destroy();
        const d = this.state.data;
        const Chart = window.Chart;
        if (!Chart) return;
        const theme = this._chartTheme();
        this._donutChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Ongoing', 'Not Started', 'Overdue'],
                datasets: [{
                    data: [
                        d.status_chart.completed,
                        d.status_chart.ongoing,
                        d.status_chart.not_started,
                        d.status_chart.overdue,
                    ],
                    backgroundColor: ['#4caf50', '#2196f3', '#ff9800', '#f44336'],
                    borderColor: theme.donutBorder,
                    borderWidth: 1,
                    hoverOffset: 6,
                }],
            },
            options: {
                cutout: '72%',
                onClick: (_event, elements) => {
                    if (!elements.length) return;
                    this.openStatusSlice(elements[0].index);
                },
                onHover: (event, elements) => {
                    const target = event?.native?.target;
                    if (target) {
                        target.style.cursor = elements.length ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: theme.tooltipBg,
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        callbacks: {
                            label: (ctx) => {
                                const total = d.status_chart.total || 0;
                                return ` ${ctx.label}: ${ctx.raw} (${total ? Math.round(ctx.raw / total * 100) : 0}%)`;
                            },
                        },
                    },
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
        const theme = this._chartTheme();
        this._barChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: MONTHS,
                datasets: [{
                    label: 'Services',
                    data: this.state.data.monthly_data,
                    backgroundColor: '#2196f3',
                    borderRadius: 5,
                    borderSkipped: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (_event, elements) => {
                    if (!elements.length) return;
                    this.openMonthlySlice(elements[0].index);
                },
                onHover: (event, elements) => {
                    const target = event?.native?.target;
                    if (target) {
                        target.style.cursor = elements.length ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { color: theme.legend, font: { size: 12 }, boxWidth: 12 } },
                    tooltip: { mode: 'index', intersect: false, backgroundColor: theme.tooltipBg, titleColor: '#fff', bodyColor: '#fff' },
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: theme.grid }, ticks: { color: theme.axis, font: { size: 11 } } },
                    x: { grid: { display: false }, ticks: { color: theme.axis, font: { size: 11 } } },
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

