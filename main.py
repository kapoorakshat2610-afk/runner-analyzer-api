from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import pandas as pd
import joblib
import io


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
