import logging
import secrets
import string
import os
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List # Import List for response model

# Import shared models and schemas
from shared_models.models import User, APIToken, Base # Import Base for init_db
from shared_models.schemas import UserCreate, UserResponse, TokenResponse, UserDetailResponse # Import required schemas

# Database utilities (needs to be created)
from shared_models.database import get_db, init_db # New import

# Import the new routers
from app.api.routes import core as core_router
from app.api.routes import billing as billing_router

# Logging configuration
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("admin_api")

# App initialization
app = FastAPI(title="Vexa Admin API")

# Security - Reuse logic from bot-manager/auth.py for admin token verification
API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key", auto_error=False) # Use a distinct header
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN") # Read from environment

async def verify_admin_token(admin_api_key: str = Security(API_KEY_HEADER)):
    """Dependency to verify the admin API token."""
    if not ADMIN_API_TOKEN:
        logger.error("CRITICAL: ADMIN_API_TOKEN environment variable not set!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication is not configured on the server."
        )
    
    if not admin_api_key or admin_api_key != ADMIN_API_TOKEN:
        logger.warning(f"Invalid admin token provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin token."
        )
    logger.info("Admin token verified successfully.")
    # No need to return anything, just raises exception on failure 

# Router setup (OLD - REMOVED)
# router = APIRouter(
#     prefix="/admin",
#     tags=["Admin"],
#     dependencies=[Depends(verify_admin_token)]
# )

# --- Helper Functions --- (MOVED TO core.py)
# def generate_secure_token(length=40):
#     alphabet = string.ascii_letters + string.digits
#     return ''.join(secrets.choice(alphabet) for i in range(length))

# --- Admin Endpoints (MOVED TO core.py) --- 
# @router.post("/users", ...)
# ...
# @router.get("/users", ...)
# ...
# @router.post("/users/{user_id}/tokens", ...)
# ...

# TODO: Add endpoints for GET /users/{id}, DELETE /users/{id}, DELETE /tokens/{token_value}

# Include the OLD router in the main app (REMOVED)
# app.include_router(router)

# Include the NEW routers, applying the prefix and admin token dependency
app.include_router(
    core_router.router, 
    prefix="/admin", 
    tags=["Admin"], # Apply a general tag, specific tags are in the router files
    dependencies=[Depends(verify_admin_token)]
)
app.include_router(
    billing_router.router, 
    prefix="/admin", # Apply the same prefix
    tags=["Admin"], # Apply a general tag, specific tags are in the router files
    # Note: Most billing routes require admin token (applied here),
    # but /internal/log_referral uses its own user auth (defined in billing.py)
    dependencies=[Depends(verify_admin_token)] 
)

# Add startup event to initialize DB (if needed for this service)
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Admin API...")
    # Requires database_utils.py to be created in admin-api/app
    # Ensure shared_models.database.init_db can handle models from both
    # models.py and billing_models.py if it creates tables.
    await init_db(drop_tables=True) 
    logger.info("Database schema recreated.")

# Root endpoint (optional)
@app.get("/")
async def root():
    return {"message": "Vexa Admin API"}
