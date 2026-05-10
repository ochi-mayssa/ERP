from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from inventory.models import Product
from decimal import Decimal

User = get_user_model()

class Lead(models.Model):
    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('cold_call', 'Cold Call'),
        ('trade_show', 'Trade Show'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('lost', 'Lost'),
    ]

    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} ({self.contact_person})"

class Customer(models.Model):
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    customer_since = models.DateField(default=timezone.now)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_used = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=100, default="Net 30")
    tax_id = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    @property
    def remaining_credit(self):
        return self.credit_limit - self.credit_used

class Opportunity(models.Model):
    STAGE_CHOICES = [
        ('proposal_sent', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, limit_choices_to={'is_raw_material': False})
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    probability = models.IntegerField(default=50) # 0-100
    expected_close_date = models.DateField()
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='proposal_sent')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_opportunities')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_opportunities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_value(self):
        return self.quantity * self.unit_price

    def __str__(self):
        target = self.customer.company_name if self.customer else (self.lead.company_name if self.lead else "Unknown")
        return f"Opp: {target} - {self.product.name}"

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    quote_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quotations')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    valid_until = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    pdf_file = models.FileField(upload_to='quotations/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_quotations')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.quote_number:
            year = timezone.now().year
            last_quote = Quotation.objects.filter(quote_number__startswith=f'QT-{year}').order_by('-quote_number').first()
            if last_quote:
                last_num = int(last_quote.quote_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.quote_number = f'QT-{year}-{new_num:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.quote_number

    @property
    def total_amount(self):
        return sum(line.line_total for line in self.lines.all())

class QuotationLine(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def line_total(self):
        total = self.quantity * self.unit_price
        discount = total * (self.discount_percentage / Decimal('100'))
        return total - discount

class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_production', 'In Production'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_orders')
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    order_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            year = timezone.now().year
            last_order = SalesOrder.objects.filter(order_number__startswith=f'SO-{year}').order_by('-order_number').first()
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.order_number = f'SO-{year}-{new_num:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number

class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    quantity_shipped = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity_ordered * self.unit_price

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            last_invoice = Invoice.objects.filter(invoice_number__startswith=f'INV-{year}').order_by('-invoice_number').first()
            if last_invoice:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.invoice_number = f'INV-{year}-{new_num:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def is_overdue(self):
        return self.status != 'paid' and self.due_date < timezone.now().date()

class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_payments')

    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.invoice_number}"
