from rest_framework import serializers

from .models import Product, Transaction


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "unit",
            "stock_quantity",
            "reorder_level",
            "is_raw_material",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "type",
            "product",
            "product_name",
            "quantity",
            "reference_note",
            "timestamp",
            "username",
        ]
