{
    'name': 'Purchase Request to Expense',
    'version': '14.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Create expense reports from purchase requests',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'AGPL-3',
    'depends': [
        'purchase_request',
        'hr_expense_advance_clearing',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expense_views.xml',
        'wizard/purchase_request_line_make_expense_sheet_view.xml',
        'wizard/purchase_request_line_make_advance_sheet_view.xml',
        'views/purchase_request_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}