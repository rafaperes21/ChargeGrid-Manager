import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nao foi possivel validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or user.blocked:
        raise credentials_error

    return user


def require_role(role: UserRole) -> Callable[..., User]:
    """Dependency factory: barra acesso cruzado entre owner e customer.

    Um `customer` nunca pode enxergar rota de `owner` (dado financeiro do estabelecimento)
    e vice-versa - e o criterio de aceite explicito do M1 (teste de 403)."""

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao tem permissao para acessar este recurso",
            )
        return current_user

    return _dependency


require_owner = require_role(UserRole.owner)
require_customer = require_role(UserRole.customer)
