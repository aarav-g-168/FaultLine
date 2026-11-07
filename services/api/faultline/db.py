from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def database(url: str):
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={'check_same_thread': False, 'timeout': 15}
        if url.startswith('sqlite')
        else {'connect_timeout': 5},
    )
    if url.startswith('sqlite'):

        @event.listens_for(engine, 'connect')
        def sqlite_constraints(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

    return engine, sessionmaker(engine, expire_on_commit=False)
