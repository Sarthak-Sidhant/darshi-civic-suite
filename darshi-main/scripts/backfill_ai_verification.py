import asyncio
import os
import sys
import logging
import httpx
from datetime import datetime

# Add app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import postgres_service as db_service
from app.services import ai_service
from app.core.exceptions import AIServiceError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill_verification():
    """
    Finds reports that are PENDING_VERIFICATION and have no AI analysis,
    then triggers AI verification for them.
    """
    logger.info("Starting AI verification backfill...")
    
    try:
        # 0. Ensure schema is correct (Auto-migration)
        async with db_service.get_db_connection() as conn:
            try:
                # Check if flag_reason column exists
                await conn.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS flag_reason TEXT;")
                logger.info("Schema check: ensured 'flag_reason' column exists.")
            except Exception as e:
                logger.warning(f"Schema check failed (might be fine if column exists): {e}")

        # 1. Fetch pending reports
        async with db_service.get_db_connection() as conn:
            # We want pending reports that might have missed verification
            # Checking status or missing ai_analysis
            rows = await conn.fetch("""
                SELECT id, image_urls, latitude, longitude 
                FROM reports 
                WHERE status = 'PENDING_VERIFICATION' 
                OR (ai_analysis IS NULL AND status NOT IN ('REJECTED', 'FLAGGED'))
            """)
            
            logger.info(f"Found {len(rows)} reports requiring verification.")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for row in rows:
                    report_id = row['id']
                    image_urls = row['image_urls']
                    
                    if not image_urls:
                        logger.warning(f"Report {report_id} has no images. Skipping.")
                        continue
                        
                    # Prefer WebP, fallback to first available
                    image_url = None
                    if isinstance(image_urls, list):
                        # Find webp if valid list of dicts, or just first string
                        if image_urls and isinstance(image_urls[0], dict):
                             for img in image_urls:
                                 if img.get('format') == 'webp':
                                     image_url = img.get('url')
                                     break
                             if not image_url:
                                 image_url = image_urls[0].get('url')
                        elif image_urls and isinstance(image_urls[0], str):
                            image_url = image_urls[0]
                    
                    if not image_url:
                         logger.warning(f"Could not determine image URL for report {report_id}. Skipping.")
                         continue

                    logger.info(f"Processing report {report_id}...")
                    
                    try:
                        # Download Image
                        resp = await client.get(image_url)
                        if resp.status_code != 200:
                            logger.error(f"Failed to download image for report {report_id}: HTTP {resp.status_code}")
                            continue
                        
                        image_bytes = resp.content
                        
                        # Analyze
                        analysis = ai_service.analyze_image(image_bytes)
                        
                        # Map integer severity (1-10) to string enum ('low', 'medium', 'high', 'critical')
                        severity_score = analysis.severity
                        severity_str = 'low'
                        if severity_score >= 9:
                            severity_str = 'critical'
                        elif severity_score >= 7:
                            severity_str = 'high'
                        elif severity_score >= 5:
                            severity_str = 'medium'
                        
                        # Prepare updates - only use columns that exist!
                        updates = {
                            "severity": severity_str
                        }

                        if not analysis.is_valid:
                            updates["status"] = "REJECTED"
                            updates["flag_reason"] = analysis.description or "AI rejected"
                            await db_service.add_timeline_event(report_id, "AI_REJECTED", "Backfill: Rejected by AI")
                        else:
                            updates["status"] = "VERIFIED"
                            updates["category"] = analysis.category # Update category if AI identified it
                            await db_service.add_timeline_event(report_id, "VERIFIED", f"Backfill: Verified by AI as {analysis.category}")
                        
                        # Update DB
                        # Note: We need to use update_report from db_service, but it might verify user again?
                        # Using direct update for simplicity and safety in script
                        query = """
                            UPDATE reports 
                            SET 
                                ai_analysis = $1,
                                status = COALESCE($2, status),
                                flag_reason = $3,
                                category = COALESCE($4, category),
                                severity = COALESCE($5, severity),
                                verified_at = CASE WHEN $2 = 'VERIFIED' THEN NOW() ELSE verified_at END
                            WHERE id = $6
                        """
                        
                        # Construct AI analysis JSON
                        ai_json = analysis.model_dump_json() if hasattr(analysis, 'model_dump_json') else analysis.json()
                        
                        await conn.execute(
                            query,
                            ai_json,
                            updates.get("status"),
                            updates.get("flag_reason"),
                            updates.get("category"),
                            updates.get("severity"),
                            report_id
                        )
                        
                        logger.info(f"Successfully backfilled report {report_id}. Status: {updates.get('status', 'Unchanged')}")
                        
                    except AIServiceError as e:
                        logger.error(f"AI Analysis failed for report {report_id}: {e}")
                    except Exception as e:
                        logger.error(f"Error processing report {report_id}: {e}")

    except Exception as e:
        logger.error(f"Backfill script failed: {e}")

if __name__ == "__main__":
    asyncio.run(backfill_verification())
