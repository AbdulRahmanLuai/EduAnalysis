import logging
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from jwt import ExpiredSignatureError, InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from app.config import settings
from app.db import get_session
from app.repos.user_repo import UserRepo

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def create_access_token(data: dict) -> str:
    """Create JWT with dict payload, automatically adds exp claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.EXPIRATION_TIME)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"JWT created for subject: {data.get('sub')}")
    return token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session),
):
    """Dependency that extracts user from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if not email:
            logger.warning("JWT missing 'sub' claim")
            raise credentials_exception
        logger.debug(f"JWT decoded for email={email}")
    except ExpiredSignatureError:
        logger.warning("JWT expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        logger.warning("JWT invalid")
        raise credentials_exception

    repo = UserRepo()
    user = repo.get_user_by_email(db, email)
    if not user:
        logger.warning(f"User not found for email={email} from valid token")
        raise credentials_exception
    return user