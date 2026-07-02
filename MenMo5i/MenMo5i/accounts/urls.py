from django.urls import path

from .views import (
    AccountView,
    CartView,
    SecureLoginView,
    SecureLogoutView,
    SecurePasswordChangeDoneView,
    SecurePasswordChangeView,
    SignupView,
)


urlpatterns = [
    path('login/', SecureLoginView.as_view(), name='login'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('logout/', SecureLogoutView.as_view(), name='logout'),
    path('account/', AccountView.as_view(), name='account'),
    path('password/', SecurePasswordChangeView.as_view(), name='password_change'),
    path('password/done/', SecurePasswordChangeDoneView.as_view(), name='password_change_done'),
    path('cart/', CartView.as_view(), name='cart'),  # Cart page URL
]
