from typing import Optional

from pydantic import BaseModel, Field


class JobOut(BaseModel):
    id: int
    source: str
    title: str
    company: str
    location: str
    url: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = "USD"
    skills: list[str] = Field(default_factory=list)


class SkillStat(BaseModel):
    skill: str
    count: int
    percentage: float


class SalaryBucket(BaseModel):
    label: str
    count: int
    min_salary: float
    max_salary: float


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
    query: str = Field(min_length=1, examples=["React Engineer"])
    location: str = ""
    cv_skills: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=200)


class InsightsResponse(BaseModel):
    query: str
    location: str
    job_count: int
    jobs: list[JobOut]
    top_skills: list[SkillStat]
    missing_skills: list[SkillStat]
    salary_distribution: list[SalaryBucket]
    interview_questions: list[ResourceOut]
    books: list[ResourceOut]
    courses: list[ResourceOut]
    github_projects: list[ResourceOut]
    certifications: list[ResourceOut]
    roadmap: list[RoadmapStep]
    estimated_study_hours: float


class HealthResponse(BaseModel):
    status: str
    database: str
