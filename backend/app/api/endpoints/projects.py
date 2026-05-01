import logging
from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from app.db import get_session
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.project_service import ProjectService
from app.repos.project_repo import ProjectRepo
from app.repos.assessment_type_repo import AssessmentTypeRepo
from app.core.security import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

def get_project_service() -> ProjectService:
    return ProjectService(ProjectRepo(), AssessmentTypeRepo())

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    logger.info(f"Creating project for user_id={current_user.id}, name='{project_data.name}'")
    try:
        project = service.create_project(db, project_data, current_user.id)
        logger.info(f"Project created id={project.id} with {len(project_data.assessment_types)} assessment types")
        return project
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    logger.info(f"Delete request for project_id={project_id} by user_id={current_user.id}")
    try:
        service.delete_project(db, project_id, current_user.id)
        logger.info(f"Project {project_id} deleted")
        return None
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        raise

@router.get("", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    logger.info(f"Fetching projects for user_id={current_user.id}")
    try:
        projects = service.get_user_projects(db, current_user.id)
        logger.info(f"Returned {len(projects)} projects")
        return projects
    except Exception as e:
        logger.error(f"Failed to fetch projects: {e}", exc_info=True)
        raise