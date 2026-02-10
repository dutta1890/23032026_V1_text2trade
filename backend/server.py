"""
Text2trade Backend Server
=========================
A minimal FastAPI backend with simple email/password authentication.
Users are stored in memory (lost on restart - MVP only).

AUTHENTICATION FLOW (Plain English):
1. SIGNUP: User sends email + password → We store it in a dictionary → Return success
2. LOGIN: User sends email + password → We check if it matches → Return success/failure
3. No tokens, no sessions, no encryption - just simple string matching

File Structure:
- server.py (this file): Main FastAPI application with auth routes
"""

from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from typing import Dict


# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables from .env file
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main FastAPI app instance
app = FastAPI(
    title="Text2trade API",
    description="A minimal backend with simple auth for Text2trade",
    version="0.2.0"
)

# Create an API router with /api prefix
# All routes will be accessible under /api/*
api_router = APIRouter(prefix="/api")


# =============================================================================
# IN-MEMORY USER STORAGE
# =============================================================================

# Simple dictionary to store users
# Format: { "email@example.com": "password123" }
# WARNING: This is lost when server restarts - MVP only!
users_db: Dict[str, str] = {}


# =============================================================================
# REQUEST/RESPONSE MODELS
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


class AuthRequest(BaseModel):
    """
    Request model for signup and login.
    Both endpoints use the same format: email + password.
    """
    email: EmailStr       # Valid email format required
    password: str         # Any string, no complexity requirements


class AuthResponse(BaseModel):
    """
    Response model for successful authentication.
    Returns the user's email to confirm who logged in.
    """
    success: bool
    message: str
    email: str


class ErrorResponse(BaseModel):
    """Response model for error messages"""
    success: bool
    message: str


# =============================================================================
# API ROUTES - GENERAL
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
        "version": "0.2.0"
    }


# =============================================================================
# API ROUTES - AUTHENTICATION
# =============================================================================

@api_router.post("/signup", response_model=AuthResponse)
async def signup(request: AuthRequest):
    """
    SIGNUP ENDPOINT
    ---------------
    Creates a new user account.
    
    How it works:
    1. Check if email already exists in our users dictionary
    2. If exists → return error (can't have duplicate accounts)
    3. If new → store email:password in dictionary → return success
    
    No password hashing - this is MVP only!
    """
    email = request.email.lower()  # Normalize email to lowercase
    password = request.password
    
    # Check if user already exists
    if email in users_db:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Check password is not empty
    if not password or len(password) < 1:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty"
        )
    
    # Store the new user (plain text password - MVP only!)
    users_db[email] = password
    
    # Log the signup (don't log password!)
    logger.info(f"New user signed up: {email}")
    
    return {
        "success": True,
        "message": "Account created successfully",
        "email": email
    }


@api_router.post("/login", response_model=AuthResponse)
async def login(request: AuthRequest):
    """
    LOGIN ENDPOINT
    --------------
    Authenticates an existing user.
    
    How it works:
    1. Look up email in our users dictionary
    2. If not found → return error (user doesn't exist)
    3. If found → compare passwords
    4. If passwords match → return success
    5. If passwords don't match → return error
    
    No tokens or sessions - frontend handles state!
    """
    email = request.email.lower()  # Normalize email to lowercase
    password = request.password
    
    # Check if user exists
    if email not in users_db:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Check password matches
    if users_db[email] != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Log the login (don't log password!)
    logger.info(f"User logged in: {email}")
    
    return {
        "success": True,
        "message": "Login successful",
        "email": email
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
logger.info("Text2trade API server initialized with authentication")
