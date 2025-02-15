{
    'name': 'Purchase Request to Expense',
    'author': 'PT SAI, Odoo Community Association (OCA)',
    'version': '14.0.1.0.0',
    'summary': 'Create expense from purchase requests',
    'author': 'Your Company',
    'website': 'https://github.com/OCA/purchase-workflow',
    'category': 'Purchase Management',
    'depends': [
        'purchase_request',
        'hr_expense',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expense_views.xml',
        'wizard/purchase_request_line_make_expense.xml',
        'views/purchase_request_line_views.xml',
        'views/purchase_request_views.xml',
    ],
    'installable': True,
    'license': 'AGPL-3',
}