/** @odoo-module **/
import { Component, onMounted, onWillStart, onWillUnmount, useEffect, useRef, useState , xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class L4eInventoryDashboard extends Component {
    static template = xml`
<div class="l4e_dashboard_wrapper bg-light p-4 overflow-auto h-100">

            <div t-if="state.loading" class="d-flex justify-content-center align-items-center h-100 w-100 position-absolute top-0 start-0 bg-white bg-opacity-75" style="z-index: 1000;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>

            <div t-if="state.data" class="d-flex flex-column gap-4">

                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 bg-white p-3 rounded-3 shadow-sm">
                    <div class="d-flex align-items-center gap-2">
                        <span class="fs-4 fw-bold text-dark flex-shrink-0">Inventory Dashboard</span>

                        <div class="position-relative product-dropdown-container" style="width: 220px;">
                            <div class="input-group input-group-sm cursor-pointer" t-on-click="toggleDropdown">
                                <span class="input-group-text bg-light border-end-0 text-muted">
                                    <i class="fa fa-search"></i>
                                </span>
                                <input type="text" class="form-control border-start-0 border-end-0 bg-light" style="min-width: 0;" placeholder="Select Product..." t-model="state.search_query" t-on-input="onSearchInput" t-on-focus="onSearchFocus"/>
                                <button t-if="state.selected_product_id" class="btn btn-outline-secondary border-start-0 border-end-0 bg-light text-muted px-2" type="button" t-on-click="clearProductFilter">
                                    <i class="fa fa-times"></i>
                                </button>
                                <span class="input-group-text bg-light border-start-0 text-muted">
                                    <i class="fa fa-caret-down"></i>
                                </span>
                            </div>
                            <div t-if="state.show_suggestions &amp;&amp; state.suggestions.length" class="position-absolute bg-white border rounded shadow-lg w-100 mt-1" style="z-index: 1050; max-height: 220px; overflow-y: auto;">
                                <div class="list-group list-group-flush">
                                    <t t-foreach="state.suggestions" t-as="prod" t-key="prod.id">
                                        <button type="button" class="list-group-item list-group-item-action d-flex align-items-center gap-2 py-2 border-0" t-on-click="() => this.selectProduct(prod.id, prod.name)">
                                            <img t-attf-src="/web/image/product.product/#{prod.id}/image_128" class="rounded border p-1 bg-white" style="width: 28px; height: 28px; object-fit: cover;" onerror="this.src='/web/static/img/placeholder.png'"/>
                                            <span class="text-dark small text-truncate fw-semibold" t-out="prod.name"></span>
                                        </button>
                                    </t>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="d-flex flex-wrap align-items-center gap-2">
                        <div class="btn-group btn-group-sm shadow-sm" role="group">
                            <button type="button" class="btn btn-outline-primary py-1 px-2.5" t-att-class="{'active': state.active_filter === 'this_month'}" t-on-click="() => this.changeFilter('this_month')">This Month</button>
                            <button type="button" class="btn btn-outline-primary py-1 px-2.5" t-att-class="{'active': state.active_filter === 'last_30_days'}" t-on-click="() => this.changeFilter('last_30_days')">Last 30 Days</button>
                            <button type="button" class="btn btn-outline-primary py-1 px-2.5" t-att-class="{'active': state.active_filter === 'this_quarter'}" t-on-click="() => this.changeFilter('this_quarter')">This Quarter</button>
                            <button type="button" class="btn btn-outline-primary py-1 px-2.5" t-att-class="{'active': state.active_filter === 'this_year'}" t-on-click="() => this.changeFilter('this_year')">This Year</button>
                        </div>

                        <div class="d-flex align-items-center gap-1.5 border rounded p-1 bg-light">
                            <input type="date" class="form-control form-control-sm border-0 bg-transparent py-0" style="width: 110px; font-size: 0.8rem;" t-att-value="state.date_from" t-att-max="state.date_to" t-on-change="onDateFromChange"/>
                            <span class="text-muted small">to</span>
                            <input type="date" class="form-control form-control-sm border-0 bg-transparent py-0" style="width: 110px; font-size: 0.8rem;" t-att-value="state.date_to" t-att-min="state.date_from" t-on-change="onDateToChange"/>
                            <button class="btn btn-sm btn-primary py-1 px-2" t-on-click="applyCustomDates">Apply</button>
                        </div>
                    </div>
                </div>

                <div class="row g-3">

                    <div class="col-12 col-sm-6 col-md-4 col-lg">
                        <div class="card h-100 border-0 shadow-sm rounded-3 p-3 kpi-card cursor-pointer" t-on-click="clickTotalInventoryValue">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <span class="text-muted small fw-semibold">Total Inventory Value</span>
                                    <h3 class="fw-bold mt-2 mb-1" t-out="formatCurrency(state.data.kpis.total_value.value)"></h3>
                                    <div class="d-flex align-items-center gap-1">
                                        <span class="small fw-semibold" t-att-class="state.data.kpis.total_value.trend >= 0 ? 'text-success' : 'text-danger'">
                                            <i t-att-class="state.data.kpis.total_value.trend >= 0 ? 'fa fa-arrow-up' : 'fa fa-arrow-down'"></i>
                                            <t t-out="Math.abs(state.data.kpis.total_value.trend)"/>%
                                        </span>
                                        <span class="text-muted small">vs Last Month</span>
                                    </div>
                                </div>
                                <div class="kpi-icon-bg bg-purple-light rounded-3 p-2 text-purple">
                                    <i class="fa fa-cubes fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-sm-6 col-md-4 col-lg">
                        <div class="card h-100 border-0 shadow-sm rounded-3 p-3 kpi-card cursor-pointer" t-on-click="clickTotalProducts">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <span class="text-muted small fw-semibold">Total Products</span>
                                    <h3 class="fw-bold mt-2 mb-1" t-out="formatNumber(state.data.kpis.total_products.value)"></h3>
                                    <div class="d-flex align-items-center gap-1">
                                        <span class="small fw-semibold" t-att-class="state.data.kpis.total_products.trend >= 0 ? 'text-success' : 'text-danger'">
                                            <i t-att-class="state.data.kpis.total_products.trend >= 0 ? 'fa fa-arrow-up' : 'fa fa-arrow-down'"></i>
                                            <t t-out="Math.abs(state.data.kpis.total_products.trend)"/>%
                                        </span>
                                        <span class="text-muted small">vs Last Month</span>
                                    </div>
                                </div>
                                <div class="kpi-icon-bg bg-teal-light rounded-3 p-2 text-teal">
                                    <i class="fa fa-database fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-sm-6 col-md-4 col-lg">
                        <div class="card h-100 border-0 shadow-sm rounded-3 p-3 kpi-card cursor-pointer" t-on-click="clickStockMoves">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <span class="text-muted small fw-semibold">Stock Moves</span>
                                    <h3 class="fw-bold mt-2 mb-1" t-out="formatNumber(state.data.kpis.stock_moves.value)"></h3>
                                    <div class="d-flex align-items-center gap-1">
                                        <span class="small fw-semibold" t-att-class="state.data.kpis.stock_moves.trend >= 0 ? 'text-success' : 'text-danger'">
                                            <i t-att-class="state.data.kpis.stock_moves.trend >= 0 ? 'fa fa-arrow-up' : 'fa fa-arrow-down'"></i>
                                            <t t-out="Math.abs(state.data.kpis.stock_moves.trend)"/>%
                                        </span>
                                        <span class="text-muted small">vs Last Month</span>
                                    </div>
                                </div>
                                <div class="kpi-icon-bg bg-orange-light rounded-3 p-2 text-orange">
                                    <i class="fa fa-exchange fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-sm-6 col-md-4 col-lg">
                        <div class="card h-100 border-0 shadow-sm rounded-3 p-3 kpi-card cursor-pointer" t-on-click="clickLowStock">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <span class="text-muted small fw-semibold">Low Stock Products</span>
                                    <h3 class="fw-bold mt-2 mb-1" t-out="formatNumber(state.data.kpis.low_stock.value)"></h3>
                                    <div class="d-flex align-items-center gap-1">
                                        <span class="small fw-semibold" t-att-class="state.data.kpis.low_stock.trend &lt;= 0 ? 'text-success' : 'text-danger'">
                                            <i t-att-class="state.data.kpis.low_stock.trend &lt;= 0 ? 'fa fa-arrow-down' : 'fa fa-arrow-up'"></i>
                                            <t t-out="Math.abs(state.data.kpis.low_stock.trend)"/>%
                                        </span>
                                        <span class="text-muted small">vs Last Month</span>
                                    </div>
                                </div>
                                <div class="kpi-icon-bg bg-danger-light rounded-3 p-2 text-danger">
                                    <i class="fa fa-warning fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-sm-6 col-md-4 col-lg">
                        <div class="card h-100 border-0 shadow-sm rounded-3 p-3 kpi-card">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <span class="text-muted small fw-semibold">In / Out (This Month)</span>
                                    <div class="mt-2 mb-1">
                                        <div class="d-flex gap-2">
                                            <span class="fw-bold text-success small">In: </span>
                                            <span class="fw-bold text-dark small" t-out="formatNumber(state.data.kpis.in_out.in)"></span>
                                        </div>
                                        <div class="d-flex gap-2">
                                            <span class="fw-bold text-danger small">Out: </span>
                                            <span class="fw-bold text-dark small" t-out="formatNumber(state.data.kpis.in_out.out)"></span>
                                        </div>
                                    </div>
                                </div>
                                <div class="kpi-icon-bg bg-blue-light rounded-3 p-2 text-blue">
                                    <i class="fa fa-arrows-h fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-4">

                    <div class="col-12 col-lg-8">
                        <div class="card border-0 shadow-sm rounded-3 p-3 chart-card h-100">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <span class="fw-bold text-dark fs-5">Inventory Value Over Time</span>
                                <span class="badge bg-secondary-light text-secondary rounded-pill px-3 py-2 text-capitalize" t-out="state.active_filter.replace('_', ' ')"></span>
                            </div>
                            <div class="chart-container" style="position: relative; height: 300px;">
                                <canvas t-ref="lineChart"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-lg-4">
                        <div class="card border-0 shadow-sm rounded-3 p-3 chart-card h-100 d-flex flex-column">
                            <div class="mb-3 flex-shrink-0">
                                <span class="fw-bold text-dark fs-5">Inventory by Product Category</span>
                            </div>
                            <div class="d-flex flex-row align-items-center justify-content-between gap-2 w-100 flex-grow-1">
                                <div class="chart-container doughnut-wrapper flex-shrink-0" style="position: relative; height: 180px; width: 180px;">
                                    <canvas t-ref="donutChart"></canvas>
                                    <div class="doughnut-center text-center">
                                        <span class="text-muted d-block" style="font-size: 0.7rem;">Total Value</span>
                                        <span class="fw-bold text-dark" style="font-size: 0.9rem;" t-out="formattedTotalValue"></span>
                                    </div>
                                </div>

                                <div class="flex-grow-1 overflow-auto" style="max-height: 200px;">
                                    <div class="d-flex flex-column gap-2">
                                        <t t-foreach="categoryBreakdown" t-as="cat" t-key="cat.id">
                                            <div class="d-flex align-items-center justify-content-between gap-1 small cursor-pointer legend-row py-1 px-2" t-on-click="() => this.openCategoryProducts(cat.id, cat.name)">
                                                <div class="d-flex align-items-center gap-2 text-truncate" style="font-size: 0.72rem;">
                                                    <span class="legend-dot rounded-circle" t-attf-style="background-color: #{cat.color};"></span>
                                                    <span class="text-dark text-truncate fw-semibold" t-out="cat.name"></span>
                                                </div>
                                                <span class="fw-bold text-muted flex-shrink-0" style="font-size: 0.72rem;">
                                                    <t t-out="cat.formatted_value"/> (<t t-out="cat.percentage"/>%)
                                                </span>
                                            </div>
                                        </t>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-4">

                    <div class="col-12 col-lg-4">
                        <div class="card border-0 shadow-sm rounded-3 p-3 table-card h-100">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <span class="fw-bold text-dark fs-5">Top 5 Products by Value</span>
                            </div>
                            <div class="table-responsive flex-grow-1">
                                <table class="table table-hover align-middle mb-0">
                                    <thead class="table-light">
                                        <tr class="small text-muted text-uppercase">
                                            <th style="width: 50%;">Product</th>
                                            <th class="text-end" style="width: 25%;">On Hand</th>
                                            <th class="text-end" style="width: 25%;">Value</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <t t-foreach="state.data.top_products" t-as="p" t-key="p.id">
                                            <tr>
                                                <td class="cursor-pointer" t-on-click="() => this.openProductForm(p.id)">
                                                    <div class="d-flex align-items-center gap-2">
                                                        <img t-attf-src="/web/image/product.template/#{p.tmpl_id}/image_128" class="rounded border p-1" style="width: 32px; height: 32px; object-fit: cover;" onerror="this.src='/web/static/img/placeholder.png'"/>
                                                        <span class="fw-semibold text-dark text-truncate d-block" style="max-width: 240px;" t-out="p.name"></span>
                                                    </div>
                                                </td>
                                                <td class="text-end fw-semibold text-muted" t-out="formatNumber(p.qty_on_hand)"></td>
                                                <td class="text-end fw-bold text-dark" t-out="formatCurrency(p.value)"></td>
                                            </tr>
                                        </t>
                                    </tbody>
                                </table>
                            </div>
                            <div class="text-start mt-3 pt-2 border-top">
                                <button class="btn btn-link btn-sm text-primary p-0 d-flex align-items-center gap-1 fw-bold text-decoration-none" t-on-click="viewProducts">
                                    View all products <i class="fa fa-arrow-right"></i>
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-lg-4">
                        <div class="card border-0 shadow-sm rounded-3 p-3 table-card h-100">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <span class="fw-bold text-dark fs-5">Stock by Location</span>
                            </div>
                            <div class="table-responsive flex-grow-1">
                                <table class="table table-hover align-middle mb-0">
                                    <thead class="table-light">
                                        <tr class="small text-muted text-uppercase">
                                            <th style="width: 45%;">Location</th>
                                            <th class="text-end" style="width: 25%;">Quantity</th>
                                            <th class="text-end" style="width: 30%;">Value</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <t t-foreach="state.data.locations" t-as="loc" t-key="loc.id">
                                            <tr>
                                                <td class="cursor-pointer" t-on-click="() => this.openLocationQuants(loc.id, loc.name)">
                                                    <span class="fw-semibold text-dark text-truncate d-block" style="max-width: 200px;" t-out="loc.name"></span>
                                                </td>
                                                <td class="text-end fw-semibold text-muted" t-out="formatNumber(loc.qty)"></td>
                                                <td class="text-end fw-bold text-dark">
                                                    <span t-out="formatCurrency(loc.value)"></span>

                                                    <div class="progress mt-1" style="height: 4px;">
                                                        <div class="progress-bar bg-purple" role="progressbar" t-attf-style="width: #{(loc.value / (state.data.kpis.total_value.value || 1.0)) * 100}%;"></div>
                                                    </div>
                                                </td>
                                            </tr>
                                        </t>
                                    </tbody>
                                </table>
                            </div>
                            <div class="text-start mt-3 pt-2 border-top">
                                <button class="btn btn-link btn-sm text-primary p-0 d-flex align-items-center gap-1 fw-bold text-decoration-none" t-on-click="viewLocations">
                                    View all locations <i class="fa fa-arrow-right"></i>
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="col-12 col-lg-4">
                        <div class="card border-0 shadow-sm rounded-3 p-3 table-card h-100 d-flex flex-column">
                            <div class="mb-3">
                                <span class="fw-bold text-dark fs-5">In / Out (This Month)</span>
                            </div>

                            <div class="row g-2 mb-3">
                                <div class="col-6">
                                    <div class="p-2 border rounded bg-light cursor-pointer shadow-hover" t-on-click="clickIncomingMoves">
                                        <span class="text-muted small fw-semibold d-block">Incoming (In)</span>
                                        <span class="fw-bold text-success fs-5" t-out="formatNumber(state.data.kpis.in_out.in)"></span>
                                        <div class="text-muted small">
                                            vs LM <span t-att-class="state.data.kpis.in_out.in_trend >= 0 ? 'text-success' : 'text-danger'"><i t-att-class="state.data.kpis.in_out.in_trend >= 0 ? 'fa fa-arrow-up' : 'fa fa-arrow-down'"></i> <t t-out="Math.abs(state.data.kpis.in_out.in_trend)"/>%</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded bg-light cursor-pointer shadow-hover" t-on-click="clickOutgoingMoves">
                                        <span class="text-muted small fw-semibold d-block">Outgoing (Out)</span>
                                        <span class="fw-bold text-danger fs-5" t-out="formatNumber(state.data.kpis.in_out.out)"></span>
                                        <div class="text-muted small">
                                            vs LM <span t-att-class="state.data.kpis.in_out.out_trend >= 0 ? 'text-danger' : 'text-success'"><i t-att-class="state.data.kpis.in_out.out_trend >= 0 ? 'fa fa-arrow-down' : 'fa fa-arrow-up'"></i> <t t-out="Math.abs(state.data.kpis.in_out.out_trend)"/>%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <span class="fw-bold text-dark small text-uppercase mb-2 d-block">Top 5 Product Moves</span>

                            <div class="table-responsive flex-grow-1">
                                <table class="table table-hover align-middle mb-0">
                                    <thead class="table-light">
                                        <tr class="small text-muted text-uppercase">
                                            <th style="width: 40%;">Product</th>
                                            <th class="text-end" style="width: 20%;">In</th>
                                            <th class="text-end" style="width: 20%;">Out</th>
                                            <th class="text-end" style="width: 20%;">Net</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <t t-foreach="state.data.product_moves" t-as="pm" t-key="pm.id">
                                            <tr>
                                                <td class="cursor-pointer" t-on-click="() => this.openProductMoves(pm.id, pm.name)">
                                                    <span class="fw-semibold text-dark text-truncate d-block" style="max-width: 180px;" t-out="pm.name"></span>
                                                </td>
                                                <td class="text-end fw-semibold text-success" t-out="formatNumber(pm.in)"></td>
                                                <td class="text-end fw-semibold text-danger" t-out="formatNumber(pm.out)"></td>
                                                <td class="text-end fw-bold" t-att-class="pm.net >= 0 ? 'text-success' : 'text-danger'" t-out="formatNumber(pm.net)"></td>
                                            </tr>
                                        </t>
                                    </tbody>
                                </table>
                            </div>

                            <div class="text-start mt-3 pt-2 border-top">
                                <button class="btn btn-link btn-sm text-primary p-0 d-flex align-items-center gap-1 fw-bold text-decoration-none" t-on-click="viewMoves">
                                    View detailed moves <i class="fa fa-arrow-right"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
`;
    static props = ["*"];

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

        onMounted(() => {
            if (window.l4eDashboardTheme) {
                this._themeCleanup = window.l4eDashboardTheme.subscribe(() => {
                    if (this.state.data) {
                        this.renderLineChart();
                        this.renderDonutChart();
                    }
                });
            }
        });

        onWillUnmount(() => {
            if (this.lineChart) this.lineChart.destroy();
            if (this.donutChart) this.donutChart.destroy();
            if (this._themeCleanup) this._themeCleanup();
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

    onDateFromChange(ev) {
        this.changeFilter('custom');
        const val = ev.target.value || '';
        this.state.date_from = val;
        if (val && this.state.date_to && val > this.state.date_to) {
            this.state.date_to = val;
        }
    }

    onDateToChange(ev) {
        this.changeFilter('custom');
        const val = ev.target.value || '';
        this.state.date_to = val;
        if (val && this.state.date_from && val < this.state.date_from) {
            this.state.date_from = val;
        }
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

    getChartTheme() {
        const isDark = Boolean(window.l4eDashboardTheme && window.l4eDashboardTheme.isDark());
        return {
            axis: isDark ? '#cbd5e1' : '#6c757d',
            grid: isDark ? '#334155' : '#e9ecef',
            pointBorder: isDark ? '#0f172a' : '#fff',
            tooltipBg: isDark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(33, 37, 41, 0.95)',
            donutBorder: isDark ? '#1e293b' : '#fff',
        };
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
        const theme = this.getChartTheme();

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
                    pointBorderColor: theme.pointBorder,
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
                        backgroundColor: theme.tooltipBg,
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
                    yAxes: [{
                        ticks: {
                            beginAtZero: true,
                            min: 0,
                            fontColor: theme.axis,
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
                        },
                        gridLines: { color: theme.grid }
                    }],
                    xAxes: [{
                        gridLines: { display: false },
                        ticks: { fontColor: theme.axis }
                    }],
                    x: {
                        grid: { display: false },
                        ticks: { color: theme.axis }
                    },
                    y: {
                        beginAtZero: true,
                        min: 0,
                        grid: { color: theme.grid },
                        ticks: {
                            color: theme.axis,
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
        const theme = this.getChartTheme();

        this.donutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: colors.slice(0, dataValues.length),
                    borderWidth: 2,
                    borderColor: theme.donutBorder,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                onHover: (evt, activeElements) => {
                    const target = evt?.native?.target || evt?.target || (evt?.chart && evt.chart.canvas);
                    if (target && target.style) {
                        target.style.cursor = (activeElements && activeElements.length) ? 'pointer' : 'default';
                    }
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
                        backgroundColor: theme.tooltipBg,
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
        return {
            symbol: this.state.data?.currency_symbol || '$',
            position: this.state.data?.currency_position || 'before',
            id: this.state.data?.currency_id
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

