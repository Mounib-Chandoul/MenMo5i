from django.urls import path
from . import views

# This sets the namespace your HTML template was looking for!
app_name = 'generation_engine'

urlpatterns = [
    # Make sure you have a function named 'design_view' (or similar) inside your views.py
    path('design/', views.design_view, name='design'),
]