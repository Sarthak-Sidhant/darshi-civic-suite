"""
Image Processing Service

Handles image optimization (WebP/JPEG conversion) and perceptual hashing (dHash).
"""

from PIL import Image
import imagehash
import io
from typing import Tuple, Optional
from app.core.logging_config import get_logger
from app.core.exceptions import ValidationError

logger = get_logger(__name__)

# Image quality settings
WEBP_QUALITY = 85  # High quality WebP (smaller than JPEG)
JPEG_QUALITY = 90  # High quality JPEG for fallback
MAX_DIMENSION = 2048  # Max width/height to prevent huge images


def calculate_dhash(image_bytes: bytes, hash_size: int = 8) -> str:
    """
    Calculate perceptual dHash (difference hash) of an image.

    dHash is robust to:
    - Crops and minor edits
    - Compression artifacts
    - Slight color changes
    - Small rotations and scaling

    Args:
        image_bytes: Raw image data
        hash_size: Hash size (8 = 64-bit hash, good balance)

    Returns:
        Hexadecimal string representation of the hash

    Raises:
        ValidationError: If image cannot be processed
    """
    try:
        # Open image
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed (handles RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Calculate dHash
        hash_obj = imagehash.dhash(image, hash_size=hash_size)

        # Return as hex string
        hash_str = str(hash_obj)
        logger.debug(f"Calculated dHash: {hash_str}")

        return hash_str

    except Exception as e:
        logger.error(f"Failed to calculate dHash: {e}", exc_info=True)
        raise ValidationError(
            message="Failed to process image for duplicate detection",
            details=str(e)
        ) from e


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two dHash strings.

    Lower distance = more similar images.
    Typical thresholds:
    - 0-5: Very similar (likely duplicates)
    - 6-10: Similar (possibly related)
    - 11+: Different images

    Args:
        hash1: First dHash hex string
        hash2: Second dHash hex string

    Returns:
        Hamming distance (number of different bits)
    """
    try:
        # Convert hex strings to imagehash objects
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)

        # Calculate Hamming distance
        distance = h1 - h2

        return distance

    except Exception as e:
        logger.error(f"Failed to calculate Hamming distance: {e}")
        return 999  # Return high value on error (treat as different)


# Alias for backwards compatibility
calculate_hamming_distance = hamming_distance


def optimize_image(
    image_bytes: bytes,
    format: str = 'webp',
    quality: int = None
) -> Tuple[bytes, str]:
    """
    Optimize image by converting to WebP or JPEG with compression.

    Also resizes if image is too large.

    Args:
        image_bytes: Original image data
        format: Target format ('webp' or 'jpeg')
        quality: Compression quality (None = use defaults)

    Returns:
        Tuple of (optimized_bytes, content_type)

    Raises:
        ValidationError: If image cannot be processed
    """
    try:
        # Open image
        image = Image.open(io.BytesIO(image_bytes))

        # Get original format and size
        original_format = image.format
        original_size = len(image_bytes)
        width, height = image.size

        logger.debug(f"Original image: {original_format}, {width}x{height}, {original_size} bytes")

        # Check image dimensions (max 50MP to prevent memory exhaustion)
        max_megapixels = 50_000_000
        if width * height > max_megapixels:
            raise ValidationError(
                message=f"Image resolution too high: {width}x{height} ({width*height/1_000_000:.1f}MP)",
                details=f"Maximum resolution is 50 megapixels. Please resize your image.",
                field="image"
            )

        # Convert to RGB if needed (WebP doesn't support all modes well)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Keep alpha channel for PNG-like images
            if format == 'webp':
                # WebP supports alpha
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
            else:
                # JPEG doesn't support alpha, convert to RGB with white background
                if image.mode == 'RGBA' or image.mode == 'LA':
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = background
                else:
                    image = image.convert('RGB')
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large (maintain aspect ratio)
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            logger.info(f"Resizing large image from {width}x{height}")
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            width, height = image.size
            logger.debug(f"Resized to: {width}x{height}")

        # Convert to target format
        output = io.BytesIO()

        if format.lower() == 'webp':
            # Save as WebP
            q = quality if quality is not None else WEBP_QUALITY
            image.save(output, format='WEBP', quality=q, method=6)  # method=6 = best compression
            content_type = 'image/webp'
        else:
            # Save as JPEG
            q = quality if quality is not None else JPEG_QUALITY
            image.save(output, format='JPEG', quality=q, optimize=True)
            content_type = 'image/jpeg'

        optimized_bytes = output.getvalue()
        optimized_size = len(optimized_bytes)

        # Calculate compression ratio
        compression_ratio = (1 - optimized_size / original_size) * 100

        logger.info(
            f"Image optimized: {original_format} -> {format.upper()}, "
            f"{original_size} -> {optimized_size} bytes "
            f"({compression_ratio:.1f}% reduction)"
        )

        return optimized_bytes, content_type

    except Exception as e:
        logger.error(f"Failed to optimize image: {e}", exc_info=True)
        raise ValidationError(
            message="Failed to optimize image",
            details=str(e)
        ) from e


def process_report_image(image_bytes: bytes) -> dict:
    """
    Process a report image: optimize and calculate dHash.

    Creates both WebP (modern browsers) and JPEG (fallback) versions.

    Args:
        image_bytes: Original image data

    Returns:
        Dictionary with:
        - dhash: Perceptual hash for duplicate detection
        - webp_bytes: WebP optimized image
        - webp_content_type: 'image/webp'
        - jpeg_bytes: JPEG optimized image
        - jpeg_content_type: 'image/jpeg'

    Raises:
        ValidationError: If image processing fails
    """
    try:
        # Calculate dHash from original image
        dhash = calculate_dhash(image_bytes)

        # Create WebP version (primary)
        webp_bytes, webp_content_type = optimize_image(image_bytes, format='webp')

        # Create JPEG version (fallback for older browsers)
        jpeg_bytes, jpeg_content_type = optimize_image(image_bytes, format='jpeg')

        return {
            'dhash': dhash,
            'webp_bytes': webp_bytes,
            'webp_content_type': webp_content_type,
            'jpeg_bytes': jpeg_bytes,
            'jpeg_content_type': jpeg_content_type
        }

    except Exception as e:
        logger.error(f"Failed to process report image: {e}", exc_info=True)
        raise ValidationError(
            message="Failed to process image",
            details=str(e)
        ) from e
