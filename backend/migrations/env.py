"""Alembic environment: connects to the database and knows every table via Base.metadata."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

import deltaweb.models  # noqa: F401  (registers every table in Base.metadata)
from deltaweb.config import get_settings
from deltaweb.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    # Tests pass the URL of their throwaway container; everything else uses the settings
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    """``alembic upgrade head --sql``: print the SQL instead of running it."""
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
