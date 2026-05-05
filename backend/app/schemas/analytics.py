from pydantic import BaseModel
from typing import List, Optional, Dict


class SemesterScores(BaseModel):
    total: List[float]
    assessments: Dict[str, List[float]]

class SectionScoresItem(BaseModel):
    course_code: str
    semesters: Dict[int, SemesterScores]      # key = semester_number

class SectionScoresResponse(BaseModel):
    items: List[SectionScoresItem]

class StudentPerformanceItem(BaseModel):
    course_code: str
    semester_number: int
    assessment_type: str
    score: float

class StudentPerformanceRequest(BaseModel):
    student_external_id: str
    course_codes: list[str]
    
class SectionScoresRequest(BaseModel):
    grade: int
    section: str

class SemesterScores(BaseModel):
    total: List[float]
    assessments: Dict[str, List[float]]

class SectionScoresItem(BaseModel):
    course_code: str
    semesters: Dict[int, SemesterScores]     

class SectionScoresResponse(BaseModel):
    items: List[SectionScoresItem]