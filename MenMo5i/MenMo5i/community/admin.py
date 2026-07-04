from django.contrib import admin
from django.contrib.admin import register

from .models import Follow, Like


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at']
    list_filter = ['created_at']
    search_fields = ['follower__username', 'following__username']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'art', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username']
