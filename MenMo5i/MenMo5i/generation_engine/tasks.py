from celery import shared_task
from .models import ShirtTemplate
from .services.compositor import composite_design_on_shirt
from .services.ai_engine import render_mockup_scene
import os

@shared_task
def generate_tshirt_mockup_pipeline(template_id, user_design_path, prompt, output_db_record_id):
    try:
        template = ShirtTemplate.objects.get(id=template_id)
        
        # 1. Run the local pixel layer compositor matrix
        composited_image = composite_design_on_shirt(template, user_design_path)
        
        # Save composite image to temporary media storage path so it has a valid web URL
        temp_path = f"media/tmp/composite_{output_db_record_id}.png"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        composited_image.save(temp_path)
        
        # Turn file paths into absolute URLs to feed into the Replicate API node
        domain = "https://yourdomain.com" # Swap with your Ngrok or production domain
        composited_url = f"{domain}/{temp_path}"
        mask_url = f"{domain}{template.mask_image.url}"
        
        # 2. Fire Request to AI inference worker
        final_mockup_url = render_mockup_scene(composited_url, mask_url, prompt)
        
        # 3. Update your Database transaction with the finished asset location
        # (Assuming you have a GenerationResult model tracking user histories)
        # result = GenerationResult.objects.get(id=output_db_record_id)
        # result.final_image_url = final_mockup_url
        # result.status = "SUCCESS"
        # result.save()
        
        return final_mockup_url
        
    except Exception as e:
        # Handle exceptions safely and flip status records to "FAILED"
        print(f"Pipeline Error: {str(e)}")
        return None