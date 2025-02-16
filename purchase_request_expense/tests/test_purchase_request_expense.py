from odoo.exceptions import UserError
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestExpenseExtended(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create employee
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Test Employee",
            }
        )

        # Create user
        cls.user = cls.env["res.users"].create(
            {
                "name": "Test User",
                "login": "testuser",
                "email": "test@test.com",
                "employee_id": cls.employee.id,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref(
                                "purchase_request.group_purchase_request_user"
                            ).id,
                            cls.env.ref("hr_expense.group_hr_expense_user").id,
                            cls.env.ref("base.group_user").id,
                        ],
                    )
                ],
            }
        )

        # Update employee with user
        cls.employee.user_id = cls.user.id

        # Create analytic account
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Test Analytic Account",
            }
        )

        # Create expense product
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Expense Product",
                "type": "service",
                "can_be_expensed": True,
                "standard_price": 100.0,
            }
        )

        # Create purchase request
        cls.purchase_request = cls.env["purchase.request"].create(
            {
                "name": "Test PR",
                "requested_by": cls.user.id,
                "picking_type_id": cls.env.ref("stock.picking_type_in").id,
            }
        )

        # Create purchase request line
        cls.pr_line = cls.env["purchase.request.line"].create(
            {
                "request_id": cls.purchase_request.id,
                "product_id": cls.product.id,
                "product_qty": 1.0,
                "estimated_cost": 100.0,
                "analytic_account_id": cls.analytic_account.id,
            }
        )

    def test_01_module_installation_check(self):
        """Test the _has_expense_advance_clearing method"""
        wizard = self.env["purchase.request.line.make.expense"].create(
            {
                "employee_id": self.employee.id,
            }
        )

        # Check if hr_expense_advance_clearing is in the installed modules list
        module = self.env["ir.module.module"].search(
            [("name", "=", "hr_expense_advance_clearing")]
        )
        is_installed = module.state == "installed" if module else False

        # Test should pass whether module is installed or not
        self.assertEqual(
            wizard._has_expense_advance_clearing(),
            is_installed,
            "Module installation check should match actual installation status",
        )

    def test_02_error_handling_no_items(self):
        """Test error when trying to create expense without items"""
        wizard = self.env["purchase.request.line.make.expense"].create(
            {
                "employee_id": self.employee.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.make_expense()

    def test_03_error_handling_done_request(self):
        """Test error when trying to create expense from done request"""
        self.purchase_request.state = "done"
        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id],
        }
        with self.assertRaises(UserError):
            self.env["purchase.request.line.make.expense"].with_context(ctx).create(
                {
                    "employee_id": self.employee.id,
                }
            )

    def test_04_analytic_account_propagation(self):
        """Test analytic account propagation to expense"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id],
        }
        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )
        action = wizard.make_expense()

        expense = self.env["hr.expense"].browse(action.get("res_id"))
        self.assertEqual(
            expense.analytic_account_id,
            self.analytic_account,
            "Analytic account should be propagated to expense",
        )

    def test_05_zero_quantity_validation(self):
        """Test validation for zero quantity"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id],
        }
        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )

        # Set quantity to 0
        wizard.item_ids.product_qty = 0.0

        with self.assertRaises(UserError):
            wizard.make_expense()

    def test_06_onchange_product_description(self):
        """Test product description onchange"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        self.product.description_purchase = "Test Description"

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id],
        }
        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )

        wizard.item_ids.onchange_product_id()
        expected_name = f"{self.product.name}\n{self.product.description_purchase}"
        self.assertEqual(
            wizard.item_ids.name,
            expected_name,
            "Product description should be included in expense description",
        )

    def test_07_multiple_company_validation(self):
        """Test validation for lines from different companies"""
        # Create second company
        company2 = self.env["res.company"].create(
            {
                "name": "Test Company 2",
            }
        )

        # Create second purchase request in different company
        pr2 = self.purchase_request.copy()
        pr2.company_id = company2.id

        ctx = {
            "active_model": "purchase.request",
            "active_ids": [self.purchase_request.id, pr2.id],
        }

        with self.assertRaises(UserError):
            self.env["purchase.request.line.make.expense"].with_context(ctx).create(
                {
                    "employee_id": self.employee.id,
                }
            )

    def test_08_check_group_validation(self):
        """Test validation for different procurement groups"""
        # Create procurement groups
        group1 = self.env["procurement.group"].create({"name": "Group 1"})
        group2 = self.env["procurement.group"].create({"name": "Group 2"})

        # Assign different groups to requests
        self.purchase_request.group_id = group1
        pr2 = self.purchase_request.copy()
        pr2.group_id = group2

        ctx = {
            "active_model": "purchase.request",
            "active_ids": [self.purchase_request.id, pr2.id],
        }

        with self.assertRaises(UserError):
            self.env["purchase.request.line.make.expense"].with_context(ctx).create(
                {
                    "employee_id": self.employee.id,
                }
            )

    def test_09_picking_type_validation(self):
        """Test validation for picking type"""
        # Create a new purchase request with default picking type
        test_request = self.env["purchase.request"].create(
            {
                "name": "Test PR Without Picking Type",
                "requested_by": self.user.id,
            }
        )

        # Create a line for this request
        test_line = self.env["purchase.request.line"].create(
            {
                "request_id": test_request.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
            }
        )

        # Now try to create expense
        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [test_line.id],
        }

        # The validation should raise UserError since the default picking type
        # might not be appropriate for expense creation
        with self.assertRaises(UserError):
            self.env["purchase.request.line.make.expense"].with_context(ctx).create(
                {
                    "employee_id": self.employee.id,
                }
            )

    def test_10_advance_expense(self):
        """Test creation of advance expense"""
        # Get existing advance product or create new one
        advance_product = self.env.ref(
            "hr_expense_advance_clearing.product_emp_advance", raise_if_not_found=False
        )
        if not advance_product:
            advance_product = self.env["product.product"].create(
                {
                    "name": "Employee Advance",
                    "type": "service",
                    "can_be_expensed": True,
                    "standard_price": 1000.0,
                    "property_account_expense_id": self.env["account.account"]
                    .create(
                        {
                            "name": "Test Expense Account",
                            "code": "TEST_EXP",
                            "user_type_id": self.env.ref(
                                "account.data_account_type_expenses"
                            ).id,
                        }
                    )
                    .id,
                }
            )

        # Create purchase request line with advance product
        advance_line = self.env["purchase.request.line"].create(
            {
                "request_id": self.purchase_request.id,
                "product_id": advance_product.id,
                "product_qty": 1.0,
                "estimated_cost": 1000.0,
            }
        )

        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [advance_line.id],
        }

        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )

        action = wizard.make_expense()
        expense = self.env["hr.expense"].browse(action.get("res_id"))

        if self.env[
            "purchase.request.line.make.expense"
        ]._has_expense_advance_clearing():
            self.assertTrue(expense.advance)
            self.assertEqual(
                expense.account_id, advance_product.property_account_expense_id
            )

    def test_11_purchase_state_validation(self):
        """Test validation for purchase state"""
        self.pr_line.purchase_state = "done"

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id],
        }

        with self.assertRaises(UserError):
            self.env["purchase.request.line.make.expense"].with_context(ctx).create(
                {
                    "employee_id": self.employee.id,
                }
            )

    def test_12_multiple_line_creation(self):
        """Test creation of multiple expenses at once"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        # Create another line
        line2 = self.pr_line.copy()

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id, line2.id],
        }

        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )

        action = wizard.make_expense()

        # Verify action returns tree view for multiple expenses
        self.assertEqual(action.get("view_mode"), "tree,form")
        self.assertTrue(action.get("domain"))

    def test_13_default_get_from_purchase_request(self):
        """Test default_get when called from purchase request model"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        ctx = {
            "active_model": "purchase.request",
            "active_ids": [self.purchase_request.id],
        }

        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )

        self.assertEqual(len(wizard.item_ids), 1)
        self.assertEqual(wizard.item_ids[0].line_id, self.pr_line)

    def test_14_no_product_validation(self):
        """Test validation when no product is selected"""
        self.purchase_request.button_to_approve()
        self.purchase_request.button_approved()

        ctx = {
            "active_model": "purchase.request.line",
            "active_ids": [self.pr_line.id],
        }

        wizard = (
            self.env["purchase.request.line.make.expense"]
            .with_context(ctx)
            .create(
                {
                    "employee_id": self.employee.id,
                }
            )
        )

        # Remove product from wizard line
        wizard.item_ids.write({"product_id": False})

        with self.assertRaises(UserError):
            wizard.make_expense()
