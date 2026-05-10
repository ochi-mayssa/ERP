from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('settings/', views.notification_settings, name='settings'),
    path('test/', views.test_whatsapp, name='test_whatsapp'),
]
