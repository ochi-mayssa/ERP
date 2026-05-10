from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import BomItem, Product, ProductionOrder, Transaction


class InventoryWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="owner",
            password="factorypass123",
        )
        self.raw_material = Product.objects.create(
            sku="RM-001",
            name="Steel Sheet",
            unit="kg",
            stock_quantity=Decimal("10.00"),
            reorder_level=Decimal("3.00"),
            is_raw_material=True,
        )
        self.finished_product = Product.objects.create(
            sku="FG-001",
            name="Metal Cabinet",
            unit="pcs",
            stock_quantity=Decimal("2.00"),
            reorder_level=Decimal("1.00"),
            is_raw_material=False,
        )
        self.extra_raw_material = Product.objects.create(
            sku="RM-002",
            name="Hinge Set",
            unit="pcs",
            stock_quantity=Decimal("50.00"),
            reorder_level=Decimal("10.00"),
            is_raw_material=True,
        )
        BomItem.objects.create(
            finished_product=self.finished_product,
            raw_material=self.raw_material,
            quantity_needed=Decimal("2.00"),
        )
        BomItem.objects.create(
            finished_product=self.finished_product,
            raw_material=self.extra_raw_material,
            quantity_needed=Decimal("4.00"),
        )
        self.other_finished_product = Product.objects.create(
            sku="FG-002",
            name="Metal Shelf",
            unit="pcs",
            stock_quantity=Decimal("1.00"),
            reorder_level=Decimal("1.00"),
            is_raw_material=False,
        )
        BomItem.objects.create(
            finished_product=self.other_finished_product,
            raw_material=self.raw_material,
            quantity_needed=Decimal("20.00"),
        )

    def test_receive_transaction_increases_stock(self):
        Transaction.objects.create(
            type=Transaction.RECEIVE,
            product=self.raw_material,
            quantity=Decimal("5.00"),
            user=self.user,
        )

        self.raw_material.refresh_from_db()
        self.assertEqual(self.raw_material.stock_quantity, Decimal("15.00"))

    def test_ship_transaction_cannot_exceed_stock(self):
        with self.assertRaises(ValidationError):
            Transaction.objects.create(
                type=Transaction.SHIP,
                product=self.finished_product,
                quantity=Decimal("99.00"),
                user=self.user,
            )

    def test_product_list_requires_login(self):
        response = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_logged_in_user_can_view_low_stock_report(self):
        self.client.login(username="owner", password="factorypass123")

        response = self.client.get(reverse("inventory:low_stock_report"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Low Stock Report")

    def test_production_order_confirm_consumes_raw_materials_and_adds_finished_goods(self):
        order = ProductionOrder.objects.create(
            finished_product=self.finished_product,
            quantity=Decimal("2.00"),
            created_by=self.user,
        )
        order.populate_items_from_bom()

        order.confirm(user=self.user)

        self.raw_material.refresh_from_db()
        self.extra_raw_material.refresh_from_db()
        self.finished_product.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(order.status, ProductionOrder.CONFIRMED)
        self.assertEqual(self.raw_material.stock_quantity, Decimal("6.00"))
        self.assertEqual(self.extra_raw_material.stock_quantity, Decimal("42.00"))
        self.assertEqual(self.finished_product.stock_quantity, Decimal("4.00"))

    def test_production_order_create_view_builds_draft_and_items(self):
        self.client.login(username="owner", password="factorypass123")

        response = self.client.post(
            reverse("inventory:production_order_create"),
            {"finished_product": self.finished_product.pk, "quantity": "1.00"},
        )

        self.assertEqual(response.status_code, 302)
        order = ProductionOrder.objects.get()
        self.assertEqual(order.status, ProductionOrder.DRAFT)
        self.assertEqual(order.items.count(), 2)

    def test_production_order_confirm_fails_when_raw_material_stock_is_short(self):
        order = ProductionOrder.objects.create(
            finished_product=self.finished_product,
            quantity=Decimal("100.00"),
            created_by=self.user,
        )
        order.populate_items_from_bom()

        with self.assertRaises(ValidationError):
            order.confirm(user=self.user)

    def test_production_order_list_can_filter_by_status(self):
        self.client.login(username="owner", password="factorypass123")
        draft_order = ProductionOrder.objects.create(
            finished_product=self.finished_product,
            quantity=Decimal("1.00"),
            created_by=self.user,
        )
        draft_order.populate_items_from_bom()
        confirmed_order = ProductionOrder.objects.create(
            finished_product=self.finished_product,
            quantity=Decimal("1.00"),
            created_by=self.user,
        )
        confirmed_order.populate_items_from_bom()
        confirmed_order.confirm(user=self.user)

        response = self.client.get(reverse("inventory:production_order_list"), {"status": "draft"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#{draft_order.pk}")
        self.assertNotContains(response, f"#{confirmed_order.pk}")

    def test_production_order_list_can_filter_shortages_only(self):
        self.client.login(username="owner", password="factorypass123")
        ready_order = ProductionOrder.objects.create(
            finished_product=self.finished_product,
            quantity=Decimal("1.00"),
            created_by=self.user,
        )
        ready_order.populate_items_from_bom()
        shortage_order = ProductionOrder.objects.create(
            finished_product=self.other_finished_product,
            quantity=Decimal("1.00"),
            created_by=self.user,
        )
        shortage_order.populate_items_from_bom()

        response = self.client.get(reverse("inventory:production_order_list"), {"shortages": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("inventory:production_order_detail", args=[shortage_order.pk]))
        self.assertNotContains(response, reverse("inventory:production_order_detail", args=[ready_order.pk]))
        self.assertContains(response, "Shortage")
