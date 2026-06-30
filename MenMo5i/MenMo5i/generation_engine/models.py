import uuid
from django.conf import settings
from django.db import models


class DesignSession(models.Model):
    class Category(models.TextChoices):
        ABSTRACT = 'abstract', 'Abstract'
        TYPOGRAPHY = 'typography', 'Typography'
        ILLUSTRATION = 'illustration', 'Illustration'
        TECHWEAR = 'techwear', 'Techwear'
        MINIMAL = 'minimal', 'Minimal'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    raw_prompt = models.TextField()
    category = models.CharField(max_length=32, choices=Category.choices, default=Category.ABSTRACT)
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} / {self.get_category_display()}"


class GeneratedArt(models.Model):
    session = models.ForeignKey(DesignSession, on_delete=models.CASCADE, related_name='artworks')
    transparent_png_url = models.URLField(max_length=1000)

    def __str__(self):
        return f"Art for {self.session_id}"
