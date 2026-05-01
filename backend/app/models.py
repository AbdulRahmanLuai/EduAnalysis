from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    hashed_password: str

    __table_args__ = (UniqueConstraint("email"),)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    academic_year_start: int
    is_populated: bool = Field(default=False)
    user_id: int = Field(foreign_key="users.id")


class Section(SQLModel, table=True):
    __tablename__ = "sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    grade: str
    name: str
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    __table_args__ = (UniqueConstraint("name", "project_id"),)


class Student(SQLModel, table=True):
    __tablename__ = "students"

    id: Optional[int] = Field(default=None, primary_key=True)
    st_external_id: str
    name: str
    section_id: int = Field(foreign_key="sections.id", ondelete="CASCADE")
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    __table_args__ = (UniqueConstraint("st_external_id", "project_id"),)


class Course(SQLModel, table=True):
    __tablename__ = "courses"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    __table_args__ = (UniqueConstraint("code", "project_id"),)


class Semester(SQLModel, table=True):
    __tablename__ = "semesters"

    id: Optional[int] = Field(default=None, primary_key=True)
    number: int
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    __table_args__ = (UniqueConstraint("number", "project_id"),)


class CourseOffering(SQLModel, table=True):
    __tablename__ = "course_offerings"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", ondelete="CASCADE")
    section_id: int = Field(foreign_key="sections.id", ondelete="CASCADE")
    semester_id: int = Field(foreign_key="semesters.id", ondelete="CASCADE")

    __table_args__ = (UniqueConstraint("course_id", "section_id", "semester_id"),)


class AssessmentType(SQLModel, table=True):
    __tablename__ = "assessment_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    weight: int = Field(ge=0)          # changed to int, min 0
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    __table_args__ = (UniqueConstraint("name", "project_id"),)


class Mark(SQLModel, table=True):
    __tablename__ = "marks"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id", ondelete="CASCADE")
    assessment_id: int = Field(foreign_key="assessment_types.id", ondelete="CASCADE")
    course_offering_id: int = Field(foreign_key="course_offerings.id", ondelete="CASCADE")
    score: float = Field(ge=0)       

    __table_args__ = (
        UniqueConstraint("student_id", "assessment_id", "course_offering_id"),
    )