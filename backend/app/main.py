import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from app.db import engine
from app.config import settings
from app.logging_config import setup_logging

# Setup logging before anything else
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up – creating database tables if needed")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    logger.debug("Root endpoint called")
    return {"message": "Welcome to EduAnalytics API"}

@app.get("/health")
def health_check():
    logger.debug("Health check called")
    return {"status": "ok"}

from app.api.endpoints import auth, projects
app.include_router(auth.router)
app.include_router(projects.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)