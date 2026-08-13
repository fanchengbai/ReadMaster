from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_app_settings, get_session
from app.core.config import Settings
from app.schemas.vocabulary import (
    DictionaryEntry,
    Familiarity,
    SaveUserWordRequest,
    UpdateUserWordRequest,
    UserWordResponse,
)
from app.services.dictionary import lookup_dictionary
from app.services.vocabulary import (
    delete_user_word,
    list_user_words,
    save_user_word,
    update_user_word,
)

router = APIRouter(tags=["vocabulary"])


@router.get("/dictionary/{word}", response_model=DictionaryEntry)
def dictionary_lookup_endpoint(
    word: str,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> DictionaryEntry:
    return lookup_dictionary(session, word, settings.dictionary_database_path)


@router.post("/user-words", response_model=UserWordResponse, status_code=status.HTTP_201_CREATED)
def save_user_word_endpoint(
    request: SaveUserWordRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> UserWordResponse:
    return save_user_word(session, request, settings.dictionary_database_path)


@router.get("/user-words", response_model=list[UserWordResponse])
def list_user_words_endpoint(
    session: Annotated[Session, Depends(get_session)],
    familiarity: Annotated[Familiarity | None, Query()] = None,
) -> list[UserWordResponse]:
    return list_user_words(session, familiarity)


@router.patch("/user-words/{user_word_id}", response_model=UserWordResponse)
def update_user_word_endpoint(
    user_word_id: str,
    update: UpdateUserWordRequest,
    session: Annotated[Session, Depends(get_session)],
) -> UserWordResponse:
    return update_user_word(session, user_word_id, update)


@router.delete("/user-words/{user_word_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_word_endpoint(
    user_word_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    delete_user_word(session, user_word_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
