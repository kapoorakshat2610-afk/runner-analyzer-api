from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    athlete: str

    overall_score: float = 0.0

    average_knee_angle: float = 0.0

    confidence: float = 0.0

    frames: int = 0

    performance_level: str = "unknown"


class SessionResponse(SessionCreate):
    id: int
    user_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "athlete"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str