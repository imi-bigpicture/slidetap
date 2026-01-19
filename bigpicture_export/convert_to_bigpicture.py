#!/usr/bin/env python3
"""
Convert breast tissue CSV dataset to BigPicture MetaFleX XML format.

This script reads data.csv and observations.csv and generates the XML files
required for BigPicture submission following the MetaFleX schema v2.0.0.

Usage:
    python convert_to_bigpicture.py --data data.csv --observations observations.csv --output ./output
"""

import argparse
import csv
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from xml.dom import minidom


@dataclass
class BiologicalBeing:
    identifier: str
    sex: str
    species: str = "human"


@dataclass
class Case:
    identifier: str
    biological_being_id: str


@dataclass
class Specimen:
    identifier: str
    case_id: str
    specimen_type: str
    extraction_method: str
    anatomical_site: str
    age_interval_start: str
    age_interval_duration: str


@dataclass
class Block:
    identifier: str
    specimen_ids: List[str] = field(default_factory=list)
    embedding: str = ""


@dataclass
class Slide:
    identifier: str
    block_id: str
    staining: str


@dataclass
class Image:
    identifier: str
    slide_id: str
    path: str
    filename: str


@dataclass
class Observation:
    identifier: str
    item_type: str
    item_id: str
    statement_type: str
    statement_status: str
    diagnose_code: str
    pt_classification: str
    freetext: str


def parse_data_csv(filepath: Path) -> tuple[
    Dict[str, BiologicalBeing],
    Dict[str, Case],
    Dict[str, Specimen],
    Dict[str, Block],
    Dict[str, Slide],
    Dict[str, Image],
]:
    """Parse data.csv and extract hierarchical entities."""
    beings: Dict[str, BiologicalBeing] = {}
    cases: Dict[str, Case] = {}
    specimens: Dict[str, Specimen] = {}
    blocks: Dict[str, Block] = {}
    slides: Dict[str, Slide] = {}
    images: Dict[str, Image] = {}

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # BiologicalBeing (Patient)
            being_id = row["Biological being ID"]
            if being_id not in beings:
                beings[being_id] = BiologicalBeing(
                    identifier=being_id,
                    sex=row["Sex"],
                    species=row["Animal species"],
                )

            # Case
            case_id = row["Case ID"]
            if case_id not in cases:
                cases[case_id] = Case(
                    identifier=case_id,
                    biological_being_id=being_id,
                )

            # Specimen
            specimen_id = row["Specimen ID"]
            if specimen_id not in specimens:
                specimens[specimen_id] = Specimen(
                    identifier=specimen_id,
                    case_id=case_id,
                    specimen_type=row["Specimen type"],
                    extraction_method=row["Extraction method"],
                    anatomical_site=row["Anatomical site"],
                    age_interval_start=row["Age at extraction interval start"],
                    age_interval_duration=row["Age at extraction interval duration"],
                )

            # Block
            block_id = row["Block ID"]
            if block_id not in blocks:
                blocks[block_id] = Block(
                    identifier=block_id,
                    specimen_ids=[specimen_id],
                    embedding=row["Block preparation"],
                )
            elif specimen_id not in blocks[block_id].specimen_ids:
                blocks[block_id].specimen_ids.append(specimen_id)

            # Slide
            slide_id = row["Slide ID"]
            if slide_id not in slides:
                slides[slide_id] = Slide(
                    identifier=slide_id,
                    block_id=block_id,
                    staining=row["Staining"],
                )

            # Image
            image_id = row["Image ID"]
            image_path = row["Image path"]
            filename = Path(image_path).name
            if image_id not in images:
                images[image_id] = Image(
                    identifier=image_id,
                    slide_id=slide_id,
                    path=image_path,
                    filename=filename,
                )

    return beings, cases, specimens, blocks, slides, images


def parse_observations_csv(filepath: Path) -> Dict[str, Observation]:
    """Parse observations.csv and extract observation data."""
    observations: Dict[str, Observation] = {}

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            obs_id = row["Observation ID"]
            observations[obs_id] = Observation(
                identifier=obs_id,
                item_type=row["Item type"],
                item_id=row["Item ID"],
                statement_type=row["Statement type"],
                statement_status=row["Statement status"],
                diagnose_code=row.get("Code attribute Diagnose", ""),
                pt_classification=row.get("Custom attribute pT classification", ""),
                freetext=row.get("Freetext", ""),
            )

    return observations


