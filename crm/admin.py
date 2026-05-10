from django.contrib import admin
from .models import Lead, Customer, Opportunity, Quotation, QuotationLine, SalesOrder, SalesOrderLine, Invoice, Payment

class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 1

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('quote_number', 'customer', 'status', 'total_amount', 'created_at')
    inlines = [QuotationLineInline]

class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'status', 'total_amount', 'order_date')
    inlines = [SalesOrderLineInline]

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'status', 'source', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('company_name', 'contact_person', 'email')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'is_active', 'customer_since')
    search_fields = ('company_name', 'contact_person', 'email')

@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'stage', 'probability', 'total_value', 'expected_close_date')
    list_filter = ('stage',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'status', 'total_amount', 'balance_due', 'due_date')
    list_filter = ('status',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'payment_date', 'method')
