#!/usr/bin/env python3
"""
Script to analyze image sizes across all reports in Firestore.
Checks both image_data (new format) and image_urls (old format).
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import db_service
from app.core.logging_config import get_logger
import httpx
import asyncio

logger = get_logger(__name__)


async def get_image_size(url: str) -> int:
    """Get image size in bytes from URL."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url)
            if response.status_code == 200:
                content_length = response.headers.get('content-length')
                if content_length:
                    return int(content_length)

            # Fallback to GET if HEAD doesn't work
            response = await client.get(url)
            return len(response.content)
    except Exception as e:
        logger.warning(f"Failed to get size for {url}: {e}")
        return 0


def format_size(bytes_size: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


async def analyze_image_sizes():
    """Analyze image sizes across all reports."""
    print("🔍 Analyzing image sizes across all reports...\n")

    # Get all reports
    reports = db_service.get_all_reports_raw()

    if not reports:
        print("❌ No reports found in database")
        return

    print(f"📊 Found {len(reports)} reports\n")

    total_images = 0
    total_size_bytes = 0
    webp_sizes = []
    jpeg_sizes = []
    legacy_sizes = []

    reports_with_images = 0
    reports_with_new_format = 0
    reports_with_old_format = 0

    for idx, report in enumerate(reports, 1):
        report_id = report.get('id', 'unknown')
        title = report.get('title', 'Untitled')

        print(f"[{idx}/{len(reports)}] {report_id[:8]}... - {title[:50]}")

        # Check new format (image_data)
        if 'image_data' in report and report['image_data']:
            reports_with_new_format += 1
            reports_with_images += 1

            for img_idx, img_data in enumerate(report['image_data'], 1):
                webp_url = img_data.get('webp_url')
                jpeg_url = img_data.get('jpeg_url')

                if webp_url:
                    webp_size = await get_image_size(webp_url)
                    if webp_size > 0:
                        webp_sizes.append(webp_size)
                        total_size_bytes += webp_size
                        total_images += 1
                        print(f"  └─ Image {img_idx} (WebP): {format_size(webp_size)}")

                if jpeg_url:
                    jpeg_size = await get_image_size(jpeg_url)
                    if jpeg_size > 0:
                        jpeg_sizes.append(jpeg_size)
                        total_size_bytes += jpeg_size
                        total_images += 1
                        print(f"  └─ Image {img_idx} (JPEG): {format_size(jpeg_size)}")

        # Check old format (image_urls)
        elif 'image_urls' in report and report['image_urls']:
            reports_with_old_format += 1
            reports_with_images += 1

            for img_idx, img_url in enumerate(report['image_urls'], 1):
                img_size = await get_image_size(img_url)
                if img_size > 0:
                    legacy_sizes.append(img_size)
                    total_size_bytes += img_size
                    total_images += 1
                    print(f"  └─ Image {img_idx} (Legacy): {format_size(img_size)}")
        else:
            print(f"  └─ No images")

        print()

    # Statistics
    print("\n" + "="*60)
    print("📈 STATISTICS")
    print("="*60)

    print(f"\n📋 Reports:")
    print(f"  Total reports: {len(reports)}")
    print(f"  Reports with images: {reports_with_images}")
    print(f"  Reports with new format (image_data): {reports_with_new_format}")
    print(f"  Reports with old format (image_urls): {reports_with_old_format}")

    print(f"\n🖼️  Images:")
    print(f"  Total images: {total_images}")
    print(f"  WebP images: {len(webp_sizes)}")
    print(f"  JPEG images: {len(jpeg_sizes)}")
    print(f"  Legacy format images: {len(legacy_sizes)}")

    print(f"\n💾 Storage:")
    print(f"  Total storage used: {format_size(total_size_bytes)}")

    if webp_sizes:
        avg_webp = sum(webp_sizes) / len(webp_sizes)
        print(f"  Average WebP size: {format_size(avg_webp)}")
        print(f"  Min WebP size: {format_size(min(webp_sizes))}")
        print(f"  Max WebP size: {format_size(max(webp_sizes))}")

    if jpeg_sizes:
        avg_jpeg = sum(jpeg_sizes) / len(jpeg_sizes)
        print(f"  Average JPEG size: {format_size(avg_jpeg)}")
        print(f"  Min JPEG size: {format_size(min(jpeg_sizes))}")
        print(f"  Max JPEG size: {format_size(max(jpeg_sizes))}")

    if legacy_sizes:
        avg_legacy = sum(legacy_sizes) / len(legacy_sizes)
        print(f"  Average legacy size: {format_size(avg_legacy)}")
        print(f"  Min legacy size: {format_size(min(legacy_sizes))}")
        print(f"  Max legacy size: {format_size(max(legacy_sizes))}")

    if webp_sizes and jpeg_sizes:
        total_webp = sum(webp_sizes)
        total_jpeg = sum(jpeg_sizes)
        savings = total_jpeg - total_webp
        savings_percent = (savings / total_jpeg * 100) if total_jpeg > 0 else 0
        print(f"\n💰 WebP Savings:")
        print(f"  JPEG total: {format_size(total_jpeg)}")
        print(f"  WebP total: {format_size(total_webp)}")
        print(f"  Savings: {format_size(savings)} ({savings_percent:.1f}%)")

    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(analyze_image_sizes())
