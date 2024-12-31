from odoo import models, fields, api


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    
    
    expense_count = fields.Integer(
        string='Expense Count',
        compute='_compute_expense_count',
        store=False
    )
    expense_ids = fields.One2many(
        'hr.expense.sheet',
        'purchase_request_id',
        string='Expenses'
    )
    
    @api.model
    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we need to remove domain from existing records
        """
        if column_name != 'assigned_to':
            super()._init_column(column_name)
            
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ Overriding fields_get to remove the domain from assigned_to field """
        res = super(PurchaseRequest, self).fields_get(allfields, attributes)
        if 'assigned_to' in res:
            res['assigned_to']['domain'] = []
        return res

    def _compute_assigned_to_domain(self):
        """ If there's a compute method for domain, we override it """
        return []

    # Monkey patch the domain attribute if it exists
    if hasattr(models.Model.fields_get, 'assigned_to'):
        models.Model.fields_get.assigned_to.domain = []
    
    
    
    def _compute_expense_count(self):
        for request in self:
            request.expense_count = len(request.expense_ids)

    def action_view_expense_sheets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.action_hr_expense_sheet_all")
        action['domain'] = [('purchase_request_id', '=', self.id)]
        action['views'] = [
            (self.env.ref('hr_expense.view_hr_expense_sheet_tree').id, 'tree'),
            (False, 'form')
        ]
        if len(self.expense_ids) == 1:
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
            action['res_id'] = self.expense_ids.id
        return action
    
        
    def check_products(self):
        self.ensure_one()
        for line in self.line_ids:
            if not line.product_id:
                raise UserError(_("Line '%s' has no product set.") % line.name)
            if not line.product_id.can_be_expensed:
                raise UserError(_("Product '%s' is not configured to be expensed.") % line.product_id.name)