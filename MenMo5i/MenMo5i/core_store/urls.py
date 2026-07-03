from django.urls import path

from . import views

urlpatterns = [
    path('design/<uuid:session_id>/', views.design_detail_view, name='design_detail'),
    path('design/<uuid:session_id>/export/design/', views.export_design_view, name='export_design'),
    path('design/<uuid:session_id>/export/shirt/', views.export_shirt_view, name='export_shirt'),
    path('cart/add/<int:art_id>/', views.add_to_cart_view, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_view, name='cart_remove'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/', views.order_history_view, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/confirmed/', views.order_confirmation_view, name='order_confirmation'),
]
