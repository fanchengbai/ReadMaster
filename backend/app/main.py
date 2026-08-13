from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.api.books import router as books_router
from app.api.health import router as health_router
from app.api.review import router as review_router
from app.api.vocabulary import router as vocabulary_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, app_error_handler
from app.db.database import Database
from app.db.migrations import run_migrations


def create_app(
    settings: Settings | None = None,
    *,
    database_url: str | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app_settings.data_dir.mkdir(parents=True, exist_ok=True)
        resolved_database_url = database_url or app_settings.resolved_database_url
        database = Database(resolved_database_url)
        if resolved_database_url.endswith(":memory:"):
            database.create_schema()
        else:
            run_migrations(resolved_database_url)
        app.state.database = database
        app.state.settings = app_settings
        yield
        database.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.include_router(health_router, prefix=app_settings.api_prefix)
    app.include_router(books_router, prefix=app_settings.api_prefix)
    app.include_router(vocabulary_router, prefix=app_settings.api_prefix)
    app.include_router(review_router, prefix=app_settings.api_prefix)
    return app


app = create_app()
