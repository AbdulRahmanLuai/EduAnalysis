from sqlmodel import Session, select
from app.models import Project

class ProjectRepo:
    def create(self, db: Session, project: Project) -> Project:
        db.add(project)
        db.flush() 
        return project

    def get_by_id(self, db: Session, project_id: int) -> Project | None:
        return db.get(Project, project_id)

    def get_by_user(self, db: Session, user_id: int) -> list[Project]:
        stmt = select(Project).where(Project.user_id == user_id)
        return list(db.exec(stmt).all())

    def delete(self, db: Session, project: Project) -> None:
        db.delete(project)
