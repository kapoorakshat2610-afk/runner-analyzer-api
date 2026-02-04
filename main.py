import joblib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd

app = FastAPI(title="Sports Analysis API")

@app.get("/")
def home():
    return {"message": "Backend running successfully"}

@app.get("/analyze")
def analyze():
    df = pd.read_csv("knee_angles.csv")
    avg_knee_angle = df["knee_angle"].mean()

    if avg_knee_angle >= 170:
        level = "Beginner"
    elif avg_knee_angle >= 160:
        level = "Intermediate"
    else:
        level = "Advanced"

    return {
        "average_knee_angle": round(avg_knee_angle, 2),
        "performance_level": level,
        "total_frames": len(df)
    }

@app.get("/ui", response_class=HTMLResponse)
def ui():
    with open("index.html", "r") as f:
        return f.read()
