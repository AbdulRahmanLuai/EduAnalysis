from sqlmodel import Session, select
from app.models import Section

class SectionRepo:
    def create_all(self, db: Session, sections: list[Section]) -> None:
        db.add_all(sections)
        db.flush()

    def get_by_project(self, db: Session, project_id: int) -> list[Section]:
        stmt = select(Section).where(Section.project_id == project_id)
        return list(db.exec(stmt).all())