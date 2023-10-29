"""Flask configuration."""
from os import environ
from typing import Optional


class Config(object):
    """Base configuration"""

    base = "SLIDETAP_"

    TESTING = False
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_TIMEZONE = "Europe/Stockholm"
    SLIDETAP_INCLUDE_LEVELS = None

    def __init__(self):
        base = "SLIDETAP_"
        self.SLIDETAP_STORAGE = self.env_get(base + "STORAGE")
        self.SLIDETAP_KEEPALIVE = self.env_get(base + "KEEPALIVE")
        self.SQLALCHEMY_DATABASE_URI = self.env_get(base + "DBURI")

        self.SLIDETAP_WEBAPPURL = self.env_get(base + "WEBAPPURL")
        self.SLIDETAP_ENFORCE_HTTPS = (
            self.env_get(base + "ENFORCE_HTTPS", "true") == "true"
        )
        self.SLIDETAP_SECRET_KEY = self.env_get(base + "SECRET_KEY")
        include_levels = self.env_get(base + "INCLUDE_LEVELS", None)
        if include_levels is None:
            self.SLIDETAP_INCLUDE_LEVELS = None
        else:
            self.SLIDETAP_INCLUDE_LEVELS = [
                int(value) for value in include_levels.split(",")
            ]

    @staticmethod
    def env_get(name: str, default: Optional[str] = None) -> str:
        """Get environmental variable by name. If not found, return default if set,
        otherwise raise ValueError."""
        value = environ.get(name)
        if value is not None:
            return value
        if default is None:
            raise ValueError(f"Environmental variable {name} must be set")
        return default


class ConfigProduction(Config):
    pass


class ConfigDevelopment(Config):
    """Enables debug mode, reload on change."""

    DEBUG = True
    TESTING = True


class ConfigTest(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True

    SLIDETAP_STORAGE = None
    SLIDETAP_KEEPALIVE = 30
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SLIDETAP_WEBAPPURL = "http://localhost:13000"
    SLIDETAP_ENFORCE_HTTPS = False
    SLIDETAP_SECRET_KEY = "secret"

    def __init__(self):
        pass