def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def add_string_attribute(parent: ET.Element, tag_name: str, value_text: str) -> None:
    """Add a STRING_ATTRIBUTE element to an ATTRIBUTES parent."""
    attr = ET.SubElement(parent, "STRING_ATTRIBUTE")
    tag = ET.SubElement(attr, "TAG")
    tag.text = tag_name
    value = ET.SubElement(attr, "VALUE")
    value.text = value_text


def add_code_attribute(
    parent: ET.Element,
    tag_name: str,
    code: str,
    scheme: str,
    meaning: str,
    scheme_version: Optional[str] = None,
) -> None:
    """Add a CODE_ATTRIBUTE element to an ATTRIBUTES parent."""
    attr = ET.SubElement(parent, "CODE_ATTRIBUTE")
    tag = ET.SubElement(attr, "TAG")
    tag.text = tag_name
    value = ET.SubElement(attr, "VALUE")
    code_elem = ET.SubElement(value, "CODE")
    code_elem.text = code
    scheme_elem = ET.SubElement(value, "SCHEME")
    scheme_elem.text = scheme
    meaning_elem = ET.SubElement(value, "MEANING")
    meaning_elem.text = meaning
    scheme_version_elem = ET.SubElement(value, "SCHEME_VERSION")
    if scheme_version:
        scheme_version_elem.text = scheme_version
    else:
        scheme_version_elem.set("xsi:nil", "true")
        scheme_version_elem.set(
            "xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"
        )


def add_nil_attributes(parent: ET.Element) -> None:
    """Add a nil ATTRIBUTES element."""
    attrs = ET.SubElement(parent, "ATTRIBUTES")
    attrs.set("xsi:nil", "true")
    attrs.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")


def create_sample_xml(
    beings: Dict[str, BiologicalBeing],
    cases: Dict[str, Case],
    specimens: Dict[str, Specimen],
    blocks: Dict[str, Block],
    slides: Dict[str, Slide],
) -> ET.Element:
    """Create sample.xml with full hierarchy per MetaFleX v2.0.0 schema."""
    root = ET.Element("SAMPLE_SET")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # BiologicalBeings
    for being in beings.values():
        elem = ET.SubElement(root, "BIOLOGICAL_BEING")
        elem.set("alias", being.identifier)

        attrs = ET.SubElement(elem, "ATTRIBUTES")
        add_string_attribute(attrs, "sex", being.sex)
        add_string_attribute(attrs, "species", being.species)

    # Cases
    for case in cases.values():
        elem = ET.SubElement(root, "CASE")
        elem.set("alias", case.identifier)

        # Reference to BiologicalBeing
        being_ref = ET.SubElement(elem, "BIOLOGICAL_BEING_REF")
        being_ref.set("alias", case.biological_being_id)

        add_nil_attributes(elem)

    # Specimens
    for specimen in specimens.values():
        elem = ET.SubElement(root, "SPECIMEN")
        elem.set("alias", specimen.identifier)

        # Reference - extracted from biological being (via case)
        case = cases[specimen.case_id]
        extracted_ref = ET.SubElement(elem, "EXTRACTED_FROM_REF")
        extracted_ref.set("alias", case.biological_being_id)

        # Case reference (optional)
        part_of_case_ref = ET.SubElement(elem, "PART_OF_CASE_REF")
        part_of_case_ref.set("alias", specimen.case_id)

        attrs = ET.SubElement(elem, "ATTRIBUTES")
        add_string_attribute(attrs, "specimen_type", specimen.specimen_type)
        add_string_attribute(attrs, "extraction_method", specimen.extraction_method)
        add_string_attribute(attrs, "anatomical_site", specimen.anatomical_site)
        add_string_attribute(
            attrs, "age_at_extraction_interval_start", specimen.age_interval_start
        )
        add_string_attribute(
            attrs, "age_at_extraction_interval_duration", specimen.age_interval_duration
        )

    # Blocks
    for block in blocks.values():
        elem = ET.SubElement(root, "BLOCK")
        elem.set("alias", block.identifier)

        # Reference - sampled from specimen(s)
        for spec_id in block.specimen_ids:
            sampled_ref = ET.SubElement(elem, "SAMPLED_FROM_REF")
            sampled_ref.set("alias", spec_id)

        attrs = ET.SubElement(elem, "ATTRIBUTES")
        add_string_attribute(attrs, "embedding", block.embedding)

    # Slides
    for slide in slides.values():
        elem = ET.SubElement(root, "SLIDE")
        elem.set("alias", slide.identifier)

        # Reference - created from block
        created_ref = ET.SubElement(elem, "CREATED_FROM_REF")
        created_ref.set("alias", slide.block_id)

        # Reference to staining information (required)
        staining_ref = ET.SubElement(elem, "STAINING_INFORMATION_REF")
        staining_ref.set("alias", slide.staining)

        add_nil_attributes(elem)

    return root


