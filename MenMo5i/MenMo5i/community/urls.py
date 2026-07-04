from django.urls import path

from .views import community_gallery_view, toggle_follow_view, toggle_like_view

app_name = 'community'
urlpatterns = [
    path('', community_gallery_view, name='gallery'),
    path('follow/<int:user_id>/', toggle_follow_view, name='toggle_follow'),
    path('like/<int:art_id>/', toggle_like_view, name='toggle_like'),
]
