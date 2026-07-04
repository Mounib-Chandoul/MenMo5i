from django.urls import path
from . import views

app_name = 'generation_engine'

urlpatterns = [
    path('design/', views.design_view, name='design'),
    path('prompts/save/', views.save_prompt_view, name='save_prompt'),
    path('prompts/', views.saved_prompts_json, name='saved_prompts_json'),
    path('prompts/<int:prompt_id>/delete/', views.delete_saved_prompt_view, name='delete_saved_prompt'),
]
