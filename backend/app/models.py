from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    hashed_password: str

    projects: List["Project"] = Relationship(back_populates="user")

    __table_args__ = (UniqueConstraint("email"),)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    academic_year_start: int
    is_populated: bool = Field(default=False)
    user_id: int = Field(foreign_key="users.id")

    user: Optional[User] = Relationship(back_populates="projects")

    # Children with cascade delete (ORM‑level cascade)
    sections: List["Section"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    students: List["Student"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    courses: List["Course"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    semesters: List["Semester"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    assessment_types: List["AssessmentType"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Section(SQLModel, table=True):
    __tablename__ = "sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    grade: str
    name: str
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    project: Optional[Project] = Relationship(back_populates="sections")
    students: List["Student"] = Relationship(
        back_populates="section",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    course_offerings: List["CourseOffering"] = Relationship(
        back_populates="section",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (UniqueConstraint("name", "project_id"),)


class Student(SQLModel, table=True):
    __tablename__ = "students"

    id: Optional[int] = Field(default=None, primary_key=True)
    st_external_id: str
    name: str
    section_id: int = Field(foreign_key="sections.id", ondelete="CASCADE")
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    section: Optional[Section] = Relationship(back_populates="students")
    project: Optional[Project] = Relationship(back_populates="students")
    marks: List["Mark"] = Relationship(
        back_populates="student",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (UniqueConstraint("st_external_id", "project_id"),)


class Course(SQLModel, table=True):
    __tablename__ = "courses"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    project: Optional[Project] = Relationship(back_populates="courses")
    course_offerings: List["CourseOffering"] = Relationship(
        back_populates="course",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (UniqueConstraint("code", "project_id"),)


class Semester(SQLModel, table=True):
    __tablename__ = "semesters"

    id: Optional[int] = Field(default=None, primary_key=True)
    number: int
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    project: Optional[Project] = Relationship(back_populates="semesters")
    course_offerings: List["CourseOffering"] = Relationship(
        back_populates="semester",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (UniqueConstraint("number", "project_id"),)


class CourseOffering(SQLModel, table=True):
    __tablename__ = "course_offerings"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", ondelete="CASCADE")
    section_id: int = Field(foreign_key="sections.id", ondelete="CASCADE")
    semester_id: int = Field(foreign_key="semesters.id", ondelete="CASCADE")

    course: Optional[Course] = Relationship(back_populates="course_offerings")
    section: Optional[Section] = Relationship(back_populates="course_offerings")
    semester: Optional[Semester] = Relationship(back_populates="course_offerings")
    marks: List["Mark"] = Relationship(
        back_populates="course_offering",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (UniqueConstraint("course_id", "section_id", "semester_id"),)


class AssessmentType(SQLModel, table=True):
    __tablename__ = "assessment_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    weight: int = Field(ge=0)
    project_id: int = Field(foreign_key="projects.id", ondelete="CASCADE")

    project: Optional[Project] = Relationship(back_populates="assessment_types")
    marks: List["Mark"] = Relationship(
        back_populates="assessment_type",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (UniqueConstraint("name", "project_id"),)


class Mark(SQLModel, table=True):
    __tablename__ = "marks"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id", ondelete="CASCADE")
    assessment_id: int = Field(foreign_key="assessment_types.id", ondelete="CASCADE")
    course_offering_id: int = Field(foreign_key="course_offerings.id", ondelete="CASCADE")
    score: float = Field(ge=0)

    student: Optional[Student] = Relationship(back_populates="marks")
    assessment_type: Optional[AssessmentType] = Relationship(back_populates="marks")
    course_offering: Optional[CourseOffering] = Relationship(back_populates="marks")

    __table_args__ = (
        UniqueConstraint("student_id", "assessment_id", "course_offering_id"),
    )