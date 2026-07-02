import os
from django.core.management.base import BaseCommand
from generation_engine.models import ShirtTemplate
from generation_engine.services.compositor import composite_design_on_shirt
from generation_engine.services.ai_engine import render_mockup_scene

class Command(BaseCommand):
    help = "Run the full pipeline: composite the design and call the AI scene generator"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting complete AI pipeline test..."))

        # 1. Fetch your shirt template from the database
        template = ShirtTemplate.objects.first()
        if not template:
            self.stdout.write(self.style.ERROR("No ShirtTemplate found in the database!"))
            return

        user_design_path = "test_logo.png" 
        if not os.path.exists(user_design_path):
            self.stdout.write(self.style.ERROR(f"Please place a transparent PNG named '{user_design_path}' in your root folder."))
            return

        # 2. Compile the design onto the shirt surface matrix
        self.stdout.write("Compositing design graphic locally...")
        final_image = composite_design_on_shirt(template, user_design_path)
        
        # Save the composite temporarily so it can be served to the internet
        temp_path = "media/tmp_test_composite.png"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        final_image.save(temp_path)

        # 3. CRITICAL NOTE FOR LOCALHOST TESTING
        # Because the AI server lives on a remote cloud, it cannot access files stored on "127.0.0.1".
        # For testing right now, paste public image URLs below or use a free tool like Ngrok 
        # to expose your local media folder to the web.
        
        # For testing, you can swap these with temporary direct public links (Imgur, Discord images, etc.)
        test_public_composite_url = "https://i.imgur.com/YOUR_SAMPLE_COMPOSITE.png"
        test_public_mask_url = "https://i.imgur.com/YOUR_SAMPLE_MASK.png"
        
        # 4. Define your user's test prompt description
        sample_user_prompt = "standing outside a moody cyberpunk coffee shop in downtown Tunis at night, neon reflections"

        self.stdout.write(self.style.NOTICE(f"Dispatching to Generative AI engine with prompt: '{sample_user_prompt}'..."))
        
        try:
            # 5. Fire off the request to the GPU cluster
            ai_mockup_result_url = render_mockup_scene(
                composited_image_url=test_public_composite_url,
                mask_image_url=test_public_mask_url,
                user_prompt=sample_user_prompt
            )
            
            self.stdout.write(self.style.SUCCESS(f"\n🎉 AI Generation Complete! View your final mockup here:\n{ai_mockup_result_url}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"AI Server Connection Failed: {str(e)}"))