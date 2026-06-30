from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = (username or kwargs.get("email") or kwargs.get("identifier") or "").strip()
        if not identifier or password is None:
            return None

        lookup = {}
        if "@" in identifier:
            lookup["email__iexact"] = identifier
        else:
            lookup["username__iexact"] = identifier

        try:
            user = User.objects.get(**lookup)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(**lookup).order_by("id").first()

        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
