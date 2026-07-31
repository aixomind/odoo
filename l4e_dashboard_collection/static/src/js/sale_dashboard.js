/** @odoo-module **/
import { registry }    from "@web/core/registry";
import { useService }  from "@web/core/utils/hooks";
import { Component, onWillStart, useState , xml } from "@odoo/owl";

export class SaleDashboardAction extends Component {
    static template = xml`
<div class="o_sdash_page">

    <div class="o_sdash_hero">
        <div class="o_sdash_hero_left">
            <div class="o_sdash_hero_icon"><i class="fa fa-bar-chart"/></div>
            <div>
                <div class="o_sdash_hero_title">Sales Dashboard</div>
                <div class="o_sdash_hero_sub">Overview of your sales pipeline &amp; invoice status</div>
            </div>
        </div>

        <div class="o_sdash_hero_filters">

            <div class="o_sdash_year_row">
                <t t-foreach="availableYears" t-as="yr" t-key="yr">
                    <button class="o_sdash_chip"
                            t-att-class="{ active: state.filterYear === yr }"
                            t-on-click="() => this.onSelectYear(yr)">
                        <t t-out="yr"/>
                    </button>
                </t>
            </div>

            <div class="o_sdash_daterange">
                <i class="fa fa-calendar o_sdash_dr_icon"/>
                <input type="date"
                       class="o_sdash_date_input"
                       t-att-value="state.fromDate"
                       t-on-change="(e) => this.onFromDateChange(e)"
                       title="From date"/>
                <span class="o_sdash_dr_sep">→</span>
                <input type="date"
                       class="o_sdash_date_input"
                       t-att-value="state.toDate"
                       t-on-change="(e) => this.onToDateChange(e)"
                       title="To date"/>
                <t t-if="state.fromDate or state.toDate">
                    <button class="o_sdash_clear_btn" t-on-click="onClearDates" title="Clear dates">
                        <i class="fa fa-times"/>
                    </button>
                </t>
            </div>

        </div>
    </div>

    <t t-if="activeBadgeLabel">
        <div class="o_sdash_badge_bar">
            <span class="o_sdash_badge">
                <i class="fa fa-filter me-1"/>
                <t t-out="activeBadgeLabel"/>
                <button class="o_sdash_badge_clear" t-on-click="onClearDates" title="Clear">
                    <i class="fa fa-times"/>
                </button>
            </span>
        </div>
    </t>

    <div class="o_sdash_content">

        <div class="o_sdash_section_head">
            <span class="o_sdash_section_dot"/>
            Sale Orders
        </div>

        <t t-if="state.loading">
            <div class="o_sdash_loading">
                <i class="fa fa-spinner fa-spin me-2"/>Loading stats…
            </div>
        </t>

        <t t-else="">
            <div class="o_sdash_grid">
                <t t-foreach="state.cards" t-as="card" t-key="card.key">
                    <button class="o_sdash_card"
                            t-att-style="'--cc:' + card.color"
                            t-on-click="() => this.onCardClick(card.key)">

                        <div class="o_sdash_card_top">
                            <span class="o_sdash_card_icon_wrap">
                                <i t-attf-class="fa {{ card.icon }}"/>
                            </span>
                            <span class="o_sdash_card_label" t-out="card.label"/>
                        </div>

                        <div class="o_sdash_card_count">
                            <t t-out="card.count"/>
                            <span class="o_sdash_card_unit"> Orders</span>
                        </div>

                        <t t-if="card.amount_formatted">
                            <div class="o_sdash_card_amount" t-out="card.amount_formatted"/>
                        </t>

                        <div class="o_sdash_card_sub" t-out="card.sub_label"/>

                        <span class="o_sdash_card_arrow"><i class="fa fa-arrow-right"/></span>

                    </button>
                </t>
            </div>
        </t>

    </div>

</div>
`;
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

