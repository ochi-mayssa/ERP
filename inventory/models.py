from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction as db_transaction
from django.db.models import F, Q
from django.utils import timezone


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)
    stock_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_raw_material = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # QR Code Field
    qr_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Cost & Pricing Fields
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    average_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labor_hours_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    labor_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    overhead_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)

    class Meta:
        ordering = ['name']
        permissions = [
            ("can_view_inventory", "Can view inventory"),
            ("can_manage_stock", "Can manage stock (stock in/out)"),
            ("can_manage_products", "Can manage products (create/edit/delete)"),
            ("can_manage_purchase", "Can manage purchase (POs, suppliers)"),
            ("can_manage_users", "Can manage users"),
        ]

    def __str__(self):
        return f'{self.sku} - {self.name}'

    @property
    def is_low_stock(self):
        return self.stock_quantity < self.reorder_level


class BomItem(models.Model):
    finished_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='bom_items',
        limit_choices_to={'is_raw_material': False},
    )
    raw_material = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='used_in_boms',
        limit_choices_to={'is_raw_material': True},
    )
    quantity_needed = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('finished_product', 'raw_material')
        ordering = ['finished_product__name', 'raw_material__name']

    def __str__(self):
        return f'{self.finished_product.name} needs {self.quantity_needed} {self.raw_material.unit} of {self.raw_material.name}'

    def clean(self):
        if self.finished_product_id and self.raw_material_id and self.finished_product_id == self.raw_material_id:
            raise ValidationError('Finished product and raw material must be different products.')
        if self.finished_product and self.finished_product.is_raw_material:
            raise ValidationError('Finished product cannot be marked as a raw material.')
        if self.raw_material and not self.raw_material.is_raw_material:
            raise ValidationError('Raw material must be marked as a raw material.')


class Transaction(models.Model):
    RECEIVE = 'receive'
    ISSUE = 'issue'
    PRODUCE = 'produce'
    SHIP = 'ship'
    ADJUST = 'adjust'

    TYPE_CHOICES = [
        (RECEIVE, 'Receive'),
        (ISSUE, 'Issue to Production'),
        (PRODUCE, 'Produce'),
        (SHIP, 'Ship Finished Goods'),
        (ADJUST, 'Adjust'),
    ]

    STOCK_EFFECTS = {
        RECEIVE: 1,
        ISSUE: -1,
        PRODUCE: 1,
        SHIP: -1,
        ADJUST: 1,
    }

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    reference_note = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp', '-id']

    @property
    def signed_quantity(self):
        multiplier = self.STOCK_EFFECTS.get(self.type, 1)
        return self.quantity * multiplier

    def __str__(self):
        return f'{self.get_type_display()} - {self.product.name} ({self.quantity})'

    def clean(self):
        if self.quantity is None or self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')
        if self.type == self.PRODUCE and self.product.is_raw_material:
            raise ValidationError('Produce transactions must target a finished product.')
        if self.type in {self.ISSUE, self.SHIP}:
            if self.type == self.ISSUE and not self.product.is_raw_material:
                raise ValidationError('Issue transactions should target raw materials.')
            if self.type == self.SHIP and self.product.is_raw_material:
                raise ValidationError('Ship transactions should target finished goods.')
            if self.product.stock_quantity < self.quantity:
                raise ValidationError('Not enough stock available for this transaction.')

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.pk:
            raise ValidationError('Editing transactions is disabled in the MVP to protect stock history.')

        multiplier = self.STOCK_EFFECTS[self.type]
        with db_transaction.atomic():
            self.product.stock_quantity = F('stock_quantity') + (multiplier * self.quantity)
            self.product.save(update_fields=['stock_quantity', 'updated_at'])
            super().save(*args, **kwargs)
        self.product.refresh_from_db(fields=['stock_quantity'])

    @classmethod
    def low_stock_products(cls):
        return Product.objects.filter(stock_quantity__lt=F('reorder_level')).order_by('name')

    @classmethod
    def stock_products_queryset(cls):
        return Product.objects.filter(Q(is_raw_material=True) | Q(is_raw_material=False)).order_by('name')


