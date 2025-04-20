import logging
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, status, Security, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

# Import shared models and schemas
from shared_models.models import User, APIToken
from shared_models.schemas import UserCreate, UserResponse, TokenResponse, UserDetailResponse

# Database and Auth dependencies
from shared_models.database import get_db

# Import CRUD functions
from app.crud import crud_user, crud_token

logger = logging.getLogger("admin_api.routes.core")

router = APIRouter()

# --- User Endpoints --- 
@router.post("/users", 
             response_model=UserResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new user",
             tags=["Users & Tokens"])
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_user = await crud_user.create_user(db=db, obj_in=user_in)
        # Use UserResponse schema for consistency
        return UserResponse.from_orm(db_user)
    except ValueError as e: # Handles duplicate email
        logger.warning(f"Failed to create user '{user_in.email}': {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating user '{user_in.email}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/users", 
            response_model=List[UserResponse],
            summary="List all users",
            tags=["Users & Tokens"])
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    # This endpoint doesn't strictly need a CRUD function, but could have one
    result = await db.execute(select(User).offset(skip).limit(limit).order_by(User.id))
    users = result.scalars().all()
    return [UserResponse.from_orm(u) for u in users]

# --- NEW: Get User by ID ---
@router.get("/users/{user_id}",
            response_model=UserResponse, # Consider UserDetailResponse if you want tokens listed
            summary="Get a specific user by ID",
            tags=["Users & Tokens"])
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.from_orm(db_user)

# --- NEW: Delete User by ID ---
@router.delete("/users/{user_id}",
             status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a user by ID",
             tags=["Users & Tokens"])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    deleted_user = await crud_user.remove_user(db=db, user_id=user_id)
    if deleted_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Token Endpoints --- 
@router.post("/users/{user_id}/tokens", 
             response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Generate a new API token for a user",
             tags=["Users & Tokens"])
async def create_token_for_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        db_token = await crud_token.create_token_for_user(db=db, user=user)
        return TokenResponse.from_orm(db_token)
    except Exception as e:
        logger.error(f"Unexpected error creating token for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error creating token")

# --- NEW: Delete Token by Value ---
@router.delete("/tokens/{token_value}",
             status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a token by its value",
             tags=["Users & Tokens"])
async def delete_token(token_value: str, db: AsyncSession = Depends(get_db)):
    # Basic validation: Ensure token value isn't excessively long/short or suspicious
    if not (20 < len(token_value) < 100):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format provided")
        
    deleted_token = await crud_token.remove_token(db=db, token_value=token_value)
    if deleted_token is None:
        # Return 404 even if token format was invalid but didn't exist, or just didn't exist
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)