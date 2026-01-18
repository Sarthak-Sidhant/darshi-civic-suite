import asyncio
import logging
import os
import io
import httpx
from typing import Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ranchi_scraper import Ranchi_SmartScraper

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grivredr")

app = FastAPI(title="Grivredr - Ranchi Smart Scraper Service")

# Configuration
CALLBACK_URL_BASE = os.getenv("CALLBACK_URL_BASE", "http://backend:8080/api/v1/webhooks/ranchi-scraper")

class ReportSubmission(BaseModel):
    report_id: str
    name: str
    mobile: Optional[str] = "9999999999"  # Default dummy
    email: Optional[str] = "help@darshi.app"
    description: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    problem_type: Optional[str] = "491"
    ai_category: Optional[str] = None

async def run_scraper_and_callback(submission: ReportSubmission):
    """
    Runs the scraper and calls back the main backend with the result.
    """
    logger.info(f"Processing report {submission.report_id}")
    
    # 1. Prepare data for scraper
    scraper_data = {
        'name': submission.name or "Citizen",
        'mobile': submission.mobile,
        'email': submission.email,
        'contact': submission.mobile,
        'address': submission.address,
        'remarks': f"{submission.description} (Report ID: {submission.report_id}) [AI Category: {submission.ai_category}]",
        # Default mapping logic (improvements needed for real production)
        'problem_type': submission.problem_type or '491', 
        'area': '503' # Random Ward
    }

    # 2. Run Scraper
    scraper = Ranchi_SmartScraper(headless=True)
    result = await scraper.submit_grievance(scraper_data)
    
    success = result.get('success', False)
    tracking_id = result.get('tracking_id')
    screenshot_bytes = result.get('screenshot')
    error_msg = result.get('error', '')
    
    logger.info(f"Scraper finished. Success: {success}, Tracking ID: {tracking_id}")

    # 3. Callback to Backend
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare files if screenshot exists
            files = {}
            if screenshot_bytes:
                files = {'screenshot': ('confirmation.png', screenshot_bytes, 'image/png')}
            
            # Prepare form data
            data = {
                'report_id': submission.report_id,
                'success': str(success).lower(),
                'tracking_id': tracking_id or '',
                'error': error_msg
            }
            
            logger.info(f"Sending callback to {CALLBACK_URL_BASE}")
            resp = await client.post(CALLBACK_URL_BASE, data=data, files=files)
            
            if resp.status_code == 200:
                logger.info("Callback successful")
            else:
                logger.error(f"Callback failed: {resp.status_code} - {resp.text}")
                
    except Exception as e:
        logger.error(f"Failed to send callback: {e}")

@app.post("/submit")
async def submit_grievance(submission: ReportSubmission, background_tasks: BackgroundTasks):
    """
    Endpoint to receive a report submission and trigger the scraper in background.
    """
    background_tasks.add_task(run_scraper_and_callback, submission)
    return {"status": "processing", "report_id": submission.report_id}

@app.get("/health")
def health_check():
    return {"status": "ok"}
