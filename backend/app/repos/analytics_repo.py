from sqlmodel import Session, distinct, select
from sqlalchemy.orm import joinedload
from app.models import Mark, CourseOffering, Course, Semester, AssessmentType, Student

class AnalyticsRepo:
    def get_student_performance(
        self,
        db: Session,
        project_id: int,
        student_external_id: str,
        course_codes: list[str]
    ) -> list[dict]:
        """Return flat list of {course_code, semester_number, assessment_type, score} for the given student & courses."""

        stmt = (
            select(Mark)
            .join(CourseOffering, Mark.course_offering_id == CourseOffering.id)
            .join(Course, CourseOffering.course_id == Course.id)
            .join(Semester, CourseOffering.semester_id == Semester.id)
            .join(AssessmentType, Mark.assessment_id == AssessmentType.id)
            .join(Student, Mark.student_id == Student.id)
            .options(
                joinedload(Mark.course_offering).joinedload(CourseOffering.course),
                joinedload(Mark.course_offering).joinedload(CourseOffering.semester),
                joinedload(Mark.assessment_type),
            )
            .where(
                Student.st_external_id == student_external_id,
                Student.project_id == project_id,
                Course.code.in_(course_codes),
                Course.project_id == project_id,
                Semester.project_id == project_id,
            )
        )
        results = db.exec(stmt).all()

        return [
            {
                "course_code": mark.course_offering.course.code,
                "semester_number": mark.course_offering.semester.number,
                "assessment_type": mark.assessment_type.name,
                "score": mark.score,
            }
            for mark in results
        ]
        
    def get_courses_by_student(self, db: Session, project_id: int, student_external_id: str) -> list[str]:
        """Return distinct course codes for which the student has marks."""
        stmt = (
            select(distinct(Course.code))
            .join(CourseOffering, CourseOffering.course_id == Course.id)
            .join(Mark, Mark.course_offering_id == CourseOffering.id)
            .join(Student, Mark.student_id == Student.id)
            .where(
                Course.project_id == project_id,
                Student.st_external_id == student_external_id,
                Student.project_id == project_id,
            )
        )
        return list(db.exec(stmt).all())
    
   