def create_image_xml(images: Dict[str, Image]) -> ET.Element:
    """Create image.xml referencing slides per MetaFleX v2.0.0 schema."""
    root = ET.Element("IMAGE_SET")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Placeholder checksum (64 hex chars for SHA256)
    placeholder_checksum = "0" * 64

    for img in images.values():
        image_elem = ET.SubElement(root, "IMAGE")
        image_elem.set("alias", img.identifier)

        # Reference to slide
        image_of = ET.SubElement(image_elem, "IMAGE_OF")
        image_of.set("alias", img.slide_id)

        # IMAGE_TYPE is required - WSI_IMAGE for whole slide images
        image_type = ET.SubElement(image_elem, "IMAGE_TYPE")
        ET.SubElement(image_type, "WSI_IMAGE")

        # Files section (placeholder - actual DICOM files would be added after conversion)
        files = ET.SubElement(image_elem, "FILES")
        file_elem = ET.SubElement(files, "FILE")
        file_elem.set("filename", f"IMAGES/IMAGE_{img.identifier}/{img.identifier}.dcm")
        file_elem.set("filetype", "dcm")
        file_elem.set("checksum_method", "SHA256")
        # checksum is required - this is the checksum of the (encrypted) file to be submitted
        file_elem.set("checksum", placeholder_checksum)
        # unencrypted_checksum is optional - checksum before encryption
        file_elem.set("unencrypted_checksum", placeholder_checksum)

        # Attributes
        attrs = ET.SubElement(image_elem, "ATTRIBUTES")
        add_string_attribute(attrs, "original_path", img.path)
        add_string_attribute(attrs, "original_filename", img.filename)

    return root


