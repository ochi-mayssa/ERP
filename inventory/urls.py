from django.urls import path

from . import api_views, views

app_name = "inventory"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("search/", views.global_search, name="global_search"),
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("production-orders/", views.production_order_list, name="production_order_list"),
    path("production-orders/new/", views.production_order_create, name="production_order_create"),
    path("production-orders/preview/", views.production_order_preview, name="production_order_preview"),
    path("production-orders/<int:pk>/", views.production_order_detail, name="production_order_detail"),
    path("production-orders/<int:pk>/confirm/", views.production_order_confirm, name="production_order_confirm"),
    path("production-orders/<int:pk>/start/", views.production_order_start, name="production_order_start"),
    path("production-orders/<int:pk>/complete/", views.production_order_complete, name="production_order_complete"),
    path("production-orders/<int:pk>/cancel/", views.production_order_cancel, name="production_order_cancel"),
    path("stock-in/", views.stock_in, name="stock_in"),
    path("stock-out/", views.stock_out, name="stock_out"),
    path("produce/", views.produce_stock, name="produce_stock"),
    path("bom/", views.bom_viewer, name="bom_viewer"),
    path("reports/low-stock/", views.low_stock_report, name="low_stock_report"),
    path("transactions/", views.transaction_history, name="transaction_history"),
    path("transactions/export/", views.export_transactions_csv, name="export_transactions_csv"),
    path("api/products/", api_views.ProductListApiView.as_view(), name="api_products"),
    path("api/transactions/", api_views.TransactionListApiView.as_view(), name="api_transactions"),
    
    # User Management
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/toggle/", views.user_toggle_status, name="user_toggle_status"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),

    # Suppliers
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/new/", views.supplier_create, name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.supplier_edit, name="supplier_edit"),

    # Purchase Orders
    path("purchase-orders/", views.purchase_order_list, name="purchase_order_list"),
    path("purchase-orders/new/", views.purchase_order_create, name="purchase_order_create"),
    path("purchase-orders/<int:pk>/", views.purchase_order_detail, name="purchase_order_detail"),
    path("purchase-orders/<int:pk>/order/", views.purchase_order_order, name="purchase_order_order"),
    path("purchase-orders/<int:pk>/receive/", views.purchase_order_receive, name="purchase_order_receive"),
    path("purchase-orders/<int:pk>/cancel/", views.purchase_order_cancel, name="purchase_order_cancel"),

    # QR Scanning
    path("scan/", views.scan_page, name="scan_page"),
    path("scan/lookup/", views.scan_lookup, name="scan_lookup"),
    path("products/generate-qr-all/", views.generate_all_qrcodes, name="generate_all_qrcodes"),

    # Reports
    path("reports/profitability/", views.profitability_report, name="profitability_report"),
]
