# BigPicture Submission Checklist

Complete workflow for preparing a dataset for BigPicture submission using the MetaFleX v2.0.0 specification.

## Quick Start

**Automated workflow** (runs steps 1-5):
```bash
cd bigpicture_export
bash run_workflow.sh all
```

**Step-by-step execution:**
```bash
bash run_workflow.sh step1  # Generate XML
bash run_workflow.sh step2  # Convert to DICOM
bash run_workflow.sh step3  # Generate thumbnails
bash run_workflow.sh step4  # Compute checksums
bash run_workflow.sh step5  # Validate XML
# ... then manual steps, then:
bash run_workflow.sh step6  # Encrypt files
bash run_workflow.sh step7  # Update encrypted checksums
bash run_workflow.sh step8  # Encrypt metadata
```

---

## Detailed Checklist

### Prerequisites
- [ ] Python 3.10+ installed
- [ ] Install required packages: `pip install openslide-python pillow wsidicomizer crypt4gh`
- [ ] Install xmllint: `sudo apt-get install libxml2-utils` (Ubuntu/Debian)
- [ ] Prepare input files: `data.csv` and `observations.csv`
- [ ] Clone/update schema submodule: `git submodule update --init`

### Step 1: Generate XML Metadata
**Script:** `convert_to_bigpicture.py`

```bash
python convert_to_bigpicture.py \
  --data data.csv \
  --observations observations.csv \
  --output ./bigpicture_output \
  --dataset-id BREAST_TISSUE_2025
```

**Output:**
- ✓ `METADATA/sample.xml`
- ✓ `METADATA/image.xml`
- ✓ `METADATA/observation.xml`
- ✓ `METADATA/staining.xml`
- ✓ `METADATA/dataset.xml`

### Step 2: Convert SVS to DICOM
**Script:** `convert_svs_to_dicom.py`

```bash
python convert_svs_to_dicom.py \
  --data data.csv \
  --output ./bigpicture_output/DATASET_BREAST_TISSUE_2025
```

**Output:**
- ✓ DICOM files in `IMAGES/IMAGE_{id}/{id}.dcm`

### Step 3: Generate Thumbnails
**Script:** `generate_thumbnails.py`

```bash
python generate_thumbnails.py \
  --data data.csv \
  --output ./bigpicture_output/DATASET_BREAST_TISSUE_2025 \
  --size 512
```

**Output:**
- ✓ Thumbnails in `LANDING_PAGE/THUMBNAILS/{id}.jpg`

### Step 4: Compute Checksums
**Script:** `update_image_checksums.py`

```bash
python update_image_checksums.py \
  --metadata ./bigpicture_output/DATASET_BREAST_TISSUE_2025/METADATA \
  --images ./bigpicture_output/DATASET_BREAST_TISSUE_2025/IMAGES
```

**Output:**
- ✓ Updated `METADATA/image.xml` with unencrypted checksums

### Step 5: Validate XML
**Command:** `xmllint` via `run_workflow.sh`

```bash
bash run_workflow.sh step5
```

**Validates:**
- ✓ All XML files against BigPicture MetaFleX v2.0.0 schemas

---

### MANUAL STEPS (Create Additional XML Files)

#### Create `METADATA/policy.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<POLICY alias="BREAST_TISSUE_2025_POLICY">
  <TITLE>Breast Tissue Dataset Access Policy</TITLE>
  <POLICY_TEXT>Data access requires approval from the Data Access Committee.</POLICY_TEXT>
</POLICY>
```

#### Create `LANDING_PAGE/landing_page.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<LANDING_PAGE>
  <TITLE>Breast Tissue Whole Slide Image Dataset</TITLE>
  <DESCRIPTION>
    Curated dataset of breast tissue slides with HE staining,
    including diagnostic observations and TNM classifications.
  </DESCRIPTION>
  <KEYWORDS>breast, pathology, WSI, HE, carcinoma</KEYWORDS>
