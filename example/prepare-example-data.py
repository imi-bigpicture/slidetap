from pathlib import Path

from requests import Session

storage = Path(__file__).parent / "storage"

image_folder = storage / "images"


slidetap_app_folder = Path(__file__).parent.parent / "slidetap-app"
test_data_folder = slidetap_app_folder / "tests" / "test_data"


openslide_test_slide_url = (
    "https://data.cytomine.coop/open/openslide/aperio-svs/CMU-1.svs"
)
extension = ".svs"

session = Session()

for folder in test_data_folder.iterdir():
    if folder.is_dir():
        destination_folder = image_folder / folder.name
        destination_folder.mkdir(exist_ok=True, parents=True)
        print(f"Downloading {folder.name} to {destination_folder}")
        with session.get(openslide_test_slide_url, stream=True) as stream:
            with open(
                (destination_folder / destination_folder.name).with_suffix(extension),
                "wb",
            ) as output_file:
                for chunk in stream.iter_content(chunk_size=1024):
                    output_file.write(chunk)
