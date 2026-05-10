from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q

from .models import Lead, Customer, Opportunity, Quotation, QuotationLine, SalesOrder, SalesOrderLine, Invoice, Payment
from .forms import (
    LeadForm, CustomerForm, OpportunityForm, QuotationForm, QuotationLineFormSet,
    SalesOrderForm, SalesOrderLineFormSet, InvoiceForm, PaymentForm
)
from inventory.models import Product, Transaction, ProductionOrder

# Lead Views
class LeadListView(LoginRequiredMixin, ListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    context_object_name = 'leads'
    ordering = ['-created_at']

class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = 'crm/lead_detail.html'

class LeadCreateView(LoginRequiredMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = 'crm/lead_form.html'
    success_url = reverse_lazy('crm:lead_list')

class LeadUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = 'crm/lead_form.html'
    success_url = reverse_lazy('crm:lead_list')

def convert_lead_to_customer(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if lead.status != 'qualified':
        lead.status = 'qualified'
        lead.save()
    
    # Check if customer already exists for this lead
    customer = Customer.objects.filter(email=lead.email).first()
    if not customer:
        customer = Customer.objects.create(
            company_name=lead.company_name,
            contact_person=lead.contact_person,
            email=lead.email,
            phone=lead.phone,
            notes=lead.notes,
            assigned_to=lead.assigned_to
        )
        messages.success(request, f"Lead converted to Customer: {customer.company_name}")
    else:
        messages.info(request, f"Customer already exists for {lead.email}")
    
    return redirect('crm:customer_detail', pk=customer.pk)

# Customer Views
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'crm/customer_list.html'
    context_object_name = 'customers'
    ordering = ['company_name']

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'crm/customer_detail.html'

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'crm/customer_form.html'
    success_url = reverse_lazy('crm:customer_list')

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'crm/customer_form.html'
    success_url = reverse_lazy('crm:customer_list')

# Opportunity Views
class OpportunityListView(LoginRequiredMixin, ListView):
    model = Opportunity
    template_name = 'crm/opportunity_list.html'
    context_object_name = 'opportunities'
    ordering = ['-created_at']

class OpportunityKanbanView(LoginRequiredMixin, ListView):
    model = Opportunity
    template_name = 'crm/opportunity_kanban.html'
    context_object_name = 'opportunities'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stages = dict(Opportunity.STAGE_CHOICES)
        context['stages'] = stages
        context['opportunities_by_stage'] = {
            stage: Opportunity.objects.filter(stage=stage) for stage in stages.keys()
        }
        return context

class OpportunityCreateView(LoginRequiredMixin, CreateView):
    model = Opportunity
    form_class = OpportunityForm
    template_name = 'crm/opportunity_form.html'
    success_url = reverse_lazy('crm:opportunity_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class OpportunityUpdateView(LoginRequiredMixin, UpdateView):
    model = Opportunity
    form_class = OpportunityForm
    template_name = 'crm/opportunity_form.html'
    success_url = reverse_lazy('crm:opportunity_list')

from .utils import generate_quotation_pdf, generate_invoice_pdf
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# Quotation Views
class QuotationListView(LoginRequiredMixin, ListView):
    model = Quotation
    template_name = 'crm/quotation_list.html'
    context_object_name = 'quotations'
    ordering = ['-created_at']

class QuotationDetailView(LoginRequiredMixin, DetailView):
    model = Quotation
    template_name = 'crm/quotation_detail.html'

class QuotationCreateView(LoginRequiredMixin, CreateView):
    model = Quotation
    form_class = QuotationForm
    template_name = 'crm/quotation_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['lines'] = QuotationLineFormSet(self.request.POST)
        else:
            data['lines'] = QuotationLineFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        lines = context['lines']
        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()
            if lines.is_valid():
                lines.instance = self.object
                lines.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('crm:quotation_detail', kwargs={'pk': self.object.pk})

def quotation_pdf(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    buffer = generate_quotation_pdf(quotation)
    return HttpResponse(buffer, content_type='application/pdf', 
                        headers={'Content-Disposition': f'attachment; filename="{quotation.quote_number}.pdf"'})

# Sales Order Views
class SalesOrderListView(LoginRequiredMixin, ListView):
    model = SalesOrder
    template_name = 'crm/salesorder_list.html'
    context_object_name = 'sales_orders'
    ordering = ['-created_at']

class SalesOrderDetailView(LoginRequiredMixin, DetailView):
    model = SalesOrder
    template_name = 'crm/salesorder_detail.html'

class SalesOrderCreateView(LoginRequiredMixin, CreateView):
    model = SalesOrder
    form_class = SalesOrderForm
    template_name = 'crm/salesorder_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['lines'] = SalesOrderLineFormSet(self.request.POST)
        else:
            data['lines'] = SalesOrderLineFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        lines = context['lines']
        with transaction.atomic():
            self.object = form.save()
            if lines.is_valid():
                lines.instance = self.object
                lines.save()
            
            # Calculate total amount
            self.object.total_amount = sum(line.line_total for line in self.object.lines.all())
            self.object.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('crm:salesorder_detail', kwargs={'pk': self.object.pk})

def confirm_sales_order(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if order.status == 'draft':
        order.status = 'confirmed'
        order.save()
        
        # Auto-create Production Orders for items that need manufacturing
        for line in order.lines.all():
            if line.product.bom_items.exists():
                ProductionOrder.objects.create(
                    finished_product=line.product,
                    quantity=line.quantity_ordered,
                    status='draft',
                    created_by=request.user
                )
        messages.success(request, f"Sales Order {order.order_number} confirmed and production orders created.")
    return redirect('crm:salesorder_detail', pk=pk)

def ship_sales_order(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if order.status in ['confirmed', 'in_production']:
        with transaction.atomic():
            for line in order.lines.all():
                if line.product.stock_quantity < line.quantity_ordered:
                    messages.error(request, f"Not enough stock for {line.product.name}")
                    return redirect('crm:salesorder_detail', pk=pk)
                
                # Create SHIP transaction
                Transaction.objects.create(
                    type=Transaction.SHIP,
                    product=line.product,
                    quantity=line.quantity_ordered,
                    reference_note=f"Sales Order {order.order_number}",
                    user=request.user
                )
                line.quantity_shipped = line.quantity_ordered
                line.save()
            
            order.status = 'shipped'
            order.save()
            messages.success(request, f"Sales Order {order.order_number} shipped.")
    return redirect('crm:salesorder_detail', pk=pk)

# Invoice Views
class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'crm/invoice_list.html'
    context_object_name = 'invoices'
    ordering = ['-invoice_date']

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'crm/invoice_detail.html'

def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    buffer = generate_invoice_pdf(invoice)
    return HttpResponse(buffer, content_type='application/pdf', 
                        headers={'Content-Disposition': f'attachment; filename="{invoice.invoice_number}.pdf"'})

def create_invoice_from_order(request, order_pk):
    order = get_object_or_404(SalesOrder, pk=order_pk)
    invoice = Invoice.objects.create(
        sales_order=order,
        customer=order.customer,
        invoice_date=timezone.now().date(),
        due_date=timezone.now().date() + timezone.timedelta(days=30),
        total_amount=order.total_amount,
        status='draft'
    )
    messages.success(request, f"Invoice {invoice.invoice_number} created from order {order.order_number}")
    return redirect('crm:invoice_detail', pk=invoice.pk)

# Payment Views
class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'crm/payment_form.html'

    def form_valid(self, form):
        with transaction.atomic():
            payment = form.save()
            invoice = payment.invoice
            invoice.amount_paid += payment.amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
            invoice.save()
            
            # Update customer credit used
            customer = invoice.customer
            customer.credit_used += payment.amount
            customer.save()
            
            messages.success(self.request, f"Payment recorded for invoice {invoice.invoice_number}")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('crm:invoice_detail', kwargs={'pk': self.object.invoice.pk})

# Dashboard View
def crm_dashboard(request):
    last_7_days = timezone.now() - timezone.timedelta(days=7)
    last_30_days = timezone.now() - timezone.timedelta(days=30)
    
    new_leads = Lead.objects.filter(created_at__gte=last_7_days).count()
    won_opportunities = Opportunity.objects.filter(stage='won', updated_at__gte=last_30_days).count()
    overdue_invoices = Invoice.objects.filter(due_date__lt=timezone.now().date()).exclude(status='paid').count()
    
    top_customers = Customer.objects.annotate(
        total_sales=Sum('sales_orders__total_amount')
    ).order_by('-total_sales')[:5]
    
    pipeline_data = {
        'leads': Lead.objects.count(),
        'opportunities': Opportunity.objects.count(),
        'quotations': Quotation.objects.count(),
        'orders': SalesOrder.objects.count(),
    }
    
    context = {
        'new_leads': new_leads,
        'won_opportunities': won_opportunities,
        'overdue_invoices': overdue_invoices,
        'top_customers': top_customers,
        'pipeline_data': pipeline_data,
    }
    return render(request, 'crm/dashboard.html', context)

# Reports
def sales_pipeline_report(request):
    stages = dict(Opportunity.STAGE_CHOICES)
    report_data = []
    for stage_code, stage_name in stages.items():
        opps = Opportunity.objects.filter(stage=stage_code)
        total_value = sum(opp.total_value for opp in opps)
        report_data.append({
            'stage': stage_name,
            'count': opps.count(),
            'value': total_value
        })
    return render(request, 'crm/reports/pipeline.html', {'report_data': report_data})

def customer_statement(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    invoices = customer.invoices.all().order_by('invoice_date')
    payments = Payment.objects.filter(invoice__customer=customer).order_by('payment_date')
    
    # Combine into a timeline
    statement_items = []
    for inv in invoices:
        statement_items.append({'date': inv.invoice_date, 'type': 'Invoice', 'ref': inv.invoice_number, 'amount': inv.total_amount, 'balance_effect': inv.total_amount})
    for pmnt in payments:
        statement_items.append({'date': pmnt.payment_date, 'type': 'Payment', 'ref': f"PMT for {pmnt.invoice.invoice_number}", 'amount': pmnt.amount, 'balance_effect': -pmnt.amount})
    
    statement_items.sort(key=lambda x: x['date'])
    
    current_balance = 0
    for item in statement_items:
        current_balance += item['balance_effect']
        item['running_balance'] = current_balance
        
    return render(request, 'crm/reports/statement.html', {
        'customer': customer,
        'statement_items': statement_items,
        'total_balance': current_balance
    })

def aging_report(request):
    today = timezone.now().date()
    overdue_invoices = Invoice.objects.filter(due_date__lt=today).exclude(status='paid')
    
    aging_data = {
        '30_days': overdue_invoices.filter(due_date__gte=today - timezone.timedelta(days=30)),
        '60_days': overdue_invoices.filter(due_date__lt=today - timezone.timedelta(days=30), due_date__gte=today - timezone.timedelta(days=60)),
        '90_days': overdue_invoices.filter(due_date__lt=today - timezone.timedelta(days=60), due_date__gte=today - timezone.timedelta(days=90)),
        'over_90': overdue_invoices.filter(due_date__lt=today - timezone.timedelta(days=90)),
    }
    
    summary = {k: sum(inv.balance_due for inv in v) for k, v in aging_data.items()}
    summary['total'] = sum(summary.values())
    
    return render(request, 'crm/reports/aging.html', {
        'aging_data': aging_data,
        'summary': summary,
        'today': today
    })

def top_customers_report(request):
    # Top by revenue
    top_revenue = Customer.objects.annotate(
        revenue=Sum('sales_orders__total_amount')
    ).filter(revenue__gt=0).order_by('-revenue')[:10]
    
    # Simple profit margin estimation (selling price - average cost)
    # This is a complex query, simplified for now
    top_margin = Customer.objects.annotate(
        total_orders=Count('sales_orders')
    ).filter(total_orders__gt=0)[:10]
    
    return render(request, 'crm/reports/top_customers.html', {
        'top_revenue': top_revenue,
        'top_margin': top_margin
    })

def conversion_report(request):
    total_leads = Lead.objects.count()
    qualified_leads = Lead.objects.filter(status='qualified').count()
    
    # Assuming conversion means lead became a customer (we check if email exists in Customer)
    # This is an approximation
    customers_from_leads = Customer.objects.filter(email__in=Lead.objects.values_list('email', flat=True)).count()
    
    conversion_rate = (customers_from_leads / total_leads * 100) if total_leads > 0 else 0
    
    return render(request, 'crm/reports/conversion.html', {
        'total_leads': total_leads,
        'qualified_leads': qualified_leads,
        'converted_count': customers_from_leads,
        'conversion_rate': round(conversion_rate, 2)
    })

@login_required
@require_POST
def update_opportunity_stage(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk)
    stage = request.POST.get('stage')
    if stage in dict(Opportunity.STAGE_CHOICES):
        opportunity.stage = stage
        opportunity.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid stage'}, status=400)
