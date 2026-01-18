"""
Cloudflare R2 Storage Service - S3-compatible object storage

This module provides file upload operations using Cloudflare R2 via boto3 (S3-compatible API).
Replaces Google Cloud Storage with self-hosted storage solution.

Architecture:
- S3-compatible API using boto3 client
- Public read access for uploaded files
- WebP + JPEG dual-format uploads for optimization
- Retry logic for resilience
"""

import boto3
import uuid
import logging
from botocore.exceptions import ClientError, ConnectionError as BotoConnectionError
from botocore.config import Config
from app.core.config import settings
from app.core.exceptions import (
    StorageError,
    StorageConnectionError,
    StorageUploadError,
    BucketNotFoundError,
    StorageQuotaExceededError
)
from app.core.error_handling import retry_storage_operation, ErrorContext
from app.core.validation import validate_file

logger = logging.getLogger(__name__)

# Lazy initialization of R2 client
_s3_client = None
_client_initialized = False
BUCKET_NAME = settings.R2_BUCKET_NAME
R2_PUBLIC_URL = settings.R2_PUBLIC_URL

# boto3 configuration
boto_config = Config(
    retries={'max_attempts': 3, 'mode': 'standard'},
    connect_timeout=30,
    read_timeout=120
)


def get_s3_client():
    """
    Get or create S3 client (lazy initialization).

    This function creates the R2 client on first use instead of at module import time.
    This prevents startup failures if R2 is temporarily unavailable.

    Returns:
        boto3 S3 client configured for Cloudflare R2

    Raises:
        StorageConnectionError: If client initialization fails
    """
    global _s3_client, _client_initialized

    if _s3_client is None:
        try:
            _s3_client = boto3.client(
                's3',
                endpoint_url=settings.R2_ENDPOINT,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name='auto',  # R2 uses 'auto' region
                config=boto_config
            )
            logger.info(f"Cloudflare R2 client created for bucket: {BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to create R2 client: {e}", exc_info=True)
            raise StorageConnectionError(
                message="Failed to initialize R2 storage client",
                details=str(e)
            ) from e

    # Verify bucket access only on first use (not at import time)
    if not _client_initialized:
        try:
            _s3_client.head_bucket(Bucket=BUCKET_NAME)
            logger.info(f"R2 bucket verified: {BUCKET_NAME}")
            _client_initialized = True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.error(f"R2 bucket not found: {BUCKET_NAME}")
                raise BucketNotFoundError(
                    message=f"R2 bucket '{BUCKET_NAME}' not found. Create it in Cloudflare R2 dashboard.",
                    bucket=BUCKET_NAME
                ) from e
            else:
                # Don't fail - log warning and allow retry on next request
                logger.warning(f"Could not verify R2 bucket (will retry on next request): {e}")
                _client_initialized = True  # Mark as initialized to avoid repeated verification attempts
        except Exception as e:
            # Allow app to start even if bucket verification fails
            logger.warning(f"R2 bucket verification failed (will retry on first operation): {e}")
            _client_initialized = True  # Mark as initialized to avoid repeated verification attempts

    return _s3_client


@retry_storage_operation(max_attempts=2)
def upload_file(file_bytes: bytes, content_type: str, filename: str = None) -> str:
    """
    Upload file to Cloudflare R2 and return public URL.

    Args:
        file_bytes: File content
        content_type: MIME type
        filename: Optional original filename for validation

    Returns:
        Public URL of uploaded file

    Raises:
        StorageError: If upload fails
        StorageUploadError: If file upload fails
    """
    # Get S3 client (lazy initialization)
    client = get_s3_client()

    # Validate file before upload
    try:
        validate_file(file_bytes, content_type, filename)
    except Exception as e:
        logger.warning(f"File validation failed: {e}")
        raise

    # Generate unique filename
    file_uuid = str(uuid.uuid4())
    object_key = f"reports/{file_uuid}"

    with ErrorContext("storage", "upload_file", StorageUploadError, bucket=BUCKET_NAME, filename=object_key):
        try:
            logger.debug(f"Uploading file to R2: size={len(file_bytes)} bytes, content_type={content_type}")

            # Upload to R2 with public-read ACL
            client.put_object(
                Bucket=BUCKET_NAME,
                Key=object_key,
                Body=file_bytes,
                ContentType=content_type,
                ACL='public-read'  # Make publicly accessible
            )

            # Construct public URL
            public_url = f"{R2_PUBLIC_URL}/{object_key}"

            logger.info(f"File uploaded successfully to R2: {object_key}")
            return public_url

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'NoSuchBucket':
                raise BucketNotFoundError(
                    message=f"R2 bucket {BUCKET_NAME} not found",
                    bucket=BUCKET_NAME
                ) from e
            elif error_code == 'RequestTimeout':
                raise StorageUploadError(
                    message="File upload timed out",
                    bucket=BUCKET_NAME,
                    filename=object_key,
                    details=error_message
                ) from e
            elif error_code == 'SlowDown' or error_code == 'ServiceUnavailable':
                raise StorageError(
                    message="R2 storage rate limit exceeded",
                    bucket=BUCKET_NAME,
                    filename=object_key,
                    details=error_message
                ) from e
            elif error_code == 'EntityTooLarge':
                raise StorageQuotaExceededError(
                    message="File size exceeds R2 limits",
                    bucket=BUCKET_NAME,
                    details=error_message
                ) from e
            else:
                raise StorageUploadError(
                    message="File upload to R2 failed",
                    bucket=BUCKET_NAME,
                    filename=object_key,
                    details=error_message
                ) from e

        except BotoConnectionError as e:
            raise StorageConnectionError(
                message="Failed to connect to R2",
                details=str(e)
            ) from e

        except Exception as e:
            raise StorageUploadError(
                message="Unexpected error during R2 upload",
                bucket=BUCKET_NAME,
                filename=object_key,
                details=str(e)
            ) from e


