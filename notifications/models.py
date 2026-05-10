from django.db import models
from django.conf import settings
from django.utils import timezone

class WhatsAppRecipient(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='whatsapp_settings')
    phone_number = models.CharField(max_length=20, help_text="Format: +countrycode_number (e.g., +14155238886)")
    is_active = models.BooleanField(default=True)
    
    # Notification Preferences
    low_stock_alerts = models.BooleanField(default=False)
    production_updates = models.BooleanField(default=False)
    purchase_approvals = models.BooleanField(default=False)
    goods_received = models.BooleanField(default=False)
    daily_summary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.phone_number})"

class WhatsAppMessage(models.Model):
    TYPES = [
        ('low_stock', 'Low Stock'),
        ('production', 'Production Update'),
        ('purchase', 'Purchase Order'),
        ('receipt', 'Goods Received'),
        ('daily', 'Daily Summary'),
        ('test', 'Test Message'),
    ]
    
    recipient = models.ForeignKey(WhatsAppRecipient, on_delete=models.CASCADE, related_name='messages')
    type = models.CharField(max_length=20, choices=TYPES)
    content = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='sent')
    twilio_sid = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.type} to {self.recipient.user.username} at {self.sent_at}"
