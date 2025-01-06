# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    expense_id = fields.Many2one(
        comodel_name='hr.expense',
        string='Expense',
        copy=False,
        index=True,
    )
   
    pending_qty_to_receive = fields.Float(
        compute='_compute_pending_qty',
        string='Pending Quantity to Receive',
        store=True,
    )
    estimated_cost = fields.Float(
        string='Estimated Cost',
        default=0.0,
    )

    @api.depends('product_qty', 'qty_in_progress', 'qty_done')
    def _compute_pending_qty(self):
        for line in self:
            line.pending_qty_to_receive = line.product_qty - line.qty_in_progress - line.qty_done