from rest_framework import generics

from .models import Product, Transaction
from .serializers import ProductSerializer, TransactionSerializer


class ProductListApiView(generics.ListAPIView):
    queryset = Product.objects.order_by("name")
    serializer_class = ProductSerializer


class TransactionListApiView(generics.ListAPIView):
    queryset = Transaction.objects.select_related("product", "user").order_by("-timestamp", "-id")
    serializer_class = TransactionSerializer
