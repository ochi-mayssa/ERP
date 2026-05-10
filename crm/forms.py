from django import forms
from django.forms import inlineformset_factory
from .models import Lead, Customer, Opportunity, Quotation, QuotationLine, SalesOrder, SalesOrderLine, Invoice, Payment

class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

class LeadForm(BootstrapModelForm):
    class Meta:
        model = Lead
        fields = ['company_name', 'contact_person', 'email', 'phone', 'source', 'status', 'notes', 'assigned_to', 'estimated_value']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class CustomerForm(BootstrapModelForm):
    class Meta:
        model = Customer
        fields = ['company_name', 'contact_person', 'email', 'phone', 'customer_since', 'credit_limit', 'payment_terms', 'tax_id', 'is_active', 'notes', 'assigned_to']
        widgets = {
            'customer_since': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class OpportunityForm(BootstrapModelForm):
    class Meta:
        model = Opportunity
        fields = ['lead', 'customer', 'product', 'quantity', 'unit_price', 'probability', 'expected_close_date', 'stage', 'notes', 'assigned_to']
        widgets = {
            'expected_close_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class QuotationForm(BootstrapModelForm):
    class Meta:
        model = Quotation
        fields = ['customer', 'opportunity', 'valid_until', 'status']
        widgets = {
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
        }

class QuotationLineForm(BootstrapModelForm):
    class Meta:
        model = QuotationLine
        fields = ['product', 'quantity', 'unit_price', 'discount_percentage']

QuotationLineFormSet = inlineformset_factory(
    Quotation, QuotationLine, form=QuotationLineForm, extra=1, can_delete=True
)

class SalesOrderForm(BootstrapModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer', 'quotation', 'order_date', 'delivery_date', 'status', 'payment_status', 'notes']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class SalesOrderLineForm(BootstrapModelForm):
    class Meta:
        model = SalesOrderLine
        fields = ['product', 'quantity_ordered', 'unit_price']

SalesOrderLineFormSet = inlineformset_factory(
    SalesOrder, SalesOrderLine, form=SalesOrderLineForm, extra=1, can_delete=True
)

class InvoiceForm(BootstrapModelForm):
    class Meta:
        model = Invoice
        fields = ['sales_order', 'customer', 'invoice_date', 'due_date', 'total_amount', 'status']
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class PaymentForm(BootstrapModelForm):
    class Meta:
        model = Payment
        fields = ['invoice', 'amount', 'payment_date', 'method', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
