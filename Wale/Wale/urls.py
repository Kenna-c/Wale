from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',       include('shop.urls',      namespace='shop')),
    path('',       include('accounts.urls',  namespace='accounts')),
    path('community/', include('community.urls', namespace='community')),
    path('payments/',  include('payments.urls',  namespace='payments')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)