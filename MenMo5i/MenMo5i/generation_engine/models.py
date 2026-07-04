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
    transparent_png_url = models.URLField(max_length=1000, blank=True, default='')
    design_image = models.ImageField(upload_to='designs/', null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=29.99)

    @property
    def image_url(self):
        if self.design_image:
            return self.design_image.url
        return self.transparent_png_url

    def __str__(self):
        return f"Art for {self.session_id}"


from django.db import models

class SavedPrompt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_prompts')
    prompt = models.TextField()
    category = models.CharField(max_length=32, choices=DesignSession.Category.choices, default=DesignSession.Category.ABSTRACT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.prompt[:50]}"


class ShirtTemplate(models.Model):
    name = models.CharField(max_length=100) # e.g., "Oversized Boxy Black Tee"
    blank_image = models.ImageField(upload_to="templates/blanks/") # Real shirt image
    mask_image = models.ImageField(upload_to="templates/masks/")   # Binary background mask
    
    # Printable box area defined as percentages (0.0 to 1.0) of the total image size
    # This allows your images to be any resolution (1080p, 4k, etc.)
    canvas_x = models.FloatField(help_text="X coordinate center-left position (0.0 - 1.0)")
    canvas_y = models.FloatField(help_text="Y coordinate top position (0.0 - 1.0)")
    canvas_width = models.FloatField(help_text="Width of printable chest area (0.0 - 1.0)")
    canvas_height = models.FloatField(help_text="Height of printable chest area (0.0 - 1.0)")

    def __str__(self):
        return self.name