#!/bin/bash
#
# BigPicture Dataset Preparation Workflow
#
# This script guides you through the complete workflow for preparing a dataset
# for BigPicture submission following the MetaFleX v2.0.0 specification.
#
# Usage:
#   bash run_workflow.sh
#
# Or run individual steps:
#   bash run_workflow.sh step1
#   bash run_workflow.sh step2
#   etc.

set -e  # Exit on error
INPUT_DIR="${INPUT_DIR:-./input}"
# Configuration - EDIT THESE VALUES
DATA_CSV="${DATA_CSV:-$INPUT_DIR/data.csv}"
OBSERVATIONS_CSV="${OBSERVATIONS_CSV:-$INPUT_DIR/observations.csv}"
DATASET_ID="${DATASET_ID:-BREAST_TISSUE_2025}"
OUTPUT_DIR="${OUTPUT_DIR:-./bigpicture_output}"
BIGPICTURE_PUBLIC_KEY="${BIGPICTURE_PUBLIC_KEY:-bigpicture.pub}"

# Derived paths
DATASET_DIR="$OUTPUT_DIR/DATASET_$DATASET_ID"
METADATA_DIR="$DATASET_DIR/METADATA"
IMAGES_DIR="$DATASET_DIR/IMAGES"
SCHEMA_DIR="bigpicture-metaflex/src"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${GREEN}===================================================================${NC}"
    echo -e "${GREEN}STEP $1: $2${NC}"
    echo -e "${GREEN}===================================================================${NC}\n"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

check_requirements() {
    print_step "0" "Checking Requirements"

    local missing=0

    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found"
        missing=1
    fi

    # Check wsidicomizer (optional for step 2)
    if ! command -v wsidicomizer &> /dev/null; then
        print_warning "wsidicomizer not found (needed for step 2)"
        echo "  Install: pip install wsidicomizer"
    fi

    # Check crypt4gh (optional for step 6)
    if ! command -v crypt4gh &> /dev/null; then
        print_warning "crypt4gh not found (needed for step 6)"
        echo "  Install: pip install crypt4gh"
    fi

    # Check xmllint (optional for step 5)
    if ! command -v xmllint &> /dev/null; then
        print_warning "xmllint not found (needed for step 5)"
        echo "  Install: sudo apt-get install libxml2-utils (Ubuntu/Debian)"
    fi

    # Check input files
    if [ ! -f "$DATA_CSV" ]; then
        print_error "Data file not found: $DATA_CSV"
        missing=1
    fi

    if [ ! -f "$OBSERVATIONS_CSV" ]; then
        print_error "Observations file not found: $OBSERVATIONS_CSV"
        missing=1
    fi

    # Check schema directory
    if [ ! -d "$SCHEMA_DIR" ]; then
        print_warning "Schema directory not found: $SCHEMA_DIR"
        echo "  The schemas are needed for validation in step 5"
    fi

    if [ $missing -eq 1 ]; then
        print_error "Missing required dependencies or files"
        exit 1
    fi

    echo -e "${GREEN}✓ All basic requirements met${NC}"
}

step1_generate_xml() {
    print_step "1" "Generate XML Metadata from CSV"

    python3 convert_to_bigpicture.py \
        --data "$DATA_CSV" \
        --observations "$OBSERVATIONS_CSV" \
        --output "$OUTPUT_DIR" \
        --dataset-id "$DATASET_ID"

    echo -e "${GREEN}✓ Step 1 complete${NC}"
    echo "Generated files in: $METADATA_DIR"
}

step2_convert_dicom() {
    print_step "2" "Convert SVS to DICOM"

    if ! command -v wsidicomizer &> /dev/null; then
        print_error "wsidicomizer not found. Install with: pip install wsidicomizer"
        exit 1
    fi

    python3 convert_svs_to_dicom.py \
        --data "$DATA_CSV" \
        --output "$DATASET_DIR"

    echo -e "${GREEN}✓ Step 2 complete${NC}"
    echo "DICOM files in: $IMAGES_DIR"
}

step3_generate_thumbnails() {
    print_step "3" "Generate Thumbnails"

    python3 generate_thumbnails.py \
        --data "$DATA_CSV" \
        --output "$DATASET_DIR" \
        --size 512

    echo -e "${GREEN}✓ Step 3 complete${NC}"
    echo "Thumbnails in: $DATASET_DIR/LANDING_PAGE/THUMBNAILS"
}

