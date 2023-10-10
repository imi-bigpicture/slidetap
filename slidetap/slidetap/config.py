"""Flask configuration."""
from os import environ
from typing import Optional


class Config(object):
    """Base configuration"""

    base = "SLIDES_"

    TESTING = False
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_TIMEZONE = "Europe/Stockholm"

    def __init__(self):
        base = "SLIDES_"
        self.SLIDES_STORAGE = self.env_get(base + "STORAGE")
        self.SLIDES_KEEPALIVE = self.env_get(base + "KEEPALIVE")
        self.SQLALCHEMY_DATABASE_URI = self.env_get(base + "DBURI")

        self.SLIDES_WEBAPPURL = self.env_get(base + "WEBAPPURL")
        self.SLIDES_ENFORCE_HTTPS = (
            self.env_get(base + "ENFORCE_HTTPS", "true") == "true"
        )
        self.SLIDES_SECRET_KEY = self.env_get(base + "SECRET_KEY")

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

    SLIDES_STORAGE = None
    SLIDES_KEEPALIVE = 30
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SLIDES_WEBAPPURL = "http://localhost:13000"
    SLIDES_ENFORCE_HTTPS = False
    SLIDES_SECRET_KEY = "secret"

    def __init__(self):
        pass