class ProductionOrder(models.Model):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (CONFIRMED, "Confirmed"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    finished_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="production_orders",
        limit_choices_to={"is_raw_material": False},
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_production_orders",
    )
    confirmed_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_production_orders",
    )
    started_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_production_orders",
    )
    completed_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_production_orders",
    )
    cancelled_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_production_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        permissions = [
            ("can_manage_production", "Can manage production (confirm/start/complete)"),
        ]

    def __str__(self):
        return f"PO-{self.pk or 'new'} {self.finished_product.name} x {self.quantity}"

    def clean(self):
        if self.quantity is None or self.quantity <= 0:
            raise ValidationError("Production quantity must be greater than zero.")
        if self.finished_product and self.finished_product.is_raw_material:
            raise ValidationError("Production orders must target a finished product.")
        if self.finished_product_id and not self.finished_product.bom_items.exists():
            raise ValidationError("This finished product does not have any BOM items.")

    def get_bom_items(self):
        return list(
            self.finished_product.bom_items.select_related("raw_material").order_by("raw_material__name")
        )

    def has_bom(self):
        return bool(self.get_bom_items())

    def calculate_requirements(self):
        requirements = []
        for bom_item in self.get_bom_items():
            required_quantity = bom_item.quantity_needed * self.quantity
            available_quantity = bom_item.raw_material.stock_quantity
            requirements.append(
                {
                    "raw_material": bom_item.raw_material,
                    "quantity_required": required_quantity,
                    "quantity_available": available_quantity,
                    "enough_stock": available_quantity >= required_quantity,
                }
            )
        return requirements

    def has_enough_stock(self):
        requirements = self.calculate_requirements()
        return bool(requirements) and all(item["enough_stock"] for item in requirements)

    def populate_items_from_bom(self):
        bom_items = self.get_bom_items()
        if not bom_items:
            raise ValidationError("This finished product does not have any BOM items.")

        self.items.all().delete()
        order_items = []
        for bom_item in bom_items:
            order_items.append(
                ProductionOrderItem(
                    production_order=self,
                    raw_material=bom_item.raw_material,
                    quantity_required=bom_item.quantity_needed * self.quantity,
                )
            )
        ProductionOrderItem.objects.bulk_create(order_items)

    def confirm(self, user=None):
        if self.status != self.DRAFT:
            raise ValidationError(f"Cannot confirm order in {self.status} status.")
        if not self.items.exists():
            self.populate_items_from_bom()

        self.status = self.CONFIRMED
        self.confirmed_by = user
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_by", "confirmed_at"])

    def start_production(self, user=None):
        if self.status != self.CONFIRMED:
            raise ValidationError(f"Cannot start production from {self.status} status.")
        
        # Check stock again before starting (issuing raw materials)
        insufficient_items = [
            item for item in self.items.select_related("raw_material").all()
            if item.raw_material.stock_quantity < item.quantity_required
        ]
        if insufficient_items:
            raise ValidationError("Not enough raw material stock to start production.")

        with db_transaction.atomic():
            for item in self.items.select_related("raw_material").all():
                Transaction.objects.create(
                    type=Transaction.ISSUE,
                    product=item.raw_material,
                    quantity=item.quantity_required,
                    reference_note=f"Production Order #{self.pk} Started",
                    user=user,
                )

            self.status = self.IN_PROGRESS
            self.started_by = user
            self.started_at = timezone.now()
            self.save(update_fields=["status", "started_by", "started_at"])

    def complete_production(self, user=None):
        if self.status != self.IN_PROGRESS:
            raise ValidationError(f"Cannot complete production from {self.status} status.")

        with db_transaction.atomic():
            Transaction.objects.create(
                type=Transaction.PRODUCE,
                product=self.finished_product,
                quantity=self.quantity,
                reference_note=f"Production Order #{self.pk} Completed",
                user=user,
            )

            self.status = self.COMPLETED
            self.completed_by = user
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_by", "completed_at"])

    def cancel_order(self, user=None):
        if self.status not in [self.DRAFT, self.CONFIRMED]:
            raise ValidationError(f"Cannot cancel order in {self.status} status.")
        
        self.status = self.CANCELLED
        self.cancelled_by = user
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_by", "cancelled_at"])


class ProductionOrderItem(models.Model):
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="production_order_items")
    quantity_required = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["raw_material__name"]
        unique_together = ("production_order", "raw_material")

    def __str__(self):
        return f"{self.production_order} needs {self.quantity_required} {self.raw_material.unit} of {self.raw_material.name}"


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    DRAFT = "draft"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (ORDERED, "Ordered"),
        (RECEIVED, "Received"),
        (CANCELLED, "Cancelled"),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_purchase_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"PO-{self.pk or 'new'} from {self.supplier.name}"

    def receive_goods(self, user=None):
        if self.status != self.ORDERED:
            raise ValidationError(f"Cannot receive goods for order in {self.status} status.")

        with db_transaction.atomic():
            for item in self.items.all():
                Transaction.objects.create(
                    type=Transaction.RECEIVE,
                    product=item.product,
                    quantity=item.quantity,
                    reference_note=f"Purchase Order #{self.pk} Received",
                    user=user,
                )

            self.status = self.RECEIVED
            self.received_at = timezone.now()
            self.save(update_fields=["status", "received_at"])


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="purchase_order_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} for {self.purchase_order}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price
