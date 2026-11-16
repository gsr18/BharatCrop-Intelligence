from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class Database:
    def __init__(self, database_url: str | None) -> None:
        self.engine: Engine | None = (
            create_engine(
                database_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
            if database_url
            else None
        )

    def is_ready(self) -> bool:
        if self.engine is None:
            return False
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
