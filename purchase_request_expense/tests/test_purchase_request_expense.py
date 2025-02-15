# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import Form
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ

@tagged('post_install', '-at_install')
class TestPurchaseRequestExpense(common.SavepointCase):
    def setUp(self):
        super(TestPurchaseRequestExpense, self).setUp()
        
        # Create employee first
        self.employee = self.env['hr.employee'].create({
            'name': 'Purchase Employee',
        })
        
        # Get user and employee
        self.purchase_user = self.env['res.users'].create({
            'name': 'Purchase User',
            'login': 'purchaseuser',
            'email': 'purchase@test.com',
            'employee_id': self.employee.id,
            'groups_id': [(6, 0, [
                self.env.ref('purchase_request.group_purchase_request_user').id,
                self.env.ref('hr_expense.group_hr_expense_user').id,
                self.env.ref('base.group_user').id,
            ])]
        })
        
        # Update employee with user
        self.employee.user_id = self.purchase_user.id

        # Create expensable category
        self.category = self.env['product.category'].create({
            'name': 'Test Category'
        })

        # Create products
        self.product_1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'type': 'service',
            'categ_id': self.category.id,
            'can_be_expensed': True,
            'standard_price': 100.0,
            'list_price': 100.0,
        })
        
        self.product_2 = self.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'service',
            'categ_id': self.category.id,
            'can_be_expensed': True,
            'standard_price': 200.0,
            'list_price': 200.0,
        })

        # Create purchase request
        self.purchase_request = self.env['purchase.request'].with_user(self.purchase_user).create({
            'name': 'Test Purchase Request',
            'requested_by': self.purchase_user.id,
        })

        # Create purchase request lines
        self.pr_line_1 = self.env['purchase.request.line'].with_user(self.purchase_user).create({
            'request_id': self.purchase_request.id,
            'product_id': self.product_1.id,
            'product_qty': 1.0,
            'estimated_cost': 100.0,
        })
        
        self.pr_line_2 = self.env['purchase.request.line'].with_user(self.purchase_user).create({
            'request_id': self.purchase_request.id,
            'product_id': self.product_2.id,
            'product_qty': 2.0,
            'estimated_cost': 400.0,
        })


    def test_01_create_expense_from_purchase_request(self):
        """Test creating expense from purchase request"""
        # Approve purchase request
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()
        self.assertEqual(self.purchase_request.state, 'approved')

        # Create wizard
        ctx = {
            'active_model': 'purchase.request',
            'active_id': self.purchase_request.id,
            'active_ids': [self.purchase_request.id],
        }
        wizard = self.env['purchase.request.line.make.expense'].with_user(self.purchase_user).with_context(ctx).create({
            'employee_id': self.employee.id,
        })
        
        # Check if lines are properly loaded
        self.assertEqual(len(wizard.item_ids), 2)
        
        # Verify line details
        line1 = wizard.item_ids.filtered(lambda l: l.product_id == self.product_1)
        self.assertEqual(line1.product_qty, 1.0)
        self.assertEqual(line1.estimated_cost, 100.0)
        
        line2 = wizard.item_ids.filtered(lambda l: l.product_id == self.product_2)
        self.assertEqual(line2.product_qty, 2.0)
        self.assertEqual(line2.estimated_cost, 400.0)

        # Create expenses
        action = wizard.make_expense()
        
        # Check created expenses
        expense_domain = [('purchase_request_line_id', 'in', self.purchase_request.line_ids.ids)]
        expenses = self.env['hr.expense'].search(expense_domain)
        
        self.assertEqual(len(expenses), 2)
        
        # Verify expense details
        exp1 = expenses.filtered(lambda e: e.product_id == self.product_1)
        self.assertEqual(exp1.quantity, 1.0)
        self.assertEqual(exp1.total_amount, 100.0)
        self.assertEqual(exp1.employee_id, self.employee)
        
        exp2 = expenses.filtered(lambda e: e.product_id == self.product_2)
        self.assertEqual(exp2.quantity, 2.0)
        self.assertEqual(exp2.total_amount, 400.0)
        self.assertEqual(exp2.employee_id, self.employee)

    
    def test_02_expense_validation(self):
        """Test expense creation validation"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        # Test with non-expensable product
        non_expense_product = self.env['product.product'].create({
            'name': 'Non Expensable Product',
            'type': 'service',
            'categ_id': self.category.id,
            'can_be_expensed': False,
            'standard_price': 150.0,
            'list_price': 150.0,
        })

        # Use savepoint to handle transaction
        with self.cr.savepoint():
            self.pr_line_1.product_id = non_expense_product.id
            
            # Create wizard with context
            ctx = {
                'active_model': 'purchase.request',
                'active_id': self.purchase_request.id,
                'active_ids': [self.purchase_request.id],
            }

            # Test that employee is required
            with self.assertRaises(ValidationError):
                self.env['purchase.request.line.make.expense'].with_context(ctx).create({})

            # Create wizard with employee
            wizard = self.env['purchase.request.line.make.expense'].with_context(ctx).create({
                'employee_id': self.employee.id,
            })
            
            # Should only have one line (the expensable one)
            self.assertEqual(len(wizard.item_ids), 1)
            self.assertEqual(wizard.item_ids[0].product_id, self.product_2)
    
    
    

    def test_03_expense_amounts_computation(self):
        """Test expense amount computations"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()
        
        # Create expense from first line
        ctx = {
            'active_model': 'purchase.request.line',
            'active_ids': [self.pr_line_1.id],
        }
        
        wizard = self.env['purchase.request.line.make.expense'].with_context(ctx).create({
            'employee_id': self.employee.id,
        })
        wizard.make_expense()
        
        # Check expense amounts
        self.assertEqual(self.pr_line_1.expense_amount, 100.0)
        self.assertEqual(self.purchase_request.expense_count, 1)
        
        # Test action_view_expenses
        action = self.purchase_request.action_view_expenses()
        self.assertEqual(action['res_model'], 'hr.expense')
        self.assertEqual(action['view_mode'], 'form')  # Should be form view as only one expense

        # Create expense from second line
        ctx['active_ids'] = [self.pr_line_2.id]
        wizard = self.env['purchase.request.line.make.expense'].with_context(ctx).create({
            'employee_id': self.employee.id,
        })
        wizard.make_expense()
        
        # Recheck amounts
        self.assertEqual(self.pr_line_2.expense_amount, 400.0)
        self.assertEqual(self.purchase_request.expense_count, 2)
        
        # Test action_view_expenses with multiple expenses
        action = self.purchase_request.action_view_expenses()
        self.assertEqual(action['view_mode'], 'tree,form')  # Should be tree view as multiple expenses