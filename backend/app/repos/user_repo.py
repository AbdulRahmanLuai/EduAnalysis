from sqlmodel import Session, select
from app.models import User

class UserRepo:
    def get_user_by_email(self, db: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return db.exec(stmt).first()

    def create_user(self, db: Session, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.flush()
        return user