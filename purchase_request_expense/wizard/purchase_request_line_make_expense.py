from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PurchaseRequestLineMakeExpense(models.TransientModel):
    _name = "purchase.request.line.make.expense"
    _description = "Purchase Request Line Make Expense"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1),
    )
    item_ids = fields.One2many(
        comodel_name="purchase.request.line.make.expense.item",
        inverse_name="wiz_id",
        string="Items",
    )

    @api.model
    def _prepare_item(self, line):
        _logger.info("Line ID: %s, Nomor PR: %s", line.id, line.request_id.id)
        advance_product = self.env.ref("hr_expense_advance_clearing.product_emp_advance", raise_if_not_found=False)
        if advance_product and line.product_id.id == advance_product.id:
            return False
        
        product = line.product_id
        if not product:
            # If no product, try to find a default expense product
            product = self.env['product.product'].search([
                ('can_be_expensed', '=', True),
                ('type', '=', 'service'),
                ('id', '!=', advance_product.id if advance_product else False)
            ], limit=1)
            if not product:
                return False
                
        if not product.can_be_expensed:
            return False
        
        vals = {
            "line_id": line.id,
            "request_id": line.request_id.id,
            "product_id": product.id,
            "name": line.name or product.name,
            "product_qty": line.pending_qty_to_receive or 1.0,
            "product_uom_id": line.product_uom_id.id or product.uom_id.id,
            "estimated_cost": line.estimated_cost,
        }
        _logger.info("Prepared item values: %s", vals)
        return vals

    
    @api.model
    def _check_valid_request_line(self, request_line_ids):
        picking_type = False
        company_id = False

        for line in self.env["purchase.request.line"].browse(request_line_ids):
            if line.request_id.state == "done":
                raise UserError(_("The purchase has already been completed."))
            if line.request_id.state != "approved":
                raise UserError(
                    _("Purchase Request %s is not approved") % line.request_id.name
                )

            if line.purchase_state == "done":
                raise UserError(_("The purchase has already been completed."))

            line_company_id = line.company_id and line.company_id.id or False
            if company_id is not False and line_company_id != company_id:
                raise UserError(_("You have to select lines from the same company."))
            else:
                company_id = line_company_id

            line_picking_type = line.request_id.picking_type_id or False
            if not line_picking_type:
                raise UserError(_("You have to enter a Picking Type."))
            if picking_type is not False and line_picking_type != picking_type:
                raise UserError(
                    _("You have to select lines from the same Picking Type.")
                )
            else:
                picking_type = line_picking_type

            
    @api.model  
    def get_items(self, request_line_ids):
        # Log the incoming request_line_ids
        _logger.info("Processing request_line_ids: %s", request_line_ids)
        request_line_obj = self.env["purchase.request.line"]
        items = []
        request_lines = request_line_obj.browse(request_line_ids)
        _logger.info("Request lines: %s", request_lines)
        self._check_valid_request_line(request_line_ids)
        for line in request_lines:
            item = self._prepare_item(line)
            _logger.info("Prepared item from line %s: %s", line, item)
            
            if item:
                items.append([0, 0, item])
        _logger.info("Final items: %s", items)
        if not items:
            raise UserError(_("No products that can be expensed were found in the selected lines."))
        return items
    
    
    @api.model
    # def default_get(self, fields):
    #     res = super().default_get(fields)
    #     active_model = self._context.get('active_model', False)
    #     request_line_ids = []
    #     if active_model == 'purchase.request.line':
    #         request_line_ids += self._context.get('active_ids', [])            
    #     elif active_model == "purchase.request":
    #         request_ids = self.env.context.get('active_ids', False)
    #         request_line_ids += (
    #             self.env[active_model].browse(request_ids).mapped("line_ids.id")
    #         )
    #     if not request_line_ids:
    #         return res
    #     res["item_ids"] = self.get_items(request_line_ids)
    #     request_lines = self.env['purchase.request.line'].browse(request_line_ids)
    #     return res
    def default_get(self, fields):
        _logger.info("default_get called with fields: %s", fields)
        res = super().default_get(fields)
        active_model = self._context.get('active_model', False)
        _logger.info("Active model: %s", active_model)
        
        request_line_ids = []
        if active_model == 'purchase.request.line':
            request_line_ids += self._context.get('active_ids', [])
            _logger.info("Got request line IDs from active_ids: %s", request_line_ids)
        elif active_model == "purchase.request":
            request_ids = self.env.context.get('active_ids', False)
            _logger.info("Got request IDs: %s", request_ids)
            if request_ids:
                lines = self.env[active_model].browse(request_ids).mapped("line_ids")
                _logger.info("Found lines from requests: %s", lines)
                request_line_ids += lines.ids
                _logger.info("Added line IDs: %s", request_line_ids)
                
        if not request_line_ids:
            _logger.warning("No request line IDs found")
            return res
            
        _logger.info("Getting items for request_line_ids: %s", request_line_ids)
        res["item_ids"] = self.get_items(request_line_ids)
        _logger.info("res['items_ids']: %s", res["item_ids"])
        return res
    

    @api.model 
    # def _prepare_expense(self, item):
    #     _logger.info("Item name: %s, Product ID: %s, PR Line ID: %s",  item.name, item.product_id.id, item.line_id)
    #     if not item.product_id:
    #         raise UserError('Please select a product for all lines')
        
    #     return {
    #         "name": item.name,
    #         "employee_id": self.employee_id.id,
    #         "product_id": item.product_id.id,
    #         "unit_amount": item.estimated_cost / item.product_qty if item.product_qty else 0.0,
    #         "quantity": item.product_qty,
    #         "product_uom_id": item.product_uom_id.id,
    #         "reference": item.request_id.name,
    #         "purchase_request_line_id": item.line_id,
    #     }
    def _prepare_expense(self, item):
        _logger.info("Preparing expense for item: %s", item)
        _logger.info("Preparing expense for item with line_id: %s", item.line_id.id if item.line_id else 'No line')
        
        if not item.product_id:
            raise UserError(_('Please select a product for the line with description: %s') % item.name)
        
        vals = {
            "name": item.name,
            "employee_id": self.employee_id.id,
            "product_id": item.product_id.id,
            "unit_amount": item.estimated_cost / item.product_qty if item.product_qty else 0.0,
            "quantity": item.product_qty,
            "product_uom_id": item.product_uom_id.id,
            "reference": item.request_id.name if item.request_id else '',
            "purchase_request_line_id": item.line_id.id if item.line_id else False,
        }
        _logger.info("Prepared expense values: %s", vals)
        return vals
    
        


    def make_expense(self):
        """Create expenses from the wizard items."""
        self.ensure_one()
        if not self.item_ids:
            raise UserError(_('You must select at least one expense line.'))
            
        # Validate all items have products before proceeding
        for item in self.item_ids:
            if not item.product_id:
                raise UserError(_("Product is required for all expense lines. Please select a product for '%s'") % item.name)

        expense_obj = self.env['hr.expense']
        expenses = self.env['hr.expense']

        for item in self.item_ids:
            if not item.product_qty:
                raise UserError(
                    _("Quantity must be greater than 0 for product %s") % item.product_id.name
                )
            
            if not item.product_id:
                raise UserError(
                    _("Product is required for line with description: %s") % item.name
                )

            # Create expense
            expense_vals = self._prepare_expense(item)
            expense = expense_obj.create(expense_vals)
            expenses += expense
            


        # Show the created expenses
        action = {
            'name': _('Created Expenses'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', expenses.ids)],
        }

        # If only one expense created, show it in form view
        if len(expenses) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': expenses.id,
            })

        return action

    
       

