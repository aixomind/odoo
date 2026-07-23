/** @odoo-module **/
import { registry }    from "@web/core/registry";
import { useService }  from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class SaleDashboardAction extends Component {
    static template = "l4e_dashboard_collection.SaleDashboardAction";
    static props    = ["*"];

    setup() {
        this.orm          = useService("orm");
        this.actionSvc    = useService("action");
        this.notification = useService("notification");

        const today         = new Date();
        this.currentYear    = today.getFullYear();
        this.availableYears = [
            this.currentYear,
            this.currentYear - 1,
            this.currentYear - 2,
            this.currentYear - 3,
        ];

        this.state = useState({
            cards:      [],
            loading:    true,
            fromDate:   '',
            toDate:     '',
            filterYear: null,
        });

        onWillStart(() => this._loadStats());
    }

    _effectiveDateFrom() {
        if (this.state.fromDate)   return this.state.fromDate;
        if (this.state.filterYear) return `${this.state.filterYear}-01-01`;
        return null;
    }

    _effectiveDateTo() {
        if (this.state.toDate)     return this.state.toDate;
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
                    date_from: this._effectiveDateFrom(),
                    date_to:   this._effectiveDateTo(),
                }
            );
            this.state.cards = result.cards || [];
        } catch (err) {
            console.error("SaleDashboard load error:", err);
            this.notification.add("Failed to load dashboard stats", { type: "warning" });
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectYear(year) {
        this.state.filterYear = (this.state.filterYear === year) ? null : year;
        this.state.fromDate   = '';
        this.state.toDate     = '';
        await this._loadStats();
    }

    async onFromDateChange(e) {
        this.state.fromDate   = e.target.value || '';
        this.state.filterYear = null;
        if ((this.state.fromDate && this.state.toDate) ||
            (!this.state.fromDate && !this.state.toDate)) {
            await this._loadStats();
        }
    }

    async onToDateChange(e) {
        this.state.toDate     = e.target.value || '';
        this.state.filterYear = null;
        if ((this.state.fromDate && this.state.toDate) ||
            (!this.state.fromDate && !this.state.toDate)) {
            await this._loadStats();
        }
    }

    async onClearDates() {
        this.state.fromDate   = '';
        this.state.toDate     = '';
        this.state.filterYear = null;
        await this._loadStats();
    }

    async onCardClick(statusKey) {
        try {
            const act = await this.orm.call(
                "sale.order",
                "action_open_sale_orders_by_status",
                [statusKey],
                {
                    date_from: this._effectiveDateFrom(),
                    date_to:   this._effectiveDateTo(),
                }
            );
            if (act) await this.actionSvc.doAction(act);
        } catch (err) {
            console.error("Navigation error:", err);
            this.notification.add("Failed to open records", { type: "danger" });
        }
    }

    get activeBadgeLabel() {
        if (this.state.filterYear)
            return `Year: ${this.state.filterYear}`;
        if (this.state.fromDate && this.state.toDate)
            return `${this.state.fromDate}  →  ${this.state.toDate}`;
        return null;
    }
}

registry.category("actions").add(
    "l4e_dashboard_collection.sale_dashboard",
    SaleDashboardAction
);
export { SaleDashboardAction };

