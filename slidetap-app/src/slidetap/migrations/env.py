"""Alembic environment for SlideTap.

The database URL is read from ``SLIDETAP_DBURI`` (with a fallback to
``sqlalchemy.url`` in alembic.ini). Bare ``postgresql://``,
``postgres://``, and ``postgresql+psycopg2://`` schemes are rewritten to
``postgresql+psycopg://`` because the project ships psycopg v3, not v2.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, make_url, pool

from slidetap.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    url = os.environ.get("SLIDETAP_DBURI") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "No database URL configured. Set SLIDETAP_DBURI or sqlalchemy.url."
        )
    for scheme in ("postgresql://", "postgres://", "postgresql+psycopg2://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme) :]
    return url


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=make_url(url).get_backend_name() == "sqlite",
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
