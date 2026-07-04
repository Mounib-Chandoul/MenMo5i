

from django.contrib import admin
from .models import SavedPrompt, ShirtTemplate

@admin.register(ShirtTemplate)
class ShirtTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'canvas_x', 'canvas_y', 'canvas_width', 'canvas_height')

@admin.register(SavedPrompt)
class SavedPromptAdmin(admin.ModelAdmin):
    list_display = ('user', 'prompt', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('prompt', 'user__username')