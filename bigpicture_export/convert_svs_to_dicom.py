#!/usr/bin/env python3
"""
Batch convert SVS whole slide images to DICOM format using wsidicomizer.

This script reads the data.csv file and converts all SVS images to DICOM format,
placing them in the appropriate IMAGE_* subdirectories.

Usage:
    python convert_svs_to_dicom.py --data data.csv --output ./output/DATASET_ID
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def convert_svs_to_dicom(data_csv: Path, output_dir: Path) -> None:
    """
    Convert all SVS images from data.csv to DICOM format.

    Args:
        data_csv: Path to data.csv containing image information
        output_dir: Base output directory (e.g., ./output/DATASET_BREAST_TISSUE_2025)
    """
    images_dir = output_dir / "IMAGES"
    images_dir.mkdir(parents=True, exist_ok=True)

    converted_count = 0
    failed_count = 0
    failed_images = []

    print(f"Reading image data from {data_csv}...")

    with open(data_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Get unique images (avoid duplicates from multiple rows)
        images = {}
        for row in reader:
            image_id = row["Image ID"]
            if image_id not in images:
                images[image_id] = {
                    "id": image_id,
                    "path": row["Image path"],
                }

        print(f"Found {len(images)} unique images to convert")

        for idx, (image_id, img_data) in enumerate(images.items(), 1):
            svs_path = img_data["path"]
            image_output_dir = images_dir / f"IMAGE_{image_id}"
            image_output_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n[{idx}/{len(images)}] Converting {image_id}...")
            print(f"  Source: {svs_path}")
            print(f"  Output: {image_output_dir}")

            # Check if source file exists (if it's a local path)
            if not svs_path.startswith("\\\\") and not Path(svs_path).exists():
                print(f"  WARNING: Source file not found, skipping")
                failed_count += 1
                failed_images.append((image_id, "Source file not found"))
                continue

            try:
                # Run wsidicomizer
                result = subprocess.run(
                    ["wsidicomizer", svs_path, str(image_output_dir)],
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout per image
                )

                if result.returncode == 0:
                    print(f"  SUCCESS")
                    converted_count += 1
                else:
                    print(f"  FAILED: {result.stderr}")
                    failed_count += 1
                    failed_images.append((image_id, result.stderr[:100]))

            except subprocess.TimeoutExpired:
                print(f"  FAILED: Conversion timeout")
                failed_count += 1
                failed_images.append((image_id, "Timeout"))
            except FileNotFoundError:
                print(f"  ERROR: wsidicomizer not found. Please install it first.")
                print(f"  Install: pip install wsidicomizer")
                sys.exit(1)
            except Exception as e:
                print(f"  FAILED: {str(e)}")
                failed_count += 1
                failed_images.append((image_id, str(e)[:100]))

    # Summary
    print("\n" + "="*60)
    print("CONVERSION SUMMARY")
    print("="*60)
    print(f"Total images:      {len(images)}")
    print(f"Successfully converted: {converted_count}")
    print(f"Failed:            {failed_count}")

    if failed_images:
        print("\nFailed conversions:")
        for image_id, error in failed_images:
            print(f"  - {image_id}: {error}")

    if failed_count > 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Batch convert SVS images to DICOM format for BigPicture submission"
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

    args = parser.parse_args()

    if not args.data.exists():
        print(f"ERROR: Data file not found: {args.data}")
        sys.exit(1)

    convert_svs_to_dicom(args.data, args.output)


if __name__ == "__main__":
    main()
