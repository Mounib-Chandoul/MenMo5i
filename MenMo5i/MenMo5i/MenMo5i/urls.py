from django.contrib import admin
from django.urls import include, path

from core_store.views import landing_page_view
from generation_engine.views import trigger_generation_placeholder

urlpatterns = [
    path('', landing_page_view, name='landing_page'),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('api/generate/', trigger_generation_placeholder, name='api_generate'),
    path('admin/', admin.site.urls),
]
