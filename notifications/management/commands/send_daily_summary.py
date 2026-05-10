from django.core.management.base import BaseCommand
from django.db.models import F
from inventory.models import Product
from notifications.models import WhatsAppRecipient
from notifications.utils import send_whatsapp

class Command(BaseCommand):
    help = 'Sends daily stock summary via WhatsApp to subscribed users'

    def handle(self, *args, **options):
        recipients = WhatsAppRecipient.objects.filter(is_active=True, daily_summary=True)
        
        if not recipients.exists():
            self.stdout.write("No recipients for daily summary.")
            return

        # Get top 5 critical raw materials (lowest stock relative to reorder level)
        critical_items = Product.objects.filter(
            is_raw_material=True,
            stock_quantity__lte=F('reorder_level') * 1.2 # Items below or near reorder level
        ).order_by('stock_quantity')[:5]

        if not critical_items.exists():
            message_body = "Factory ERP Daily Summary: All critical raw material levels are currently healthy. ✅"
        else:
            summary_list = "\n".join([
                f"- {item.name}: {item.stock_quantity} {item.unit} (Reorder: {item.reorder_level})"
                for item in critical_items
            ])
            message_body = f"Factory ERP Daily Summary 📊\n\nCritical Raw Materials:\n{summary_list}\n\nPlease check the dashboard for details."

        sent_count = 0
        for recipient in recipients:
            sid = send_whatsapp(recipient, 'daily', message_body)
            if sid:
                sent_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Successfully sent daily summary to {sent_count} recipients."))
