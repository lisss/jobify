from typing import Optional

from pydantic import BaseModel, Field


class SkillStat(BaseModel):
    skill: str
    count: int = 0
    percentage: float


class ResourceOut(BaseModel):
    kind: str
    title: str
    url: str
    provider: str = ""
    skills: list[str] = Field(default_factory=list)
    description: str = ""
    estimated_hours: Optional[float] = None


class RoadmapStep(BaseModel):
    order: int
    title: str
    skills: list[str]
    estimated_hours: float
    resources: list[ResourceOut] = Field(default_factory=list)


class InsightsRequest(BaseModel):
    query: str = Field(min_length=1, examples=["Python Backend Engineer"])
    location: str = ""
    cv_skills: list[str] = Field(default_factory=list)


class InsightsResponse(BaseModel):
    query: str
    location: str
    # Position requirements (importance in `percentage`)
    requirements: list[SkillStat]
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[SkillStat]
    unmatched_cv_skills: list[str] = Field(default_factory=list)
    interview_questions: list[ResourceOut]
    books: list[ResourceOut]
    courses: list[ResourceOut]
    certifications: list[ResourceOut]
    roadmap: list[RoadmapStep]
    estimated_study_hours: float


class HealthResponse(BaseModel):
    status: str
    database: str
