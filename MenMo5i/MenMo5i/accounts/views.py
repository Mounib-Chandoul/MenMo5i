from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import redirect, render
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
            return redirect('accounts:account')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[1])
            messages.success(request, 'Account created successfully.')
            return redirect('accounts:account')
        return render(request, self.template_name, {'form': form})


class AccountView(LoginRequiredMixin, View):
    template_name = 'accounts/account.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'user': request.user})


class SecurePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change_form.html'
    form_class = SecurePasswordChangeForm
    success_url = reverse_lazy('accounts:password_change_done')


class SecurePasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'
