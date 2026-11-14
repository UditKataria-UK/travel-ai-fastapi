
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import ALLOWED_ORIGINS
from backend.api.routes import router


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# FastAPI application
app = FastAPI(
    title="AI Trip Planner",
    description=(
        "AI-powered trip planning system built with "
        "FastAPI, LangGraph, and LLM-based agents."
    ),
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in ALLOWED_ORIGINS
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register API routes
app.include_router(router)


@app.get("/", tags=["Health"])
def home():
    return {
        "message": "AI Trip Planner API is running",
        "version": app.version,
        "status": "healthy",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
