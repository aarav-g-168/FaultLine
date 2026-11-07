from alembic import context
from faultline import models  # noqa: F401
from faultline.config import get_settings
from faultline.db import Base
from sqlalchemy import create_engine, pool

config = context.config
url = config.attributes.get('database_url') or get_settings().database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
