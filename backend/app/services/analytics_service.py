from fastapi import HTTPException
from app.repos.analytics_repo import AnalyticsRepo
from app.repos.project_repo import ProjectRepo




class AnalyticsService:
    def __init__(
        self,
        project_repo: ProjectRepo,
        analytics_repo: AnalyticsRepo,
    ) -> None:
        self.analytics_repo = analytics_repo
        self.project_repo = project_repo

    def get_student_performance(
        self,
        db,
        project_id: int,
        student_external_id: str,
        course_codes: list[str],
        user_id: int
    ):
        project = self.project_repo.get_by_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return self.analytics_repo.get_student_performance(db, project_id, student_external_id, course_codes)

                