"""Authentication module for Text2trade API."""

import os
import re
import uuid
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# MongoDB connection
mongo_client = MongoClient(os.environ.get("MONGO_URL"))
db = mongo_client[os.environ.get("DB_NAME", "text2trade")]
users_collection = db["users"]

# Create unique index on email
try:
    users_collection.create_index("email", unique=True)
except Exception as e:
    print(f"Warning: Could not create email index: {e}")

# JWT settings
JWT_SECRET = os.environ.get("JWT_SECRET", "fallback_secret_not_for_prod")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security
security = HTTPBearer()


def validate_password_strength(password: str):
    """Validate password meets strength requirements. Raises ValueError if not."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least 1 number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least 1 special character")


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str
    start_demo: bool = False
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        validate_password_strength(v)
        return v

class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str

class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def hash_password(password: str) -> str:
    """Hash password with bcrypt (12 rounds)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str, role: str = "user", account_mode: str = "real") -> str:
    """Create JWT access token (24hr expiry)."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "account_mode": account_mode,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token (7-day expiry)."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# =============================================================================
# AUTH DEPENDENCY
# =============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    # Check token blacklist
    if db["blacklisted_tokens"].find_one({"token": token}):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Fetch user from MongoDB
    user = users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User account is disabled")
    
    # Merge role from JWT (avoids DB lookup for role checks)
    user["role"] = payload.get("role", user.get("role", "user"))
    return user


async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))) -> Optional[dict]:
    """Get current user if authenticated, else return None (no error)."""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        if db["blacklisted_tokens"].find_one({"token": token}):
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        return user if user and user.get("is_active", True) else None
    except Exception:
        return None


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role. Extends get_current_user."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# =============================================================================
# AUTH FUNCTIONS
# =============================================================================

def register_user(data: UserRegister) -> UserResponse:
    """Register a new user."""
    email = data.email.lower().strip()
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "user_id": user_id,
        "email": email,
        "password_hash": hash_password(data.password),
        "role": "user",
        "created_at": now,
        "is_active": True,
        "account_mode": "demo" if data.start_demo else "real",
        "demo_capital": 10000 if data.start_demo else 0,
        "demo_created_at": now if data.start_demo else None,
        "has_completed_onboarding": False,
    }
    
    try:
        users_collection.insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error")
    
    # Seed demo data if requested
    if data.start_demo:
        try:
            from routers.account import seed_demo_data
            seed_demo_data(user_id)
        except Exception as e:
            logger.warning(f"Demo seeding failed for {user_id}: {e}")
    
    return UserResponse(user_id=user_id, email=email)

def login_user(data: UserLogin) -> TokenResponse:
    """Login user and return tokens."""
    email = data.email.lower().strip()
    
    # Find user
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account deactivated. Contact support to reactivate.")
    
    # Generate tokens
    access_token = create_access_token(user["user_id"], user["email"], user.get("role", "user"), user.get("account_mode", "real"))
    refresh_token = create_refresh_token(user["user_id"])
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

def refresh_access_token(refresh_token: str) -> AccessTokenResponse:
    """Refresh access token using refresh token."""
    payload = decode_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Fetch user
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User account is disabled")
    
    # Generate new access token only
    new_access_token = create_access_token(user["user_id"], user["email"], user.get("role", "user"), user.get("account_mode", "real"))
    
    return AccessTokenResponse(access_token=new_access_token)



# =============================================================================
# LOGOUT (TOKEN BLACKLIST)
# =============================================================================

def blacklist_token(token: str):
    """Add a token to the blacklist collection with TTL."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        db["blacklisted_tokens"].insert_one({"token": token, "expires_at": exp})
    except Exception:
        db["blacklisted_tokens"].insert_one({
            "token": token,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        })

# Create TTL index so expired blacklist entries auto-delete
try:
    db["blacklisted_tokens"].create_index("expires_at", expireAfterSeconds=0)
except Exception:
    pass


# =============================================================================
# PASSWORD RESET (OTP-based)
# =============================================================================

import secrets
import random
import logging
logger = logging.getLogger(__name__)

EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"

class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        validate_password_strength(v)
        return v

class PasswordResetResponse(BaseModel):
    success: bool
    message: str


def create_password_reset_otp(email: str) -> Optional[str]:
    """Create a 6-digit OTP for password reset (15-min expiry). Returns OTP or None."""
    email = email.lower().strip()
    user = users_collection.find_one({"email": email})
    if not user:
        return None

    otp = f"{random.randint(100000, 999999)}"
    db["password_resets"].insert_one({
        "email": email,
        "otp": otp,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        "used": False,
    })

    if EMAIL_ENABLED:
        logger.info(f"[EMAIL] Sending OTP to {email}")
        # TODO: integrate email service
    else:
        logger.info(f"[PASSWORD_RESET_OTP] email={email} otp={otp} (EMAIL_ENABLED=false, logged only)")

    return otp

# TTL index for password reset OTPs
try:
    db["password_resets"].create_index("expires_at", expireAfterSeconds=0)
except Exception:
    pass


def reset_password_with_otp(email: str, otp: str, new_password: str) -> bool:
    """Reset password using a valid OTP. Returns True on success."""
    email = email.lower().strip()
    record = db["password_resets"].find_one({
        "email": email, "otp": otp, "used": False,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    new_hash = hash_password(new_password)
    result = users_collection.update_one({"email": email}, {"$set": {"password_hash": new_hash}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    db["password_resets"].update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    return True


# =============================================================================
# CHANGE PASSWORD (requires current password)
# =============================================================================

class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        validate_password_strength(v)
        return v


def change_password(user_id: str, current_password: str, new_password: str) -> bool:
    """Change password for authenticated user. Verifies current password first."""
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = hash_password(new_password)
    users_collection.update_one({"user_id": user_id}, {"$set": {"password_hash": new_hash}})
    return True
