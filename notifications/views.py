from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WhatsAppRecipient, WhatsAppMessage
from .utils import send_whatsapp

@login_required
def notification_settings(request):
    recipient, created = WhatsAppRecipient.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        phone_number = request.POST.get("phone_number")
        is_active = request.POST.get("is_active") == "on"
        low_stock = request.POST.get("low_stock") == "on"
        production = request.POST.get("production") == "on"
        purchase = request.POST.get("purchase") == "on"
        receipt = request.POST.get("receipt") == "on"
        daily = request.POST.get("daily") == "on"
        
        recipient.phone_number = phone_number
        recipient.is_active = is_active
        recipient.low_stock_alerts = low_stock
        recipient.production_updates = production
        recipient.purchase_approvals = purchase
        recipient.goods_received = receipt
        recipient.daily_summary = daily
        recipient.save()
        
        messages.success(request, "WhatsApp notification settings updated.")
        return redirect("notifications:settings")
    
    recent_messages = WhatsAppMessage.objects.filter(recipient=recipient)[:5]
    return render(request, "notifications/settings.html", {
        "recipient": recipient,
        "recent_messages": recent_messages
    })

@login_required
def test_whatsapp(request):
    recipient = getattr(request.user, 'whatsapp_settings', None)
    if not recipient or not recipient.phone_number:
        messages.error(request, "Please set up your WhatsApp number first.")
        return redirect("notifications:settings")
    
    sid = send_whatsapp(
        recipient, 
        'test', 
        f"Hello {request.user.username}! This is a test alert from your Factory ERP WhatsApp integration. 🚀"
    )
    
    if sid:
        messages.success(request, "Test WhatsApp message sent successfully!")
    else:
        messages.error(request, "Failed to send WhatsApp message. Check Twilio configuration.")
        
    return redirect("notifications:settings")
