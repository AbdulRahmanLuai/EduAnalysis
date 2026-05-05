from sqlmodel import Session, distinct, select
from sqlalchemy.orm import joinedload
from app.models import Mark, CourseOffering, Course, Section, Semester, AssessmentType, Student
from collections import defaultdict

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
    
    from app.models import Semester  # add import

    def get_section_scores_all(
        self,
        db: Session,
        project_id: int,
        grade: int,
        section_name: str,
    ) -> list[dict]:
        base_query = (
            select(
                Course.code,
                Student.id,
                Mark.score,
                AssessmentType.name,
                AssessmentType.weight,
                Semester.number,                 
            )
            .join(Student, Mark.student_id == Student.id)
            .join(CourseOffering, Mark.course_offering_id == CourseOffering.id)
            .join(Course, CourseOffering.course_id == Course.id)
            .join(AssessmentType, Mark.assessment_id == AssessmentType.id)
            .join(Semester, CourseOffering.semester_id == Semester.id)  # added
            .join(Section, Student.section_id == Section.id)
            .where(
                Section.grade == str(grade),
                Section.name == section_name,
                Section.project_id == project_id,
                Course.project_id == project_id,
            )
        )
        rows = db.exec(base_query).all()

        # Group: course -> semester -> student -> total
        course_semesters = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # Group: course -> semester -> assessment_name -> scores
        course_sem_asses = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for code, student_id, score, at_name, weight, sem_num in rows:
            course_semesters[code][sem_num][student_id] += score * weight / 100
            course_sem_asses[code][sem_num][at_name].append(score)

        items = []
        for code in sorted(course_semesters.keys()):
            semesters_dict = {}
            for sem_num in sorted(course_semesters[code].keys()):
                totals = [round(val, 2) for val in course_semesters[code][sem_num].values()]
                assessments = {
                    at: sorted(scores)
                    for at, scores in course_sem_asses[code][sem_num].items()
                }
                semesters_dict[sem_num] = {"total": totals, "assessments": assessments}
            items.append({
                "course_code": code,
                "semesters": semesters_dict,
            })
        return items