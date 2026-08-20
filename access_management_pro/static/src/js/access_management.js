/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { SearchModel } from "@web/search/search_model";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useState } from "@odoo/owl";
import { session } from "@web/session";

function safePatch(target, extension) {
    if (!target) return;
    try {
        patch(target, extension);
    } catch (e) {
        console.warn("Access Management Pro: patch failed", e);
    }
}

// ─────────────────────────────────────────────────────────────────
//  Chatter Component Patch
//  Reads amp_chatter_rules from session (injected by ir_http.py)
//  SYNCHRONOUSLY — no async RPC, no timing issues.
// ─────────────────────────────────────────────────────────────────
if (Chatter) {
    safePatch(Chatter.prototype, {
        setup() {
            // Get model from props (available synchronously at setup time)
            const model = this.props.threadModel ||
                          this.props.webRecord?.resModel ||
                          "";

            // Read rules from session (synchronous, set at login by ir_http.py)
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
//  FormController – export menu restriction
// ─────────────────────────────────────────────────────────────────
if (FormController) {
    safePatch(FormController.prototype, {
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
//  ListController – export menu restriction
// ─────────────────────────────────────────────────────────────────
if (ListController) {
    safePatch(ListController.prototype, {
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
    safePatch(SearchModel.prototype, {
        async load(config) {
            await super.load(config);
            try {
                const allRules = session.amp_chatter_rules || {};
                // Use hidden_filters from session if available, else skip
                // (search filter restrictions still use RPC for now)
            } catch (e) {
                console.warn("Access Management Pro: SearchModel error", e);
            }
        },
    });
}
