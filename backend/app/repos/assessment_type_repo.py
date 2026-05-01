from sqlmodel import Session
from app.models import AssessmentType

class AssessmentTypeRepo:
    def create_batch(self, db: Session, assessment_types: list[AssessmentType]) -> None:
        for at in assessment_types:
            db.add(at)
        # flush is fine here, commit will happen later in the service
        db.flush()