@retry_storage_operation(max_attempts=2)
def upload_optimized_image(webp_bytes: bytes, jpeg_bytes: bytes, base_filename: str = None) -> dict:
    """
    Upload both WebP and JPEG versions of an image to R2.

    Args:
        webp_bytes: WebP optimized image
        jpeg_bytes: JPEG optimized image (fallback)
        base_filename: Optional base filename (without extension)

    Returns:
        Dictionary with:
        - webp_url: URL to WebP version
        - jpeg_url: URL to JPEG version (fallback)

    Raises:
        StorageError: If upload fails
    """
    # Get S3 client (lazy initialization)
    client = get_s3_client()

    base_uuid = base_filename if base_filename else str(uuid.uuid4())
    webp_key = f"reports/{base_uuid}.webp"
    jpeg_key = f"reports/{base_uuid}.jpg"

    with ErrorContext("storage", "upload_optimized_image", StorageUploadError, bucket=BUCKET_NAME):
        try:
            # Upload WebP version
            logger.debug(f"Uploading WebP to R2: {webp_key}, size={len(webp_bytes)} bytes")
            client.put_object(
                Bucket=BUCKET_NAME,
                Key=webp_key,
                Body=webp_bytes,
                ContentType='image/webp',
                ACL='public-read'
            )

            # Upload JPEG version
            logger.debug(f"Uploading JPEG to R2: {jpeg_key}, size={len(jpeg_bytes)} bytes")
            client.put_object(
                Bucket=BUCKET_NAME,
                Key=jpeg_key,
                Body=jpeg_bytes,
                ContentType='image/jpeg',
                ACL='public-read'
            )

            # Construct public URLs
            webp_url = f"{R2_PUBLIC_URL}/{webp_key}"
            jpeg_url = f"{R2_PUBLIC_URL}/{jpeg_key}"

            logger.info(f"Optimized images uploaded successfully to R2: {base_uuid} (WebP + JPEG)")

            return {
                'webp_url': webp_url,
                'jpeg_url': jpeg_url
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            logger.error(f"Failed to upload optimized images to R2: {error_message}", exc_info=True)

            raise StorageUploadError(
                message="Failed to upload optimized images to R2",
                bucket=BUCKET_NAME,
                filename=base_uuid,
                details=error_message
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error uploading optimized images: {e}", exc_info=True)
            raise StorageUploadError(
                message="Unexpected error during optimized image upload",
                bucket=BUCKET_NAME,
                filename=base_uuid,
                details=str(e)
            ) from e


@retry_storage_operation(max_attempts=2)
def download_image(image_url: str) -> bytes:
    """
    Download image from R2 (used for image analysis).

    Args:
        image_url: Full public URL of the image

    Returns:
        bytes: Image data

    Raises:
        StorageError: If download fails
    """
    # Get S3 client (lazy initialization)
    client = get_s3_client()

    # Extract object key from URL
    object_key = image_url.replace(f"{R2_PUBLIC_URL}/", "")

    with ErrorContext("storage", "download_image", StorageError, bucket=BUCKET_NAME, filename=object_key):
        try:
            logger.debug(f"Downloading image from R2: {object_key}")

            response = client.get_object(
                Bucket=BUCKET_NAME,
                Key=object_key
            )

            image_bytes = response['Body'].read()

            logger.debug(f"Downloaded image from R2: {object_key}, size={len(image_bytes)} bytes")
            return image_bytes

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'NoSuchKey':
                raise StorageError(
                    message=f"Image not found in R2: {object_key}",
                    bucket=BUCKET_NAME,
                    filename=object_key,
                    details=error_message
                ) from e
            else:
                raise StorageError(
                    message="Failed to download image from R2",
                    bucket=BUCKET_NAME,
                    filename=object_key,
                    details=error_message
                ) from e

        except Exception as e:
            raise StorageError(
                message="Unexpected error downloading image from R2",
                bucket=BUCKET_NAME,
                filename=object_key,
                details=str(e)
            ) from e


@retry_storage_operation(max_attempts=2)
def delete_file(image_url: str) -> bool:
    """
    Delete file from R2 (admin operation).

    Args:
        image_url: Full public URL of the file

    Returns:
        bool: True if deleted successfully

    Raises:
        StorageError: If deletion fails
    """
    # Get S3 client (lazy initialization)
    client = get_s3_client()

    # Extract object key from URL
    object_key = image_url.replace(f"{R2_PUBLIC_URL}/", "")

    with ErrorContext("storage", "delete_file", StorageError, bucket=BUCKET_NAME, filename=object_key):
        try:
            logger.debug(f"Deleting file from R2: {object_key}")

            client.delete_object(
                Bucket=BUCKET_NAME,
                Key=object_key
            )

            logger.info(f"File deleted from R2: {object_key}")
            return True

        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', str(e))

            logger.error(f"Failed to delete file from R2: {error_message}", exc_info=True)

            raise StorageError(
                message="Failed to delete file from R2",
                bucket=BUCKET_NAME,
                filename=object_key,
                details=error_message
            ) from e

        except Exception as e:
            raise StorageError(
                message="Unexpected error deleting file from R2",
                bucket=BUCKET_NAME,
                filename=object_key,
                details=str(e)
            ) from e
