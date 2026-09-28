from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class SaleOrderUpdateProductWizard(models.TransientModel):
    _name = 'sale.order.update.product.wizard'
    _description = 'Wizard to Update Product on Confirmed Sale Order'

    order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        readonly=True,
    )
    is_single_line = fields.Boolean(
        string='Single Line Mode',
        default=False,
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        readonly=True,
    )
    current_product_id = fields.Many2one(
        'product.product',
        string='Current Product',
        readonly=True,
    )
    new_product_id = fields.Many2one(
        'product.product',
        string='New Product',
        domain="[('sale_ok', '=', True)]",
    )
    line_ids = fields.One2many(
        'sale.order.update.product.wizard.line',
        'wizard_id',
        string='Order Lines',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'sale.order' and active_id:
            order = self.env['sale.order'].browse(active_id)
            res['order_id'] = order.id
            res['is_single_line'] = False
            lines = []
            for line in order.order_line.filtered(
                lambda l: not l.display_type
                and l.product_id
                and l.qty_delivered <= 0
                and not any(m.state == 'done' for m in l.move_ids)
            ):
                lines.append((0, 0, {
                    'sale_line_id': line.id,
                    'current_product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                }))
            res['line_ids'] = lines
        elif active_model == 'sale.order.line' and active_id:
            line = self.env['sale.order.line'].browse(active_id)
            res['order_id'] = line.order_id.id
            res['is_single_line'] = True
            res['sale_line_id'] = line.id
            res['current_product_id'] = line.product_id.id
            res['line_ids'] = [(0, 0, {
                'sale_line_id': line.id,
                'current_product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
            })]
        return res

    def _update_single_line(self, sale_line, new_product):
        """Update a single sale.order.line and all related stock moves and draft invoices."""
        if sale_line.order_id.state != 'sale':
            raise UserError(_("Order '%s' is not in confirmed sale state.", sale_line.order_id.name))

        if sale_line.qty_delivered > 0:
            raise UserError(_("Line with product '%(prod)s' is already delivered (%(qty)s units). Product cannot be modified.",
                              prod=sale_line.product_id.display_name, qty=sale_line.qty_delivered))

        # Check for done stock moves
        done_moves = sale_line.move_ids.filtered(lambda m: m.state == 'done')
        if done_moves:
            raise UserError(_("Stock moves for line '%(prod)s' are already marked as Done. Cannot change product.",
                              prod=sale_line.product_id.display_name))

        old_product = sale_line.product_id
        orig_price = sale_line.price_unit
        orig_qty = sale_line.product_uom_qty
        orig_discount = sale_line.discount

        # Handle tax field naming (tax_id in Odoo 17, tax_ids in Odoo 18+)
        tax_field = 'tax_id' if hasattr(sale_line, 'tax_id') else 'tax_ids'
        orig_taxes = getattr(sale_line, tax_field).ids

        # 1. Update Sale Order Line
        line_vals = {
            'product_id': new_product.id,
            'name': new_product.display_name,
            'price_unit': orig_price,
            'product_uom_qty': orig_qty,
            'discount': orig_discount,
            tax_field: [(6, 0, orig_taxes)],
        }
        uom_field = 'product_uom' if hasattr(sale_line, 'product_uom') else 'product_uom_id'
        current_uom = getattr(sale_line, uom_field, None)
        if current_uom and new_product.uom_id and current_uom.category_id != new_product.uom_id.category_id:
            line_vals[uom_field] = new_product.uom_id.id

        if hasattr(sale_line, 'product_template_id'):
            line_vals['product_template_id'] = new_product.product_tmpl_id.id

        sale_line.with_context(skip_price_recompute=True, allow_product_update=True, skip_procurement=True).write(line_vals)

        # Re-ensure price and qty were not changed by any automated constraint
        if float_compare(sale_line.price_unit, orig_price, precision_digits=2) != 0:
            sale_line.with_context(allow_product_update=True, skip_procurement=True).write({'price_unit': orig_price})
        if float_compare(sale_line.product_uom_qty, orig_qty, precision_digits=2) != 0:
            sale_line.with_context(allow_product_update=True, skip_procurement=True).write({'product_uom_qty': orig_qty})

        # 2. Update Open Stock Moves & Stock Move Lines
        open_moves = sale_line.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        # If duplicate open moves were previously spawned, clean up extras
        if len(open_moves) > 1:
            extras = open_moves[1:]
            extras._do_unreserve()
            extras._action_cancel()
            extras.sudo().unlink()
            open_moves = open_moves[:1]

        for move in open_moves:
            # Unreserve existing stock
            move._do_unreserve()

            # Update move lines (detailed operations)
            if move.move_line_ids:
                move_line_vals = {'product_id': new_product.id}
                if hasattr(move.move_line_ids, 'product_uom_id') and new_product.uom_id:
                    move_line_vals['product_uom_id'] = new_product.uom_id.id
                move.move_line_ids.write(move_line_vals)

            # Update move values
            move_vals = {
                'product_id': new_product.id,
                'description_picking': new_product.display_name,
            }
            if new_product.uom_id:
                if hasattr(move, 'product_uom'):
                    move_vals['product_uom'] = new_product.uom_id.id
                elif hasattr(move, 'product_uom_id'):
                    move_vals['product_uom_id'] = new_product.uom_id.id
            move.write(move_vals)

            # Reassign stock if transfer was in ready or waiting state
            if move.state in ('confirmed', 'assigned', 'waiting'):
                move._action_assign()

        # 3. Update Customer Invoices (Draft and Posted)
        for inv_line in sale_line.invoice_lines:
            inv_vals = {
                'product_id': new_product.id,
                'name': new_product.display_name,
            }
            if hasattr(inv_line, 'product_uom_id') and new_product.uom_id:
                inv_vals['product_uom_id'] = new_product.uom_id.id
            inv_line.with_context(check_move_validity=False).write(inv_vals)

        # 4. Post Chatter Note on Sale Order
        body = Markup(
            "<strong>%s</strong><br/>"
            "• <strong>%s</strong> %s<br/>"
            "• <strong>%s</strong> %s<br/>"
            "• <strong>%s</strong> %s (%s)<br/>"
            "• <strong>%s</strong> %s (%s)"
        ) % (
            _("Product Updated:"),
            _("Previous Product:"),
            escape(old_product.display_name),
            _("New Product:"),
            escape(new_product.display_name),
            _("Quantity:"),
            orig_qty,
            _("Unchanged"),
            _("Unit Price:"),
            orig_price,
            _("Unchanged"),
        )
        sale_line.order_id.message_post(body=body)

    def action_apply(self):
        self.ensure_one()
        updated_count = 0

        if self.is_single_line:
            if not self.new_product_id:
                raise UserError(_("Please select a New Product."))
            if self.new_product_id == self.current_product_id:
                raise UserError(_("The new product must be different from the current product."))
            if not self.sale_line_id:
                raise UserError(_("No sale order line associated with this wizard."))

            self._update_single_line(self.sale_line_id, self.new_product_id)
            updated_count += 1
        else:
            lines_to_update = self.line_ids.filtered(
                lambda l: l.new_product_id and l.new_product_id != l.current_product_id
            )
            if not lines_to_update:
                raise UserError(_("Please select a New Product for at least one line."))

            for w_line in lines_to_update:
                self._update_single_line(w_line.sale_line_id, w_line.new_product_id)
                updated_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Successfully updated %(count)s product line(s) on %(order)s.',
                             count=updated_count, order=self.order_id.name),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class SaleOrderUpdateProductWizardLine(models.TransientModel):
    _name = 'sale.order.update.product.wizard.line'
    _description = 'Line for Updating Product on Confirmed Sale Order'

    wizard_id = fields.Many2one(
        'sale.order.update.product.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Order Line',
        readonly=True,
    )
    current_product_id = fields.Many2one(
        'product.product',
        string='Current Product',
        readonly=True,
    )
    product_uom_qty = fields.Float(
        string='Quantity',
        readonly=True,
    )
    price_unit = fields.Float(
        string='Unit Price',
        readonly=True,
    )
    new_product_id = fields.Many2one(
        'product.product',
        string='New Product',
        domain="[('sale_ok', '=', True)]",
        help='Select the replacement product. Leave empty to keep the current product.',
    )
