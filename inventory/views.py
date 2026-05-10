import csv
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from notifications.models import WhatsAppRecipient
from notifications.utils import send_whatsapp

from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum, Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

from .forms import ProduceForm, ProductForm, ProductionOrderForm, StockInForm, StockOutForm, SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet
from .models import BomItem, Product, ProductionOrder, Transaction, Supplier, PurchaseOrder, PurchaseOrderItem

from crm.models import Lead, Opportunity, Quotation, SalesOrder, Invoice, Customer

@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    results = {
        'products': [],
        'customers': [],
        'leads': [],
        'orders': [],
        'invoices': []
    }
    
    if query:
        results['products'] = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )[:5]
        results['customers'] = Customer.objects.filter(
            Q(company_name__icontains=query) | Q(contact_person__icontains=query)
        )[:5]
        results['leads'] = Lead.objects.filter(
            Q(company_name__icontains=query) | Q(contact_person__icontains=query)
        )[:5]
        results['orders'] = SalesOrder.objects.filter(
            Q(order_number__icontains=query)
        )[:5]
        results['invoices'] = Invoice.objects.filter(
            Q(invoice_number__icontains=query)
        )[:5]
        
    return render(request, 'inventory/search_results.html', {'query': query, 'results': results})

@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def dashboard(request):
    # Section 1: Alert Cards
    low_stock_products = Product.objects.filter(stock_quantity__lte=F("reorder_level"))
    low_stock_count = low_stock_products.count()
    active_production_orders = ProductionOrder.objects.filter(
        status__in=[ProductionOrder.CONFIRMED, ProductionOrder.IN_PROGRESS]
    ).count()
    
    # Section 2: CRM Metrics
    today = timezone.now().date()
    last_30_days_date = today - timedelta(days=30)
    monthly_revenue = Invoice.objects.filter(
        invoice_date__gte=today.replace(day=1),
        status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    pending_purchase_count = PurchaseOrder.objects.filter(status__in=['draft', 'sent']).count()
    
    pipeline_data = {
        'leads': Lead.objects.count(),
        'opportunities': Opportunity.objects.count(),
        'quotations': Quotation.objects.count(),
        'orders': SalesOrder.objects.count(),
    }

    # Section 3: Recent Items
    recent_production_orders = ProductionOrder.objects.select_related(
        "finished_product"
    ).order_by("-created_at")[:5]

    recent_transactions = Transaction.objects.select_related(
        "product", "user"
    ).order_by("-timestamp", "-id")[:10]

    context = {
        "low_stock_count": low_stock_count,
        "active_production_orders": active_production_orders,
        "pending_purchase_count": pending_purchase_count,
        "monthly_revenue": monthly_revenue,
        "low_stock_products": low_stock_products.order_by("stock_quantity")[:10],
        "recent_production_orders": recent_production_orders,
        "recent_transactions": recent_transactions,
        "pipeline_data": pipeline_data,
    }
    return render(request, "inventory/dashboard.html", context)


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def product_list(request):
    products = Product.objects.order_by("name")
    return render(request, "inventory/product_list.html", {"products": products})


@login_required
@permission_required("inventory.can_manage_products", raise_exception=True)
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product saved successfully.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm()

    return render(request, "inventory/product_form.html", {"form": form})


@login_required
@permission_required("inventory.can_manage_stock", raise_exception=True)
def stock_in(request):
    if request.method == "POST":
        form = StockInForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            quantity = form.cleaned_data["quantity"]
            Transaction.objects.create(
                type=Transaction.RECEIVE,
                product=product,
                quantity=quantity,
                reference_note=form.cleaned_data["reference_note"],
                user=request.user,
            )
            
            # WhatsApp Alert for Low Stock (if applicable after stock in)
            product.refresh_from_db()
            if product.is_low_stock:
                recipients = WhatsAppRecipient.objects.filter(is_active=True, low_stock_alerts=True)
                for recipient in recipients:
                    send_whatsapp(
                        recipient, 
                        'low_stock', 
                        f"⚠️ LOW STOCK ALERT: {product.name} is at {product.stock_quantity} {product.unit} (Reorder level: {product.reorder_level})."
                    )

            messages.success(request, "Stock-in transaction recorded.")
            return redirect("inventory:product_list")
    else:
        initial = {}
        product_id = request.GET.get("product")
        if product_id:
            initial["product"] = product_id
        form = StockInForm(initial=initial)

    return render(request, "inventory/stock_in.html", {"form": form})


@login_required
@permission_required("inventory.can_manage_stock", raise_exception=True)
def stock_out(request):
    if request.method == "POST":
        form = StockOutForm(request.POST)
        if form.is_valid():
            Transaction.objects.create(
                type=form.cleaned_data["movement_type"],
                product=form.cleaned_data["product"],
                quantity=form.cleaned_data["quantity"],
                reference_note=form.cleaned_data["reference_note"],
                user=request.user,
            )
            messages.success(request, "Stock-out transaction recorded.")
            return redirect("inventory:product_list")
    else:
        form = StockOutForm()

    return render(request, "inventory/stock_out.html", {"form": form})


@login_required
@permission_required("inventory.can_manage_stock", raise_exception=True)
def produce_stock(request):
    if request.method == "POST":
        form = ProduceForm(request.POST)
        if form.is_valid():
            Transaction.objects.create(
                type=Transaction.PRODUCE,
                product=form.cleaned_data["product"],
                quantity=form.cleaned_data["quantity"],
                reference_note=form.cleaned_data["reference_note"],
                user=request.user,
            )
            messages.success(request, "Production transaction recorded.")
            return redirect("inventory:product_list")
    else:
        form = ProduceForm()

    return render(request, "inventory/produce.html", {"form": form})


def _build_production_preview(form):
    preview_order = None
    requirements = []
    stock_ready = False
    preview_error = None

    if form.is_bound and form.is_valid():
        preview_order = ProductionOrder(
            finished_product=form.cleaned_data["finished_product"],
            quantity=form.cleaned_data["quantity"],
        )
        try:
            preview_order.full_clean()
            requirements = preview_order.calculate_requirements()
            if not requirements:
                preview_error = "This finished product does not have any BOM items yet."
            stock_ready = bool(requirements) and all(item["enough_stock"] for item in requirements)
        except ValidationError as exc:
            preview_error = " ".join(exc.messages)

    return {
        "preview_order": preview_order,
        "requirements": requirements,
        "stock_ready": stock_ready,
        "preview_error": preview_error,
    }


def _order_has_shortage(order):
    return any(item.raw_material.stock_quantity < item.quantity_required for item in order.items.all())


def _production_order_list_context(request):
    base_queryset = ProductionOrder.objects.select_related(
        "finished_product", "created_by", "confirmed_by"
    ).prefetch_related("items__raw_material")

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    shortages_only = request.GET.get("shortages") == "1"

    if search:
        base_queryset = base_queryset.filter(
            Q(finished_product__name__icontains=search)
            | Q(finished_product__sku__icontains=search)
            | Q(created_by__username__icontains=search)
        )
    if status in {ProductionOrder.DRAFT, ProductionOrder.CONFIRMED, ProductionOrder.IN_PROGRESS, ProductionOrder.COMPLETED, ProductionOrder.CANCELLED}:
        base_queryset = base_queryset.filter(status=status)

    orders = list(base_queryset.order_by("-created_at", "-id"))
    for order in orders:
        order.has_shortage = _order_has_shortage(order)

    if shortages_only:
        orders = [order for order in orders if order.has_shortage]

    all_orders = list(
        ProductionOrder.objects.select_related("finished_product").prefetch_related("items__raw_material").all()
    )
    summary = {
        "total_orders": len(all_orders),
        "draft_orders": sum(1 for order in all_orders if order.status == ProductionOrder.DRAFT),
        "confirmed_orders": sum(1 for order in all_orders if order.status == ProductionOrder.CONFIRMED),
        "in_progress_orders": sum(1 for order in all_orders if order.status == ProductionOrder.IN_PROGRESS),
        "completed_orders": sum(1 for order in all_orders if order.status == ProductionOrder.COMPLETED),
        "shortage_orders": sum(1 for order in all_orders if _order_has_shortage(order)),
    }

    return {
        "orders": orders,
        "search": search,
        "status_filter": status,
        "shortages_only": shortages_only,
        **summary,
    }


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def production_order_list(request):
    context = _production_order_list_context(request)
    if request.headers.get("HX-Request") == "true":
        return render(request, "inventory/partials/production_order_table.html", context)
    return render(request, "inventory/production_order_list.html", context)


@login_required
@permission_required("inventory.can_manage_production", raise_exception=True)
def production_order_create(request):
    if request.method == "POST":
        form = ProductionOrderForm(request.POST)
        preview_context = _build_production_preview(form)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            try:
                order.full_clean()
                order.save()
                order.populate_items_from_bom()
                messages.success(request, "Production order created.")
                return redirect("inventory:production_order_detail", pk=order.pk)
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
    else:
        form = ProductionOrderForm()
        preview_context = _build_production_preview(form)

    context = {"form": form, **preview_context}
    return render(request, "inventory/production_order_form.html", context)


@login_required
def production_order_preview(request):
    form = ProductionOrderForm(request.GET or None)
    context = {"form": form, **_build_production_preview(form)}
    return render(request, "inventory/partials/production_order_preview.html", context)


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def production_order_detail(request, pk):
    order = get_object_or_404(
        ProductionOrder.objects.select_related("finished_product", "created_by", "confirmed_by"),
        pk=pk,
    )
    items = order.items.select_related("raw_material").order_by("raw_material__name")
    requirements = [
        {
            "raw_material": item.raw_material,
            "quantity_required": item.quantity_required,
            "quantity_available": item.raw_material.stock_quantity,
            "enough_stock": item.raw_material.stock_quantity >= item.quantity_required,
        }
        for item in items
    ]
    can_confirm = order.status == ProductionOrder.DRAFT and bool(requirements) and all(
        item["enough_stock"] for item in requirements
    )
    
    cost_data = calculate_product_unit_cost(order.finished_product)
    
    return render(
        request,
        "inventory/production_order_detail.html",
        {
            "order": order,
            "requirements": requirements,
            "can_confirm": can_confirm,
            "cost_data": cost_data,
        },
    )


@login_required
@permission_required("inventory.can_manage_production", raise_exception=True)
@require_POST
def production_order_confirm(request, pk):
    order = get_object_or_404(ProductionOrder, pk=pk)
    try:
        order.confirm(user=request.user)
        messages.success(request, "Production order confirmed.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("inventory:production_order_detail", pk=order.pk)


@login_required
@permission_required("inventory.can_manage_production", raise_exception=True)
@require_POST
def production_order_start(request, pk):
    order = get_object_or_404(ProductionOrder, pk=pk)
    try:
        order.start_production(user=request.user)
        messages.success(request, "Production started and raw materials issued.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("inventory:production_order_detail", pk=order.pk)


@login_required
@permission_required("inventory.can_manage_production", raise_exception=True)
@require_POST
def production_order_complete(request, pk):
    order = get_object_or_404(ProductionOrder, pk=pk)
    try:
        order.complete_production(user=request.user)
        
        # WhatsApp Alert for Production Completion
        recipients = WhatsAppRecipient.objects.filter(is_active=True, production_updates=True)
        for recipient in recipients:
            send_whatsapp(
                recipient,
                'production',
                f"✅ PRODUCTION COMPLETED: Order PO-{order.pk} for {order.finished_product.name} (Qty: {order.quantity}) is finished."
            )

        messages.success(request, "Production completed and finished goods added to stock.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("inventory:production_order_detail", pk=order.pk)


@login_required
@permission_required("inventory.can_manage_production", raise_exception=True)
@require_POST
def production_order_cancel(request, pk):
    order = get_object_or_404(ProductionOrder, pk=pk)
    try:
        order.cancel_order(user=request.user)
        messages.success(request, "Production order cancelled.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("inventory:production_order_detail", pk=order.pk)


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def bom_viewer(request):
    finished_products = Product.objects.filter(is_raw_material=False).order_by("name")
    selected_product = None
    bom_items = BomItem.objects.none()

    selected_product_id = request.GET.get("finished_product")
    if selected_product_id:
        selected_product = get_object_or_404(Product, pk=selected_product_id, is_raw_material=False)
        bom_items = selected_product.bom_items.select_related("raw_material").order_by("raw_material__name")

    context = {
        "finished_products": finished_products,
        "selected_product": selected_product,
        "bom_items": bom_items,
    }

    if selected_product:
        cost_info = calculate_product_unit_cost(selected_product)
        context["total_cost"] = cost_info["total_cost"]

    if request.headers.get("HX-Request") == "true":
        return render(request, "inventory/partials/bom_table.html", context)

    return render(request, "inventory/bom_viewer.html", context)


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def low_stock_report(request):
    products = Product.objects.filter(stock_quantity__lt=F("reorder_level")).order_by("name")
    return render(request, "inventory/low_stock_report.html", {"products": products})


def _filter_transactions(request):
    """Helper to apply common filters to transactions queryset."""
    queryset = Transaction.objects.select_related("product", "user").order_by("-timestamp", "-id")
    
    # Example filters (can be expanded based on request.GET)
    product_id = request.GET.get("product")
    if product_id:
        queryset = queryset.filter(product_id=product_id)
        
    tx_type = request.GET.get("type")
    if tx_type:
        queryset = queryset.filter(type=tx_type)
        
    start_date = request.GET.get("start_date")
    if start_date:
        queryset = queryset.filter(timestamp__date__gte=start_date)
        
    end_date = request.GET.get("end_date")
    if end_date:
        queryset = queryset.filter(timestamp__date__lte=end_date)
        
    return queryset


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def transaction_history(request):
    transactions = _filter_transactions(request)
    return render(request, "inventory/transaction_list.html", {"transactions": transactions})


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def export_transactions_csv(request):
    """Export filtered transactions to CSV."""
    try:
        transactions = _filter_transactions(request)
        
        response = HttpResponse(content_type='text/csv')
        filename = f"transactions_{timezone.now().strftime('%Y-%m-%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        # Header row
        writer.writerow(['Date', 'Transaction Type', 'Product SKU', 'Product Name', 'Quantity', 'Reference Note', 'User'])
        
        if not transactions.exists():
            writer.writerow(['No data available', '', '', '', '', '', ''])
            return response

        for tx in transactions:
            writer.writerow([
                tx.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                tx.get_type_display(),
                tx.product.sku,
                tx.product.name,
                tx.signed_quantity,
                tx.reference_note or '-',
                tx.user.username if tx.user else 'System'
            ])
            
        return response
    except Exception as e:
        # Fallback to headers only if something fails
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions_error.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Transaction Type', 'Product SKU', 'Product Name', 'Quantity', 'Reference Note', 'User'])
        writer.writerow(['Error occurred during export', str(e), '', '', '', '', ''])
        return response


from django.contrib.auth.models import User, Group

@login_required
@permission_required("inventory.can_manage_users", raise_exception=True)
def user_list(request):
    users = User.objects.all().prefetch_related("groups")
    return render(request, "inventory/user_list.html", {"users": users})


@login_required
@permission_required("inventory.can_manage_users", raise_exception=True)
def user_create(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role_id = request.POST.get("role")
        
        user = User.objects.create_user(username=username, email=email, password=password)
        if role_id:
            role = Group.objects.get(id=role_id)
            user.groups.add(role)
            if role.name == 'Admin':
                user.is_staff = True
                user.save()
        
        messages.success(request, f"User {username} created successfully.")
        return redirect("inventory:user_list")
    
    roles = Group.objects.all()
    return render(request, "inventory/user_form.html", {"roles": roles})


@login_required
@permission_required("inventory.can_manage_users", raise_exception=True)
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        role_id = request.POST.get("role")
        is_active = request.POST.get("is_active") == "on"
        
        user.groups.clear()
        if role_id:
            role = Group.objects.get(id=role_id)
            user.groups.add(role)
            user.is_staff = (role.name == 'Admin')
        
        user.is_active = is_active
        user.save()
        
        messages.success(request, f"User {user.username} updated.")
        return redirect("inventory:user_list")
    
    roles = Group.objects.all()
    user_role = user.groups.first()
    return render(request, "inventory/user_form.html", {"edit_user": user, "roles": roles, "user_role": user_role})


@login_required
@permission_required("inventory.can_manage_users", raise_exception=True)
def user_toggle_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot deactivate yourself.")
    else:
        user.is_active = not user.is_active
        user.save()
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f"User {user.username} has been {status}.")
    return redirect("inventory:user_list")


@login_required
@permission_required("inventory.can_manage_users", raise_exception=True)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete yourself.")
        return redirect("inventory:user_list")
    
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted.")
        return redirect("inventory:user_list")
    
    return render(request, "inventory/user_confirm_delete.html", {"user_to_delete": user})


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by("name")
    return render(request, "inventory/supplier_list.html", {"suppliers": suppliers})


@login_required
@permission_required("inventory.can_manage_purchase", raise_exception=True)
def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier added successfully.")
            return redirect("inventory:supplier_list")
    else:
        form = SupplierForm()
    return render(request, "inventory/supplier_form.html", {"form": form})


@login_required
@permission_required("inventory.can_manage_purchase", raise_exception=True)
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier updated successfully.")
            return redirect("inventory:supplier_list")
    else:
        form = SupplierForm(instance=supplier)
    return render(request, "inventory/supplier_form.html", {"form": form, "supplier": supplier})


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def purchase_order_list(request):
    orders = PurchaseOrder.objects.select_related("supplier", "created_by").order_by("-created_at")
    return render(request, "inventory/purchase_order_list.html", {"orders": orders})


@login_required
@permission_required("inventory.can_manage_purchase", raise_exception=True)
def purchase_order_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with db_transaction.atomic():
                order = form.save(commit=False)
                order.created_by = request.user
                order.save()
                formset.instance = order
                formset.save()
                
                # Calculate total amount
                total = sum(item.quantity * item.unit_price for item in order.items.all())
                order.total_amount = total
                order.save(update_fields=["total_amount"])
                
                messages.success(request, "Purchase Order created.")
                return redirect("inventory:purchase_order_detail", pk=order.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    return render(request, "inventory/purchase_order_form.html", {"form": form, "formset": formset})


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def purchase_order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder.objects.select_related("supplier", "created_by"), pk=pk)
    items = order.items.select_related("product")
    return render(request, "inventory/purchase_order_detail.html", {"order": order, "items": items})


@login_required
@permission_required("inventory.can_manage_purchase", raise_exception=True)
def purchase_order_order(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status == PurchaseOrder.DRAFT:
        order.status = PurchaseOrder.ORDERED
        order.ordered_at = timezone.now()
        order.save(update_fields=["status", "ordered_at"])
        
        # WhatsApp Alert for PO Approval/Sent
        recipients = WhatsAppRecipient.objects.filter(is_active=True, purchase_approvals=True)
        for recipient in recipients:
            send_whatsapp(
                recipient,
                'purchase',
                f"🛒 PO ORDERED: Purchase Order PO-{order.pk} to {order.supplier.name} for ${order.total_amount} is now active."
            )

        messages.success(request, "Purchase Order marked as Ordered.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


from .utils import calculate_product_unit_cost, save_qr_code_image


@login_required
@permission_required("inventory.can_manage_stock", raise_exception=True)
def purchase_order_receive(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        with db_transaction.atomic():
            for item in order.items.select_related("product").all():
                product = item.product
                old_qty = product.stock_quantity
                old_cost = product.average_cost or 0
                new_qty = item.quantity
                new_cost = item.unit_price
                
                # Update average cost: (old_avg * old_qty + new_cost * new_qty) / (old_qty + new_qty)
                total_qty = old_qty + new_qty
                if total_qty > 0:
                    product.average_cost = (old_cost * old_qty + new_cost * new_qty) / total_qty
                    product.save(update_fields=["average_cost"])

            order.receive_goods(user=request.user)
        
        # WhatsApp Alert for Goods Received
        recipients = WhatsAppRecipient.objects.filter(is_active=True, goods_received=True)
        for recipient in recipients:
            send_whatsapp(
                recipient,
                'receipt',
                f"📦 GOODS RECEIVED: Purchase Order PO-{order.pk} from {order.supplier.name} has been received and stock updated."
            )

        messages.success(request, "Goods received and stock updated.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@login_required
@permission_required("inventory.can_manage_purchase", raise_exception=True)
def purchase_order_cancel(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status in [PurchaseOrder.DRAFT, PurchaseOrder.ORDERED]:
        order.status = PurchaseOrder.CANCELLED
        order.save(update_fields=["status"])
        messages.success(request, "Purchase Order cancelled.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def scan_page(request):
    return render(request, "inventory/scan_dashboard.html")


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def scan_lookup(request):
    qr_value = request.GET.get("qr_code")
    mode = request.GET.get("mode", "lookup")
    
    product = Product.objects.filter(qr_code=qr_value).first()
    
    if not product:
        if mode == "lookup":
            return HttpResponse(
                '<div class="alert alert-danger mt-3">'
                '<i class="fas fa-times-circle me-2"></i>'
                f'Product not found for QR: <strong>{qr_value}</strong>'
                '</div>'
            )
        else:
            messages.error(request, f"Product not found for scanned code: {qr_value}")
            return redirect("inventory:scan_page")
    
    # Check for specific redirect modes
    if mode == "stock_in":
        return redirect(f"/inventory/stock-in/?product={product.id}")
    elif mode == "stock_out":
        return redirect(f"/inventory/stock-out/?product={product.id}")
    elif mode == "production":
        return redirect(f"/inventory/production-orders/new/?product={product.id}")
    
    # Default: Show cost breakdown in partial (HTMX)
    cost_data = calculate_product_unit_cost(product)
    return render(request, "inventory/partials/product_cost_detail.html", {
        "product": product,
        "cost_data": cost_data
    })


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def profitability_report(request):
    products = Product.objects.filter(is_raw_material=False).order_by("name")
    report_data = []
    
    for product in products:
        cost_info = calculate_product_unit_cost(product)
        # Get production qty in last 30 days
        last_30_days = timezone.now() - timedelta(days=30)
        prod_qty = Transaction.objects.filter(
            product=product, 
            type=Transaction.PRODUCE,
            timestamp__gte=last_30_days
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        report_data.append({
            'product': product,
            'cost': cost_info['total_cost'],
            'price': product.selling_price,
            'profit': cost_info['margin'],
            'margin_pct': (cost_info['margin'] / product.selling_price * 100) if product.selling_price and cost_info['margin'] else 0,
            'prod_qty': prod_qty,
            'total_profit': (cost_info['margin'] * prod_qty) if cost_info['margin'] else 0
        })
        
    return render(request, "inventory/profitability_report.html", {"report_data": report_data})


@login_required
@permission_required("inventory.can_manage_products", raise_exception=True)
def generate_all_qrcodes(request):
    from .utils import QRCODE_AVAILABLE, PILLOW_AVAILABLE
    if not QRCODE_AVAILABLE or not PILLOW_AVAILABLE:
        messages.error(request, "QR code generation requires 'qrcode' and 'Pillow' libraries to be installed.")
        return redirect("inventory:product_list")
        
    products = Product.objects.filter(qr_code__isnull=True)
    count = 0
    for product in products:
        if save_qr_code_image(product):
            count += 1
    messages.success(request, f"Generated {count} new QR codes.")
    return redirect("inventory:product_list")


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    # Ensure QR code exists
    qr_path = save_qr_code_image(product)
    cost_data = calculate_product_unit_cost(product)
    return render(request, "inventory/product_detail.html", {
        "product": product, 
        "qr_path": qr_path,
        "cost_data": cost_data
    })

