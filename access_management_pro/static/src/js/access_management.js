/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { SearchModel } from "@web/search/search_model";
import { onWillStart, onMounted } from "@odoo/owl";
import { session } from "@web/session";

function safePatch(target, patchName, extension) {
    if (!target) return;
    try {
        patch(target, patchName, extension);
    } catch (e) {
        console.warn("Access Management Pro: Failed to patch target", patchName, e);
    }
}

function getRpcService(env) {
    if (env && env.services && env.services.rpc) {
        return env.services.rpc.bind(env.services);
    }
    return null;
}

function applyChatterRestrictionsToForm(formEl, rules) {
    if (!formEl || !rules) return;

    if (rules.hide_chatter) formEl.classList.add('o_hide_chatter');
    if (rules.hide_send_message) formEl.classList.add('o_hide_send_message');
    if (rules.hide_log_note) formEl.classList.add('o_hide_log_note');
    if (rules.hide_schedule_activity) formEl.classList.add('o_hide_schedule_activity');
    if (rules.hide_followers) formEl.classList.add('o_hide_followers');
    if (rules.hide_attachments) formEl.classList.add('o_hide_attachments');

    const chatterEl = formEl.querySelector('.o_ChatterTopbar, .o_Chatter, .o-mail-Chatter, .oe_chatter, .o_chatter, .o_form_sheet_bg + div, [class*="Chatter"]');
    
    if (rules.hide_chatter && chatterEl) {
        chatterEl.style.setProperty('display', 'none', 'important');
        return;
    }

    const scope = chatterEl || formEl;
    const allElements = scope.querySelectorAll('button, .btn, span, a, div, i');

    allElements.forEach(el => {
        const txt = (el.textContent || '').trim().toLowerCase();
        const cls = (el.className || '').toString().toLowerCase();
        const title = (el.getAttribute('title') || '').toLowerCase();

        if (rules.hide_send_message) {
            if (txt === 'send message' || cls.includes('sendmessage') || title.includes('send message') || title.includes('send_message')) {
                let target = el.closest('button, .btn') || el;
                target.style.setProperty('display', 'none', 'important');
            }
        }

        if (rules.hide_log_note) {
            if (txt === 'log note' || cls.includes('lognote') || title.includes('log note')) {
                let target = el.closest('button, .btn') || el;
                target.style.setProperty('display', 'none', 'important');
            }
        }

        if (rules.hide_schedule_activity) {
            if (txt === 'activities' || txt === 'activity' || txt === 'schedule activity' || cls.includes('scheduleactivity') || cls.includes('activity') || title.includes('activity') || title.includes('schedule an activity')) {
                let target = el.closest('button, .btn') || el;
                target.style.setProperty('display', 'none', 'important');
            }
        }

        if (rules.hide_followers) {
            if (cls.includes('follower') || title.includes('follower') || title.includes('followers') || cls.includes('fa-user')) {
                let target = el.closest('button, .btn, .o_ChatterTopbar_followerListMenu, .o_FollowerListMenu, div') || el;
                target.style.setProperty('display', 'none', 'important');
            }
        }

        if (rules.hide_attachments) {
            if (cls.includes('attachment') || title.includes('attachment') || title.includes('attachments') || cls.includes('fa-paperclip')) {
                let target = el.closest('button, .btn, div') || el;
                target.style.setProperty('display', 'none', 'important');
            }
        }
    });
}

if (FormController) {
    safePatch(FormController.prototype, "access_management_pro_form", {
        setup() {
            this._super(...arguments);
            onWillStart(async () => {
                try {
                    const model = this.props.resModel;
                    const rpcFetch = getRpcService(this.env);
                    if (model && rpcFetch) {
                        const rules = await rpcFetch('/access_management/get_model_rules', { model });
                        if (rules) {
                            this.chatterAccessRules = rules;
                        }
                    }
                } catch (e) {
                    console.warn("Access Management Pro: Failed to fetch form chatter rules", e);
                }
            });

            onMounted(() => {
                const targetEl = this.el || (this.root && this.root.el) || document.querySelector('.o_form_view');
                if (this.chatterAccessRules && targetEl) {
                    applyChatterRestrictionsToForm(targetEl, this.chatterAccessRules);
                    const observer = new MutationObserver(() => {
                        applyChatterRestrictionsToForm(targetEl, this.chatterAccessRules);
                    });
                    observer.observe(targetEl, { childList: true, subtree: true });
                }
            });
        },

        getStaticActionMenuItems() {
            const items = this._super ? this._super(...arguments) : {};
            const isRestricted = session.disable_export || (this.chatterAccessRules && this.chatterAccessRules.disable_export);
            if (isRestricted && items) {
                for (const key in items) {
                    const desc = (items[key].description || '').toString().toLowerCase();
                    if (key.includes('export') || desc.includes('export')) {
                        delete items[key];
                    }
                }
            }
            return items;
        },

        _getActionMenuItems(state) {
            const actionMenus = this._super ? this._super(...arguments) : null;
            const isRestricted = session.disable_export || (this.chatterAccessRules && this.chatterAccessRules.disable_export);
            if (isRestricted && actionMenus && actionMenus.items && actionMenus.items.other) {
                actionMenus.items.other = actionMenus.items.other.filter(item => {
                    const desc = (item.description || '').toString().toLowerCase();
                    const key = (item.key || '').toString().toLowerCase();
                    return key !== 'export' && desc !== 'export' && !desc.includes('export');
                });
            }
            return actionMenus;
        }
    });
}

