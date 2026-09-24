from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True, unique=True)
    source: str = Field(index=True)
    title: str = Field(index=True)
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = "USD"
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    posted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Resource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(index=True)  # book | course | github | certification | interview
    title: str
    url: str = ""
    provider: str = ""
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    description: str = ""
    estimated_hours: Optional[float] = None
