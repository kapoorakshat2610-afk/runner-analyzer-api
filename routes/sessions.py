from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models.session_model import Session
from models.user_model import User
from schemas import SessionCreate, SessionResponse
from auth import get_current_user, require_role


router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"],
)


@router.post(
    "/",
    response_model=SessionResponse,
)
def create_session(
    session_data: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
):
    # Only athletes create their own performance sessions.
    if current_user.role != "athlete":
        raise HTTPException(
            status_code=403,
            detail="Only athletes can create performance sessions",
        )

    new_session = Session(
        user_id=current_user.id,
        athlete=current_user.username,
        overall_score=session_data.overall_score,
        average_knee_angle=session_data.average_knee_angle,
        confidence=session_data.confidence,
        frames=session_data.frames,
        performance_level=session_data.performance_level,
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@router.get(
    "/",
    response_model=list[SessionResponse],
)
def get_sessions(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(
        require_role("coach"),
    ),
):
    return (
        db.query(Session)
        .order_by(Session.created_at.desc())
        .all()
    )


@router.get(
    "/athlete/{athlete_name}",
    response_model=list[SessionResponse],
)
def get_athlete_sessions(
    athlete_name: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user,
    ),
):
    # Athlete can only access their own sessions.
    if current_user.role == "athlete":
        if current_user.username != athlete_name:
            raise HTTPException(
                status_code=403,
                detail="You can only access your own sessions",
            )

        return (
            db.query(Session)
            .filter(
                Session.user_id == current_user.id,
            )
            .order_by(
                Session.created_at.desc(),
            )
            .all()
        )

    # Coach can view sessions for a specific athlete.
    return (
        db.query(Session)
        .filter(
            Session.athlete == athlete_name,
        )
        .order_by(
            Session.created_at.desc(),
        )
        .all()
    )