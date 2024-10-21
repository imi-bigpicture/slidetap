from logging.config import dictConfig
from typing import Literal


def setup_logging(
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = "INFO"
) -> None:
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": (
                        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                    ),
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://flask.logging.wsgi_errors_stream",
                    "formatter": "default",
                }
            },
            "root": {"level": level, "handlers": ["wsgi"]},
        }
    )
