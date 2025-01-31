import json
from hashlib import md5
from pathlib import Path
from typing import Any, Dict

from requests import Session

storage = Path(__file__).parent / "storage"

image_folder = storage / "images"


slidetap_app_folder = Path(__file__).parent.parent / "slidetap-app"
test_data_folder = slidetap_app_folder / "tests" / "test_data"
test_data_input_file = test_data_folder / "input.json"

openslide_test_slide_files = {
    "751b0b86a3c5ff4dfc8567cf24daaa85": "https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1.svs",
    "4e00a3e05b57d85e37d19a78c4824eca": "https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-2.svs",
    "4c1a8420fd9f7f2d145683baf2fdf694": "https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-3.svs",
}
extension = ".svs"

session = Session()

test_data_input = json.loads(test_data_input_file.read_text())


def calculate_md5(file: Path) -> str:
    md5_hash = md5()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()


for index, image in enumerate(test_data_input["images"]):
    image_identifier: str = image["identifier"]
    destination_folder = image_folder / image_identifier
    destination_folder.mkdir(exist_ok=True, parents=True)
    destination_file = destination_folder / f"{image_identifier}{extension}"
    if destination_file.exists():
        print(f"File {destination_file} already exists")
        expected_hash = calculate_md5(destination_file)
        if expected_hash in openslide_test_slide_files:
            continue
        print(f"Unexpected hash: {expected_hash}, redownloading")
        destination_file.unlink()

    expected_hash, url = list(openslide_test_slide_files.items())[
        index % len(openslide_test_slide_files)
    ]
    print(f"Downloading {url} to {destination_file}")
    with session.get(url, stream=True) as stream:
        with open(destination_file, "wb") as output_file:
            for chunk in stream.iter_content(chunk_size=1024):
                output_file.write(chunk)
    hash = calculate_md5(destination_file)
    if hash != expected_hash:
        raise ValueError(
            f"Hash mismatch for {destination_file}: {hash} != {expected_hash}"
        )
