from django.contrib import admin

from .models import BomItem, Product, ProductionOrder, ProductionOrderItem, Transaction


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'unit', 'stock_quantity', 'reorder_level', 'is_raw_material')
    list_filter = ('is_raw_material',)
    search_fields = ('sku', 'name')


@admin.register(BomItem)
class BomItemAdmin(admin.ModelAdmin):
    list_display = ('finished_product', 'raw_material', 'quantity_needed')
    list_filter = ('finished_product',)
    search_fields = ('finished_product__name', 'raw_material__name')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'type', 'product', 'quantity', 'user', 'reference_note')
    list_filter = ('type', 'timestamp')
    search_fields = ('product__name', 'product__sku', 'reference_note')
    readonly_fields = ('created_at',)


class ProductionOrderItemInline(admin.TabularInline):
    model = ProductionOrderItem
    extra = 0
    readonly_fields = ("raw_material", "quantity_required")


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "finished_product", "quantity", "status", "created_by", "confirmed_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("finished_product__name",)
    readonly_fields = ("confirmed_at", "created_at")
    inlines = [ProductionOrderItemInline]