step4_update_checksums() {
    print_step "4" "Compute Checksums and Update image.xml"

    python3 update_image_checksums.py \
        --metadata "$METADATA_DIR" \
        --images "$IMAGES_DIR"

    echo -e "${GREEN}✓ Step 4 complete${NC}"
    echo "Updated: $METADATA_DIR/image.xml"
}

step5_validate_xml() {
    print_step "5" "Validate XML Against Schemas"

    if ! command -v xmllint &> /dev/null; then
        print_error "xmllint not found. Install with: sudo apt-get install libxml2-utils"
        exit 1
    fi

    if [ ! -d "$SCHEMA_DIR" ]; then
        print_error "Schema directory not found: $SCHEMA_DIR"
        echo "Schemas should be in bigpicture_export/bigpicture-metaflex/src/"
        exit 1
    fi

    echo "Validating sample.xml..."
    xmllint --schema "$SCHEMA_DIR/BP.sample.xsd" "$METADATA_DIR/sample.xml" --noout

    echo "Validating image.xml..."
    xmllint --schema "$SCHEMA_DIR/BP.image.xsd" "$METADATA_DIR/image.xml" --noout

    echo "Validating observation.xml..."
    xmllint --schema "$SCHEMA_DIR/BP.observation.xsd" "$METADATA_DIR/observation.xml" --noout

    echo "Validating staining.xml..."
    xmllint --schema "$SCHEMA_DIR/BP.staining.xsd" "$METADATA_DIR/staining.xml" --noout

    echo "Validating dataset.xml..."
    xmllint --schema "$SCHEMA_DIR/BP.dataset.xsd" "$METADATA_DIR/dataset.xml" --noout

    echo -e "${GREEN}✓ Step 5 complete - All XML files are valid${NC}"
}

step6_encrypt_files() {
    print_step "6" "Encrypt Files with crypt4gh"

    if ! command -v crypt4gh &> /dev/null; then
        print_error "crypt4gh not found. Install with: pip install crypt4gh"
        exit 1
    fi

    if [ ! -f "$BIGPICTURE_PUBLIC_KEY" ]; then
        print_error "BigPicture public key not found: $BIGPICTURE_PUBLIC_KEY"
        echo "Download the public key from the BigPicture submission portal"
        exit 1
    fi

    print_warning "This will encrypt all DICOM files. This may take a long time."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 1
    fi

    # Encrypt DICOM files
    echo "Encrypting DICOM files..."
    find "$IMAGES_DIR" -name "*.dcm" -type f | while read -r file; do
        echo "  Encrypting: $file"
        crypt4gh encrypt --recipient_pk "$BIGPICTURE_PUBLIC_KEY" < "$file" > "$file.c4gh"
        rm "$file"
    done

    # Encrypt thumbnails
    echo "Encrypting thumbnails..."
    find "$DATASET_DIR/LANDING_PAGE/THUMBNAILS" -name "*.jpg" -type f | while read -r file; do
        echo "  Encrypting: $file"
        crypt4gh encrypt --recipient_pk "$BIGPICTURE_PUBLIC_KEY" < "$file" > "$file.c4gh"
        rm "$file"
    done

    echo -e "${GREEN}✓ Step 6 complete${NC}"
}

step7_update_encrypted_checksums() {
    print_step "7" "Update Encrypted Checksums in image.xml"

    python3 update_image_checksums.py \
        --metadata "$METADATA_DIR" \
        --images "$IMAGES_DIR" \
        --encrypted

    echo -e "${GREEN}✓ Step 7 complete${NC}"
}

