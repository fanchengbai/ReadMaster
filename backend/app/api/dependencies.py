from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.database import Database


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(
    database: Annotated[Database, Depends(get_database)],
) -> Generator[Session, None, None]:
    yield from database.session()
