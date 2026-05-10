from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    path('', views.crm_dashboard, name='dashboard'),
    
    # Leads
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/add/', views.LeadCreateView.as_view(), name='lead_create'),
    path('leads/<int:pk>/edit/', views.LeadUpdateView.as_view(), name='lead_edit'),
    path('leads/<int:pk>/convert/', views.convert_lead_to_customer, name='lead_convert'),
    
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    
    # Opportunities
    path('opportunities/', views.OpportunityListView.as_view(), name='opportunity_list'),
    path('opportunities/kanban/', views.OpportunityKanbanView.as_view(), name='opportunity_kanban'),
    path('opportunities/add/', views.OpportunityCreateView.as_view(), name='opportunity_create'),
    path('opportunities/<int:pk>/edit/', views.OpportunityUpdateView.as_view(), name='opportunity_edit'),
    path('opportunities/<int:pk>/update-stage/', views.update_opportunity_stage, name='opportunity_update_stage'),
    
    # Quotations
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),
    path('quotations/<int:pk>/', views.QuotationDetailView.as_view(), name='quotation_detail'),
    path('quotations/add/', views.QuotationCreateView.as_view(), name='quotation_create'),
    path('quotations/<int:pk>/pdf/', views.quotation_pdf, name='quotation_pdf'),
    
    # Sales Orders
    path('orders/', views.SalesOrderListView.as_view(), name='salesorder_list'),
    path('orders/<int:pk>/', views.SalesOrderDetailView.as_view(), name='salesorder_detail'),
    path('orders/add/', views.SalesOrderCreateView.as_view(), name='salesorder_create'),
    path('orders/<int:pk>/confirm/', views.confirm_sales_order, name='salesorder_confirm'),
    path('orders/<int:pk>/ship/', views.ship_sales_order, name='salesorder_ship'),
    path('orders/<int:pk>/invoice/', views.create_invoice_from_order, name='invoice_create_from_order'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    
    # Payments
    path('payments/add/', views.PaymentCreateView.as_view(), name='payment_create'),
    
    # Reports
    path('reports/pipeline/', views.sales_pipeline_report, name='report_pipeline'),
    path('reports/statement/<int:pk>/', views.customer_statement, name='report_statement'),
    path('reports/aging/', views.aging_report, name='report_aging'),
    path('reports/top-customers/', views.top_customers_report, name='report_top_customers'),
    path('reports/conversion/', views.conversion_report, name='report_conversion'),
]