def create_observation_xml(observations: Dict[str, Observation]) -> ET.Element:
    """Create observation.xml with diagnosis statements per MetaFleX v2.0.0 schema."""
    root = ET.Element("OBSERVATION_SET")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    for obs in observations.values():
        obs_elem = ET.SubElement(root, "OBSERVATION")
        obs_elem.set("alias", obs.identifier)

        # Reference to the item (specimen/slide/etc.) - exactly one required
        item_type_map = {
            "Specimen": "SPECIMEN_REF",
            "Slide": "SLIDE_REF",
            "Block": "BLOCK_REF",
            "Case": "CASE_REF",
            "Image": "IMAGE_REF",
            "BiologicalBeing": "BIOLOGICAL_BEING_REF",
            "Annotation": "ANNOTATION_REF",
        }
        ref_elem_name = item_type_map.get(obs.item_type, "SPECIMEN_REF")
        ref_elem = ET.SubElement(obs_elem, ref_elem_name)
        ref_elem.set("alias", obs.item_id)

        # OBSERVER_REF is optional, skipped here

        # Statement (required)
        statement = ET.SubElement(obs_elem, "STATEMENT")

        stmt_type = ET.SubElement(statement, "STATEMENT_TYPE")
        stmt_type.text = obs.statement_type

        stmt_status = ET.SubElement(statement, "STATEMENT_STATUS")
        stmt_status.text = obs.statement_status

        # CODE_ATTRIBUTES (required, can be nil)
        code_attrs = ET.SubElement(statement, "CODE_ATTRIBUTES")
        if obs.diagnose_code:
            code_attr = ET.SubElement(code_attrs, "CODE_ATTRIBUTE")
            tag = ET.SubElement(code_attr, "TAG")
            tag.text = "diagnose"
            value = ET.SubElement(code_attr, "VALUE")
            code_elem = ET.SubElement(value, "CODE")
            code_elem.text = obs.diagnose_code
            scheme_elem = ET.SubElement(value, "SCHEME")
            scheme_elem.text = "SNOMED-CT"  # Assuming SNOMED morphology codes
            meaning_elem = ET.SubElement(value, "MEANING")
            meaning_elem.text = obs.freetext if obs.freetext else obs.diagnose_code
            scheme_version_elem = ET.SubElement(value, "SCHEME_VERSION")
            scheme_version_elem.set("xsi:nil", "true")
            scheme_version_elem.set(
                "xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"
            )
        else:
            code_attrs.set("xsi:nil", "true")
            code_attrs.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # CUSTOM_ATTRIBUTES (required, can be nil)
        custom_attrs = ET.SubElement(statement, "CUSTOM_ATTRIBUTES")
        if obs.pt_classification:
            add_string_attribute(
                custom_attrs, "pT_classification", obs.pt_classification
            )
        else:
            custom_attrs.set("xsi:nil", "true")
            custom_attrs.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # FREETEXT (required, can be nil)
        freetext = ET.SubElement(statement, "FREETEXT")
        if obs.freetext:
            freetext.text = obs.freetext
        else:
            freetext.set("xsi:nil", "true")
            freetext.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # ATTRIBUTES inside STATEMENT (required, can be nil)
        stmt_attrs = ET.SubElement(statement, "ATTRIBUTES")
        stmt_attrs.set("xsi:nil", "true")
        stmt_attrs.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # ATTRIBUTES for OBSERVATION (required, can be nil)
        add_nil_attributes(obs_elem)

    return root


def create_staining_xml(slides: Dict[str, Slide]) -> ET.Element:
    """Create staining.xml with stain definitions per MetaFleX v2.0.0 schema."""
    root = ET.Element("STAINING_SET")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Collect unique stainings
    stainings: Set[str] = set()
    for slide in slides.values():
        stainings.add(slide.staining)

    # Known stain codes (UMLS)
    stain_codes = {
        "HE": ("hematoxylin and eosin stain", "C0523965", "UMLS"),
        "H&E": ("hematoxylin and eosin stain", "C0523965", "UMLS"),
    }

    for stain in sorted(stainings):
        staining_elem = ET.SubElement(root, "STAINING")
        staining_elem.set("alias", stain)

        # Use PROCEDURE_INFORMATION for chemical stains like H&E
        # This contains attributes describing the staining procedure
        proc_info = ET.SubElement(staining_elem, "PROCEDURE_INFORMATION")
        add_string_attribute(proc_info, "staining_name", stain)

        # Add coded staining info if available
        if stain.upper() in stain_codes:
            meaning, code, scheme = stain_codes[stain.upper()]
            add_code_attribute(proc_info, "staining_code", code, scheme, meaning)

        # ATTRIBUTES (required, can be nil)
        add_nil_attributes(staining_elem)

    return root


def create_dataset_xml(
    dataset_id: str,
    images: Dict[str, Image],
    observations: Dict[str, Observation],
) -> ET.Element:
    """Create dataset.xml referencing all components per MetaFleX v2.0.0 schema."""
    root = ET.Element("DATASET")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("alias", dataset_id)

    # TITLE (required)
    title = ET.SubElement(root, "TITLE")
    title.text = f"Breast Tissue Dataset {dataset_id}"

    # SHORT_NAME (required)
    short_name = ET.SubElement(root, "SHORT_NAME")
    short_name.text = dataset_id

    # DESCRIPTION (optional)
    description = ET.SubElement(root, "DESCRIPTION")
    description.text = "Breast tissue whole slide image dataset with HE staining and diagnostic observations."

    # VERSION (required)
    version = ET.SubElement(root, "VERSION")
    version.text = "1.0.0"

    # METADATA_STANDARD (required, must match pattern 2.0.x)
    metadata_std = ET.SubElement(root, "METADATA_STANDARD")
    metadata_std.text = "2.0.0"

    # DATASET_TYPE (optional)
    dataset_type = ET.SubElement(root, "DATASET_TYPE")
    dataset_type.text = "Whole slide imaging"

    # Image references
    for img_id in images.keys():
        img_ref = ET.SubElement(root, "IMAGE_REF")
        img_ref.set("alias", img_id)

    # Observation references
    for obs_id in observations.keys():
        obs_ref = ET.SubElement(root, "OBSERVATION_REF")
        obs_ref.set("alias", obs_id)

    # ATTRIBUTES (required, can be nil)
    add_nil_attributes(root)

    return root