if (ListController) {
    safePatch(ListController.prototype, "access_management_pro_list", {
        setup() {
            this._super(...arguments);
            onWillStart(async () => {
                try {
                    const model = this.props.resModel;
                    const rpcFetch = getRpcService(this.env);
                    if (model && rpcFetch) {
                        const rules = await rpcFetch('/access_management/get_model_rules', { model });
                        if (rules) {
                            this.listAccessRules = rules;
                        }
                    }
                } catch (e) {
                    console.warn("Access Management Pro: Failed to fetch list access rules", e);
                }
            });
        },

        getStaticActionMenuItems() {
            const items = this._super ? this._super(...arguments) : {};
            const isRestricted = session.disable_export || (this.listAccessRules && this.listAccessRules.disable_export);
            if (isRestricted && items) {
                for (const key in items) {
                    const desc = (items[key].description || '').toString().toLowerCase();
                    if (key.includes('export') || desc.includes('export')) {
                        delete items[key];
                    }
                }
            }
            return items;
        },

        _getActionMenuItems(state) {
            const actionMenus = this._super ? this._super(...arguments) : null;
            const isRestricted = session.disable_export || (this.listAccessRules && this.listAccessRules.disable_export);
            if (isRestricted && actionMenus && actionMenus.items && actionMenus.items.other) {
                actionMenus.items.other = actionMenus.items.other.filter(item => {
                    const desc = (item.description || '').toString().toLowerCase();
                    const key = (item.key || '').toString().toLowerCase();
                    return key !== 'export' && desc !== 'export' && !desc.includes('export');
                });
            }
            return actionMenus;
        }
    });
}

function applySearchDropdownRestrictions() {
    const hideCustomFilter = document.body.classList.contains('o_hide_custom_filter');
    const hideCustomGroup = document.body.classList.contains('o_hide_custom_group');

    if (!hideCustomFilter && !hideCustomGroup) {
        return;
    }

    const dropdownItems = document.querySelectorAll('.o_dropdown_menu *, .o_popover *, .o_search_bar_menu *');
    dropdownItems.forEach(el => {
        if (el.children.length === 0 && el.textContent) {
            const txt = el.textContent.trim().toLowerCase();
            if (hideCustomFilter && (txt === 'custom filter...' || txt === 'custom filter' || txt === 'add custom filter')) {
                let target = el.closest('.o_menu_item, .dropdown-item, div, button') || el;
                target.style.setProperty('display', 'none', 'important');
            }
            if (hideCustomGroup && (txt === 'custom group' || txt === 'add custom group')) {
                let target = el.closest('.o_menu_item, .dropdown-item, div, button') || el;
                target.style.setProperty('display', 'none', 'important');
            }
        }
    });
}

document.addEventListener('click', () => {
    setTimeout(applySearchDropdownRestrictions, 50);
    setTimeout(applySearchDropdownRestrictions, 200);
}, true);

if (SearchModel) {
    safePatch(SearchModel.prototype, "access_management_pro_search", {
        async load(config) {
            if (this._super) {
                await this._super(...arguments);
            }
            try {
                const model = this.resModel;
                const rpcFetch = getRpcService(this.env);
                if (model && rpcFetch) {
                    const rules = await rpcFetch('/access_management/get_model_rules', { model });
                    if (rules && rules.hidden_filters && rules.hidden_filters.length > 0) {
                        const hfilters = rules.hidden_filters.map(f => f.trim().toLowerCase());
                        const customFilterKeywords = ['custom filter', 'custom filter...', 'custom_filter', 'add custom filter'];
                        const customGroupKeywords = ['custom group', 'custom_group', 'add custom group'];

                        document.body.classList.remove('o_hide_custom_filter', 'o_hide_custom_group');
                        if (hfilters.some(f => customFilterKeywords.includes(f))) {
                            document.body.classList.add('o_hide_custom_filter');
                        }
                        if (hfilters.some(f => customGroupKeywords.includes(f))) {
                            document.body.classList.add('o_hide_custom_group');
                        }

                        if (this.searchItems) {
                            for (const key in this.searchItems) {
                                const item = this.searchItems[key];
                                const desc = (item.description || item.name || item.string || '').toString().toLowerCase();
                                const name = (item.name || '').toString().toLowerCase();
                                if (hfilters.some(hf => desc.includes(hf) || hf.includes(desc) || name.includes(hf) || hf.includes(name))) {
                                    delete this.searchItems[key];
                                }
                            }
                        }

                        setTimeout(applySearchDropdownRestrictions, 100);
                    }
                }
            } catch (e) {
                console.warn("Access Management Pro: Error filtering SearchModel items", e);
            }
        }
    });
}
