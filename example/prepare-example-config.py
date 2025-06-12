import argparse
from pathlib import Path

from yaml import dump

storage = Path(__file__).parent / "storage"

storage.mkdir()

parser = argparse.ArgumentParser(
    description=("Create example config files for SlideTap")
)

parser.add_argument("--servername", type=str, default="localhost")
parser.add_argument("--port", type=int, default=3000)
parser.add_argument("--keepalive", type=int, default=1800)
parser.add_argument("--enforce-https", type=bool, default=False)
parser.add_argument("--log_level", type=str, default="DEBUG")
parser.add_argument("--dicomization-levels", type=str, default="all")
parser.add_argument("--dicomization-threads", type=int, default=1)
parser.add_argument("--celery-worker-concurrency", type=int, default=None)
parser.add_argument("--celery-worker-max-tasks-per-child", type=int, default=10)
parser.add_argument("--secret_key", type=str, default="DEVELOP")
parser.add_argument("--test-data-path", type=str, default="/storage/images")
parser.add_argument("--test-data-image-extension", type=str, default=".svs")

args = parser.parse_args()
yaml_config = {
    "keepalive": args.keepalive,
    "enforce_https": args.enforce_https,
    "log_level": args.log_level,
    "dicomization": {
        "levels": args.dicomization_levels,
        "threads": args.dicomization_threads,
    },
    "celery": {
        "concurrency": args.celery_worker_concurrency,
        "max_tasks_per_child": args.celery_worker_max_tasks_per_child,
    },
    "example_test_data": args.test_data_path,
    "example_test_data_image_extension": args.test_data_image_extension,
}
with open(storage / "config.yaml", "w") as config_file:
    dump(yaml_config, config_file)


SLIDETAP_WEB_APP = "slidetap.apps.example.web_app:web_app"
SLIDETAP_TASK_APP = "slidetap.apps.example.task_app:task_app"
SLIDETAP_SECRET_KEY = args.secret_key
SLIDETAP_CONFIG_FILE = "/storage/config.yaml"

SLIDETAP_SSL_CERTIFICATE_FOLDER = Path(__file__).parent / "ssl"
SLIDETAP_SSL_CERTIFICATE = "cert.pem"
SLIDETAP_SSL_CERTIFICATE_KEY = "privkey.pem"
SLIDETAP_API_PORT = 10000
SLIDETAP_WEBAPP_URL = args.servername + ":" + str(args.port)

with open(".env", "w") as env_file:
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
    )
