import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.db import get_session
from app.schemas.auth import UserCreate, UserLogin, Token
from app.services.auth_service import AuthService
from app.repos.user_repo import UserRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

def get_auth_service() -> AuthService:
    return AuthService(UserRepo())

@router.post("/signup", response_model=Token)
def signup_route(
    user: UserCreate,
    db: Session = Depends(get_session),
    service: AuthService = Depends(get_auth_service)
):
    logger.info(f"Signup attempt for email={user.email}")
    try:
        token = service.signup(db, user.email, user.password)
        logger.info(f"Signup successful for email={user.email}")
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as e:
        logger.warning(f"Signup failed for email={user.email}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=Token)
def login_route(
    user: UserLogin,
    db: Session = Depends(get_session),
    service: AuthService = Depends(get_auth_service)
):
    logger.info(f"Login attempt for email={user.email}")
    try:
        token = service.login(db, user.email, user.password)
        logger.info(f"Login successful for email={user.email}")
        return {"access_token": token, "token_type": "bearer"}
    except ValueError:
        logger.warning(f"Login failed for email={user.email}: invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )