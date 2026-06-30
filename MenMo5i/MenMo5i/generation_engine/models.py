# generation_engine/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User

class DesignSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    raw_prompt = models.TextField()
    status = models.CharField(max_length=20, default='Pending') # 'Pending', 'Generated'
    created_at = models.DateTimeField(auto_now_add=True)

class GeneratedArt(models.Model):
    session = models.ForeignKey(DesignSession, on_delete=models.CASCADE, related_name="artworks")
    transparent_png_url = models.URLField(max_length=1000)
