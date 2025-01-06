# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    
    purchase_request_line_id = fields.Many2one(
        comodel_name='purchase.request.line',
        string='Purchase Request Line',
        ondelete='restrict',  # Prevent deletion if referenced
        index=True,
        copy=False
    )