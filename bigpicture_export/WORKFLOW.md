# BigPicture Submission Workflow

This document describes the complete workflow to convert your breast tissue CSV dataset to the BigPicture submission format.

## Prerequisites

- Python 3.10+
- `wsidicomizer` for SVS → DICOM conversion
- `crypt4gh` for encryption
- `xmllint` for schema validation
- BigPicture MetaFleX schemas from https://github.com/imi-bigpicture/bigpicture-metaflex

## Step 1: Convert CSV → XML Metadata

Run the conversion script to generate BigPicture-compliant XML files:

```bash
python convert_to_bigpicture.py \
  --data /path/to/data.csv \
  --observations /path/to/observations.csv \
  --output ./output \
  --dataset-id BREAST_TISSUE_2025
```

**Input:**
- `data.csv` – Image and sample hierarchy data
- `observations.csv` – Diagnosis observations

**Output:** `DATASET_BREAST_TISSUE_2025/METADATA/`
- `sample.xml` – BIOLOGICAL_BEING → CASE → SPECIMEN → BLOCK → SLIDE hierarchy
- `image.xml` – IMAGE elements with WSI_IMAGE type, linked to slides
- `observation.xml` – Diagnoses with CODE_ATTRIBUTES and CUSTOM_ATTRIBUTES
- `staining.xml` – STAINING elements with PROCEDURE_INFORMATION
- `dataset.xml` – Dataset manifest with metadata standard version

## Step 2: Convert SVS → DICOM

Convert each Leica SVS file to DICOM format using `wsidicomizer`:

```bash
# For each image
wsidicomizer \
  "\\path18\scans04\leica\2025-04-09\F2025000082T1-A-1_085417.svs" \
  "./output/DATASET_BREAST_TISSUE_2025/IMAGES/IMAGE_77ba31df-8f71-4fdc-8c4b-6e7ffbd41af6/"
```

Alternatively, batch convert using a script:

```python
import subprocess
import csv
from pathlib import Path

with open("data.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        image_id = row["Image ID"]
        svs_path = row["Image path"]
        output_dir = f"./output/DATASET_BREAST_TISSUE_2025/IMAGES/IMAGE_{image_id}/"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        subprocess.run(["wsidicomizer", svs_path, output_dir])
```

## Step 3: Generate Thumbnails

Create 512x512 JPEG thumbnails for each image in `LANDING_PAGE/THUMBNAILS/`:

```python
from PIL import Image
import openslide

def create_thumbnail(svs_path: str, output_path: str, size: int = 512):
    slide = openslide.OpenSlide(svs_path)
    thumbnail = slide.get_thumbnail((size, size))
    thumbnail.save(output_path, "JPEG")
```

Place thumbnails at:
```
DATASET_BREAST_TISSUE_2025/LANDING_PAGE/THUMBNAILS/{image_id}.jpg
```

## Step 4: Compute Checksums & Update image.xml

Calculate SHA256 checksums for each DICOM file:

```python
import hashlib
from pathlib import Path

def compute_sha256(filepath: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()
```

Update `image.xml` FILE elements replacing:
- `checksum` attribute → SHA256 of the final (encrypted) file
- `unencrypted_checksum` attribute → SHA256 of the unencrypted DICOM file

## Step 5: Create Remaining XML Files

### METADATA/policy.xml

Define data access policy:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<POLICY alias="BREAST_TISSUE_2025_POLICY">
  <TITLE>Breast Tissue Dataset Access Policy</TITLE>
  <POLICY_TEXT>Data access requires approval from the Data Access Committee.</POLICY_TEXT>
</POLICY>
```

### LANDING_PAGE/landing_page.xml

Dataset description for the landing page:

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

### PRIVATE/dac.xml

Data Access Committee information:

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

### PRIVATE/submission.xml

Submission metadata:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SUBMISSION alias="BREAST_TISSUE_2025_SUBMISSION">
  <TITLE>Breast Tissue Dataset Submission</TITLE>
  <SUBMISSION_DATE>2025-01-09</SUBMISSION_DATE>
  <SUBMITTER>
    <NAME>Your Name</NAME>
    <ORGANISATION>Your Institution</ORGANISATION>
  </SUBMITTER>
</SUBMISSION>
```

## Step 6: Encrypt with crypt4gh

Encrypt all files using the BigPicture public key:

