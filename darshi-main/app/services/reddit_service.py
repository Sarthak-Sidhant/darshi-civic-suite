import praw
import logging
import os
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize PRAW instance (lazy load or on module level if config is present)
def get_reddit_instance():
    try:
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_USERNAME:
            logger.warning("Reddit configuration missing. Skipping initialization.")
            return None
            
        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT or "DarshiBot/1.0",
            username=settings.REDDIT_USERNAME,
            password=settings.REDDIT_PASSWORD
        )
        return reddit
    except Exception as e:
        logger.error(f"Failed to initialize Reddit client: {e}")
        return None

def post_report_to_reddit(report_data: dict, image_url: str = None):
    """
    Post a verified report to Reddit.
    
    Args:
        report_data: Dict containing title, description, location, category, etc.
        image_url: URL of the verified image (optional, but highly recommended)
    """
    reddit = get_reddit_instance()
    if not reddit:
        logger.warning("Reddit client not available. Skipping post.")
        return

    try:
        title = f"[{report_data.get('category', 'Report')}] {report_data.get('title')}"
        # detailed body
        body = (
            f"{report_data.get('description', '')}\n\n"
            f"**Location:** {report_data.get('location')}\n"
            f"**Status:** Verified\n\n"
            f"Submitted via [Darshi App](https://darshi.app)"
        )
        
        # Determine subreddits
        subreddits = ["darshi"] # Always post to r/darshi
        
        # Check for location-specific subs
        location_lower = (report_data.get('location') or "").lower()
        address_lower = (report_data.get('address') or "").lower()
        
        if "ranchi" in location_lower or "ranchi" in address_lower:
            subreddits.append("ranchi")
        
        # Iterate and post
        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                
                # Check if we should submit link (image) or text
                # Ideally, submit image post if we have URL, with details in comment or title
                if image_url:
                    # Submit link/image post
                    submission = subreddit.submit(title=title, url=image_url)
                    # Add comment with details
                    submission.reply(body)
                else:
                    # Text post
                    subreddit.submit(title=title, selftext=body)
                    
                logger.info(f"Successfully posted report {report_data.get('id')} to r/{sub_name}")
                
            except Exception as e:
                logger.error(f"Failed to post to r/{sub_name}: {e}")

    except Exception as e:
        logger.error(f"Error in Reddit posting logic: {e}")
