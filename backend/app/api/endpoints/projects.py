import logging
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException, Request
from sqlmodel import Session
from app.db import get_session
from app.schemas.project import AssessmentTypeInfo, ProjectCreate, ProjectResponse
from app.services.project_service import ProjectService
from app.repos.project_repo import ProjectRepo
from app.repos.assessment_type_repo import AssessmentTypeRepo
from app.core.security import get_current_user
from app.models import User
from app.config import settings
from pathlib import Path
from app.repos.semester_repo import SemesterRepo
from app.repos.section_repo import SectionRepo
from app.repos.course_repo import CourseRepo
from app.repos.student_repo import StudentRepo
from app.repos.course_offering_repo import CourseOfferingRepo
from app.repos.mark_repo import MarkRepo
import pandas as pd
from io import BytesIO
import zipfile
from fastapi.responses import StreamingResponse
from typing import Optional
from app.repos.analytics_repo import AnalyticsRepo
from app.main import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

def get_project_service() -> ProjectService:
    return ProjectService(
        ProjectRepo(),
        AssessmentTypeRepo(),
        SemesterRepo(),
        SectionRepo(),
        CourseRepo(),
        StudentRepo(),
        CourseOfferingRepo(),
        MarkRepo(),
        analytics_repo=AnalyticsRepo()
    )

@router.get("/{project_id}", response_model=ProjectResponse)
@limiter.limit("30/minute")
def get_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    return service.get_project(db, project_id, current_user.id)

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_project(
    request: Request,
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
@limiter.limit("10/minute")
def delete_project(
    request: Request,
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
@limiter.limit("30/minute")
def get_projects(
    request: Request,
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

@router.get("/{project_id}/template")
@limiter.limit("20/minute")
def get_template(
    request: Request,
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    logger.info(f"Template request for project_id={project_id} by user_id={current_user.id}")
    try:
        df, file_name = service.get_template(db, project_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error generating template")

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={file_name}"}
    )

# Allowed Excel magic bytes
EXCEL_MAGIC_BYTES = {
    b'PK\x03\x04',                              # .xlsx (ZIP-based)
    b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1',       # .xls (OLE2)
}

def _is_valid_excel_magic(file_bytes: bytes) -> bool:
    """Check if the file starts with known Excel magic bytes."""
    for magic in EXCEL_MAGIC_BYTES:
        if file_bytes.startswith(magic):
            return True
    return False

def _get_uncompressed_size(file_bytes: bytes) -> int:
    """Return total uncompressed size of all ZIP members, or 0 if not a ZIP."""
    try:
        total = 0
        with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
            for info in zf.infolist():
                total += info.file_size
        return total
    except zipfile.BadZipFile:
        return 0   

@router.post("/{project_id}/populate", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def populate_project(
    request: Request,
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    """Upload an Excel file to populate a project. File must be valid .xlsx or .xls."""
    logger.info(f"Populate request for project_id={project_id} by user_id={current_user.id}")

    allowed_ext = {".xlsx", ".xls"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_ext:
        logger.warning(f"Invalid file extension: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(allowed_ext)} files are allowed."
        )

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size is not None and file.size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB} MB)."
        )

    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB} MB)."
    )

    if not _is_valid_excel_magic(file_bytes):
        logger.warning(f"Invalid file magic bytes for {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid Excel file (magic bytes mismatch)."
        )
        
    if file_ext == ".xlsx":
        max_uncompressed = settings.MAX_UPLOAD_UNCOMPRESSED_MB * 1024 * 1024
        uncompressed_size = _get_uncompressed_size(file_bytes)
        if uncompressed_size > max_uncompressed:
            raise HTTPException(
                status_code=413,
                detail=f"File too large when uncompressed (max {settings.MAX_UPLOAD_UNCOMPRESSED_MB} MB)."
            )

    try:
        service.populate_project(db, project_id, current_user.id, file_bytes, file_ext)
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.error(f"Unexpected error during population: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during processing.")

    return {"message": "Project populated successfully"}

from app.schemas.project import StudentInfo, CourseInfo  # add to existing imports

@router.get("/{project_id}/students", response_model=list[StudentInfo])
@limiter.limit("30/minute")
def get_students(
    request: Request,
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    return service.get_project_students(db, project_id, current_user.id)

@router.get("/{project_id}/courses", response_model=list[CourseInfo])
@limiter.limit("30/minute")
def get_courses(
    request: Request,
    project_id: int,
    student_id: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    return service.get_project_courses(db, project_id, current_user.id, student_id)

@router.get("/{project_id}/assessment-types", response_model=list[AssessmentTypeInfo])
@limiter.limit("30/minute")
def get_assessment_types(
    request: Request,
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    logger.info(f"Fetching assessment types for project_id={project_id} by user_id={current_user.id}")
    res = service.get_assessment_types(db, project_id, current_user.id)
    return [AssessmentTypeInfo(name=at["name"], weight=at["weight"]) for at in res]

@router.get("/{project_id}/sections", response_model=list[dict])
@limiter.limit("30/minute")
def get_sections(
    request: Request,
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    return service.get_project_sections(db, project_id, current_user.id)