#!/usr/bin/env python3
"""
Generate JPEG thumbnails for whole slide images for BigPicture landing page.

This script reads the data.csv file and generates 512x512 JPEG thumbnails
for each image, placing them in LANDING_PAGE/THUMBNAILS/.

Usage:
    python generate_thumbnails.py --data data.csv --output ./output/DATASET_ID --size 512
"""

import argparse
import csv
import sys
from pathlib import Path

try:
    import openslide
    from PIL import Image
except ImportError:
    print("ERROR: Required packages not found.")
    print("Install with: pip install openslide-python pillow")
    sys.exit(1)


def create_thumbnail(svs_path: str, output_path: Path, size: int = 512) -> None:
    """
    Create a thumbnail from a whole slide image.

    Args:
        svs_path: Path to the SVS file
        output_path: Path where the thumbnail JPEG should be saved
        size: Maximum dimension (width or height) of the thumbnail
    """
    slide = openslide.OpenSlide(svs_path)
    thumbnail = slide.get_thumbnail((size, size))
    thumbnail.save(output_path, "JPEG", quality=85)
    slide.close()


def generate_all_thumbnails(data_csv: Path, output_dir: Path, size: int = 512) -> None:
    """
    Generate thumbnails for all images in data.csv.

    Args:
        data_csv: Path to data.csv containing image information
        output_dir: Base output directory (e.g., ./output/DATASET_BREAST_TISSUE_2025)
        size: Thumbnail size in pixels
    """
    thumbnails_dir = output_dir / "LANDING_PAGE" / "THUMBNAILS"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)

    generated_count = 0
    failed_count = 0
    failed_images = []

    print(f"Reading image data from {data_csv}...")

    with open(data_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Get unique images
        images = {}
        for row in reader:
            image_id = row["Image ID"]
            if image_id not in images:
                images[image_id] = {
                    "id": image_id,
                    "path": row["Image path"],
                }

        print(f"Found {len(images)} unique images")
        print(f"Thumbnail size: {size}x{size} pixels")
        print(f"Output directory: {thumbnails_dir}\n")

        for idx, (image_id, img_data) in enumerate(images.items(), 1):
            svs_path = img_data["path"]
            thumbnail_path = thumbnails_dir / f"{image_id}.jpg"

            print(f"[{idx}/{len(images)}] Generating thumbnail for {image_id}...")

            # Check if thumbnail already exists
            if thumbnail_path.exists():
                print(f"  Thumbnail already exists, skipping")
                generated_count += 1
                continue

            # Check if source file exists
            if not svs_path.startswith("\\\\") and not Path(svs_path).exists():
                print(f"  WARNING: Source file not found at {svs_path}")
                failed_count += 1
                failed_images.append((image_id, "Source file not found"))
                continue

            try:
                create_thumbnail(svs_path, thumbnail_path, size)
                print(f"  SUCCESS: {thumbnail_path}")
                generated_count += 1

            except Exception as e:
                print(f"  FAILED: {str(e)}")
                failed_count += 1
                failed_images.append((image_id, str(e)[:100]))

    # Summary
    print("\n" + "="*60)
    print("THUMBNAIL GENERATION SUMMARY")
    print("="*60)
    print(f"Total images:      {len(images)}")
    print(f"Successfully generated: {generated_count}")
    print(f"Failed:            {failed_count}")

    if failed_images:
        print("\nFailed thumbnails:")
        for image_id, error in failed_images:
            print(f"  - {image_id}: {error}")

    if failed_count > 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate thumbnails for BigPicture landing page"
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to data.csv containing image information",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory (e.g., ./output/DATASET_BREAST_TISSUE_2025)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=512,
        help="Thumbnail size in pixels (default: 512)",
    )

    args = parser.parse_args()

    if not args.data.exists():
        print(f"ERROR: Data file not found: {args.data}")
        sys.exit(1)

    generate_all_thumbnails(args.data, args.output, args.size)


if __name__ == "__main__":
    main()
