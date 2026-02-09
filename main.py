from pydantic import BaseModel

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
import mediapipe as mp
class Features(BaseModel):
    avg_knee_angle: float

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

@app.get("/debug_mp")
def debug_mp():
    return {
        "mp_file": getattr(mp, "__file__", None),
        "mp_version": getattr(mp, "__version__", None),
        "has_solutions": hasattr(mp, "solutions"),
        "dir_sample": [x for x in dir(mp) if "solution" in x.lower()][:30],
    }
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
    try:
        import os, tempfile
        import cv2
        import numpy as np
        import mediapipe as mp

        suffix = os.path.splitext(file.filename)[-1].lower()
        if suffix not in [".mp4", ".mov", ".avi", ".mkv"]:
            return {"error": "Unsupported video format"}

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            video_path = tmp.name

        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(static_image_mode=False)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Could not open video file"}

        knee_angles = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            if not results.pose_landmarks:
                continue

            lm = results.pose_landmarks.landmark

            hip = (lm[mp_pose.PoseLandmark.RIGHT_HIP].x,
                   lm[mp_pose.PoseLandmark.RIGHT_HIP].y)
            knee = (lm[mp_pose.PoseLandmark.RIGHT_KNEE].x,
                    lm[mp_pose.PoseLandmark.RIGHT_KNEE].y)
            ankle = (lm[mp_pose.PoseLandmark.RIGHT_ANKLE].x,
                     lm[mp_pose.PoseLandmark.RIGHT_ANKLE].y)

            angle = calc_angle(hip, knee, ankle)
            knee_angles.append(angle)

            if len(knee_angles) > 300:
                break

        cap.release()
        pose.close()
        os.remove(video_path)

        if len(knee_angles) < 5:
            return {"error": "Not enough pose frames detected"}

        avg_knee = float(np.mean(knee_angles))
        predicted = model.predict([[avg_knee]])[0]

        return {
            "average_knee_angle": round(avg_knee, 2),
            "performance_level": predicted,
            "frames_used": len(knee_angles),
            "ml_used": True,
            "source": "uploaded_video"
        }

    except Exception as e:
        return {
            "error": "Internal processing error",
            "details": str(e)
        }
@app.post("/predict_features")
def predict_features(features: Features):
    avg_knee_angle = features.avg_knee_angle
    predicted_level = model.predict([[avg_knee_angle]])[0]
    return {
        "average_knee_angle": round(avg_knee_angle, 2),
        "performance_level": predicted_level,
        "ml_used": True,
        "source": "features_json"
    }
