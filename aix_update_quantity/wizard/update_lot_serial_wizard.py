# -*- coding: utf-8 -*-
import base64
import csv
import io
from collections import Counter
from markupsafe import Markup
import openpyxl
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class L4eUpdateLotSerialWizard(models.TransientModel):
    _name = 'l4e.update.lot.serial.wizard'
    _description = 'Wizard to Update Lot and Serial Numbers for Existing Inventory'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
    ], string='Tracking Type', default='serial', required=True)
    uom_id = fields.Many2one(
        'uom.uom',
        related='product_id.uom_id',
        readonly=True,
        string='Unit of Measure',
    )
    available_location_ids = fields.Many2many(
        'stock.location',
        string='Available Locations',
        compute='_compute_available_locations',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('id', 'in', available_location_ids)]",
        help="Select a location to filter stock, or leave empty to view across warehouse stock.",
    )
    available_source_lot_ids = fields.Many2many(
        'stock.lot',
        string='Available Source Lots',
        compute='_compute_available_source_lots',
    )
    source_lot_id = fields.Many2one(
        'stock.lot',
        string='Convert From (Source Lot)',
        domain="[('id', 'in', available_source_lot_ids)]",
        help="Select an existing Lot to convert into Serial Numbers, or leave empty to update untracked stock.",
    )
    existing_qty = fields.Float(
        string='Available On Hand',
        compute='_compute_quantities',
        digits='Product Unit',
    )
    assigned_qty = fields.Float(
        string='Assigned Quantity',
        compute='_compute_quantities',
        digits='Product Unit',
    )
    remaining_qty = fields.Float(
        string='Remaining Quantity',
        compute='_compute_quantities',
        digits='Product Unit',
    )
    first_lot_name = fields.Char(
        string='First Lot / Serial Number',
        help='Starting lot or serial number for bulk generation.',
    )
    lot_count = fields.Integer(
        string='Number of Serials',
        default=1,
        help='Number of serial numbers to generate automatically.',
    )
    line_ids = fields.One2many(
        'l4e.update.lot.serial.line',
        'wizard_id',
        string='Lot / Serial Lines',
    )
    import_file = fields.Binary(
        string='Import Excel/CSV File',
        help='Upload an Excel (.xlsx, .xls) or CSV file with lot/serial numbers.',
    )
    import_filename = fields.Char(
        string='Import Filename',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        product_id = res.get('product_id') or self.env.context.get('default_product_id')
        tmpl_id = res.get('product_tmpl_id') or self.env.context.get('default_product_tmpl_id')

        if not product_id and tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)
            if tmpl.product_variant_count == 1:
                product_id = tmpl.product_variant_id.id
                res['product_id'] = product_id
            elif tmpl.product_variant_ids:
                for variant in tmpl.product_variant_ids:
                    if variant.untracked_qty > 0 or variant.qty_available > 0:
                        product_id = variant.id
                        res['product_id'] = product_id
                        break
                if not product_id:
                    product_id = tmpl.product_variant_ids[0].id
                    res['product_id'] = product_id

        if product_id:
            product = self.env['product.product'].browse(product_id)
            domain_quant_loc = product._get_domain_locations()[0]

            res['source_lot_id'] = False

            if product.tracking in ('serial', 'lot'):
                res['tracking'] = product.tracking
            else:
                res['tracking'] = 'serial'

            if product.tracking == 'serial':
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('quantity', '>', 0),
                ] + domain_quant_loc)
            else:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('lot_id', '=', False),
                    ('quantity', '>', 0),
                ] + domain_quant_loc)

            locations = quants.mapped('location_id')
            if locations:
                res['location_id'] = locations[0].id

            total_qty = sum(quants.mapped('quantity'))
            res['lot_count'] = int(total_qty) if total_qty > 0 else 1

            if hasattr(product, 'next_serial') and product.next_serial:
                res['first_lot_name'] = product.next_serial
            elif hasattr(product, 'serial_prefix_format') and product.serial_prefix_format:
                res['first_lot_name'] = product.serial_prefix_format

        return res

    @api.onchange('tracking')
    def _onchange_tracking(self):
        if self.tracking == 'serial':
            for line in self.line_ids:
                line.quantity = 1.0

    @api.depends('product_id', 'source_lot_id', 'tracking')
    def _compute_available_locations(self):
        for wizard in self:
            if not wizard.product_id:
                wizard.available_location_ids = False
                continue
            domain_quant_loc = wizard.product_id._get_domain_locations()[0]
            domain = [
                ('product_id', '=', wizard.product_id.id),
                ('quantity', '>', 0),
            ] + domain_quant_loc

            if wizard.source_lot_id:
                domain.append(('lot_id', '=', wizard.source_lot_id.id))
            elif wizard.product_id.tracking == 'none':
                domain.append(('lot_id', '=', False))

            quants = self.env['stock.quant'].search(domain)
            wizard.available_location_ids = quants.mapped('location_id')

    @api.depends('product_id')
    def _compute_available_source_lots(self):
        for wizard in self:
            if not wizard.product_id:
                wizard.available_source_lot_ids = False
                continue
            domain_quant_loc = wizard.product_id._get_domain_locations()[0]
            lot_quants = self.env['stock.quant'].search([
                ('product_id', '=', wizard.product_id.id),
                ('lot_id', '!=', False),
                ('quantity', '>', 0),
            ] + domain_quant_loc)
            wizard.available_source_lot_ids = lot_quants.mapped('lot_id')

    @api.depends('product_id', 'location_id', 'source_lot_id', 'tracking', 'line_ids.quantity')
    def _compute_quantities(self):
        for wizard in self:
            if not wizard.product_id:
                wizard.existing_qty = 0.0
                wizard.assigned_qty = 0.0
                wizard.remaining_qty = 0.0
                continue

            domain_quant_loc = wizard.product_id._get_domain_locations()[0]
            quant_domain = [
                ('product_id', '=', wizard.product_id.id),
                ('quantity', '>', 0),
            ] + domain_quant_loc

            if wizard.source_lot_id:
                quant_domain.append(('lot_id', '=', wizard.source_lot_id.id))
            elif wizard.product_id.tracking == 'none':
                quant_domain.append(('lot_id', '=', False))

            if wizard.location_id:
                quant_domain.append(('location_id', '=', wizard.location_id.id))

            quants = self.env['stock.quant'].search(quant_domain)
            wizard.existing_qty = sum(quants.mapped('quantity'))
            wizard.assigned_qty = sum(wizard.line_ids.mapped('quantity'))
            wizard.remaining_qty = max(0.0, wizard.existing_qty - wizard.assigned_qty)

    @api.onchange('source_lot_id')
    def _onchange_source_lot_id(self):
        self.line_ids = False
        domain_quant_loc = self.product_id._get_domain_locations()[0]
        quant_domain = [
            ('product_id', '=', self.product_id.id),
            ('quantity', '>', 0),
        ] + domain_quant_loc

        if self.source_lot_id:
            quant_domain.append(('lot_id', '=', self.source_lot_id.id))
        elif self.product_id.tracking == 'none':
            quant_domain.append(('lot_id', '=', False))

        quants = self.env['stock.quant'].search(quant_domain)
        locations = quants.mapped('location_id')
        self.location_id = locations[0] if locations else False
        total = sum(quants.mapped('quantity'))
        self.lot_count = int(total) if total > 0 else 1

    def action_generate_serials(self):
        self.ensure_one()
        if not self.first_lot_name:
            raise UserError(_("Please provide a starting First Lot / Serial Number."))

        count = self.lot_count or int(self.remaining_qty or self.existing_qty)
        if count <= 0:
            raise UserError(_("The number of serial numbers to generate must be greater than zero."))

        target_location = self.location_id or (self.available_location_ids and self.available_location_ids[0])
        if not target_location:
            raise UserError(_("No warehouse location with available stock found for product '%s'.", self.product_id.display_name))

        lot_names = self.env['stock.lot'].generate_lot_names(self.first_lot_name, count)

        new_lines = []
        for item in lot_names:
            lot_name_val = item.get('lot_name') if isinstance(item, dict) else (item.lot_name if hasattr(item, 'lot_name') else str(item))
            new_lines.append((0, 0, {
                'location_id': target_location.id,
                'lot_name': lot_name_val,
                'quantity': 1.0,
            }))

        self.line_ids = [(5, 0, 0)] + new_lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l4e.update.lot.serial.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import_file(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Please upload an Excel (.xlsx) or CSV file first."))

        data = base64.b64decode(self.import_file)
        filename = (self.import_filename or '').lower()
        extracted_rows = []

        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            try:
                wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
                sheet = wb.active
                raw_rows = list(sheet.iter_rows(values_only=True))
                wb.close()
            except Exception as e:
                raise UserError(_("Error reading Excel file: %s", str(e)))

            if not raw_rows:
                raise UserError(_("The uploaded Excel file is empty."))

            start_idx = 0
            first_row_vals = [str(c).strip().lower() for c in raw_rows[0] if c is not None]
            if any(h in first_row_vals for h in ['lot', 'serial', 'lot/serial', 'number', 'name', 'sn', 'serial number']):
                start_idx = 1

            for row in raw_rows[start_idx:]:
                if not row or row[0] is None:
                    continue
                lot_name = str(row[0]).strip()
                if not lot_name:
                    continue
                qty = 1.0
                if len(row) > 1 and row[1] is not None and self.tracking == 'lot':
                    try:
                        qty = float(row[1])
                    except (ValueError, TypeError):
                        qty = 1.0
                extracted_rows.append((lot_name, qty))

        elif filename.endswith('.csv') or filename.endswith('.txt'):
            try:
                text = data.decode('utf-8', errors='ignore')
                reader = csv.reader(io.StringIO(text))
                raw_rows = list(reader)
            except Exception as e:
                raise UserError(_("Error reading CSV file: %s", str(e)))

            if not raw_rows:
                raise UserError(_("The uploaded file is empty."))

            start_idx = 0
            first_row_vals = [str(c).strip().lower() for c in raw_rows[0]]
            if any(h in first_row_vals for h in ['lot', 'serial', 'lot/serial', 'number', 'name', 'sn', 'serial number']):
                start_idx = 1

            for row in raw_rows[start_idx:]:
                if not row or not row[0].strip():
                    continue
                lot_name = row[0].strip()
                qty = 1.0
                if len(row) > 1 and row[1].strip() and self.tracking == 'lot':
                    try:
                        qty = float(row[1].strip())
                    except ValueError:
                        qty = 1.0
                extracted_rows.append((lot_name, qty))
        else:
            raise UserError(_("Unsupported file format. Please upload an Excel (.xlsx) or CSV file."))

        if not extracted_rows:
            raise UserError(_("No valid lot or serial numbers were found in the uploaded file."))

        target_location = self.location_id or (self.available_location_ids and self.available_location_ids[0])
        if not target_location:
            raise UserError(_("No warehouse location found for product '%s'.", self.product_id.display_name))

        new_lines = []
        for lot_name, qty in extracted_rows:
            new_lines.append((0, 0, {
                'location_id': target_location.id,
                'lot_name': lot_name,
                'quantity': 1.0 if self.tracking == 'serial' else qty,
            }))

        self.write({
            'line_ids': [(5, 0, 0)] + new_lines,
            'import_file': False,
            'import_filename': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l4e.update.lot.serial.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply(self):
        self.ensure_one()
        precision = self.uom_id.rounding

        if not self.line_ids:
            raise UserError(_("Please add at least one Lot / Serial line."))

        if float_is_zero(self.assigned_qty, precision_rounding=precision):
            raise UserError(_("Total assigned quantity cannot be zero."))

        # 1. Validation checks
        serial_names = []
        for line in self.line_ids:
            lot_identifier = (line.lot_name or (line.lot_id and line.lot_id.name) or '').strip()
            if not lot_identifier:
                raise UserError(_("Each line must have a Lot or Serial Number specified."))
            if float_compare(line.quantity, 0, precision_rounding=precision) <= 0:
                raise UserError(_("Quantity for each line must be strictly positive."))
            if self.tracking == 'serial':
                if float_compare(line.quantity, 1.0, precision_rounding=precision) != 0:
                    raise UserError(_("For serial-tracked products, quantity must be 1.0 for each line."))
                serial_names.append(lot_identifier)

        # Check for duplicate serials in current wizard
        if self.tracking == 'serial':
            counts = Counter(serial_names)
            duplicates = [name for name, c in counts.items() if c > 1]
            if duplicates:
                raise UserError(_("Duplicate Serial Numbers detected: %s. Each serial must be unique.", ", ".join(duplicates)))

            # Check if any new serial already exists in positive stock
            existing_active_quants = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('lot_id.name', 'in', serial_names),
                ('quantity', '>', 0),
                ('location_id.usage', 'in', ['internal', 'transit']),
            ])
            if existing_active_quants:
                raise UserError(_("The following serial number(s) already exist on-hand: %s", ", ".join(existing_active_quants.mapped('lot_id.name'))))

        # Check per-location assigned vs available quantity
        locations_assigned = {}
        for line in self.line_ids:
            locations_assigned[line.location_id] = locations_assigned.get(line.location_id, 0.0) + line.quantity

        domain_quant_loc = self.product_id._get_domain_locations()[0]
        initial_tracking = self.product_id.tracking
        if self.source_lot_id:
            quant_filter = [('lot_id', '=', self.source_lot_id.id)]
        elif initial_tracking == 'none':
            quant_filter = [('lot_id', '=', False)]
        else:
            quant_filter = []

        for location, assigned_in_loc in locations_assigned.items():
            source_quants = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', location.id),
                ('quantity', '>', 0),
            ] + quant_filter + domain_quant_loc)
            available_in_loc = sum(source_quants.mapped('quantity'))
            if float_compare(assigned_in_loc, available_in_loc, precision_rounding=precision) > 0:
                raise UserError(_(
                    "The assigned quantity (%(assigned)s) in location '%(loc)s' exceeds available source quantity (%(available)s).",
                    assigned=assigned_in_loc,
                    loc=location.display_name,
                    available=available_in_loc,
                ))

        # 2. Unreserve open moves that reserved the source stock
        target_locations = self.line_ids.mapped('location_id')
        move_line_domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id', 'in', target_locations.ids),
            ('state', 'not in', ['done', 'cancel']),
            ('quantity', '>', 0),
        ]
        if self.source_lot_id:
            move_line_domain.append(('lot_id', '=', self.source_lot_id.id))
        elif initial_tracking == 'none':
            move_line_domain.append(('lot_id', '=', False))

        open_move_lines = self.env['stock.move.line'].search(move_line_domain)
        moves_to_reassign = open_move_lines.mapped('move_id')
        if moves_to_reassign:
            moves_to_reassign._do_unreserve()

        # 3. Update existing quants (convert source quant into new target lot/serial quants)
        applied_lots = []
        for line in self.line_ids:
            target_lot = line.lot_id
            target_lot_name = (line.lot_name or (target_lot and target_lot.name) or '').strip()
            company = line.location_id.company_id or self.env.company

            if not target_lot:
                target_lot = self.env['stock.lot'].search([
                    ('product_id', '=', self.product_id.id),
                    ('name', '=', target_lot_name),
                    '|', ('company_id', '=', False), ('company_id', '=', company.id),
                ], limit=1)
                if not target_lot:
                    target_lot = self.env['stock.lot'].create({
                        'name': target_lot_name,
                        'product_id': self.product_id.id,
                        'company_id': company.id,
                    })

            applied_lots.append(target_lot.name)
            qty_to_assign = line.quantity

            # Deduct from source quants at this location
            # Prioritize untracked quants first if source_lot_id is False, or any positive quants
            source_quant_domain = [
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('quantity', '>', 0),
            ] + domain_quant_loc
            if self.source_lot_id:
                source_quant_domain.append(('lot_id', '=', self.source_lot_id.id))
            elif initial_tracking == 'none':
                source_quant_domain.append(('lot_id', '=', False))

            source_quants = self.env['stock.quant'].search(source_quant_domain, order='lot_id asc, id asc')

            rem_to_deduct = qty_to_assign
            package_id = False
            owner_id = False
            in_date = fields.Datetime.now()

            for s_quant in source_quants:
                if float_is_zero(rem_to_deduct, precision_rounding=precision):
                    break
                deduct_qty = min(rem_to_deduct, s_quant.quantity)
                s_quant.sudo().write({'quantity': s_quant.quantity - deduct_qty})
                rem_to_deduct -= deduct_qty
                package_id = s_quant.package_id.id
                owner_id = s_quant.owner_id.id
                if s_quant.in_date:
                    in_date = s_quant.in_date
                if float_compare(s_quant.quantity, 0, precision_rounding=precision) <= 0 and float_compare(s_quant.reserved_quantity, 0, precision_rounding=precision) <= 0:
                    s_quant.sudo().unlink()

            # Add to target tracked quant with target_lot
            tracked_quant = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('lot_id', '=', target_lot.id),
                ('package_id', '=', package_id),
                ('owner_id', '=', owner_id),
            ], limit=1)

            if tracked_quant:
                tracked_quant.sudo().write({'quantity': tracked_quant.quantity + qty_to_assign})
            else:
                self.env['stock.quant'].sudo().create({
                    'product_id': self.product_id.id,
                    'location_id': line.location_id.id,
                    'lot_id': target_lot.id,
                    'quantity': qty_to_assign,
                    'package_id': package_id,
                    'owner_id': owner_id,
                    'in_date': in_date,
                    'company_id': company.id,
                })

        # 4. Clean up zero quants
        self.env['stock.quant']._unlink_zero_quants()

        # Update product tracking to wizard.tracking if changed
        if self.product_id.tracking != self.tracking:
            self.product_id.sudo().write({'tracking': self.tracking})
            tmpl = self.product_tmpl_id or self.product_id.product_tmpl_id
            if tmpl and tmpl.tracking != self.tracking:
                tmpl.sudo().write({'tracking': self.tracking})

        # 5. Re-assign open moves
        if moves_to_reassign:
            moves_to_reassign._action_assign()

        # 6. Post audit trail note on product chatter
        tmpl = self.product_tmpl_id or self.product_id.product_tmpl_id
        if tmpl:
            if self.source_lot_id:
                source_desc = _("Lot '%s'") % self.source_lot_id.name
            elif initial_tracking == 'none':
                source_desc = _("Untracked Stock")
            else:
                source_desc = _("All Available Stock")
            body = Markup(_(
                "<strong>Lot/Serial Numbers Updated:</strong><br/>"
                "Converted from: %(from_source)s<br/>"
                "Quantity: %(qty)s %(uom)s<br/>"
                "Assigned Numbers: %(lots)s"
            )) % {
                'from_source': source_desc,
                'qty': self.assigned_qty,
                'uom': self.uom_id.name,
                'lots': ", ".join(applied_lots[:50]) + ("..." if len(applied_lots) > 50 else ""),
            }
            tmpl.message_post(body=body)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Successfully updated %(qty)s %(uom)s with Lot/Serial numbers for %(product)s.',
                             qty=self.assigned_qty, uom=self.uom_id.name, product=self.product_id.display_name),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class L4eUpdateLotSerialLine(models.TransientModel):
    _name = 'l4e.update.lot.serial.line'
    _description = 'Line for Updating Lot / Serial Numbers'

    wizard_id = fields.Many2one(
        'l4e.update.lot.serial.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        related='wizard_id.product_id',
        readonly=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        domain="[('id', 'in', parent.available_location_ids)]",
    )
    lot_name = fields.Char(
        string='Lot/Serial Number',
        help='Name of the lot or serial number to assign.',
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Existing Lot/Serial',
        domain="[('product_id', '=', product_id)]",
        help='Optionally select an existing Lot/Serial record.',
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
        digits='Product Unit',
    )
    uom_id = fields.Many2one(
        'uom.uom',
        related='wizard_id.uom_id',
        readonly=True,
        string='Unit',
    )

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.lot_id:
            self.lot_name = self.lot_id.name
