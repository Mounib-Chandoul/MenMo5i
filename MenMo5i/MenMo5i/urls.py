from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core_store.views import landing_page_view
from generation_engine.views import design_view, trigger_generation_placeholder

urlpatterns = [
    path('', landing_page_view, name='landing_page'),
    path('design/', design_view, name='design'),
    path('generation/', include('generation_engine.urls')),
    path('community/', include('community.urls')),
    path('api/generate/', trigger_generation_placeholder, name='api_generate'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
]

# Legacy entry point kept in sync with MenMo5i/urls.py
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
