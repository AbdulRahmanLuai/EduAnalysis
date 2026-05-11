import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from app.db import engine
from app.config import settings
from app.logging_config import setup_logging
from app.api.endpoints import analytics
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from app.limiter import limiter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Add Strict-Transport-Security only when using HTTPS in production
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response



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
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
app.include_router(analytics.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)