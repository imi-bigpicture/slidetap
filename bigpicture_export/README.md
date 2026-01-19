# BigPicture Export Tools

Tools for preparing whole slide image datasets for submission to BigPicture following the MetaFleX v2.0.0 specification.

## Quick Start

**Run the complete workflow:**
```bash
cd bigpicture_export
bash run_workflow.sh all
```

**Or see the detailed checklist:**
```bash
cat CHECKLIST.md
```

## What's Included

### Scripts

1. **`convert_to_bigpicture.py`** - Generate MetaFleX v2.0.0 XML metadata from CSV files
2. **`convert_svs_to_dicom.py`** - Batch convert SVS whole slide images to DICOM format
3. **`generate_thumbnails.py`** - Generate thumbnails for the landing page
4. **`update_image_checksums.py`** - Compute SHA256 checksums and update image.xml
5. **`run_workflow.sh`** - Master orchestration script for the complete workflow

### Documentation

- **`CHECKLIST.md`** - Quick reference checklist for execution (⭐ START HERE)
- **`WORKFLOW.md`** - Detailed workflow documentation
- **`bigpicture-metaflex/`** - XML schema definitions (git submodule)

## Workflow Overview


INPUT: data.csv + observations.csv

Step 1: Generate XML Metadata
→ convert_to_bigpicture.py
✓ sample.xml, image.xml, observation.xml, staining.xml

Step 2: Convert SVS → DICOM
→ convert_svs_to_dicom.py
✓ DICOM files in IMAGES/

Step 3: Generate Thumbnails
→ generate_thumbnails.py
✓ Thumbnails in LANDING_PAGE/THUMBNAILS/

Step 4: Compute Checksums
→ update_image_checksums.py
✓ Updated image.xml with unencrypted checksums

Step 5: Validate XML
→ xmllint + MetaFleX schemas
✓ All XML validated against v2.0.0 schemas

MANUAL: Create policy.xml, landing_page.xml,
        dac.xml, submission.xml

Step 6: Encrypt Files
→ crypt4gh
✓ All DICOM and thumbnails encrypted

Step 7: Update Encrypted Checksums
→ update_image_checksums.py --encrypted
✓ image.xml updated with encrypted checksums

Step 8: Encrypt Metadata
→ crypt4gh
✓ All XML files encrypted

OUTPUT: Ready for BigPicture submission


## Installation

### Prerequisites
```bash
# Python packages
pip install openslide-python pillow wsidicomizer crypt4gh

# System packages (Ubuntu/Debian)
sudo apt-get install libxml2-utils openslide-tools

# Clone schema submodule
git submodule update --init
```

### Input Files

Prepare two CSV files:

1. **`data.csv`** - Image and sample hierarchy data with columns:
   - Biological being ID, Sex, Animal species
   - Case ID
   - Specimen ID, Specimen type, Extraction method, Anatomical site
   - Block ID, Block preparation
   - Slide ID, Staining
   - Image ID, Image path
   - Age at extraction interval start/duration

2. **`observations.csv`** - Diagnosis observations with columns:
   - Observation ID, Item type, Item ID
   - Statement type, Statement status
   - Code attribute Diagnose, Custom attribute pT classification
   - Freetext

## Usage Examples

### Generate XML only
```bash
python convert_to_bigpicture.py \
  --data data.csv \
  --observations observations.csv \
  --output ./output \
  --dataset-id MY_DATASET
```

### Convert images to DICOM
```bash
python convert_svs_to_dicom.py \
  --data data.csv \
  --output ./output/DATASET_MY_DATASET
```

### Generate thumbnails
```bash
python generate_thumbnails.py \
  --data data.csv \
  --output ./output/DATASET_MY_DATASET \
  --size 512
```

### Update checksums
```bash
# Before encryption
python update_image_checksums.py \
  --metadata ./output/DATASET_MY_DATASET/METADATA \
  --images ./output/DATASET_MY_DATASET/IMAGES

# After encryption
python update_image_checksums.py \
  --metadata ./output/DATASET_MY_DATASET/METADATA \
  --images ./output/DATASET_MY_DATASET/IMAGES \
  --encrypted
```

### Run complete workflow
```bash
# Set configuration (optional)
export DATASET_ID="MY_DATASET"
export DATA_CSV="my_data.csv"
export OBSERVATIONS_CSV="my_observations.csv"

# Run automated steps
bash run_workflow.sh all

# Run individual steps
bash run_workflow.sh step1
bash run_workflow.sh step2
# ... etc
```

## Configuration

Set environment variables to customize:

```bash
export DATA_CSV="data.csv"              # Input data file
export OBSERVATIONS_CSV="observations.csv"  # Input observations file
export DATASET_ID="BREAST_TISSUE_2025"  # Dataset identifier
export OUTPUT_DIR="./bigpicture_output" # Output directory
export BIGPICTURE_PUBLIC_KEY="bigpicture.pub"  # Public key for encryption
```

## Validation

All generated XML files are validated against the BigPicture MetaFleX v2.0.0 schemas:
- `BP.sample.xsd` - Sample hierarchy
- `BP.image.xsd` - Image metadata
- `BP.observation.xsd` - Observations
- `BP.staining.xsd` - Staining information
- `BP.dataset.xsd` - Dataset manifest

## References

- [BigPicture Preparation Guide](https://bp.nbis.se/datasets/submission/preparation-guide.html)
- [BigPicture MetaFleX Schemas](https://github.com/imi-bigpicture/bigpicture-metaflex)
- [crypt4gh Documentation](https://crypt4gh.readthedocs.io/)
- [wsidicomizer Documentation](https://github.com/imi-bigpicture/wsidicomizer)

## Troubleshooting

### Common Issues

**wsidicomizer not found:**
```bash
pip install wsidicomizer
```

**openslide error:**
```bash
# Ubuntu/Debian
sudo apt-get install openslide-tools python3-openslide

# macOS
brew install openslide
pip install openslide-python
```

**xmllint not found:**
```bash
# Ubuntu/Debian
sudo apt-get install libxml2-utils

# macOS
# xmllint is included by default
```

**crypt4gh not found:**
```bash
pip install crypt4gh
```

## License

See parent repository license.
