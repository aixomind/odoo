/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class DynamicRecordSelector extends Component {
    static template = "l4e_universal_field_update.DynamicRecordSelector";
    static components = { AutoComplete };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({
            displayName: "",
        });
        this.loadDisplayName(this.props);
        onWillUpdateProps((nextProps) => {
            if (nextProps.record.data[nextProps.name] !== this.props.record.data[this.props.name]) {
                this.loadDisplayName(nextProps);
            }
        });
    }

    async loadDisplayName(props) {
        const value = props.record.data[props.name];
        const resModel = props.record.data[props.relationField || "relation_model"];
        if (value && resModel) {
            try {
                // In Odoo 18, we fetch the display name of the selected ID
                const res = await this.orm.read(resModel, [parseInt(value)], ["display_name"]);
                if (res && res.length) {
                    this.state.displayName = res[0].display_name;
                }
            } catch (err) {
                this.state.displayName = "ID: " + value;
            }
        } else {
            this.state.displayName = "";
        }
    }


    get relationModel() {
        return this.props.record.data[this.props.relationField || "relation_model"] || "";
    }

    get sources() {
        return [
            {
                placeholder: "Search...",
                options: (request) => this.loadOptions(request),
            },
        ];
    }

    async loadOptions(request) {
        const resModel = this.relationModel;
        if (!resModel) {
            return [];
        }

        try {
            const results = await this.orm.call(
                resModel,
                "name_search",
                [],
                {
                    name: request,
                    args: [],
                    operator: "ilike",
                    limit: 8,
                }
            );

            const options = results.map((r) => ({
                value: r[0],
                label: r[1],
                onSelect: () => {
                    this.props.record.update({
                        [this.props.name]: String(r[0]),
                    });

                    this.state.displayName = r[1];
                },
            }));

            options.push({
                cssClass: "o_m2o_dropdown_option_search_more",
                label: _t("Search More..."),
                onSelect: () => this.onSearchMore(request),
            });

            return options;
        } catch (e) {
            console.error("name_search Error:", e);
            return [];
        }
    }

    async onSearchMore(request) {
        const resModel = this.relationModel;

        if (!resModel) {
            return;
        }

        const ids = await this.orm.call(
            resModel,
            "name_search",
            [],
            {
                name: request,
                args: [],
                operator: "ilike",
                limit: 320,
            }
        );

        this.dialog.add(SelectCreateDialog, {
            title: _t("Search"),
            resModel: resModel,
            domain: [["id", "in", ids.map((x) => x[0])]],
            context: {},
            noCreate: true,
            onSelected: async (resId) => {
                const ids = Array.isArray(resId) ? resId : [resId];
                if (!ids.length) {
                    return;
                }
                const record = await this.orm.read(
                    resModel,
                    ids,
                    ["display_name"]
                );
                if (record.length) {
                    this.props.record.update({
                        [this.props.name]: String(record[0].id),
                    });
                    this.state.displayName = record[0].display_name;
                }
            },
        });
    }


    onInputChange(value) {
        if (!value) {
            this.props.record.update({ [this.props.name]: false });
            this.state.displayName = "";
        }
    }

    onSelectOption(option) {
        if (option && option.onSelect) {
            option.onSelect();
        }
    }
}

registry.category("fields").add("dynamic_record_selector", {
    component: DynamicRecordSelector,
    supportedTypes: ["char"],
    extractProps: ({ options }) => ({
        relationField: (options && options.relation_field) || "relation_model",
    }),
});