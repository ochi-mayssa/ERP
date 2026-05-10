from django import forms

from .models import Product, ProductionOrder, Transaction, Supplier, PurchaseOrder, PurchaseOrderItem


class BaseStyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            if getattr(field.widget, "input_type", "") == "checkbox":
                field.widget.attrs["class"] = f"{css_class} checkbox-input".strip()
            else:
                field.widget.attrs["class"] = f"{css_class} form-control".strip()


class ProductForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "unit", "stock_quantity", "reorder_level", "is_raw_material"]
        widgets = {
            "is_raw_material": forms.CheckboxInput(attrs={"class": "checkbox-input"}),
        }


class StockInForm(BaseStyledForm):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    reference_note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.all().order_by("name")


class StockOutForm(BaseStyledForm):
    movement_type = forms.ChoiceField(
        choices=[
            (Transaction.ISSUE, "Issue raw material to production"),
            (Transaction.SHIP, "Ship finished goods"),
        ]
    )
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    reference_note = forms.CharField(max_length=255, required=False)

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get("movement_type")
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")

        if not movement_type or not product or quantity is None:
            return cleaned_data

        if movement_type == Transaction.ISSUE and not product.is_raw_material:
            self.add_error("product", "Issue transactions must use a raw material product.")
        if movement_type == Transaction.SHIP and product.is_raw_material:
            self.add_error("product", "Ship transactions must use a finished product.")
        if product.stock_quantity < quantity:
            self.add_error("quantity", "Not enough stock available for this movement.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.order_by("name")


class ProduceForm(BaseStyledForm):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    reference_note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_raw_material=False).order_by("name")


class ProductionOrderForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ["finished_product", "quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["finished_product"].queryset = Product.objects.filter(is_raw_material=False).order_by("name")


class SupplierForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "email", "phone", "address"]


class PurchaseOrderForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier"]


class PurchaseOrderItemForm(BaseStyledForm, forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["product", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.all().order_by("name")


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True
)
