from sqlmodel import Session, select
from app.models import CourseOffering

class CourseOfferingRepo:
    def create_all(self, db: Session, offerings: list[CourseOffering]) -> None:
        db.add_all(offerings)
        db.flush()

    def get_by_project(self, db: Session, project_id: int) -> list[CourseOffering]:
        # CourseOffering is linked via section/course/semester which have project_id
        stmt = select(CourseOffering).where(
            CourseOffering.section.has(project_id=project_id)
        )
        return list(db.exec(stmt).all())