"""
Text2trade Backend Server
=========================
A minimal FastAPI backend scaffold for the Text2trade application.
No business logic - just basic health check and placeholder endpoints.

File Structure:
- server.py (this file): Main FastAPI application with routes
"""

from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timezone


# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables from .env file
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main FastAPI app instance
# Note: No business logic - this is just a scaffold
app = FastAPI(
    title="Text2trade API",
    description="A minimal backend scaffold for Text2trade",
    version="0.1.0"
)

# Create an API router with /api prefix
# All routes will be accessible under /api/*
api_router = APIRouter(prefix="/api")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str           # "healthy" or "unhealthy"
    timestamp: str        # ISO format timestamp
    version: str          # API version


class RootResponse(BaseModel):
    """Response model for root endpoint"""
    message: str
    app_name: str


# =============================================================================
# API ROUTES
# =============================================================================

@api_router.get("/", response_model=RootResponse)
async def root():
    """
    Root endpoint - returns basic API info.
    Used to verify API is accessible.
    """
    return {
        "message": "Welcome to Text2trade API",
        "app_name": "Text2trade"
    }


@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns current server status and timestamp.
    Used by monitoring systems and load balancers.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0"
    }


# =============================================================================
# APP SETUP
# =============================================================================

# Include the API router in the main app
app.include_router(api_router)

# Configure CORS middleware
# Allows frontend to make requests to this backend
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
# Logs will show timestamp, logger name, level, and message
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup message
logger.info("Text2trade API server initialized")
