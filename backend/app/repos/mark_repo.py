from sqlmodel import Session
from app.models import Mark

class MarkRepo:
    def create_all(self, db: Session, marks: list[Mark]) -> None:
        db.add_all(marks)
        db.flush()