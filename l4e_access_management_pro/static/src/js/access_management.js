/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { SearchModel } from "@web/search/search_model";
import { Chatter } from "@mail/core/web/chatter";
import { useState } from "@odoo/owl";
import { session } from "@web/session";

function safePatch(target, patchName, extension) {
    if (!target) return;
    try {
        patch(target, extension);
    } catch (e) {
        try { patch(target, patchName, extension); } catch (e2) {
            console.warn("AMP: patch failed", e2);
        }
    }
}

// ─────────────────────────────────────────────────────────────────
//  Chatter Component Patch
//  Reads amp_chatter_rules from session SYNCHRONOUSLY at setup().
//  Sets ampState via useState() so OWL tracks it reactively.
//  XML template adds amp-* CSS classes to root div via t-att-class.
// ─────────────────────────────────────────────────────────────────
if (Chatter) {
    safePatch(Chatter.prototype, "amp_chatter_patch", {
        setup() {
            const model = this.props.threadModel ||
                          this.props.webRecord?.resModel || "";

            const allRules = session.amp_chatter_rules || {};
            const rules = allRules[model] || {};

            // Pre-declare all flags with useState so OWL tracks them reactively
            this.ampState = useState({
                hideChatter:          !!rules.hide_chatter,
                hideSendMessage:      !!rules.hide_send_message,
                hideLogNote:          !!rules.hide_log_note,
                hideScheduleActivity: !!rules.hide_schedule_activity,
                hideFollowers:        !!rules.hide_followers,
                hideAttachments:      !!rules.hide_attachments,
            });

            super.setup(...arguments);
        },
    });
}

// ─────────────────────────────────────────────────────────────────
//  FormController – export restriction
// ─────────────────────────────────────────────────────────────────
if (FormController) {
    safePatch(FormController.prototype, "amp_form_patch", {
        setup() {
            super.setup();
        },
        getStaticActionMenuItems() {
            const items = super.getStaticActionMenuItems?.() ?? {};
            if (session.disable_export) {
                for (const key in items) {
                    const desc = (items[key].description || "").toLowerCase();
                    if (key.includes("export") || desc.includes("export")) delete items[key];
                }
            }
            return items;
        },
        _getActionMenuItems(state) {
            const menus = super._getActionMenuItems?.(state) ?? null;
            if (session.disable_export && menus?.items?.other) {
                menus.items.other = menus.items.other.filter((item) => {
                    const desc = (item.description || "").toLowerCase();
                    const key  = (item.key || "").toLowerCase();
                    return key !== "export" && !desc.includes("export");
                });
            }
            return menus;
        },
    });
}

// ─────────────────────────────────────────────────────────────────
//  ListController – export restriction
// ─────────────────────────────────────────────────────────────────
if (ListController) {
    safePatch(ListController.prototype, "amp_list_patch", {
        setup() {
            super.setup();
        },
        getStaticActionMenuItems() {
            const items = super.getStaticActionMenuItems?.() ?? {};
            if (session.disable_export) {
                for (const key in items) {
                    const desc = (items[key].description || "").toLowerCase();
                    if (key.includes("export") || desc.includes("export")) delete items[key];
                }
            }
            return items;
        },
        _getActionMenuItems(state) {
            const menus = super._getActionMenuItems?.(state) ?? null;
            if (session.disable_export && menus?.items?.other) {
                menus.items.other = menus.items.other.filter((item) => {
                    const desc = (item.description || "").toLowerCase();
                    const key  = (item.key || "").toLowerCase();
                    return key !== "export" && !desc.includes("export");
                });
            }
            return menus;
        },
    });
}

// ─────────────────────────────────────────────────────────────────
//  SearchModel – custom filter/group restriction
// ─────────────────────────────────────────────────────────────────
function applySearchDropdownRestrictions() {
    const hideCF = document.body.classList.contains("o_hide_custom_filter");
    const hideCG = document.body.classList.contains("o_hide_custom_group");
    if (!hideCF && !hideCG) return;
    document.querySelectorAll(".o_dropdown_menu *, .o_popover *, .o_search_bar_menu *").forEach((el) => {
        if (!el.children.length && el.textContent) {
            const txt = el.textContent.trim().toLowerCase();
            if (hideCF && ["custom filter...", "custom filter", "add custom filter"].includes(txt)) {
                (el.closest(".o_menu_item, .dropdown-item, div, button") || el)
                    .style.setProperty("display", "none", "important");
            }
            if (hideCG && ["custom group", "add custom group"].includes(txt)) {
                (el.closest(".o_menu_item, .dropdown-item, div, button") || el)
                    .style.setProperty("display", "none", "important");
            }
        }
    });
}
document.addEventListener("click", () => {
    setTimeout(applySearchDropdownRestrictions, 50);
    setTimeout(applySearchDropdownRestrictions, 200);
}, true);

if (SearchModel) {
    safePatch(SearchModel.prototype, "amp_search_patch", {
        async load(config) {
            await super.load(config);
            try {
                const rpc = this.env?.services?.rpc?.bind(this.env.services);
                if (!rpc) return;
                const rules = await rpc("/access_management/get_model_rules", { model: this.resModel });
                if (!rules?.hidden_filters?.length) return;
                const hf = rules.hidden_filters.map((f) => f.trim().toLowerCase());
                document.body.classList.remove("o_hide_custom_filter", "o_hide_custom_group");
                if (hf.some((f) => ["custom filter", "custom filter...", "add custom filter"].includes(f)))
                    document.body.classList.add("o_hide_custom_filter");
                if (hf.some((f) => ["custom group", "add custom group"].includes(f)))
                    document.body.classList.add("o_hide_custom_group");
                if (this.searchItems) {
                    for (const key in this.searchItems) {
                        const item = this.searchItems[key];
                        const desc = (item.description || item.name || item.string || "").toLowerCase();
                        if (hf.some((h) => desc.includes(h) || h.includes(desc))) delete this.searchItems[key];
                    }
                }
                setTimeout(applySearchDropdownRestrictions, 100);
            } catch (e) {
                console.warn("AMP: SearchModel error", e);
            }
        },
    });
}