```bash
# Get the BigPicture public key from the submission portal

# Encrypt metadata files
for file in METADATA/*.xml; do
  crypt4gh encrypt --recipient_pk bigpicture.pub < "$file" > "$file.c4gh"
  rm "$file"
done

# Encrypt DICOM files
find IMAGES -name "*.dcm" -exec sh -c '
  crypt4gh encrypt --recipient_pk bigpicture.pub < "$1" > "$1.c4gh" && rm "$1"
' _ {} \;

# Encrypt thumbnails
for file in LANDING_PAGE/THUMBNAILS/*.jpg; do
  crypt4gh encrypt --recipient_pk bigpicture.pub < "$file" > "$file.c4gh"
  rm "$file"
done

# Encrypt landing page and private files
crypt4gh encrypt --recipient_pk bigpicture.pub < LANDING_PAGE/landing_page.xml > LANDING_PAGE/landing_page.xml.c4gh
crypt4gh encrypt --recipient_pk bigpicture.pub < PRIVATE/dac.xml > PRIVATE/dac.xml.c4gh
crypt4gh encrypt --recipient_pk bigpicture.pub < PRIVATE/submission.xml > PRIVATE/submission.xml.c4gh
```

## Step 7: Update Checksums in image.xml

Before encrypting `image.xml`, update the FILE element checksums:

```python
# For each DICOM file (before and after encryption)
unencrypted_checksum = compute_sha256("IMAGE_{id}/{id}.dcm")
encrypted_checksum = compute_sha256("IMAGE_{id}/{id}.dcm.c4gh")

# Update image.xml FILE elements:
#   checksum="<encrypted_checksum>"
#   unencrypted_checksum="<unencrypted_checksum>"
```

Then encrypt `image.xml` last.

## Step 8: Validate Against Schemas

Before encryption, validate XML files against BigPicture MetaFleX v2.0.0 schemas:

```bash
# The schema repository is available as a submodule in bigpicture_export/bigpicture-metaflex/
# Or clone it separately: git clone https://github.com/imi-bigpicture/bigpicture-metaflex.git

# Validate each file (adjust paths as needed)
SCHEMA_DIR=bigpicture-metaflex/src

xmllint --schema $SCHEMA_DIR/BP.sample.xsd METADATA/sample.xml --noout
xmllint --schema $SCHEMA_DIR/BP.image.xsd METADATA/image.xml --noout
xmllint --schema $SCHEMA_DIR/BP.observation.xsd METADATA/observation.xml --noout
xmllint --schema $SCHEMA_DIR/BP.staining.xsd METADATA/staining.xml --noout
xmllint --schema $SCHEMA_DIR/BP.dataset.xsd METADATA/dataset.xml --noout
```

Fix any validation errors before proceeding with encryption.

## Final Directory Structure

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
│   ├── IMAGE_77ba31df-8f71-4fdc-8c4b-6e7ffbd41af6/
│   │   └── 77ba31df-8f71-4fdc-8c4b-6e7ffbd41af6.dcm.c4gh
│   └── IMAGE_{...}/
│       └── {...}.dcm.c4gh
├── ANNOTATIONS/
│   └── (empty or annotation files if applicable)
├── LANDING_PAGE/
│   ├── landing_page.xml.c4gh
│   └── THUMBNAILS/
│       ├── 77ba31df-8f71-4fdc-8c4b-6e7ffbd41af6.jpg.c4gh
│       └── {...}.jpg.c4gh
└── PRIVATE/
    ├── dac.xml.c4gh
    └── submission.xml.c4gh
```

## Summary Checklist

- [ ] Run `convert_to_bigpicture.py` to generate initial XML (MetaFleX v2.0.0 compliant)
- [ ] Convert all SVS files to DICOM with `wsidicomizer`
- [ ] Generate JPEG thumbnails for all images
- [ ] Compute SHA256 checksums for unencrypted DICOM files
- [ ] Create `policy.xml`, `landing_page.xml`, `dac.xml`, `submission.xml`
- [ ] Validate all XML against BigPicture MetaFleX v2.0.0 schemas
- [ ] Encrypt DICOM and other data files with `crypt4gh`
- [ ] Compute SHA256 checksums for encrypted files
- [ ] Update `image.xml` with both checksums (`checksum` for encrypted, `unencrypted_checksum` for original)
- [ ] Encrypt remaining XML files (including `image.xml` last)
- [ ] Final validation and submission

## References

- [BigPicture Preparation Guide](https://bp.nbis.se/datasets/submission/preparation-guide.html)
- [BigPicture MetaFleX Schemas](https://github.com/imi-bigpicture/bigpicture-metaflex)
- [crypt4gh Documentation](https://crypt4gh.readthedocs.io/)
- [wsidicomizer Documentation](https://github.com/imi-bigpicture/wsidicomizer)
