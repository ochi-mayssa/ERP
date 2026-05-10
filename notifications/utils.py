import logging
from django.conf import settings
from .models import WhatsAppMessage, WhatsAppRecipient

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

logger = logging.getLogger(__name__)

def send_whatsapp(recipient, message_type, message_body):
    """
    Sends a WhatsApp message using Twilio and logs it in the database.
    recipient: WhatsAppRecipient instance
    message_type: choice from WhatsAppMessage.TYPES
    message_body: string content of the message
    """
    if not getattr(settings, 'WHATSAPP_ENABLED', False) or not TWILIO_AVAILABLE:
        if not TWILIO_AVAILABLE and getattr(settings, 'WHATSAPP_ENABLED', False):
            logger.warning("WhatsApp is enabled but 'twilio' library is not installed.")
        return None

    sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)

    if not all([sid, token, from_number]):
        logger.warning("Twilio credentials missing. WhatsApp message not sent.")
        return None

    if not recipient.is_active:
        return None

    try:
        client = Client(sid, token)
        message = client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=message_body,
            to=f'whatsapp:{recipient.phone_number}'
        )
        
        # Log the message
        WhatsAppMessage.objects.create(
            recipient=recipient,
            type=message_type,
            content=message_body,
            twilio_sid=message.sid,
            status='sent'
        )
        return message.sid
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {str(e)}")
        # Optionally log failed message to DB
        WhatsAppMessage.objects.create(
            recipient=recipient,
            type=message_type,
            content=message_body,
            status='failed'
        )
        return None
