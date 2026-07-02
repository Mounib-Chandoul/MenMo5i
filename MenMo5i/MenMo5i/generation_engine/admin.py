

# Register your models here.
from django.contrib import admin
from .models import ShirtTemplate

@admin.register(ShirtTemplate)
class ShirtTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'canvas_x', 'canvas_y', 'canvas_width', 'canvas_height')