</LANDING_PAGE>
```

#### Create `PRIVATE/dac.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<DAC alias="BREAST_TISSUE_DAC">
  <TITLE>Breast Tissue Dataset DAC</TITLE>
  <CONTACTS>
    <CONTACT>
      <NAME>Your Name</NAME>
      <EMAIL>your.email@institution.com</EMAIL>
    </CONTACT>
  </CONTACTS>
</DAC>
```

#### Create `PRIVATE/submission.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<SUBMISSION alias="BREAST_TISSUE_2025_SUBMISSION">
  <TITLE>Breast Tissue Dataset Submission</TITLE>
  <SUBMISSION_DATE>2025-01-19</SUBMISSION_DATE>
  <SUBMITTER>
    <NAME>Your Name</NAME>
    <ORGANISATION>Your Institution</ORGANISATION>
  </SUBMITTER>
</SUBMISSION>
```

- [ ] Create all 4 manual XML files above

---

### Step 6: Encrypt Files
**Script:** `run_workflow.sh step6`

```bash
# First, download BigPicture public key from submission portal
# Save as: bigpicture.pub

bash run_workflow.sh step6
```

**Encrypts:**
- ✓ All DICOM files (`*.dcm` → `*.dcm.c4gh`)
- ✓ All thumbnails (`*.jpg` → `*.jpg.c4gh`)

### Step 7: Update Encrypted Checksums
**Script:** `update_image_checksums.py`

```bash
python update_image_checksums.py \
  --metadata ./bigpicture_output/DATASET_BREAST_TISSUE_2025/METADATA \
  --images ./bigpicture_output/DATASET_BREAST_TISSUE_2025/IMAGES \
  --encrypted
```

**Output:**
- ✓ Updated `METADATA/image.xml` with both encrypted and unencrypted checksums

### Step 8: Encrypt Metadata
**Script:** `run_workflow.sh step8`

```bash
bash run_workflow.sh step8
```

**Encrypts:**
- ✓ All metadata XML files
- ✓ `landing_page.xml`
- ✓ All files in `PRIVATE/`

---

## Final Checklist

- [ ] All steps 1-8 completed
- [ ] All required XML files created and encrypted
- [ ] Final directory structure verified (see below)
- [ ] Ready for submission to BigPicture

## Expected Final Directory Structure

```
DATASET_BREAST_TISSUE_2025/
├── METADATA/
│   ├── dataset.xml.c4gh
│   ├── sample.xml.c4gh
│   ├── image.xml.c4gh
│   ├── observation.xml.c4gh
│   ├── staining.xml.c4gh
│   └── policy.xml.c4gh
├── IMAGES/
│   ├── IMAGE_{id}/
│   │   └── {id}.dcm.c4gh
│   └── ... (one directory per image)
├── LANDING_PAGE/
│   ├── landing_page.xml.c4gh
│   └── THUMBNAILS/
│       ├── {id}.jpg.c4gh
│       └── ... (one thumbnail per image)
└── PRIVATE/
    ├── dac.xml.c4gh
    └── submission.xml.c4gh
```

---

## Configuration

Set these environment variables before running (optional):

```bash
export DATA_CSV="data.csv"
export OBSERVATIONS_CSV="observations.csv"
export DATASET_ID="BREAST_TISSUE_2025"
export OUTPUT_DIR="./bigpicture_output"
export BIGPICTURE_PUBLIC_KEY="bigpicture.pub"
```

## Script Reference

| Script | Purpose |
|--------|---------|
| `convert_to_bigpicture.py` | Generate XML metadata from CSV |
| `convert_svs_to_dicom.py` | Batch convert SVS to DICOM |
| `generate_thumbnails.py` | Generate thumbnails for landing page |
| `update_image_checksums.py` | Compute and update checksums in image.xml |
| `run_workflow.sh` | Master workflow orchestration script |

## Help

For detailed workflow documentation, see `WORKFLOW.md`.

For individual script help:
```bash
python convert_to_bigpicture.py --help
python convert_svs_to_dicom.py --help
python generate_thumbnails.py --help
python update_image_checksums.py --help
bash run_workflow.sh
```
