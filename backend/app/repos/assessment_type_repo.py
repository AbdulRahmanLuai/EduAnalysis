from sqlmodel import Session, select
from app.models import AssessmentType

class AssessmentTypeRepo:
    def create_batch(self, db: Session, assessment_types: list[AssessmentType]) -> None:
        for at in assessment_types:
            db.add(at)
        db.flush()

    def get_by_project(self, db: Session, project_id: int) -> list[AssessmentType]:
        stmt = select(AssessmentType).where(AssessmentType.project_id == project_id)
        return list(db.exec(stmt).all())