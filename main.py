import os, tempfile
import numpy as np
import cv2
import mediapipe as mp
from fastapi import UploadFile, File

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import pandas as pd
import joblib
import io

def calc_angle(a, b, c):
    a = np.array(a)  # hip
    b = np.array(b)  # knee
    c = np.array(c)  # ankle

    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
    angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
    return float(angle)

app = FastAPI(title="Sports Analysis API")
model = joblib.load("runner_model.pkl")


@app.get("/")
def home():
    return {"message": "Backend running successfully"}
    
@app.get("/analyze")
def analyze():
    df = pd.read_csv("knee_angles.csv")
    avg_knee_angle = df["knee_angle"].mean()

    predicted_level = model.predict([[avg_knee_angle]])[0]

    return {
        "average_knee_angle": round(avg_knee_angle, 2),
        "performance_level": predicted_level,
        "total_frames": len(df),
        "ml_used": True
    }


@app.get("/ui", response_class=HTMLResponse)
def ui():
    with open("index.html", "r") as f:
        return f.read()
@app.post("/analyze_csv")
async def analyze_csv(file: UploadFile = File(...)):
    # Read uploaded file bytes
    contents = await file.read()

    # Convert bytes -> dataframe
    df = pd.read_csv(io.BytesIO(contents))

    # Validate required column
    if "knee_angle" not in df.columns:
        return {"error": "CSV must contain a column named 'knee_angle'"}

    # Compute features
    avg_knee_angle = df["knee_angle"].mean()

    # ML prediction
    predicted_level = model.predict([[avg_knee_angle]])[0]

    return {
        "average_knee_angle": round(avg_knee_angle, 2),
        "performance_level": predicted_level,
        "total_frames": len(df),
        "ml_used": True,
        "source": "uploaded_csv"
    }
import os
from fastapi.responses import HTMLResponse

@app.get("/webui", response_class=HTMLResponse)
def webui():
    path = os.path.join(os.path.dirname(__file__), "webui.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
@app.post("/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    # Save uploaded video to a temp file
    suffix = os.path.splitext(file.filename)[-1].lower()
    if suffix not in [".mp4", ".mov", ".avi", ".mkv"]:
        return {"error": "Unsupported video format. Upload mp4/mov/avi/mkv"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        video_path = tmp.name

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        os.remove(video_path)
        return {"error": "Could not open video file"}

    knee_angles = []
    processed_frames = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    # ✅ Speed control: process every Nth frame (set 2 or 3 for faster)
    FRAME_SKIP = 2

    frame_index = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_index += 1
        if frame_index % FRAME_SKIP != 0:
            continue

        processed_frames += 1

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if not results.pose_landmarks:
            continue

        lm = results.pose_landmarks.landmark

        # Right leg points
        hip = (lm[mp_pose.PoseLandmark.RIGHT_HIP].x, lm[mp_pose.PoseLandmark.RIGHT_HIP].y)
        knee = (lm[mp_pose.PoseLandmark.RIGHT_KNEE].x, lm[mp_pose.PoseLandmark.RIGHT_KNEE].y)
        ankle = (lm[mp_pose.PoseLandmark.RIGHT_ANKLE].x, lm[mp_pose.PoseLandmark.RIGHT_ANKLE].y)

        angle = calc_angle(hip, knee, ankle)
        knee_angles.append(angle)

        # Safety stop for very long videos
        if processed_frames >= 600:   # ~600 processed frames cap
            break

    cap.release()
    pose.close()
    os.remove(video_path)

    if len(knee_angles) < 5:
        return {"error": "Not enough pose frames detected. Try clearer video / full body visible."}

    avg_knee = float(np.mean(knee_angles))
    predicted_level = model.predict([[avg_knee]])[0]

    return {
        "average_knee_angle": round(avg_knee, 2),
        "performance_level": predicted_level,
        "frames_used": len(knee_angles),
        "total_frames_in_video": total_frames,
        "ml_used": True,
        "source": "uploaded_video"
    }

