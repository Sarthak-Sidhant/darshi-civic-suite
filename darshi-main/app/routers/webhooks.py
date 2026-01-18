import asyncio
from typing import Optional
from fastapi import APIRouter, Form, UploadFile, File, Request, HTTPException, BackgroundTasks
from app.core.logging_config import get_logger
from app.services import postgres_service as db_service, storage_service

router = APIRouter()
logger = get_logger(__name__)

@router.post("/api/v1/webhooks/ranchi-scraper")
async def ranchi_scraper_callback(
    request: Request,
    report_id: str = Form(...),
    success: str = Form(...),
    tracking_id: Optional[str] = Form(None),
    error: Optional[str] = Form(None),
    screenshot: Optional[UploadFile] = File(None)
):
    """
    Webhook callback from Grivredr service.
    Receives scraping result and optional screenshot.
    """
    is_success = success.lower() == 'true'
    logger.info(f"Received webhook for report {report_id}. Success: {is_success}")

    try:
        image_url = None
        
        # 1. Upload Screenshot if present
        if screenshot and screenshot.filename:
            try:
                content = await screenshot.read()
                # Use storage service to upload to R2
                # We reuse 'upload_image' or similar. Since it's a PNG, we might want to optimize it or just upload as is.
                # For speed/simplicity, we'll assume it's valid PNG and upload directly if possible, 
                # but storage_service usually expects optimization. 
                # Let's create a helper or just use upload_optimized_image if we can convert it, 
                # OR just bypass to basic S3 upload if exposed.
                
                # Check storage_service capabilities from previous file view...
                # It has upload_optimized_image (webp, jpeg).
                # To be safe and quick, we can just upload as 'raw' if we have a method, or assume it's a "file".
                # If storage_service doesn't expose raw upload, we might need to modify it or hack it.
                # Let's try to use `image_service` to process it first to fit the pipeline?
                # "in the status, uploads the final screenshot" -> user wants it visible.
                
                # Let's assume we can add a simple upload method or use an existing one.
                # I'll double check storage_service.py content in next step if this fails, but for now let's try to use `upload_file` if it exists, or just process it.
                
                # Actually, best experience: Process it so it loads fast on frontend.
                from app.services import image_service
                processed = image_service.process_report_image(content)
                urls = storage_service.upload_optimized_image(processed['webp_bytes'], processed['jpeg_bytes'])
                if urls:
                    image_url = urls['webp_url'] # Prefer WebP
            except Exception as e:
                logger.error(f"Failed to process/upload screenshot: {e}")

        # 2. Update Report Status & Timeline
        if is_success:
            # Add timeline event with tracking ID and screenshot
            message = f"Details submitted to Ranchi Smart Portal. Tracking ID: {tracking_id}"
            await db_service.add_timeline_event(report_id, "EXTERNAL_SUBMISSION", message)
            
            # If we have an image, we want to show it.
            # We can add ANOTHER event or append to the message.
            # Best way: Add a specific event for the proof.
            if image_url:
                await db_service.add_timeline_event(
                    report_id, 
                    "SUBMISSION_PROOF", 
                    f"Submission Confirmation Screenshot: {image_url}"
                )
                
            # Update status to denote external processing
            await db_service.update_report(report_id, {"status": "IN_PROGRESS", "external_ref_id": tracking_id})
            
        else:
            await db_service.add_timeline_event(report_id, "EXTERNAL_SUBMISSION_FAILED", f"Failed to submit to portal: {error}")
            # We don't fail the whole report, just log the failure.

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")

    return {"status": "ok"}
