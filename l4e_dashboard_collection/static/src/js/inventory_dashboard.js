import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { currencies } from "@web/core/currency";

export class L4eInventoryDashboard extends Component {
    static template = "l4e_dashboard_collection.InventoryDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.lineCanvasRef = useRef("lineChart");
        this.donutCanvasRef = useRef("donutChart");

        const savedFilter = sessionStorage.getItem('l4e_dashboard_active_filter') || "this_month";
        const savedDateFrom = sessionStorage.getItem('l4e_dashboard_date_from') || "";
        const savedDateTo = sessionStorage.getItem('l4e_dashboard_date_to') || "";
        const savedProductId = sessionStorage.getItem('l4e_dashboard_selected_product_id')
            ? parseInt(sessionStorage.getItem('l4e_dashboard_selected_product_id'))
            : null;
        const savedSearchQuery = sessionStorage.getItem('l4e_dashboard_search_query') || "";

        this.state = useState({
            date_from: savedDateFrom,
            date_to: savedDateTo,
            active_filter: savedFilter,
            search_query: savedSearchQuery,
            selected_product_id: savedProductId,
            suggestions: [],
            show_suggestions: false,
            data: null,
            loading: true,
        });

        useEffect(() => {
            const handleOutsideClick = (e) => {
                if (this.state.show_suggestions && !e.target.closest('.product-dropdown-container')) {
                    this.state.show_suggestions = false;
                }
            };
            document.addEventListener('click', handleOutsideClick);
            return () => document.removeEventListener('click', handleOutsideClick);
        });

