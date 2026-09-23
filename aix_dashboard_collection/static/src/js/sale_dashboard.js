/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class SaleDashboardAction extends Component {
    static template = "l4e_dashboard_collection.SaleDashboardAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionSvc = useService("action");
        this.notification = useService("notification");

        const today = new Date();
        this.currentYear = today.getFullYear();
        this.availableYears = [
            this.currentYear,
            this.currentYear - 1,
            this.currentYear - 2,
            this.currentYear - 3,
        ];

        this.state = useState({
            cards: [],
            summary: {},
            monthlyRevenue: [],
            recentActivities: [],
            teams: [],
            users: [],
            loading: true,
            fromDate: "",
            toDate: "",
            filterYear: this.currentYear,
            teamId: "",
            userId: "",
        });

        onWillStart(() => this._loadStats());
    }

    _effectiveDateFrom() {
        if (this.state.fromDate) return this.state.fromDate;
        if (this.state.filterYear) return `${this.state.filterYear}-01-01`;
        return null;
    }

    _effectiveDateTo() {
        if (this.state.toDate) return this.state.toDate;
        if (this.state.filterYear) return `${this.state.filterYear}-12-31`;
        return null;
    }

    async _loadStats() {
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "sale.order",
                "get_sale_dashboard_stats",
                [],
                {
                    team_id: this.state.teamId || false,
                    user_id: this.state.userId || false,
                    date_from: this._effectiveDateFrom(),
                    date_to: this._effectiveDateTo(),
                }
            );
            this.state.cards = result.cards || [];
            this.state.summary = result.summary || {};
            this.state.monthlyRevenue = result.monthly_revenue || [];
            this.state.recentActivities = result.recent_activities || [];
            this.state.teams = result.teams || [];
            this.state.users = result.users || [];
        } catch (err) {
            console.error("SaleDashboard load error:", err);
            this.notification.add("Failed to load dashboard stats", { type: "warning" });
        } finally {
            this.state.loading = false;
        }
    }

    async onYearChange(ev) {
        const value = ev.target.value;
        this.state.filterYear = value ? parseInt(value, 10) : null;
        this.state.fromDate = "";
        this.state.toDate = "";
        await this._loadStats();
    }

    async onTeamChange(ev) {
        this.state.teamId = ev.target.value || "";
        await this._loadStats();
    }

    async onUserChange(ev) {
        this.state.userId = ev.target.value || "";
        await this._loadStats();
    }

    async onFromDateChange(ev) {
        const val = ev.target.value || "";
        this.state.fromDate = val;
        if (val && this.state.toDate && val > this.state.toDate) {
            this.state.toDate = val;
        }
        this.state.filterYear = null;
        if ((this.state.fromDate && this.state.toDate) || (!this.state.fromDate && !this.state.toDate)) {
            await this._loadStats();
        }
    }

    async onToDateChange(ev) {
        const val = ev.target.value || "";
        this.state.toDate = val;
        if (val && this.state.fromDate && val < this.state.fromDate) {
            this.state.fromDate = val;
        }
        this.state.filterYear = null;
        if ((this.state.fromDate && this.state.toDate) || (!this.state.fromDate && !this.state.toDate)) {
            await this._loadStats();
        }
    }

    async onClearDates() {
        this.state.fromDate = "";
        this.state.toDate = "";
        this.state.filterYear = this.currentYear;
        await this._loadStats();
    }

    async resetFilters() {
        this.state.fromDate = "";
        this.state.toDate = "";
        this.state.filterYear = this.currentYear;
        this.state.teamId = "";
        this.state.userId = "";
        await this._loadStats();
    }

    async onCardClick(statusKey) {
        try {
            const act = await this.orm.call(
                "sale.order",
                "action_open_sale_orders_by_status",
                [statusKey],
                {
                    team_id: this.state.teamId || false,
                    user_id: this.state.userId || false,
                    date_from: this._effectiveDateFrom(),
                    date_to: this._effectiveDateTo(),
                }
            );
            if (act) await this.actionSvc.doAction(act);
        } catch (err) {
            console.error("Navigation error:", err);
            this.notification.add("Failed to open records", { type: "danger" });
        }
    }

    async openSummaryMetric(metricKey) {
        const statusByMetric = {
            revenue: "total",
            avg: "total",
            conversion: "quotations",
            delivery: "fully_invoiced",
            outstanding: "to_invoice",
        };
        await this.onCardClick(statusByMetric[metricKey] || "total");
    }

    async openMonthlyPoint(point) {
        if (!point || !point.date_from || !point.date_to) return;
        try {
            const act = await this.orm.call(
                "sale.order",
                "action_open_sale_orders_by_status",
                ["total"],
                {
                    team_id: this.state.teamId || false,
                    user_id: this.state.userId || false,
                    date_from: point.date_from,
                    date_to: point.date_to,
                }
            );
            if (act) await this.actionSvc.doAction(act);
        } catch (err) {
            console.error("Monthly navigation error:", err);
            this.notification.add("Failed to open monthly records", { type: "danger" });
        }
    }

    openRecentActivity(activity) {
        if (!activity || !activity.id) return;
        this.actionSvc.doAction({
            type: "ir.actions.act_window",
            name: activity.title || "Sale Order",
            res_model: "sale.order",
            res_id: activity.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    _formatCompact(value) {
        const amount = Math.abs(value || 0);
        if (amount >= 1000000) return `$${(amount / 1000000).toFixed(0)}M`;
        if (amount >= 1000) return `$${(amount / 1000).toFixed(0)}K`;
        return `$${amount.toFixed(0)}`;
    }

    get primaryCards() {
        return this.state.cards.slice(0, 5);
    }

    get summaryMetrics() {
        const summary = this.state.summary || {};
        return [
            { key: "revenue", label: "Total Revenue", value: summary.total_revenue || "$0.00", icon: "fa-bar-chart", tone: "purple", trend: "18.6%" },
            { key: "avg", label: "Avg Order Value", value: summary.avg_order_value || "$0.00", icon: "fa-line-chart", tone: "green", trend: "12.4%" },
            { key: "conversion", label: "Conversion Rate", value: summary.conversion_rate || "0.0%", icon: "fa-briefcase", tone: "orange", trend: "4.2%" },
            { key: "delivery", label: "Avg Delivery Time", value: summary.avg_delivery_time || "0 Days", icon: "fa-calendar", tone: "pink", trend: "1.3%" },
            { key: "outstanding", label: "Outstanding", value: summary.outstanding || "$0.00", icon: "fa-database", tone: "blue", sub: `${summary.outstanding_orders || 0} Orders` },
        ];
    }

    get chartData() {
        return this.state.monthlyRevenue.length ? this.state.monthlyRevenue : [];
    }

    get chartPoints() {
        const data = this.chartData;
        if (!data.length) return [];
        const width = 760;
        const height = 260;
        const left = 58;
        const right = 18;
        const top = 22;
        const bottom = 36;
        const max = Math.max(...data.map((item) => item.value || 0), 1);
        const usableWidth = width - left - right;
        const usableHeight = height - top - bottom;
        return data.map((item, index) => {
            const x = left + (data.length === 1 ? usableWidth / 2 : (index * usableWidth) / (data.length - 1));
            const y = top + (1 - ((item.value || 0) / max)) * usableHeight;
            return { ...item, x, y };
        });
    }

    get chartPolyline() {
        return this.chartPoints.map((point) => `${point.x},${point.y}`).join(" ");
    }

    get chartAreaPath() {
        const points = this.chartPoints;
        if (!points.length) return "";
        const baseY = 224;
        return `M ${points[0].x} ${baseY} L ${points.map((point) => `${point.x} ${point.y}`).join(" L ")} L ${points[points.length - 1].x} ${baseY} Z`;
    }

    get chartYTicks() {
        const max = Math.max(...this.chartData.map((item) => item.value || 0), 1);
        return [0, 1, 2, 3, 4].map((index) => {
            const ratio = index / 4;
            return {
                y: 22 + ratio * 202,
                label: this._formatCompact(max * (1 - ratio)),
            };
        });
    }

    get activeBadgeLabel() {
        if (this.state.filterYear) return `Year: ${this.state.filterYear}`;
        if (this.state.fromDate && this.state.toDate) return `${this.state.fromDate} to ${this.state.toDate}`;
        return "All Periods";
    }

    getCardClass(card) {
        return `o_sdash_order_card tone-${card.key}`;
    }

    getActivityClass(activity) {
        return `o_sdash_activity_icon tone-${activity.tone || "blue"}`;
    }
}

registry.category("actions").add(
    "l4e_dashboard_collection.sale_dashboard",
    SaleDashboardAction
);
export { SaleDashboardAction };
