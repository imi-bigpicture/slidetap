#!/usr/bin/env python3
"""
Update image.xml with SHA256 checksums for DICOM files.

This script computes SHA256 checksums for both unencrypted and encrypted DICOM files
and updates the image.xml file with the correct checksum values.

Usage:
    # After DICOM conversion (before encryption):
    python update_image_checksums.py --metadata ./output/DATASET_ID/METADATA --images ./output/DATASET_ID/IMAGES

    # After encryption (updates both checksums):
    python update_image_checksums.py --metadata ./output/DATASET_ID/METADATA --images ./output/DATASET_ID/IMAGES --encrypted
"""

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict


def compute_sha256(filepath: Path) -> str:
    """
    Compute SHA256 checksum of a file.

    Args:
        filepath: Path to the file

    Returns:
        SHA256 checksum as hexadecimal string (64 characters)
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def find_dicom_files(images_dir: Path, encrypted: bool = False) -> Dict[str, Path]:
    """
    Find all DICOM files in the IMAGES directory.

    Args:
        images_dir: Path to IMAGES directory
        encrypted: If True, look for .dcm.c4gh files, otherwise .dcm files

    Returns:
        Dictionary mapping image_id to DICOM file path
    """
    pattern = "**/*.dcm.c4gh" if encrypted else "**/*.dcm"
    dicom_files = {}

    for dcm_path in images_dir.glob(pattern):
        # Extract image ID from path: IMAGES/IMAGE_{id}/{id}.dcm
        image_id = dcm_path.parent.name.replace("IMAGE_", "")
        dicom_files[image_id] = dcm_path

    return dicom_files


def update_image_xml_checksums(
    metadata_dir: Path,
    images_dir: Path,
    encrypted: bool = False,
) -> None:
    """
    Update image.xml with computed checksums.

    Args:
        metadata_dir: Path to METADATA directory containing image.xml
        images_dir: Path to IMAGES directory containing DICOM files
        encrypted: If True, update both checksum and unencrypted_checksum
    """
    image_xml_path = metadata_dir / "image.xml"

    if not image_xml_path.exists():
        print(f"ERROR: image.xml not found at {image_xml_path}")
        sys.exit(1)

    print(f"Reading {image_xml_path}...")

    # Parse XML
    tree = ET.parse(image_xml_path)
    root = tree.getroot()

    # Find all DICOM files
    print(f"Scanning for DICOM files in {images_dir}...")

    if encrypted:
        # Find both encrypted and unencrypted files
        encrypted_files = find_dicom_files(images_dir, encrypted=True)
        unencrypted_files = find_dicom_files(images_dir, encrypted=False)
        print(f"Found {len(encrypted_files)} encrypted DICOM files")
        print(f"Found {len(unencrypted_files)} unencrypted DICOM files")
    else:
        # Only unencrypted files
        unencrypted_files = find_dicom_files(images_dir, encrypted=False)
        encrypted_files = {}
        print(f"Found {len(unencrypted_files)} unencrypted DICOM files")

    # Update checksums in XML
    updated_count = 0
    missing_files = []

    for image_elem in root.findall("IMAGE"):
        image_id = image_elem.get("alias")

        # Find FILE element
        files_elem = image_elem.find("FILES")
        if files_elem is None:
            print(f"WARNING: No FILES element for image {image_id}")
            continue

        file_elem = files_elem.find("FILE")
        if file_elem is None:
            print(f"WARNING: No FILE element for image {image_id}")
            continue

        # Compute and update unencrypted checksum
        if image_id in unencrypted_files:
            unencrypted_path = unencrypted_files[image_id]
            print(f"Computing unencrypted checksum for {image_id}...")
            unencrypted_checksum = compute_sha256(unencrypted_path)
            file_elem.set("unencrypted_checksum", unencrypted_checksum)
            print(f"  unencrypted_checksum: {unencrypted_checksum}")

            # If not encrypted mode, also set checksum to unencrypted value
            if not encrypted:
                file_elem.set("checksum", unencrypted_checksum)
                print(f"  checksum: {unencrypted_checksum}")

            updated_count += 1
        else:
            print(f"WARNING: Unencrypted DICOM file not found for image {image_id}")
            missing_files.append((image_id, "unencrypted"))

        # Compute and update encrypted checksum (if in encrypted mode)
        if encrypted and image_id in encrypted_files:
            encrypted_path = encrypted_files[image_id]
            print(f"Computing encrypted checksum for {image_id}...")
            encrypted_checksum = compute_sha256(encrypted_path)
            file_elem.set("checksum", encrypted_checksum)
            print(f"  checksum (encrypted): {encrypted_checksum}")
        elif encrypted:
            print(f"WARNING: Encrypted DICOM file not found for image {image_id}")
            missing_files.append((image_id, "encrypted"))

    # Write updated XML
    print(f"\nWriting updated image.xml...")
    tree.write(image_xml_path, encoding="utf-8", xml_declaration=True)

    # Re-prettify the XML
    try:
        from xml.dom import minidom
        with open(image_xml_path, "r", encoding="utf-8") as f:
            xml_string = f.read()
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")
        with open(image_xml_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
    except Exception as e:
        print(f"WARNING: Could not prettify XML: {e}")

    # Summary
    print("\n" + "="*60)
    print("CHECKSUM UPDATE SUMMARY")
    print("="*60)
    print(f"Total images in XML:   {len(root.findall('IMAGE'))}")
    print(f"Updated checksums:     {updated_count}")
    print(f"Missing files:         {len(missing_files)}")

    if missing_files:
        print("\nMissing files:")
        for image_id, file_type in missing_files:
            print(f"  - {image_id}: {file_type} file not found")

    if missing_files:
        print("\nWARNING: Some checksums could not be updated")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Update image.xml with DICOM file checksums"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="Path to METADATA directory containing image.xml",
    )
    parser.add_argument(
        "--images",
        type=Path,
        required=True,
        help="Path to IMAGES directory containing DICOM files",
    )
    parser.add_argument(
        "--encrypted",
        action="store_true",
        help="Update checksums for encrypted files (sets both checksum and unencrypted_checksum)",
    )

    args = parser.parse_args()

    if not args.metadata.exists():
        print(f"ERROR: Metadata directory not found: {args.metadata}")
        sys.exit(1)

    if not args.images.exists():
        print(f"ERROR: Images directory not found: {args.images}")
        sys.exit(1)

    update_image_xml_checksums(args.metadata, args.images, args.encrypted)
    print("\nDone!")


if __name__ == "__main__":
    main()
