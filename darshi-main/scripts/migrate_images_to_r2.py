#!/usr/bin/env python3
"""
Migrate images from Google Cloud Storage to Cloudflare R2.
Downloads images from GCS and uploads them to R2 with the same paths.
"""
import os
import sys
from pathlib import Path
from typing import Optional
import concurrent.futures

import boto3
from google.cloud import storage
from botocore.exceptions import ClientError
from tqdm import tqdm


# Configuration from environment
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')  # e.g., "your-project-reports"
R2_ENDPOINT = os.getenv('R2_ENDPOINT')  # e.g., "https://xxxxx.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', 'darshi-reports')

# Temporary directory for downloads
TEMP_DIR = Path('data/image_migration_temp')
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def validate_config():
    """Validate required environment variables."""
    required = {
        'GCS_BUCKET_NAME': GCS_BUCKET_NAME,
        'R2_ENDPOINT': R2_ENDPOINT,
        'R2_ACCESS_KEY_ID': R2_ACCESS_KEY_ID,
        'R2_SECRET_ACCESS_KEY': R2_SECRET_ACCESS_KEY,
    }

    missing = [key for key, value in required.items() if not value]
    if missing:
        print("ERROR: Missing required environment variables:")
        for key in missing:
            print(f"  - {key}")
        print()
        print("Set them in your shell:")
        print("  export GCS_BUCKET_NAME=your-gcs-bucket")
        print("  export R2_ENDPOINT=https://xxxxx.r2.cloudflarestorage.com")
        print("  export R2_ACCESS_KEY_ID=your-r2-access-key")
        print("  export R2_SECRET_ACCESS_KEY=your-r2-secret-key")
        sys.exit(1)


def get_gcs_client():
    """Initialize GCS client."""
    try:
        client = storage.Client()
        return client
    except Exception as e:
        print(f"ERROR: Failed to initialize GCS client: {e}")
        print("Make sure GOOGLE_APPLICATION_CREDENTIALS is set.")
        sys.exit(1)


def get_r2_client():
    """Initialize R2 (S3-compatible) client."""
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name='auto',  # R2 uses 'auto' for region
        )
        return s3
    except Exception as e:
        print(f"ERROR: Failed to initialize R2 client: {e}")
        sys.exit(1)


def list_gcs_blobs(gcs_client):
    """List all blobs in GCS bucket."""
    bucket = gcs_client.bucket(GCS_BUCKET_NAME)
    blobs = list(bucket.list_blobs())
    return blobs


def download_from_gcs(blob, local_path: Path) -> bool:
    """Download a blob from GCS to local file."""
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))
        return True
    except Exception as e:
        print(f"  ERROR downloading {blob.name}: {e}")
        return False


def upload_to_r2(r2_client, local_path: Path, r2_key: str, content_type: str) -> bool:
    """Upload a file to R2."""
    try:
        with open(local_path, 'rb') as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType=content_type,
                # Make objects publicly readable
                ACL='public-read',
            )
        return True
    except ClientError as e:
        print(f"  ERROR uploading {r2_key}: {e}")
        return False


def get_content_type(filename: str) -> str:
    """Determine content type from filename."""
    ext = Path(filename).suffix.lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
    }
    return content_types.get(ext, 'application/octet-stream')


def migrate_blob(blob, gcs_client, r2_client) -> tuple[str, bool]:
    """Migrate a single blob from GCS to R2."""
    blob_name = blob.name
    local_path = TEMP_DIR / blob_name

    try:
        # Download from GCS
        if not download_from_gcs(blob, local_path):
            return blob_name, False

        # Upload to R2
        content_type = get_content_type(blob_name)
        if not upload_to_r2(r2_client, local_path, blob_name, content_type):
            return blob_name, False

        # Clean up local file
        local_path.unlink()

        return blob_name, True

    except Exception as e:
        print(f"  ERROR migrating {blob_name}: {e}")
        return blob_name, False


def main():
    """Main migration function."""
    print("=" * 70)
    print("Darshi Image Migration Tool")
    print("Google Cloud Storage → Cloudflare R2")
    print("=" * 70)
    print()

    # Validate configuration
    validate_config()

    # Initialize clients
    print("Initializing cloud storage clients...")
    gcs_client = get_gcs_client()
    r2_client = get_r2_client()
    print("  ✓ Connected to GCS")
    print("  ✓ Connected to R2")
    print()

    # List all blobs in GCS
    print(f"Listing blobs in GCS bucket '{GCS_BUCKET_NAME}'...")
    blobs = list_gcs_blobs(gcs_client)
    total_blobs = len(blobs)
    print(f"  Found {total_blobs} blobs")
    print()

    if total_blobs == 0:
        print("No blobs to migrate. Exiting.")
        return

    # Calculate total size
    total_size_mb = sum(blob.size for blob in blobs) / (1024 * 1024)
    print(f"Total size: {total_size_mb:.2f} MB")
    print()

    # Confirm migration
    response = input(f"Migrate {total_blobs} images to R2? (yes/no): ").strip().lower()
    if response not in ('yes', 'y'):
        print("Migration cancelled.")
        return

    print()
    print("Starting migration...")
    print()

    # Migrate blobs in parallel
    success_count = 0
    failed_blobs = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        futures = {
            executor.submit(migrate_blob, blob, gcs_client, r2_client): blob
            for blob in blobs
        }

        # Process results with progress bar
        with tqdm(total=total_blobs, desc="Migrating", unit="file") as pbar:
            for future in concurrent.futures.as_completed(futures):
                blob_name, success = future.result()
                if success:
                    success_count += 1
                else:
                    failed_blobs.append(blob_name)
                pbar.update(1)

    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"  Total blobs: {total_blobs}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(failed_blobs)}")
    print()

    if failed_blobs:
        print("Failed blobs:")
        for blob_name in failed_blobs:
            print(f"  - {blob_name}")
        print()

    # Clean up temp directory
    try:
        if TEMP_DIR.exists():
            for file in TEMP_DIR.rglob('*'):
                if file.is_file():
                    file.unlink()
            TEMP_DIR.rmdir()
    except Exception as e:
        print(f"Warning: Failed to clean up temp directory: {e}")

    print("=" * 70)
    print()

    if failed_blobs:
        print("⚠️  Some blobs failed to migrate. Check errors above.")
        sys.exit(1)
    else:
        print("✓ All images migrated successfully!")
        print()
        print("Next steps:")
        print("  1. Verify images are accessible in R2")
        print("  2. Update application code to use R2 URLs")
        print("  3. Test image retrieval in your app")
        print("  4. Once confirmed, you can delete the GCS bucket")


if __name__ == '__main__':
    main()
