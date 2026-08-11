from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.dependencies import get_database
from app.db.database import Database

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


@router.get("/health", response_model=HealthResponse)
def health_check(
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=request.app.version,
        database="ok" if database.ping() else "unavailable",
    )