class PurchaseRequestLineMakeExpenseItem(models.TransientModel):
    _name = "purchase.request.line.make.expense.item"
    _description = "Purchase Request Line Make Expense Item"
    
    wiz_id = fields.Many2one(
        comodel_name="purchase.request.line.make.expense",
        string="Wizard",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    line_id = fields.Many2one(
        comodel_name="purchase.request.line",
        string="Purchase Request Line"
    )
    
    line_id_display = fields.Integer(
        string="Line ID",
        compute="_compute_line_id_display",
        store=True
    )

    @api.depends("line_id")
    def _compute_line_id_display(self):
        for record in self:
            record.line_id_display = record.line_id.id if record.line_id else 0
    
    
    
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        related="line_id.request_id",
        string="Purchase Request",
        readonly=False
    )
    
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=False,
        domain=[('can_be_expensed','=',True)],
        required=True, 
    )
    
    @api.onchange('line_id')
    def _onchange_line_id(self):
        if self.line_id:
            # Get advance product for filtering
            advance_product = self.env.ref("hr_expense_advance_clearing.product_emp_advance", raise_if_not_found=False)
            
            if self.line_id.product_id and self.line_id.product_id.id != (advance_product.id if advance_product else False):
                self.product_id = self.line_id.product_id
            else:
                # Try to find a default expense product
                product = self.env['product.product'].search([
                    ('can_be_expensed', '=', True),
                    ('type', '=', 'service'),
                    ('id', '!=', advance_product.id if advance_product else False)
                ], limit=1)
                if product:
                    self.product_id = product.id

    
    name = fields.Char(string="Description", required=True)
    product_qty = fields.Float(
        string="Quantity to purchase",
        digits="Product Unit of Measure"
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM"
    )
    estimated_cost = fields.Float(string="Estimated Cost")
    
    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.description_purchase:
                name += "\n" + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.name = name