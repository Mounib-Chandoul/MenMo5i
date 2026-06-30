from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth import get_user_model


User = get_user_model()
FIELD_CLASS = "w-full bg-zinc-950/80 border border-zinc-800 px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-violet-500 transition-colors duration-200"


class IdentifierAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": "Username or email",
                "class": FIELD_CLASS,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Password",
                "class": FIELD_CLASS,
            }
        ),
    )


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "Email address",
                "class": FIELD_CLASS,
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "autocomplete": "username",
                    "placeholder": "Username",
                    "class": FIELD_CLASS,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {
                "autocomplete": "new-password",
                "placeholder": "Create password",
                "class": FIELD_CLASS,
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "autocomplete": "new-password",
                "placeholder": "Confirm password",
                "class": FIELD_CLASS,
            }
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


class SecurePasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Current password",
                "class": FIELD_CLASS,
            }
        ),
    )
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "New password",
                "class": FIELD_CLASS,
            }
        ),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Confirm new password",
                "class": FIELD_CLASS,
            }
        ),
    )
