import logging
from sqlmodel import Session
from fastapi import HTTPException, status
from app.models import Project, AssessmentType
from app.repos.project_repo import ProjectRepo
from app.repos.assessment_type_repo import AssessmentTypeRepo
from app.schemas.project import ProjectCreate

logger = logging.getLogger(__name__)


class ProjectService:

    def __init__(self, repo: ProjectRepo, assessment_repo: AssessmentTypeRepo):
        self.repo = repo
        self.assessment_repo = assessment_repo

    def create_project(self, db: Session, data: ProjectCreate, user_id: int) -> Project:
        logger.info(f"Creating project for user_id={user_id}, name='{data.name}'")
        
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
        project = self.repo.create(db, project)
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

    def get_user_projects(self, db: Session, user_id: int) -> list[Project]:
        logger.debug(f"Fetching projects for user_id={user_id}")
        projects = self.repo.get_by_user(db, user_id)
        logger.debug(f"Found {len(projects)} projects")
        return projects

    def delete_project(self, db: Session, project_id: int, user_id: int) -> None:
        logger.info(f"Deleting project {project_id} for user_id={user_id}")
        project = self.repo.get_by_id(db, project_id)
        if not project:
            logger.warning(f"Delete failed: project {project_id} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if project.user_id != user_id:
            logger.warning(f"Delete forbidden: project {project_id} owned by user {project.user_id}, not {user_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        self.repo.delete(db, project)
        db.commit()
        logger.info(f"Project {project_id} deleted successfully")