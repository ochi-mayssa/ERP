from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('notifications/', include('notifications.urls')),
    path('crm/', include('crm.urls')),
    path('', include('inventory.urls')),
]
