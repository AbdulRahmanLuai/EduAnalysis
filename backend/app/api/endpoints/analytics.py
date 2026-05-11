from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.db import get_session
from app.services.analytics_service import AnalyticsService
from app.repos.project_repo import ProjectRepo
from app.core.security import get_current_user
from app.repos.analytics_repo import AnalyticsRepo
from app.schemas.analytics import SectionScoresRequest, SectionScoresResponse, StudentPerformanceItem, StudentPerformanceRequest
import logging
from app.main import limiter


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/analytics", tags=["analytics"])

def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(
        project_repo=ProjectRepo(),
        analytics_repo=AnalyticsRepo(),
    )
    

@router.post("/student-performance", response_model=list[StudentPerformanceItem])
@limiter.limit("20/minute")
def get_student_performance(
    project_id: int,
    data: StudentPerformanceRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service)
):
    logger.info(f"Fetching student performance for user_id={current_user.id}, project_id={project_id}, student_external_id='{data.student_external_id}', course_codes={data.course_codes}")
    
    return service.get_student_performance(db, project_id, data.student_external_id, data.course_codes, current_user.id)

@router.post("/section-scores", response_model=SectionScoresResponse)
@limiter.limit("20/minute")
def get_section_scores(
    project_id: int,
    data: SectionScoresRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service)
):
    items = service.get_section_scores(db, project_id, data.grade, data.section, current_user.id)
    return {"items": items}