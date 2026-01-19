# Script Execution Order

Complete sequence of scripts to execute for BigPicture dataset preparation.

## Prerequisites
```bash
pip install openslide-python pillow wsidicomizer crypt4gh
sudo apt-get install libxml2-utils  # For xmllint
git submodule update --init  # Get schemas
```

---

## Automated Method (Recommended)

```bash
cd bigpicture_export

# Run all automated steps (1-5)
bash run_workflow.sh all

# Create manual XML files (see CHECKLIST.md)
# - METADATA/policy.xml
# - LANDING_PAGE/landing_page.xml
# - PRIVATE/dac.xml
# - PRIVATE/submission.xml

# Complete encryption steps
bash run_workflow.sh step6  # Encrypt files
bash run_workflow.sh step7  # Update encrypted checksums
bash run_workflow.sh step8  # Encrypt metadata
```

---

## Manual Method (Step-by-Step)

### Step 1: Generate XML Metadata
```bash
python convert_to_bigpicture.py \
  --data data.csv \
  --observations observations.csv \
  --output ./bigpicture_output \
  --dataset-id BREAST_TISSUE_2025
```

### Step 2: Convert SVS to DICOM
```bash
python convert_svs_to_dicom.py \
  --data data.csv \
  --output ./bigpicture_output/DATASET_BREAST_TISSUE_2025
```

### Step 3: Generate Thumbnails
```bash
python generate_thumbnails.py \
  --data data.csv \
  --output ./bigpicture_output/DATASET_BREAST_TISSUE_2025 \
  --size 512
```

### Step 4: Compute Checksums (Unencrypted)
```bash
python update_image_checksums.py \
  --metadata ./bigpicture_output/DATASET_BREAST_TISSUE_2025/METADATA \
  --images ./bigpicture_output/DATASET_BREAST_TISSUE_2025/IMAGES
```

### Step 5: Validate XML
```bash
cd bigpicture_export
SCHEMA_DIR=bigpicture-metaflex/src
METADATA_DIR=../bigpicture_output/DATASET_BREAST_TISSUE_2025/METADATA

xmllint --schema $SCHEMA_DIR/BP.sample.xsd $METADATA_DIR/sample.xml --noout
xmllint --schema $SCHEMA_DIR/BP.image.xsd $METADATA_DIR/image.xml --noout
xmllint --schema $SCHEMA_DIR/BP.observation.xsd $METADATA_DIR/observation.xml --noout
xmllint --schema $SCHEMA_DIR/BP.staining.xsd $METADATA_DIR/staining.xml --noout
xmllint --schema $SCHEMA_DIR/BP.dataset.xsd $METADATA_DIR/dataset.xml --noout
```

### MANUAL: Create Additional XML Files
Create these 4 files manually (templates in CHECKLIST.md):
- `METADATA/policy.xml`
- `LANDING_PAGE/landing_page.xml`
- `PRIVATE/dac.xml`
- `PRIVATE/submission.xml`

### Step 6: Encrypt DICOM and Thumbnails
```bash
# Download bigpicture.pub from submission portal first

DATASET_DIR=./bigpicture_output/DATASET_BREAST_TISSUE_2025
PUBLIC_KEY=bigpicture.pub

# Encrypt DICOM files
find $DATASET_DIR/IMAGES -name "*.dcm" -type f | while read file; do
  crypt4gh encrypt --recipient_pk $PUBLIC_KEY < "$file" > "$file.c4gh"
  rm "$file"
done

# Encrypt thumbnails
find $DATASET_DIR/LANDING_PAGE/THUMBNAILS -name "*.jpg" -type f | while read file; do
  crypt4gh encrypt --recipient_pk $PUBLIC_KEY < "$file" > "$file.c4gh"
  rm "$file"
done
```

### Step 7: Update Checksums (Encrypted)
```bash
python update_image_checksums.py \
  --metadata ./bigpicture_output/DATASET_BREAST_TISSUE_2025/METADATA \
  --images ./bigpicture_output/DATASET_BREAST_TISSUE_2025/IMAGES \
  --encrypted
```

### Step 8: Encrypt Metadata XML Files
```bash
DATASET_DIR=./bigpicture_output/DATASET_BREAST_TISSUE_2025
PUBLIC_KEY=bigpicture.pub

# Encrypt metadata
for file in $DATASET_DIR/METADATA/*.xml; do
  crypt4gh encrypt --recipient_pk $PUBLIC_KEY < "$file" > "$file.c4gh"
  rm "$file"
done

# Encrypt landing page
crypt4gh encrypt --recipient_pk $PUBLIC_KEY \
  < $DATASET_DIR/LANDING_PAGE/landing_page.xml \
  > $DATASET_DIR/LANDING_PAGE/landing_page.xml.c4gh
rm $DATASET_DIR/LANDING_PAGE/landing_page.xml

# Encrypt private files
for file in $DATASET_DIR/PRIVATE/*.xml; do
  crypt4gh encrypt --recipient_pk $PUBLIC_KEY < "$file" > "$file.c4gh"
  rm "$file"
done
```

---

## Summary

**5 Python Scripts:**
1. `convert_to_bigpicture.py` - Generate XML from CSV
2. `convert_svs_to_dicom.py` - SVS → DICOM conversion
3. `generate_thumbnails.py` - Create thumbnails
4. `update_image_checksums.py` - Compute/update checksums (run twice: before and after encryption)
5. `run_workflow.sh` - Master orchestration script

**Or just use the master script:**
```bash
bash run_workflow.sh all           # Automated steps 1-5
# Create manual XML files
bash run_workflow.sh step6         # Encrypt files
bash run_workflow.sh step7         # Update encrypted checksums
bash run_workflow.sh step8         # Encrypt metadata
```

**That's it!** Your dataset is ready for BigPicture submission.
