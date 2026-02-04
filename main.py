import joblib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd

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
