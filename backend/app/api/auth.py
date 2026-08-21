from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import GoogleAuthRequest, LoginRequest, RegisterRequest, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> Token:
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail ja cadastrado")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return Token(access_token=create_access_token(user.id, user.role.value))


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha invalidos"
    )

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or user.hashed_password is None:
        raise invalid_credentials
    if not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    return Token(access_token=create_access_token(user.id, user.role.value))


@router.post("/google", response_model=Token)
def login_with_google(payload: GoogleAuthRequest, db: Session = Depends(get_db)) -> Token:
    """Recebe o id_token que o frontend obtem via Google Sign-In (client-side) e valida
    a assinatura/audience contra o Google - o backend nunca participa do fluxo de redirect."""
    try:
        claims = google_id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), settings.google_oauth_client_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token do Google invalido"
        ) from exc

    google_sub = claims["sub"]
    email = claims["email"]

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            user.google_sub = google_sub
        else:
            user = User(
                email=email,
                google_sub=google_sub,
                full_name=claims.get("name", email),
                role=UserRole.customer,
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    if user.blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario bloqueado")

    return Token(access_token=create_access_token(user.id, user.role.value))
