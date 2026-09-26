from datetime import datetime

from sqlalchemy import Column, JSON, LargeBinary
from sqlmodel import Field, SQLModel


class CvUpload(SQLModel, table=True):
    """CV file stored for an anonymous browser session."""

    __tablename__ = "cv_upload"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    filename: str
    content_type: str = "application/octet-stream"
    content: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
