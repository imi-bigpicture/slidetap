import argparse
import secrets
from pathlib import Path

from yaml import dump

storage = Path(__file__).parent / "storage"

storage.mkdir(exist_ok=True)

parser = argparse.ArgumentParser(
    description=("Create example config files for SlideTap")
)

parser.add_argument("--servername", type=str, default="localhost")
parser.add_argument("--port", type=int, default=3000)
parser.add_argument("--keep-alive", type=int, default=1800)
parser.add_argument("--log_level", type=str, default="DEBUG")
parser.add_argument("--dicomization-levels", type=str, default="all")
parser.add_argument("--dicomization-threads", type=int, default=1)
parser.add_argument("--task-worker-concurrency", type=int, default=4)
parser.add_argument(
    "--secret_key",
    type=str,
    default=None,
    help="At least 32 bytes. A random key is generated when not given.",
)
parser.add_argument("--postgres-user", type=str, default="slidetap")
parser.add_argument(
    "--postgres-password",
    type=str,
    default=None,
    help=(
        "Kept from an existing .env when not given, as Postgres only applies it "
        "when the database volume is created. Otherwise a random one is generated."
    ),
)
parser.add_argument("--test-data-path", type=str, default="/storage/images")
parser.add_argument("--test-data-image-extension", type=str, default=".svs")

args = parser.parse_args()
yaml_config = {
    "keep_alive": args.keep_alive,
    "log_level": args.log_level,
    "dicomization": {
        "levels": args.dicomization_levels,
        "threads": args.dicomization_threads,
    },
    "task": {
        "concurrency": args.task_worker_concurrency,
    },
    "example_test_data": args.test_data_path,
    "example_test_data_image_extension": args.test_data_image_extension,
}
with open(storage / "config.yaml", "w") as config_file:
    dump(yaml_config, config_file)


SLIDETAP_WEB_APP = "slidetap_example.web_app:app"
SLIDETAP_TASK_APP = "slidetap_example"
SLIDETAP_SECRET_KEY = args.secret_key or secrets.token_urlsafe(32)
SLIDETAP_CONFIG_FILE = "/storage/config.yaml"

SLIDETAP_SSL_CERTIFICATE_FOLDER = Path(__file__).parent / "ssl"
SLIDETAP_SSL_CERTIFICATE = "cert.pem"
SLIDETAP_SSL_CERTIFICATE_KEY = "privkey.pem"
SLIDETAP_API_PORT = 10000
SLIDETAP_WEBAPP_URL = args.servername + ":" + str(args.port)

env_path = Path(__file__).parent / ".env"
existing_env: dict[str, str] = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        name, separator, value = line.partition("=")
        if separator:
            existing_env[name.strip()] = value.strip()
POSTGRES_USER = args.postgres_user
POSTGRES_PASSWORD = (
    args.postgres_password
    or existing_env.get("POSTGRES_PASSWORD")
    or secrets.token_urlsafe(32)
)
POSTGRES_DB = "slidetap"

with open(env_path, "w") as env_file:
    env_file.write(
        f"SLIDETAP_SERVERNAME={args.servername}\n"
        f"SLIDETAP_PORT={args.port}\n"
        f"SLIDETAP_STORAGE={storage}\n"
        f"SLIDETAP_APIPORT={SLIDETAP_API_PORT}\n"
        f"SLIDETAP_CONFIG_FILE={SLIDETAP_CONFIG_FILE}\n"
        f"SLIDETAP_WEB_APP={SLIDETAP_WEB_APP}\n"
        f"SLIDETAP_TASK_APP={SLIDETAP_TASK_APP}\n"
        f"SLIDETAP_SSL_CERTIFICATE_FOLDER={SLIDETAP_SSL_CERTIFICATE_FOLDER}\n"
        f"SLIDETAP_SSL_CERTIFICATE={SLIDETAP_SSL_CERTIFICATE}\n"
        f"SLIDETAP_SSL_CERTIFICATE_KEY={SLIDETAP_SSL_CERTIFICATE_KEY}\n"
        f"SLIDETAP_SECRET_KEY={SLIDETAP_SECRET_KEY}\n"
        f"SLIDETAP_WEBAPP_URL={SLIDETAP_WEBAPP_URL}\n"
        f"POSTGRES_USER={POSTGRES_USER}\n"
        f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}\n"
        f"POSTGRES_DB={POSTGRES_DB}\n"
    )
