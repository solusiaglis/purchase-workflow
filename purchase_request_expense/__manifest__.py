# Copyright 2025 PT Solusi Aglis Indonesia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Purchase Request to Expense",
    "version": "14.0.1.0.0",
    "summary": "Create expense from purchase requests",
    "author": "PT Solusi Aglis Indonesia, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/purchase-workflow",
    "category": "Purchase Management",
    "depends": [
        "purchase_request",
        "hr_expense",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_expense_views.xml",
        "wizard/purchase_request_line_make_expense.xml",
        "views/purchase_request_line_views.xml",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
}
