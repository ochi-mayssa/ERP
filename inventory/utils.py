import os
import uuid
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

def generate_qr_code_value(product_id):
    """Generates a unique QR code value."""
    random_str = uuid.uuid4().hex[:6].upper()
    return f"PROD-{product_id}-{random_str}"

def save_qr_code_image(product):
    """Generates a QR code PNG image and returns the file path relative to MEDIA_ROOT."""
    if not QRCODE_AVAILABLE or not PILLOW_AVAILABLE:
        logger.warning("QR Code generation skipped: 'qrcode' or 'Pillow' library is not installed.")
        return None

    if not product.qr_code:
        product.qr_code = generate_qr_code_value(product.id)
        product.save(update_fields=['qr_code'])

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(product.qr_code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Ensure media directory exists
    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)

    file_name = f"{product.sku or product.id}.png"
    file_path = os.path.join(qr_dir, file_name)
    
    img.save(file_path)
    return f"qrcodes/{file_name}"

def calculate_product_unit_cost(product):
    """
    Calculates the unit cost of a finished product based on its BOM, 
    labor, and overhead.
    """
    if product.is_raw_material:
        return product.average_cost or 0

    material_cost = 0
    bom_items = product.bom_items.select_related('raw_material')
    
    for item in bom_items:
        # Use average_cost of raw material
        raw_cost = item.raw_material.average_cost or 0
        material_cost += (raw_cost * item.quantity_needed)

    # Labor Cost = hours * rate
    labor_cost = product.labor_hours_per_unit * product.labor_hourly_rate
    
    # Subtotal
    subtotal = material_cost + labor_cost
    
    # Overhead = subtotal * %
    overhead_cost = subtotal * (product.overhead_percentage / 100)
    
    total_cost = subtotal + overhead_cost
    
    return {
        'material_cost': material_cost,
        'labor_cost': labor_cost,
        'overhead_cost': overhead_cost,
        'total_cost': total_cost,
        'margin': (product.selling_price - total_cost) if product.selling_price else None
    }