def main():
    parser = argparse.ArgumentParser(
        description="Convert breast tissue CSV dataset to BigPicture XML format"
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to data.csv",
    )
    parser.add_argument(
        "--observations",
        type=Path,
        required=True,
        help="Path to observations.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./bigpicture_output"),
        help="Output directory for XML files",
    )
    parser.add_argument(
        "--dataset-id",
        type=str,
        default="BREAST_TISSUE_001",
        help="Dataset identifier",
    )

    args = parser.parse_args()

    # Create output directory structure
    output_dir = args.output / f"DATASET_{args.dataset_id}"
    metadata_dir = output_dir / "METADATA"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # Also create placeholder directories
    (output_dir / "IMAGES").mkdir(exist_ok=True)
    (output_dir / "ANNOTATIONS").mkdir(exist_ok=True)
    (output_dir / "LANDING_PAGE" / "THUMBNAILS").mkdir(parents=True, exist_ok=True)
    (output_dir / "PRIVATE").mkdir(exist_ok=True)

    print(f"Parsing {args.data}...")
    beings, cases, specimens, blocks, slides, images = parse_data_csv(args.data)

    print(f"Parsing {args.observations}...")
    observations = parse_observations_csv(args.observations)

    print(f"Found:")
    print(f"  - {len(beings)} biological beings (patients)")
    print(f"  - {len(cases)} cases")
    print(f"  - {len(specimens)} specimens")
    print(f"  - {len(blocks)} blocks")
    print(f"  - {len(slides)} slides")
    print(f"  - {len(images)} images")
    print(f"  - {len(observations)} observations")

    # Generate XML files
    print("\nGenerating XML files...")

    sample_xml = create_sample_xml(beings, cases, specimens, blocks, slides)
    with open(metadata_dir / "sample.xml", "w", encoding="utf-8") as f:
        f.write(prettify_xml(sample_xml))
    print(f"  - sample.xml")

    image_xml = create_image_xml(images)
    with open(metadata_dir / "image.xml", "w", encoding="utf-8") as f:
        f.write(prettify_xml(image_xml))
    print(f"  - image.xml")

    observation_xml = create_observation_xml(observations)
    with open(metadata_dir / "observation.xml", "w", encoding="utf-8") as f:
        f.write(prettify_xml(observation_xml))
    print(f"  - observation.xml")

    staining_xml = create_staining_xml(slides)
    with open(metadata_dir / "staining.xml", "w", encoding="utf-8") as f:
        f.write(prettify_xml(staining_xml))
    print(f"  - staining.xml")

    dataset_xml = create_dataset_xml(args.dataset_id, images, observations)
    with open(metadata_dir / "dataset.xml", "w", encoding="utf-8") as f:
        f.write(prettify_xml(dataset_xml))
    print(f"  - dataset.xml")

    print(f"\nOutput written to: {output_dir}")
    print("\nNext steps:")
    print("  1. Convert SVS images to DICOM using wsidicomizer")
    print("  2. Update image.xml checksums after DICOM conversion")
    print("  3. Encrypt all files with crypt4gh")
    print("  4. Update checksums in image.xml for encrypted files")
    print("  5. Create policy.xml, landing_page.xml, and PRIVATE/*.xml")
    print("  6. Validate XML against BigPicture MetaFleX schemas with xmllint")


if __name__ == "__main__":
    main()
