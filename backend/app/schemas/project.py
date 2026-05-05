from pydantic import BaseModel, Field
from typing import Optional

class AssessmentTypeInput(BaseModel):
    name: str
    weight: int = Field(ge=0, le=100)

class ProjectCreate(BaseModel):
    name: str
    academic_year_start: int
    description: Optional[str] = Field(default=None, max_length=500)
    assessment_types: list[AssessmentTypeInput]

class ProjectResponse(BaseModel):
    id: int
    name: str
    academic_year_start: int
    description: Optional[str] = None
    user_id: int
    is_populated: bool
    model_config = {"from_attributes": True}
    
    
class StudentInfo(BaseModel):
    st_external_id: str
    name: str

class CourseInfo(BaseModel):
    code: str