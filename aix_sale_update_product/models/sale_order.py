# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_update_product_wizard(self):
        self.ensure_one()
        if self.state != 'sale':
            raise UserError(_("You can only update products on confirmed sales orders."))

        eligible_lines = self.order_line.filtered(
            lambda l: not l.display_type
            and l.product_id
            and l.qty_delivered <= 0
            and not any(m.state == 'done' for m in l.move_ids)
        )

        if not eligible_lines:
            raise UserError(_("No eligible undelivered lines found on this order. Products cannot be changed once delivered."))

        wizard_lines = []
        for line in eligible_lines:
            wizard_lines.append((0, 0, {
                'sale_line_id': line.id,
                'current_product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
            }))

        wizard = self.env['sale.order.update.product.wizard'].create({
            'order_id': self.id,
            'is_single_line': False,
            'line_ids': wizard_lines,
        })

        return {
            'name': _('Update Products on Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.update.product.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    state = fields.Selection(
        related='order_id.state',
        string='Order Status',
        readonly=True,
    )

    @api.depends('product_id', 'state', 'qty_invoiced', 'qty_delivered')
    def _compute_product_updatable(self):
        super()._compute_product_updatable()
        if self.env.context.get('allow_product_update'):
            for line in self:
                line.product_updatable = True

    def _get_protected_fields(self):
        res = super()._get_protected_fields()
        if self.env.context.get('allow_product_update'):
            return [f for f in res if f not in (
                'product_id', 'name', 'price_unit',
                'product_uom_id', 'product_uom', 'product_uom_qty',
                'tax_id', 'tax_ids', 'analytic_distribution', 'discount'
            )]
        return res

    def write(self, vals):
        if self.env.context.get('allow_product_update'):
            for line in self:
                self.env.cache.set(line, line._fields['product_updatable'], True)
        return super().write(vals)

    def action_open_update_product_wizard(self):
        self.ensure_one()
        if self.order_id.state != 'sale':
            raise UserError(_("You can only update products on confirmed sales orders."))

        if self.qty_delivered > 0:
            raise UserError(_("This line has already been delivered (%(qty)s delivered). Products cannot be changed once delivered.", qty=self.qty_delivered))

        done_moves = self.move_ids.filtered(lambda m: m.state == 'done')
        if done_moves:
            raise UserError(_("Stock moves for this line have already been completed. Product cannot be changed."))

        wizard = self.env['sale.order.update.product.wizard'].create({
            'order_id': self.order_id.id,
            'is_single_line': True,
            'sale_line_id': self.id,
            'current_product_id': self.product_id.id,
            'line_ids': [(0, 0, {
                'sale_line_id': self.id,
                'current_product_id': self.product_id.id,
                'product_uom_qty': self.product_uom_qty,
                'price_unit': self.price_unit,
            })],
        })

        return {
            'name': _('Update Product'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.update.product.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
