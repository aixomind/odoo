/** @odoo-module **/

import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup();
        this.useCustomTrackingCard = fields.Attr(false);
    },
});
