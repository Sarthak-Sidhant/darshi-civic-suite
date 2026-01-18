#!/usr/bin/env python3
"""
Migration Script: Add dhash_bucket field to existing reports

This script adds the dhash_bucket field (first 4 chars of image_dhash) to all
existing reports in Firestore. This enables the optimized bucket-based duplicate
detection that reduces data transfer by 90%.

Usage:
    python migrate_dhash_bucket.py [--dry-run]

Options:
    --dry-run    Show what would be updated without making changes
"""

import sys
import os
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(
    log_level="INFO",
    log_file=None,  # Log to console only
    enable_sentry=False
)

logger = get_logger(__name__)


def migrate_dhash_buckets(dry_run=False):
    """
    Add dhash_bucket field to all reports that have image_dhash but no dhash_bucket.

    Args:
        dry_run: If True, only print what would be updated without making changes
    """
    try:
        # Initialize Firestore
        db = firestore.Client(project=settings.PROJECT_ID)

        logger.info("Starting dhash_bucket migration...")
        logger.info(f"Dry run: {dry_run}")

        # Query reports that have image_dhash but no dhash_bucket
        # Note: Firestore doesn't have a "field doesn't exist" filter, so we fetch all
        query = db.collection('reports')

        total_reports = 0
        updated_reports = 0
        skipped_reports = 0
        error_reports = 0

        # Use batched writes for efficiency (max 500 per batch)
        batch = db.batch()
        batch_count = 0

        for doc in query.stream():
            total_reports += 1

            data = doc.to_dict()
            image_dhash = data.get('image_dhash')
            dhash_bucket = data.get('dhash_bucket')

            # Skip if already has bucket or no dhash
            if dhash_bucket or not image_dhash:
                skipped_reports += 1
                if total_reports % 100 == 0:
                    logger.info(f"Processed {total_reports} reports...")
                continue

            # Compute bucket (first 4 hex chars)
            new_bucket = image_dhash[:4] if len(image_dhash) >= 4 else image_dhash

            if dry_run:
                logger.info(f"Would update {doc.id}: dhash={image_dhash[:16]}... -> bucket={new_bucket}")
                updated_reports += 1
            else:
                try:
                    # Add to batch
                    batch.update(doc.reference, {'dhash_bucket': new_bucket})
                    batch_count += 1
                    updated_reports += 1

                    # Commit batch when reaching limit
                    if batch_count >= 500:
                        batch.commit()
                        logger.info(f"Committed batch of {batch_count} updates")
                        batch = db.batch()
                        batch_count = 0

                except Exception as e:
                    logger.error(f"Failed to update {doc.id}: {e}")
                    error_reports += 1

            if total_reports % 100 == 0:
                logger.info(f"Processed {total_reports} reports...")

        # Commit remaining batch
        if not dry_run and batch_count > 0:
            batch.commit()
            logger.info(f"Committed final batch of {batch_count} updates")

        # Summary
        logger.info("\n" + "="*60)
        logger.info("Migration Summary:")
        logger.info(f"  Total reports processed: {total_reports}")
        logger.info(f"  Reports updated: {updated_reports}")
        logger.info(f"  Reports skipped: {skipped_reports}")
        logger.info(f"  Errors: {error_reports}")
        logger.info("="*60)

        if dry_run:
            logger.info("\nDry run complete. No changes were made.")
            logger.info("Run without --dry-run to apply changes.")
        else:
            logger.info("\nMigration complete!")
            logger.info("\nNext steps:")
            logger.info("1. Deploy updated Firestore indexes: firebase deploy --only firestore:indexes")
            logger.info("2. Wait for indexes to build (check Firebase Console)")
            logger.info("3. Deploy updated backend code")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    # Run migration
    migrate_dhash_buckets(dry_run=dry_run)
