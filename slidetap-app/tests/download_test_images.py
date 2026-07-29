#    Copyright 2026 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Fetch the whole slide images the integration test reads.

The slides are not in the repository: ``*.svs`` is gitignored. Both images the
test expects are the same public slide under different names, so one download
covers both.

The slide is a small exported region of CMU-1 with a single pyramid level,
which the pipeline handles under the default ``DicomizationConfig`` (levels
``None``, meaning all of them). Full CMU-1 works too and is what a developer
may already have on disk, but it is 170 MB against 2 MB for no extra coverage.

Run from ``slidetap-app``::

    uv run python tests/download_test_images.py
"""

import shutil
import sys
import urllib.request
from hashlib import sha256
from pathlib import Path

URL = (
    "https://openslide.cs.cmu.edu/download/openslide-testdata/"
    "Aperio/CMU-1-Small-Region.svs"
)
SHA256 = "ed92d5a9f2e86df67640d6f92ce3e231419ce127131697fbbce42ad5e002c8a7"
"""Published for the slide in the openslide-testdata ``index.json``."""

TEST_DATA_PATH = Path(__file__).parent.joinpath("test_data")
IMAGE_IDENTIFIERS = ("ABC-1+2-A-1", "ABC-1+2-A-2")
"""Image identifiers in ``test_data/input.json``.

``ExampleImageImportInterface`` resolves each to
``test_data/<identifier>/<identifier>.svs``.
"""

_CHUNK_SIZE = 1024 * 1024


def image_paths() -> list[Path]:
    """Return the slide path expected for each image in the test input."""
    return [
        TEST_DATA_PATH.joinpath(identifier, identifier).with_suffix(".svs")
        for identifier in IMAGE_IDENTIFIERS
    ]


def missing_image_paths() -> list[Path]:
    """Return the expected slide paths that are not on disk."""
    return [path for path in image_paths() if not path.exists()]


def _checksum(path: Path) -> str:
    digest = sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL} to {path}.")
    # URL is an https literal, so the scheme audit S310 warns about does not apply.
    urllib.request.urlretrieve(URL, path)  # noqa: S310
    checksum = _checksum(path)
    if checksum != SHA256:
        path.unlink()
        sys.exit(f"Checksum mismatch for {path}: expected {SHA256}, got {checksum}.")
    print(f"Checksum OK for {path}.")


def main() -> None:
    missing = missing_image_paths()
    if not missing:
        print(f"Test images already present in {TEST_DATA_PATH}.")
        return

    # Copy from a slide that is already here rather than downloading twice.
    source = next((path for path in image_paths() if path.exists()), None)
    if source is None:
        source = missing.pop(0)
        _download(source)

    for path in missing:
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Copying {source} to {path}.")
        shutil.copyfile(source, path)


if __name__ == "__main__":
    main()