        onWillStart(async () => {
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
            } catch (e1) {
                try {
                    await loadJS("/web/static/lib/chart/chart.js");
                } catch (e2) {
                    console.warn("Chart.js fallback:", e2);
                }
            }
            if (this.state.active_filter !== 'custom' || !this.state.date_from || !this.state.date_to) {
                const dates = this.getDatesForFilter(this.state.active_filter);
                this.state.date_from = dates.date_from;
                this.state.date_to = dates.date_to;
            }
            await this.fetchDashboardData();
        });

        useEffect(() => {
            if (this.state.data) {
                this.renderLineChart();
                this.renderDonutChart();
            }
        }, () => [this.state.data]);

        onWillUnmount(() => {
            if (this.lineChart) this.lineChart.destroy();
            if (this.donutChart) this.donutChart.destroy();
        });
    }

    getDatesForFilter(filter) {
        const today = new Date();
        let date_from = "";
        let date_to = today.toISOString().split('T')[0];

        if (filter === "this_month") {
            const start = new Date(today.getFullYear(), today.getMonth(), 1);
            const offset = start.getTimezoneOffset() * 60000;
            const localStart = new Date(start.getTime() - offset);
            date_from = localStart.toISOString().split('T')[0];
        } else if (filter === "last_30_days") {
            const start = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
            const offset = start.getTimezoneOffset() * 60000;
            const localStart = new Date(start.getTime() - offset);
            date_from = localStart.toISOString().split('T')[0];
        } else if (filter === "this_quarter") {
            const quarterMonth = Math.floor(today.getMonth() / 3) * 3;
            const start = new Date(today.getFullYear(), quarterMonth, 1);
            const offset = start.getTimezoneOffset() * 60000;
            const localStart = new Date(start.getTime() - offset);
            date_from = localStart.toISOString().split('T')[0];
        } else if (filter === "this_year") {
            const start = new Date(today.getFullYear(), 0, 1);
            const offset = start.getTimezoneOffset() * 60000;
            const localStart = new Date(start.getTime() - offset);
            date_from = localStart.toISOString().split('T')[0];
        }
        return { date_from, date_to };
    }

    async fetchDashboardData() {
        this.state.loading = true;
        try {
            const res = await this.orm.call(
                'l4e.inventory.dashboard',
                'get_dashboard_data',
                [],
                {
                    date_from: this.state.date_from,
                    date_to: this.state.date_to,
                    product_id: this.state.selected_product_id
                }
            );
            this.state.data = res;
        } catch (err) {
            console.error("Failed to load inventory dashboard data:", err);
        } finally {
            this.state.loading = false;
        }
    }

    async changeFilter(filterType) {
        this.state.active_filter = filterType;
        if (filterType !== 'custom') {
            const dates = this.getDatesForFilter(filterType);
            this.state.date_from = dates.date_from;
            this.state.date_to = dates.date_to;

            sessionStorage.setItem('l4e_dashboard_active_filter', filterType);
            sessionStorage.setItem('l4e_dashboard_date_from', dates.date_from);
            sessionStorage.setItem('l4e_dashboard_date_to', dates.date_to);

            await this.fetchDashboardData();
        } else {
            sessionStorage.setItem('l4e_dashboard_active_filter', 'custom');
        }
    }

    async applyCustomDates() {
        this.state.active_filter = 'custom';
        sessionStorage.setItem('l4e_dashboard_active_filter', 'custom');
        sessionStorage.setItem('l4e_dashboard_date_from', this.state.date_from);
        sessionStorage.setItem('l4e_dashboard_date_to', this.state.date_to);
        await this.fetchDashboardData();
    }

    async onSearchInput() {
        const query = this.state.search_query.trim();
        if (query.length < 2) {
            this.state.suggestions = [];
            this.state.show_suggestions = false;
            return;
        }
        try {
            const products = await this.orm.searchRead(
                'product.product',
                [['name', 'ilike', query], ['active', '=', true], ['categ_id.show_in_dashboard', '=', true]],
                ['id', 'name', 'product_tmpl_id'],
                { limit: 8 }
            );
            this.state.suggestions = products.map(p => ({
                id: p.id,
                name: typeof p.name === 'object' && p.name !== null ? p.name[this.env.lang || 'en_US'] || p.name['en_US'] || Object.values(p.name)[0] : p.name,
                tmpl_id: p.product_tmpl_id ? p.product_tmpl_id[0] : null
            }));
            this.state.show_suggestions = true;
        } catch (err) {
            console.error("Failed to search products:", err);
        }
    }

    async selectProduct(productId, productName) {
        this.state.selected_product_id = productId;
        this.state.search_query = productName;
        this.state.show_suggestions = false;

        sessionStorage.setItem('l4e_dashboard_selected_product_id', productId);
        sessionStorage.setItem('l4e_dashboard_search_query', productName);

        await this.fetchDashboardData();
    }

    async clearProductFilter() {
        this.state.selected_product_id = null;
        this.state.search_query = "";
        this.state.show_suggestions = false;

        sessionStorage.removeItem('l4e_dashboard_selected_product_id');
        sessionStorage.removeItem('l4e_dashboard_search_query');

        await this.fetchDashboardData();
    }

    async onSearchFocus() {
        if (this.state.search_query.trim().length === 0) {
            try {
                const products = await this.orm.searchRead(
                    'product.product',
                    [['active', '=', true], ['categ_id.show_in_dashboard', '=', true]],
                    ['id', 'name', 'product_tmpl_id'],
                    { limit: 20 }
                );
                this.state.suggestions = products.map(p => ({
                    id: p.id,
                    name: typeof p.name === 'object' && p.name !== null ? p.name[this.env.lang || 'en_US'] || p.name['en_US'] || Object.values(p.name)[0] : p.name,
                    tmpl_id: p.product_tmpl_id ? p.product_tmpl_id[0] : null
                }));
                this.state.show_suggestions = true;
            } catch (err) {
                console.error("Failed to load dropdown products:", err);
            }
        } else {
            this.state.show_suggestions = true;
        }
    }

    async toggleDropdown(e) {
        if (e.target.closest('.btn-outline-secondary') || e.target.tagName === 'INPUT') {
            return;
        }
        if (this.state.show_suggestions) {
            this.state.show_suggestions = false;
        } else {
            await this.onSearchFocus();
        }
    }

    renderLineChart() {
        if (typeof Chart === "undefined") return;
        if (this.lineChart) {
            this.lineChart.destroy();
        }
        if (!this.lineCanvasRef.el) return;
        const ctx = this.lineCanvasRef.el.getContext("2d");
        const labels = this.state.data.values_over_time.map(d => d.date);
        const dataValues = this.state.data.values_over_time.map(d => d.value);

        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, "rgba(111, 66, 193, 0.4)");
        gradient.addColorStop(1, "rgba(111, 66, 193, 0.0)");

        this.lineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Inventory Value',
                    data: dataValues,
                    borderColor: '#6f42c1',
                    borderWidth: 3,
                    pointBackgroundColor: '#6f42c1',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    backgroundColor: gradient,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(33, 37, 41, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += this.formatCurrency(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#6c757d' }
                    },
                    y: {
                        grid: { color: '#e9ecef' },
                        ticks: {
                            color: '#6c757d',
                            callback: (value) => {
                                const currency = this.getCompanyCurrency();
                                const symbol = currency.symbol;
                                const pos = currency.position;
                                let formattedValue = value;
                                if (value >= 1000000) {
                                    formattedValue = (value / 1000000).toFixed(1) + 'M';
                                } else if (value >= 1000) {
                                    formattedValue = (value / 1000).toFixed(0) + 'k';
                                } else {
                                    formattedValue = value;
                                }
                                return pos === 'before' ? symbol + formattedValue : formattedValue + ' ' + symbol;
                            }
                        }
                    }
                }
            }
        });
    }

    renderDonutChart() {
        if (typeof Chart === "undefined") return;
        if (this.donutChart) {
            this.donutChart.destroy();
        }
        if (!this.donutCanvasRef.el) return;
        const ctx = this.donutCanvasRef.el.getContext("2d");
        const categories = this.state.data.categories || [];
        const labels = categories.map(c => c.name);
        const dataValues = categories.map(c => c.value);

        const colors = ['#0d6efd', '#20c997', '#ffc107', '#d63384', '#6f42c1', '#fd7e14', '#17a2b8', '#6c757d'];

        this.donutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: colors.slice(0, dataValues.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                onHover: (evt, activeElements) => {
                    evt.chart.canvas.style.cursor = activeElements.length ? 'pointer' : 'default';
                },
                onClick: (evt, activeElements) => {
                    if (activeElements && activeElements.length > 0) {
                        const firstPoint = activeElements[0];
                        const index = firstPoint.index;
                        const category = this.state.data.categories[index];
                        if (category) {
                            this.openCategoryProducts(category.id, category.name);
                        }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(33, 37, 41, 0.95)',
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0) || 1.0;
                                const value = context.raw;
                                const pct = ((value / total) * 100).toFixed(1);
                                const formatted = this.formatCurrency(value);
                                return ` ${context.label}: ${formatted} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    get categoryBreakdown() {
        if (!this.state.data || !this.state.data.categories) return [];
        const total = this.state.data.categories.reduce((a, c) => a + c.value, 0) || 1.0;
        const colors = ['#0d6efd', '#20c997', '#ffc107', '#d63384', '#6f42c1', '#fd7e14', '#17a2b8', '#6c757d'];
        return this.state.data.categories.map((c, i) => {
            const pct = ((c.value / total) * 100).toFixed(1);
            return {
                ...c,
                color: colors[i % colors.length],
                percentage: pct,
                formatted_value: this.formatCurrency(c.value, 0)
            };
        });
    }

    getCompanyCurrency() {
        const currencyId = this.state.data?.currency_id;
        const currency = currencyId ? currencies[currencyId] : null;
        return {
            symbol: currency ? currency.symbol : (this.state.data?.currency_symbol || '$'),
            position: currency ? currency.position : (this.state.data?.currency_position || 'before'),
            id: currencyId
        };
    }

    get formattedTotalValue() {
        if (!this.state.data || !this.state.data.kpis) {
            const currency = this.getCompanyCurrency();
            const symbol = currency.symbol;
            const pos = currency.position;
            return pos === 'before' ? symbol + '0' : '0 ' + symbol;
        }
        return this.formatCurrency(this.state.data.kpis.total_value.value, 0);
    }

    formatCurrency(value, maxDigits = 2) {
        const currency = this.getCompanyCurrency();
        const formattedAmount = new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: maxDigits
        }).format(value);
        return currency.position === 'before' ? currency.symbol + formattedAmount : formattedAmount + ' ' + currency.symbol;
    }

    formatNumber(value) {
        return new Intl.NumberFormat('en-US').format(value);
    }

    viewProducts() {
        const domain = [['categ_id.show_in_dashboard', '=', true]];
        if (this.state.selected_product_id) {
            domain.push(['product_variant_ids', 'in', [this.state.selected_product_id]]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Products',
            res_model: 'product.template',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: { search_default_goods: 1, default_is_storable: true }
        }, { clear_breadcrumbs: true });
    }

    viewLocations() {
        this.actionService.doAction("stock.action_location_form", { clear_breadcrumbs: true });
    }

    viewMoves() {
        const domain = [
            ['product_id.categ_id.show_in_dashboard', '=', true],
            ['state', '=', 'done'],
            ['date', '>=', this.state.date_from],
            ['date', '<=', this.state.date_to]
        ];
        if (this.state.selected_product_id) {
            domain.push(['product_id', '=', this.state.selected_product_id]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Detailed Moves',
            res_model: 'stock.move',
            views: [[false, 'list'], [false, 'form']],
            domain: domain
        }, { clear_breadcrumbs: true });
    }

    async clickTotalInventoryValue() {
        const domain = [['product_id.categ_id.show_in_dashboard', '=', true]];
        if (this.state.selected_product_id) {
            domain.push(['product_id', '=', this.state.selected_product_id]);
        }
        try {
            await this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Stock Valuation',
                res_model: 'stock.valuation.layer',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                context: { search_default_group_by_product: 1 }
            }, { clear_breadcrumbs: true });
        } catch (err) {
            const quantDomain = [['product_id.categ_id.show_in_dashboard', '=', true], ['location_id.usage', '=', 'internal']];
            if (this.state.selected_product_id) {
                quantDomain.push(['product_id', '=', this.state.selected_product_id]);
            }
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Inventory Valuation',
                res_model: 'stock.quant',
                views: [[false, 'list'], [false, 'form']],
                domain: quantDomain
            }, { clear_breadcrumbs: true });
        }
    }

    clickTotalProducts() {
        const domain = [['categ_id.show_in_dashboard', '=', true]];
        if (this.state.selected_product_id) {
            domain.push(['product_variant_ids', 'in', [this.state.selected_product_id]]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Products',
            res_model: 'product.template',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: { search_default_goods: 1, default_is_storable: true }
        }, { clear_breadcrumbs: true });
    }

    clickStockMoves() {
        const domain = [
            ['product_id.categ_id.show_in_dashboard', '=', true],
            ['state', '=', 'done'],
            ['date', '>=', this.state.date_from],
            ['date', '<=', this.state.date_to]
        ];
        if (this.state.selected_product_id) {
            domain.push(['product_id', '=', this.state.selected_product_id]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Stock Moves',
            res_model: 'stock.move',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        }, { clear_breadcrumbs: true });
    }

    clickLowStock() {
        if (!this.state.data || !this.state.data.kpis.low_stock.product_ids.length) return;
        const productIds = this.state.data.kpis.low_stock.product_ids;
        const domain = [['product_variant_ids', 'in', productIds]];
        if (this.state.selected_product_id) {
            domain.push(['product_variant_ids', 'in', [this.state.selected_product_id]]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Low Stock Products',
            res_model: 'product.template',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: { search_default_goods: 1, default_is_storable: true }
        }, { clear_breadcrumbs: true });
    }

    clickIncomingMoves() {
        const domain = [
            ['product_id.categ_id.show_in_dashboard', '=', true],
            ['state', '=', 'done'],
            ['date', '>=', this.state.date_from],
            ['date', '<=', this.state.date_to],
            ['location_id.usage', '!=', 'internal'],
            ['location_dest_id.usage', '=', 'internal']
        ];
        if (this.state.selected_product_id) {
            domain.push(['product_id', '=', this.state.selected_product_id]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Incoming Stock Moves',
            res_model: 'stock.move',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        }, { clear_breadcrumbs: true });
    }

    clickOutgoingMoves() {
        const domain = [
            ['product_id.categ_id.show_in_dashboard', '=', true],
            ['state', '=', 'done'],
            ['date', '>=', this.state.date_from],
            ['date', '<=', this.state.date_to],
            ['location_id.usage', '=', 'internal'],
            ['location_dest_id.usage', '!=', 'internal']
        ];
        if (this.state.selected_product_id) {
            domain.push(['product_id', '=', this.state.selected_product_id]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Outgoing Stock Moves',
            res_model: 'stock.move',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        }, { clear_breadcrumbs: true });
    }

    openCategoryProducts(categoryId, categoryName) {
        const domain = [['categ_id', '=', categoryId]];
        if (this.state.selected_product_id) {
            domain.push(['product_variant_ids', 'in', [this.state.selected_product_id]]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Products - ${categoryName}`,
            res_model: 'product.template',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: { search_default_goods: 1, default_is_storable: true }
        }, { clear_breadcrumbs: true });
    }

    openProductForm(productId) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'product.product',
            res_id: productId,
            views: [[false, 'form']],
            target: 'current',
        }, { clear_breadcrumbs: true });
    }

    openLocationQuants(locationId, locationName) {
        const domain = [['location_id', '=', locationId], ['product_id.categ_id.show_in_dashboard', '=', true]];
        if (this.state.selected_product_id) {
            domain.push(['product_id', '=', this.state.selected_product_id]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Stock Quants - ${locationName}`,
            res_model: 'stock.quant',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        }, { clear_breadcrumbs: true });
    }

    openProductMoves(productId, productName) {
        const domain = [
            ['product_id', '=', productId],
            ['state', '=', 'done'],
            ['date', '>=', this.state.date_from],
            ['date', '<=', this.state.date_to]
        ];
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Stock Moves - ${productName}`,
            res_model: 'stock.move',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        }, { clear_breadcrumbs: true });
    }
}

registry.category("actions").add("l4e_dashboard_collection.inventory_dashboard", L4eInventoryDashboard);
export { L4eInventoryDashboard };

