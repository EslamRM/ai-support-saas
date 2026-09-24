"""
Alembic migration environment.

Responsibility: point Alembic at our SQLAlchemy metadata and at the DB
URL from app.core.config.settings, so migrations never hardcode a
connection string that could drift from the app's own config.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# Import every model module so Base.metadata is fully populated before
# autogenerate compares it against the live schema. New modules append
# to this list as they're added (knowledge_base, documents, ... in
# later phases).
from app.modules.tenants import models as _tenants_models  # noqa: E402,F401
from app.modules.auth import models as _auth_models  # noqa: E402,F401
from app.modules.knowledge_base import models as _kb_models  # noqa: E402,F401
from app.modules.documents import models as _documents_models  # noqa: E402,F401
from app.modules.conversations import models as _conversations_models  # noqa: E402,F401
from app.modules.tickets import models as _tickets_models  # noqa: E402,F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
