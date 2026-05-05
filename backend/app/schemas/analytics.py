from pydantic import BaseModel

class StudentPerformanceItem(BaseModel):
    course_code: str
    semester_number: int
    assessment_type: str
    score: float

class StudentPerformanceRequest(BaseModel):
    student_external_id: str
    course_codes: list[str]