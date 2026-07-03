from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import redirect, render

from community.models import Follow
from generation_engine.models import DesignSession
from django.urls import reverse_lazy
from django.views import View

from .forms import IdentifierAuthenticationForm, SecurePasswordChangeForm, SignupForm


class SecureLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = IdentifierAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, 'Welcome back.')
        return super().form_valid(form)


class SecureLogoutView(LogoutView):
    next_page = reverse_lazy('landing_page')


class SignupView(View):
    template_name = 'accounts/signup.html'
    form_class = SignupForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('account')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[1])
            messages.success(request, 'Account created successfully.')
            return redirect('account')
        return render(request, self.template_name, {'form': form})


class AccountView(LoginRequiredMixin, View):
    template_name = 'accounts/account.html'

    def get(self, request, *args, **kwargs):
        User = get_user_model()
        following_ids = list(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
        following_users = User.objects.filter(id__in=following_ids).order_by('username')
        recent_followed_designs = DesignSession.objects.filter(user_id__in=following_ids, is_public=True).select_related('user').prefetch_related('artworks').order_by('-created_at')[:6]
        return render(request, self.template_name, {
            'user': request.user,
            'following_users': following_users,
            'following_count': len(following_ids),
            'recent_followed_designs': recent_followed_designs,
        })


class SecurePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change_form.html'
    form_class = SecurePasswordChangeForm
    success_url = reverse_lazy('password_change_done')


class SecurePasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'

class CartView(LoginRequiredMixin, View):
    template_name = 'accounts/cart.html'

    def get(self, request, *args, **kwargs):
        from core_store.models import CartItem
        cart_items = CartItem.objects.filter(
            user=request.user
        ).select_related('art__session__user').order_by('-added_at')
        total = sum(item.total_price for item in cart_items)
        return render(request, self.template_name, {
            'cart': cart_items,
            'cart_total': total,
        })
    

