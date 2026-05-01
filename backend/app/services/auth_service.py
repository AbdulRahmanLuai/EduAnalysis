import logging
from sqlmodel import Session
from app.models import User
from app.repos.user_repo import UserRepo
from app.core.security import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, user_repo: UserRepo):
        self.repo = user_repo

    def signup(self, db: Session, email: str, password: str) -> str:
        logger.info(f"Signup service called for email={email}")
        existing = self.repo.get_user_by_email(db, email)
        if existing:
            logger.warning(f"Signup failed: email already registered {email}")
            raise ValueError("Email already registered")
        
        created_user = self.repo.create_user(db, email, hashed_password=hash_password(password))
        db.commit()
        logger.info(f"User created with id={created_user.id}, email={email}")
        return create_access_token(data={"sub": created_user.email})

    def login(self, db: Session, email: str, password: str) -> str:
        logger.info(f"Login service called for email={email}")
        user = self.repo.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Login failed for email={email}: invalid credentials")
            raise ValueError("Invalid credentials")
        logger.info(f"Login successful for user_id={user.id}, email={email}")
        return create_access_token(data={"sub": user.email})