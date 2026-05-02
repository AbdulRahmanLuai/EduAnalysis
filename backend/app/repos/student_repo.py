from sqlmodel import Session, select
from app.models import Student

class StudentRepo:
    def create_all(self, db: Session, students: list[Student]) -> None:
        db.add_all(students)
        db.flush()

    def get_by_project(self, db: Session, project_id: int) -> list[Student]:
        stmt = select(Student).where(Student.project_id == project_id)
        return list(db.exec(stmt).all())