from odoo import fields, models


class InventoryBackdateLog(models.Model):
    _name = 'inventory.backdate.log'
    _description = 'Inventory Adjustment Backdating History'
    _order = 'id desc'
    _rec_name = 'reference'

    reference = fields.Char(string='Reference', readonly=True, index=True)
    move_id = fields.Many2one(
        'stock.move', string='Stock Move', readonly=True, ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)

    old_date = fields.Datetime(string='Previous Date', readonly=True)
    new_date = fields.Datetime(string='New Date', readonly=True)
    old_accounting_date = fields.Date(string='Previous Accounting Date', readonly=True)
    new_accounting_date = fields.Date(string='New Accounting Date', readonly=True)

    account_move_ids = fields.Many2many(
        'account.move', string='Journal Entries', readonly=True)
    # Names are snapshotted as text so the history stays readable for users
    # without accounting access, and survives a deleted entry.
    account_move_names = fields.Char(string='Journal Entry Numbers', readonly=True)
    valuation_layer_count = fields.Integer(string='Valuation Layers', readonly=True)
    move_line_count = fields.Integer(string='Move Lines', readonly=True)
    analytic_line_count = fields.Integer(string='Analytic Lines', readonly=True)

    user_id = fields.Many2one(
        'res.users', string='Changed By', readonly=True,
        default=lambda self: self.env.user, index=True)
    apply_datetime = fields.Datetime(
        string='Applied On', readonly=True, default=fields.Datetime.now, index=True)
    note = fields.Text(string='Notes', readonly=True)
