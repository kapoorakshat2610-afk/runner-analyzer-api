from fastapi import FastAPI

from database import Base, engine
from routes.auth import router as auth_router
from routes.sessions import router as sessions_router
from routes.analysis import router as analysis_router

import models.session_model
import models.user_model


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI Sports Talent API",
    description="Backend API for AI Sports Talent Analysis",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "AI Sports Talent Backend is running",
        "status": "success",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ai-sports-talent-backend",
    }


app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(analysis_router)