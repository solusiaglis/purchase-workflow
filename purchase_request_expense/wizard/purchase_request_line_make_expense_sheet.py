from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseRequestLineMakeExpenseSheet(models.TransientModel):
    _name = "purchase.request.line.make.expense.sheet"
    _description = "Purchase Request Line Make Expense Sheet"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1),
    )
    item_ids = fields.One2many(
        comodel_name="purchase.request.line.make.expense",
        inverse_name="wiz_id",
        string="Items",
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_model = self._context.get('active_model')
        
        if active_model == 'purchase.request':
            # If called from purchase request, get all its lines
            request = self.env[active_model].browse(self._context.get('active_id'))
            request_line_ids = request.line_ids.ids
        else:
            # If called from lines directly
            request_line_ids = self._context.get('active_ids', [])

        if not request_line_ids:
            return res

        items = []
        request_lines = self.env['purchase.request.line'].browse(request_line_ids)
        
        # Rest of your filtering logic...
        advance_product = self.env.ref('hr_expense_advance_clearing.product_emp_advance')
        for line in request_lines:
            # For regular expense
            if line.product_id.can_be_expensed and line.product_id.id != advance_product.id:
                items.append([0, 0, {
                    'line_id': line.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_qty': line.product_qty,
                    # 'product_uom_id': line.product_uom_id.id,
                    'estimated_cost': line.estimated_cost,
                }])
        res['item_ids'] = items
        return res

    def make_expense_sheet(self):
        self.ensure_one()
        expense_ids = []
        
        for item in self.item_ids:
            expense_vals = {
                'product_id': item.product_id.id,
                'name': item.name,
                'unit_amount': item.estimated_cost / item.product_qty if item.product_qty else 0.0,
                'quantity': item.product_qty,
                'employee_id': self.employee_id.id,
            }
            
            expense = self.env['hr.expense'].create(expense_vals)
            print("===========================")
            print("===========================")
            print("Daftar expense", expense)
            expense_ids.append(expense.id)
            
            

        # Get the purchase request from the context
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        purchase_request = False
        if active_model == 'purchase.request':
            purchase_request = self.env[active_model].browse(active_id)
        elif self.item_ids:
            purchase_request = self.item_ids[0].line_id.request_id

        expense_sheet = self.env['hr.expense.sheet'].create({
            'employee_id': self.employee_id.id,
            'name': 'Expense from %s' % (purchase_request.name if purchase_request else ''),
            'expense_line_ids': [(6, 0, expense_ids)],
            'purchase_request_id': purchase_request.id if purchase_request else False,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense.sheet',
            'res_id': expense_sheet.id,
            'view_mode': 'form',
            'target': 'current',
        }

class PurchaseRequestLineMakeExpense(models.TransientModel):
    _name = "purchase.request.line.make.expense"
    _description = "Purchase Request Line Make Expense"
    
    wiz_id = fields.Many2one(
        comodel_name="purchase.request.line.make.expense.sheet",
        string="Wizard",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    line_id = fields.Many2one(
        comodel_name="purchase.request.line",
        string="Purchase Request Line"
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product"
    )
    name = fields.Char(string="Description", required=True)
    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit of Measure"
    )
    # product_uom_id = fields.Many2one(
    #     comodel_name="uom.uom",
    #     string="UoM"
    # )
    estimated_cost = fields.Float(string="Estimated Cost")