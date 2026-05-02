from sqlmodel import Session, select
from app.models import Course

class CourseRepo:
    def create_all(self, db: Session, courses: list[Course]) -> None:
        db.add_all(courses)
        db.flush()

    def get_by_project(self, db: Session, project_id: int) -> list[Course]:
        stmt = select(Course).where(Course.project_id == project_id)
        return list(db.exec(stmt).all())