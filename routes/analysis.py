import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session as DBSession

from auth import get_current_user
from database import get_db
from models.session_model import Session
from models.user_model import User
from services.video_analyzer import analyze_running_video

router = APIRouter(tags=["Video Analysis"])


@router.post("/analyze_video")
async def analyze_video(
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only athletes are allowed to create running analyses.
    if current_user.role != "athlete":
        raise HTTPException(
            status_code=403,
            detail="Only athletes can analyze running videos",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is missing",
        )

    allowed_extensions = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
    }

    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported video format. "
                "Use MP4, MOV, AVI, MKV, or WEBM."
            ),
        )

    temp_path = None

    try:
        # Save uploaded video temporarily.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temp_file:
            temp_path = temp_file.name

            content = await file.read()

            if not content:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded video is empty",
                )

            temp_file.write(content)

        # Run MediaPipe + OpenCV analysis.
        report = analyze_running_video(temp_path)

        # Save the result to our authenticated SQLite sessions table.
        new_session = Session(
            user_id=current_user.id,
            athlete=current_user.username,
            overall_score=float(
                report.get("overall_score", 0.0)
            ),
            average_knee_angle=float(
                report.get("average_knee_angle", 0.0)
            ),
            confidence=float(
                report.get("keypoints_confidence", 0.0)
            ),
            frames=int(
                report.get("frames_analyzed", 0)
            ),
            performance_level=str(
                report.get(
                    "performance_level",
                    "unknown",
                )
            ),
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # Return both the analysis report and the created session ID.
        return {
            **report,
            "session_id": new_session.id,
            "athlete": current_user.username,
        }

    except HTTPException:
        raise

    except RuntimeError as exc:
        db.rollback()

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Video analysis failed: {exc}",
        )

    finally:
        # Always remove temporary uploaded video.
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass