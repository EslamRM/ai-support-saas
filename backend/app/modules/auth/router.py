"""
Module: auth
File responsibility (router.py): HTTP surface for signup/login/refresh/me.
Route handlers stay thin: parse request -> call service -> return
response. AuthService raises DomainError subclasses on failure; those are
translated to HTTP status codes by the handler registered in main.py, not
here.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    TenantSignupRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_tenant(payload: TenantSignupRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    service = AuthService(db)
    _, access, refresh = service.signup_tenant(
        payload.tenant_name, payload.email, payload.password, payload.full_name
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    service = AuthService(db)
    _, access, refresh = service.login(payload.email, payload.password)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    service = AuthService(db)
    access, refresh = service.refresh(payload.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserResponse)
def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
