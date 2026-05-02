from sqlmodel import Session, select
from app.models import Semester

class SemesterRepo:
    def create_all(self, db: Session, semesters: list[Semester]) -> None:
        db.add_all(semesters)
        db.flush()

    def get_by_project(self, db: Session, project_id: int) -> list[Semester]:
        stmt = select(Semester).where(Semester.project_id == project_id)
        return list(db.exec(stmt).all())