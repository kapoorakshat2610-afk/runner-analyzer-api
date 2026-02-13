from __future__ import annotations

import math
import os
import tempfile
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# ----------------------------
# FastAPI setup
# ----------------------------
app = FastAPI(title="Runner Analyzer API", version="1.0.0")

# Allow your Flutter app / browser access (safe default for hackathon)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"ok": True, "message": "Runner Analyzer API is running"}


@app.get("/health")
def health():
    return {"ok": True}


# ----------------------------
# Report builder (Option 1)
# ----------------------------
def build_report(
    average_knee_angle: float,
    ml_used: bool = True,
    source: str = "uploaded_video",
    frames_analyzed: Optional[int] = None,
    keypoints_confidence: Optional[float] = None,
):
    IDEAL = 165.0
    diff = abs(IDEAL - float(average_knee_angle))

    score = 100.0 - (diff * 2.0)
    score = max(0.0, min(100.0, score))

    # Explainable buckets (judge-friendly)
    if score >= 85:
        level = "advanced"
    elif score >= 60:
        level = "intermediate"
    else:
        level = "beginner"

    mistakes = []
    suggestions = []

    if diff <= 2:
        mistakes.append("No major mistakes detected.")
        suggestions.append("Maintain this running form and consistency.")
        suggestions.append("Keep stride smooth and controlled.")
    elif diff <= 6:
        mistakes.append("Minor knee alignment deviation from ideal.")
        suggestions.append("Aim closer to 165° knee angle during stride.")
        suggestions.append("Focus on steady stride mechanics and knee drive.")
    else:
        mistakes.append("Knee angle deviation is high compared to ideal.")
        suggestions.append("Practice knee-drive drills and controlled landing technique.")
        suggestions.append("Record from side view with good lighting for better accuracy.")
        suggestions.append("Reduce overstriding and keep cadence steady.")

    return {
        "overall_score": round(score, 1),
        "average_knee_angle": round(float(average_knee_angle), 1),
        "difference_from_ideal": round(diff, 1),
        "ideal_knee_angle": IDEAL,
        "performance_level": level,
        "mistakes": mistakes,
        "suggestions": suggestions,
        "ml_used": bool(ml_used),
        "source": source,
        "frames_analyzed": frames_analyzed,
        "keypoints_confidence": round(float(keypoints_confidence), 3) if keypoints_confidence is not None else None,
    }


# ----------------------------
# Pose + Knee Angle utilities
# ----------------------------
def _angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Angle ABC in degrees where points are 2D/3D.
    """
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom == 0:
        return float("nan")
    cosang = np.dot(ba, bc) / denom
    cosang = float(np.clip(cosang, -1.0, 1.0))
    return math.degrees(math.acos(cosang))


def analyze_video_knee_angle(video_path: str) -> dict:
    """
    Returns:
      {
        "avg_knee_angle": float,
        "frames_analyzed": int,
        "confidence": float
      }
    """
    try:
        import mediapipe as mp
    except Exception as e:
        raise RuntimeError(f"mediapipe import failed: {e}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Cannot open video")

    mp_pose = mp.solutions.pose

    # Use a moderate model complexity for decent accuracy
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    # Sample every N frames to keep it fast on Render
    frame_step = 5

    angles = []
    confs = []
    frames_used = 0

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_idx += 1
        if frame_idx % frame_step != 0:
            continue

        # MediaPipe expects RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if not results.pose_landmarks:
            continue

        lm = results.pose_landmarks.landmark

        # Landmarks for knee angle:
        # Left: hip(23), knee(25), ankle(27)
        # Right: hip(24), knee(26), ankle(28)
        # Use x,y (image-normalized coords) + z (optional)
        def pt(i: int) -> np.ndarray:
            return np.array([lm[i].x, lm[i].y, lm[i].z], dtype=np.float32)

        left = _angle_3pts(pt(23), pt(25), pt(27))
        right = _angle_3pts(pt(24), pt(26), pt(28))

        # Use average of valid sides
        vals = []
        if not math.isnan(left):
            vals.append(left)
        if not math.isnan(right):
            vals.append(right)

        if not vals:
            continue

        angles.append(float(np.mean(vals)))

        # confidence proxy: average visibility of hips/knees/ankles used
        vis = [
            lm[23].visibility, lm[25].visibility, lm[27].visibility,
            lm[24].visibility, lm[26].visibility, lm[28].visibility
        ]
        confs.append(float(np.mean(vis)))

        frames_used += 1

    cap.release()
    pose.close()

    if frames_used == 0 or len(angles) == 0:
        raise RuntimeError("No valid pose frames detected. Try a clearer side-view video.")

    return {
        "avg_knee_angle": float(np.mean(angles)),
        "frames_analyzed": int(frames_used),
        "confidence": float(np.mean(confs)) if confs else None,
    }


# ----------------------------
# Main endpoint
# ----------------------------
@app.post("/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name missing")

    # Save to a temp file
    suffix = os.path.splitext(file.filename)[-1].lower()
    if suffix not in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        # still allow, but warn
        suffix = ".mp4"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            content = await file.read()
            tmp.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    # Analyze
    try:
        out = analyze_video_knee_angle(temp_path)
        report = build_report(
            average_knee_angle=out["avg_knee_angle"],
            ml_used=True,
            source="uploaded_video",
            frames_analyzed=out["frames_analyzed"],
            keypoints_confidence=out.get("confidence"),
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass
