import logging
from sqlmodel import Session
from fastapi import HTTPException, status
from app.repos.project_repo import ProjectRepo
from app.repos.assessment_type_repo import AssessmentTypeRepo
from app.schemas.project import ProjectCreate
import pandas as pd
import io
from app.models import (Semester, Section, Student, Course, CourseOffering, Mark, Project, AssessmentType)
from app.repos.project_repo import ProjectRepo
from app.repos.assessment_type_repo import AssessmentTypeRepo
from app.repos.semester_repo import SemesterRepo
from app.repos.section_repo import SectionRepo
from app.repos.course_repo import CourseRepo
from app.repos.student_repo import StudentRepo
from app.repos.course_offering_repo import CourseOfferingRepo
from app.repos.mark_repo import MarkRepo
from app.repos.analytics_repo import AnalyticsRepo
from app.schemas.project import ProjectCreate
from typing import Optional
from app.config import settings




logger = logging.getLogger(__name__)


class ProjectService:

    def __init__(
        self,
        project_repo: ProjectRepo,
        assessment_repo: AssessmentTypeRepo,
        semester_repo: SemesterRepo,
        section_repo: SectionRepo,
        course_repo: CourseRepo,
        student_repo: StudentRepo,
        offering_repo: CourseOfferingRepo,
        mark_repo: MarkRepo,
        analytics_repo: AnalyticsRepo
    ):
        self.project_repo = project_repo
        self.assessment_repo = assessment_repo
        self.semester_repo = semester_repo
        self.section_repo = section_repo
        self.course_repo = course_repo
        self.student_repo = student_repo
        self.offering_repo = offering_repo
        self.mark_repo = mark_repo
        self.analytics_repo = analytics_repo
        self.base_columns = ["term", "grade", "section", "student_id", "student_name", "course_code"]

    def create_project(self, db: Session, data: ProjectCreate, user_id: int) -> Project:
        logger.info(f"Creating project for user_id={user_id}, name='{data.name}'")
        
        project_count = len(self.project_repo.get_by_user(db, user_id))
        if project_count >= settings.MAX_PROJECTS_PER_USER:
            raise HTTPException(
                status_code=400,
                detail=f"Project limit reached ({settings.MAX_PROJECTS_PER_USER} max). Please delete an existing project first."
            )
        
        # validate sum of weights add to 100
        weight_sum = sum([a_t.weight for a_t in data.assessment_types])
        if (weight_sum != 100):
            raise HTTPException(400, "weights must sum to 100")
        
        print(weight_sum)
        project = Project(
            name=data.name,
            academic_year_start=data.academic_year_start,
            description=data.description,
            user_id=user_id
        )
        project = self.project_repo.create(db, project)
        logger.debug(f"Project row created with id={project.id}")

        assessment_types = [
            AssessmentType(name=at.name, weight=at.weight, project_id=project.id)
            for at in data.assessment_types
        ]
        self.assessment_repo.create_batch(db, assessment_types)
        logger.debug(f"Created {len(assessment_types)} assessment types for project {project.id}")

        db.commit()
        db.refresh(project)
        logger.info(f"Project {project.id} committed successfully")
        return project

    def get_project(self, db: Session, project_id: int, user_id: int) -> Project:
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return project
    
    def get_user_projects(self, db: Session, user_id: int) -> list[Project]:
        logger.debug(f"Fetching projects for user_id={user_id}")
        projects = self.project_repo.get_by_user(db, user_id)
        logger.debug(f"Found {len(projects)} projects")
        return projects

    def delete_project(self, db: Session, project_id: int, user_id: int) -> None:
        logger.info(f"Deleting project {project_id} for user_id={user_id}")
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            logger.warning(f"Delete failed: project {project_id} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if project.user_id != user_id:
            logger.warning(f"Delete forbidden: project {project_id} owned by user {project.user_id}, not {user_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        self.project_repo.delete(db, project)
        db.commit()
        logger.info(f"Project {project_id} deleted successfully")
        
    def get_template(self, db: Session, project_id: int, user_id: int) -> tuple[pd.DataFrame, str]:
        """Return a DataFrame with the required columns for the given project."""
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")        

        # get assessment type names for this project
        assessment_types = self.assessment_repo.get_by_project(db, project_id)
        assessment_columns = [at.name for at in assessment_types]

        columns = self.base_columns + assessment_columns
        return pd.DataFrame(columns=columns), f"project_{project.name}_template"

    def populate_project(
        self, db: Session, project_id: int, user_id: int, file_bytes: bytes, file_ext: str
    ) -> None:
        # --- nested validation ---
        def validate_df(df: pd.DataFrame) -> pd.DataFrame:
            columns = self.base_columns.copy()
            assessment_types = self.assessment_repo.get_by_project(db, project_id)
            for at in assessment_types:
                columns.append(at.name)

            # Missing columns
            missing = set(columns) - set(df.columns)
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Excel file: Missing required columns: {', '.join(missing)}."
                )

            df = df[columns]

            # Null values
            null_cols = df.columns[df.isnull().any()].tolist()
            if null_cols:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Excel file: Empty cells found in columns: {', '.join(null_cols)}."
                )

            # Column type checks (term, grade must be integers)
            for col in ["term", "grade"]:
                if not pd.api.types.is_numeric_dtype(df[col]) or not (df[col] % 1 == 0).all():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Excel file: Column '{col}' must contain whole numbers only."
                    )

            # Term range 1‑3
            if not df["term"].between(1, 3, inclusive="both").all():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Excel file: Column 'term' must be between 1 and 3."
                )

            # Grade range 1‑13
            if not df["grade"].between(1, 13, inclusive="both").all():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Excel file: Column 'grade' must be between 1 and 13."
                )

            # Assessment type validations
            for at in assessment_types:
                col = at.name
                if not pd.api.types.is_numeric_dtype(df[col]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Excel file: Column '{col}' must be a number."
                    )
                if not df[col].between(0, 100, inclusive="both").all():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Excel file: Column '{col}' values must be between 0 and 100."
                    )

            # Duplicate rows (same student, course, term)
            dupes = df.duplicated(subset=["student_id", "course_code", "term"], keep=False)
            if dupes.any():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Excel file: Duplicate rows found for the same student, course, and term."
                )

            # Inconsistent student names
            name_check = df.groupby("student_id")["student_name"].nunique()
            if (name_check > 1).any():
                bad_ids = name_check[name_check > 1].index.tolist()
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Excel file: Student ID(s) {', '.join(map(str, bad_ids))} have multiple names. Each ID must have a consistent name."
                )

            # Student in multiple grades/sections
            mapping_check = df.groupby("student_id")[["grade", "section"]].nunique()
            inconsistent = mapping_check[(mapping_check > 1).any(axis=1)]
            if not inconsistent.empty:
                bad_ids = inconsistent.index.tolist()
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Excel file: Student ID(s) {', '.join(map(str, bad_ids))} appear in multiple grades or sections. Each student must belong to a single grade and section."
                )

            return df

        # --- main logic ---
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(403, detail="Not authorized")
        if project.is_populated:
            raise HTTPException(400, detail="Project already populated")

        df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')
        df = validate_df(df)

        # 1. Create semesters – convert numpy.int64 -> int
        semesters = [
            Semester(number=int(num), project_id=project_id)
            for num in sorted(df["term"].unique())
        ]
        self.semester_repo.create_all(db, semesters)

        # 2. Create sections – grade/name are already native from itertuples if we use int/str
        sections = [
            Section(grade=int(row.grade), name=str(row.section), project_id=project_id)
            for row in df[["grade", "section"]].drop_duplicates().itertuples(index=False)
        ]
        self.section_repo.create_all(db, sections)

        # 3. Create courses
        courses = [
            Course(code=str(code), project_id=project_id)
            for code in df["course_code"].unique()
        ]
        self.course_repo.create_all(db, courses)

        # Build lookup dicts (keys are already Python int/str from ORM)
        semester_dict = {s.number: s.id for s in self.semester_repo.get_by_project(db, project_id)}
        section_dict = {(s.grade, s.name): s.id for s in self.section_repo.get_by_project(db, project_id)}
        course_dict = {c.code: c.id for c in self.course_repo.get_by_project(db, project_id)}

        # 4. Create students – cast st_external_id to str, grade/section to int/str for section lookup
        student_data = df[["student_id", "student_name", "grade", "section"]].drop_duplicates("student_id")
        students = [
            Student(
                st_external_id=str(row.student_id),
                name=str(row.student_name),
                section_id=section_dict[(int(row.grade), str(row.section))],
                project_id=project_id
            )
            for row in student_data.itertuples(index=False)
        ]
        self.student_repo.create_all(db, students)
        student_dict = {s.st_external_id: s.id for s in self.student_repo.get_by_project(db, project_id)}

        # 5. Create course offerings
        offering_data = df[["course_code", "grade", "section", "term"]].drop_duplicates()
        offerings = [
            CourseOffering(
                course_id=course_dict[str(row.course_code)],
                section_id=section_dict[(int(row.grade), str(row.section))],
                semester_id=semester_dict[int(row.term)]
            )
            for row in offering_data.itertuples(index=False)
        ]
        self.offering_repo.create_all(db, offerings)

        # Build offering lookup
        offering_list = self.offering_repo.get_by_project(db, project_id)
        offering_dict = {
            (co.course_id, co.section_id, co.semester_id): co.id
            for co in offering_list
        }

        # 6. Create marks – convert scores to float
        assessment_types = self.assessment_repo.get_by_project(db, project_id)
        marks = []
        for row in df.itertuples(index=False):
            sid = student_dict[str(row.student_id)]
            oid = offering_dict[(
                course_dict[str(row.course_code)],
                section_dict[(int(row.grade), str(row.section))],
                semester_dict[int(row.term)]
            )]
            for at in assessment_types:
                marks.append(Mark(
                    student_id=sid,
                    assessment_id=at.id,
                    course_offering_id=oid,
                    score=float(getattr(row, at.name))
                ))
        self.mark_repo.create_all(db, marks)

        # 7. Final commit
        project.is_populated = True
        db.add(project)
        db.commit()
        logger.info(f"Project {project_id} populated: {len(students)} students, {len(marks)} marks")
        
        
    def get_project_students(self, db: Session, project_id: int, user_id: int) -> list[dict]:
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(403, detail="Not authorized")
        students = self.student_repo.get_by_project(db, project_id)
        return [{"st_external_id": s.st_external_id, "name": s.name} for s in students]



    def get_project_courses(
        self, db: Session, project_id: int, user_id: int, student_id: Optional[str] = None
    ) -> list[dict]:
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(403, detail="Not authorized")

        if student_id:
            codes = self.analytics_repo.get_courses_by_student(db, project_id, student_id)
            return [{"code": code} for code in codes]
        else:
            courses = self.course_repo.get_by_project(db, project_id)
            return [{"code": c.code} for c in courses]
        
        
    def get_assessment_types(self, db: Session, project_id: int, user_id: int) -> list[dict]:
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(403, detail="Not authorized")

        assessment_types = self.assessment_repo.get_by_project(db, project_id)
        return [{"name": at.name, "weight": at.weight} for at in assessment_types]
    
    def get_project_sections(self, db: Session, project_id: int, user_id: int) -> list[dict]:
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(403, detail="Not authorized")
        sections = self.section_repo.get_by_project(db, project_id)
        return [{"grade": s.grade, "name": s.name} for s in sections]