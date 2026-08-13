from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.schemas.review import (
    ReviewSessionResponse,
    ReviewStatsResponse,
    SubmitReviewRequest,
    SubmitReviewResponse,
)
from app.services.review import create_review_session, get_review_stats, submit_review

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/session", response_model=ReviewSessionResponse)
def review_session_endpoint(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
) -> ReviewSessionResponse:
    return create_review_session(session, limit)


@router.post("/answer", response_model=SubmitReviewResponse)
def submit_review_endpoint(
    request: SubmitReviewRequest,
    session: Annotated[Session, Depends(get_session)],
) -> SubmitReviewResponse:
    return submit_review(session, request)


@router.get("/stats", response_model=ReviewStatsResponse)
def review_stats_endpoint(
    session: Annotated[Session, Depends(get_session)],
) -> ReviewStatsResponse:
    return get_review_stats(session)
