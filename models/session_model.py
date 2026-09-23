from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime

from database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    athlete = Column(
        String,
        nullable=False,
        index=True,
    )

    overall_score = Column(
        Float,
        default=0.0,
    )

    average_knee_angle = Column(
        Float,
        default=0.0,
    )

    confidence = Column(
        Float,
        default=0.0,
    )

    frames = Column(
        Integer,
        default=0,
    )

    performance_level = Column(
        String,
        default="unknown",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )