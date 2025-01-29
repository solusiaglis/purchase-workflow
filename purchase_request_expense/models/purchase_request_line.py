# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'
   
    expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="purchase_request_line_id",
        string="Expenses",
        readonly=True,
    )
    
    expense_amount = fields.Monetary(
        string="Expense Amount",
        compute="_compute_expense_amount",
    )
    
    @api.depends("expense_ids", "expense_ids.total_amount")
    def _compute_expense_amount(self):
        for line in self:
            line.expense_amount = sum(line.expense_ids.mapped("total_amount"))
            
            