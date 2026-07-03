import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from generation_engine.models import GeneratedArt, ShirtTemplate


class Command(BaseCommand):
    help = "Seed local test design images for existing GeneratedArt records"

    def handle(self, *args, **options):
        # 1. Ensure shirt template images exist
        template = ShirtTemplate.objects.first()
        if template:
            self.stdout.write(f"  ShirtTemplate: {template.name}")
        else:
            self.stdout.write(self.style.ERROR("No ShirtTemplate found!"))

        # 2. Find the test logo
        logo_src = os.path.join(settings.BASE_DIR, "test_logo.png")
        if not os.path.exists(logo_src):
            self.stdout.write(self.style.ERROR(f"test_logo.png not found at {logo_src}"))
            return

        with open(logo_src, "rb") as f:
            logo_data = f.read()

        self.stdout.write(f"  test_logo.png: {len(logo_data)} bytes")

        # 3. Create a design from the test logo
        design_path = "designs/test_logo_seed.png"
        if not default_storage.exists(design_path):
            default_storage.save(design_path, ContentFile(logo_data))
            self.stdout.write(f"  Copied -> {design_path}")
        else:
            self.stdout.write(f"  Already exists: {design_path}")

        # 4. Update all GeneratedArt records that lack a local design_image
        updated = 0
        for art in GeneratedArt.objects.filter(design_image__isnull=True):
            art.design_image = design_path
            art.save(update_fields=["design_image"])
            self.stdout.write(f"  Updated art id={art.id} -> {design_path}")
            updated += 1

        for art in GeneratedArt.objects.filter(design_image__isnull=False):
            fp = art.design_image.path if hasattr(art.design_image, "path") else None
            exists = os.path.exists(fp) if fp else False
            self.stdout.write(f"  Art id={art.id} design_image={art.design_image} file_exists={exists}")

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} artworks."))
