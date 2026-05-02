import logging
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlmodel import Session
from app.db import get_session
from app.schemas.project import ProjectCreate, ProjectResponse
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
from fastapi.responses import StreamingResponse

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
    )
    
@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    return service.get_project(db, project_id, current_user.id)

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


from fastapi.responses import StreamingResponse
import pandas as pd

@router.get("/{project_id}/template")
def get_template(
    project_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    """
    Download an empty Excel template for the project.
    The file contains required columns plus assessment type headers.
    """
    logger.info(f"Template request for project_id={project_id} by user_id={current_user.id}")

    try:
        df, file_name = service.get_template(db, project_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error generating template")

    # Convert DataFrame to Excel bytes in memory
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


@router.post("/{project_id}/populate", status_code=status.HTTP_200_OK)
async def populate_project(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    """Upload an Excel file to populate a project. File must be valid .xlsx or .xls."""
    logger.info(f"Populate request for project_id={project_id} by user_id={current_user.id}")

    # 1. Validate file extension (quick rejection)
    allowed_ext = {".xlsx", ".xls"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_ext:
        logger.warning(f"Invalid file extension: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(allowed_ext)} files are allowed."
        )

    # 2. Check file size before reading whole file
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size is not None and file.size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB} MB)."
        )

    # 3. Read file content (limits to max_size + 1 to detect oversized files)
    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB} MB)."
    )

    # 4. Validate magic bytes (real Excel, not just a renamed file)
    if not _is_valid_excel_magic(file_bytes):
        logger.warning(f"Invalid file magic bytes for {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid Excel file (magic bytes mismatch)."
        )

    # 5. Delegate to service for data processing
    try:
        service.populate_project(db, project_id, current_user.id, file_bytes, file_ext)
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        logger.error(f"Unexpected error during population: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during processing.")

    return {"message": "Project populated successfully"}