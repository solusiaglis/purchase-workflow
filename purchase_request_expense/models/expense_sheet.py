from odoo import models, fields

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    purchase_request_line_id = fields.Many2one(
        comodel_name='purchase.request.line',
        string='Purchase Request Line',
        readonly=True,
    )

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    purchase_request_id = fields.Many2one(
        comodel_name='purchase.request',
        string='Purchase Request',
        readonly=True,
    )