step8_encrypt_metadata() {
    print_step "8" "Encrypt Metadata XML Files"

    if ! command -v crypt4gh &> /dev/null; then
        print_error "crypt4gh not found. Install with: pip install crypt4gh"
        exit 1
    fi

    if [ ! -f "$BIGPICTURE_PUBLIC_KEY" ]; then
        print_error "BigPicture public key not found: $BIGPICTURE_PUBLIC_KEY"
        exit 1
    fi

    # Encrypt all metadata XML files
    for file in "$METADATA_DIR"/*.xml; do
        if [ -f "$file" ]; then
            echo "Encrypting: $file"
            crypt4gh encrypt --recipient_pk "$BIGPICTURE_PUBLIC_KEY" < "$file" > "$file.c4gh"
            rm "$file"
        fi
    done

    # Encrypt additional XML files if they exist
    if [ -f "$DATASET_DIR/LANDING_PAGE/landing_page.xml" ]; then
        echo "Encrypting landing_page.xml"
        crypt4gh encrypt --recipient_pk "$BIGPICTURE_PUBLIC_KEY" < "$DATASET_DIR/LANDING_PAGE/landing_page.xml" > "$DATASET_DIR/LANDING_PAGE/landing_page.xml.c4gh"
        rm "$DATASET_DIR/LANDING_PAGE/landing_page.xml"
    fi

    if [ -d "$DATASET_DIR/PRIVATE" ]; then
        for file in "$DATASET_DIR/PRIVATE"/*.xml; do
            if [ -f "$file" ]; then
                echo "Encrypting: $file"
                crypt4gh encrypt --recipient_pk "$BIGPICTURE_PUBLIC_KEY" < "$file" > "$file.c4gh"
                rm "$file"
            fi
        done
    fi

    echo -e "${GREEN}✓ Step 8 complete${NC}"
}

show_summary() {
    echo -e "\n${GREEN}===================================================================${NC}"
    echo -e "${GREEN}WORKFLOW SUMMARY${NC}"
    echo -e "${GREEN}===================================================================${NC}\n"

    echo "Dataset: $DATASET_ID"
    echo "Output directory: $DATASET_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Review the generated files in $DATASET_DIR"
    echo "  2. Create additional required XML files:"
    echo "     - METADATA/policy.xml"
    echo "     - LANDING_PAGE/landing_page.xml"
    echo "     - PRIVATE/dac.xml"
    echo "     - PRIVATE/submission.xml"
    echo "  3. Complete remaining encryption steps if not done"
    echo "  4. Submit to BigPicture"
    echo ""
}

# Main execution
case "${1:-all}" in
    step0|check)
        check_requirements
        ;;
    step1)
        check_requirements
        step1_generate_xml
        ;;
    step2)
        check_requirements
        step2_convert_dicom
        ;;
    step3)
        check_requirements
        step3_generate_thumbnails
        ;;
    step4)
        check_requirements
        step4_update_checksums
        ;;
    step5)
        check_requirements
        step5_validate_xml
        ;;
    step6)
        check_requirements
        step6_encrypt_files
        ;;
    step7)
        check_requirements
        step7_update_encrypted_checksums
        ;;
    step8)
        check_requirements
        step8_encrypt_metadata
        ;;
    all)
        check_requirements
        step1_generate_xml
        step2_convert_dicom
        step3_generate_thumbnails
        step4_update_checksums
        step5_validate_xml
        echo -e "\n${YELLOW}Automated workflow complete up to validation.${NC}"
        echo -e "${YELLOW}Manual steps remaining:${NC}"
        echo "  - Create policy.xml, landing_page.xml, dac.xml, submission.xml"
        echo "  - Run: bash run_workflow.sh step6  (encrypt files)"
        echo "  - Run: bash run_workflow.sh step7  (update encrypted checksums)"
        echo "  - Run: bash run_workflow.sh step8  (encrypt metadata)"
        show_summary
        ;;
    *)
        echo "BigPicture Dataset Preparation Workflow"
        echo ""
        echo "Usage: bash run_workflow.sh [step]"
        echo ""
        echo "Steps:"
        echo "  step0 (check)  - Check requirements"
        echo "  step1          - Generate XML metadata from CSV"
        echo "  step2          - Convert SVS to DICOM"
        echo "  step3          - Generate thumbnails"
        echo "  step4          - Compute checksums and update image.xml"
        echo "  step5          - Validate XML against schemas"
        echo "  step6          - Encrypt DICOM and thumbnail files"
        echo "  step7          - Update encrypted checksums in image.xml"
        echo "  step8          - Encrypt metadata XML files"
        echo "  all            - Run all automated steps (1-5)"
        echo ""
        echo "Configuration (set as environment variables):"
        echo "  DATA_CSV              = $DATA_CSV"
        echo "  OBSERVATIONS_CSV      = $OBSERVATIONS_CSV"
        echo "  DATASET_ID            = $DATASET_ID"
        echo "  OUTPUT_DIR            = $OUTPUT_DIR"
        echo "  BIGPICTURE_PUBLIC_KEY = $BIGPICTURE_PUBLIC_KEY"
        ;;
esac
