import logging
from typing import Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from shared_models import models, schemas

logger = logging.getLogger("admin_api.crud.user")

async def get_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get a single user by ID."""
    return await db.get(models.User, user_id)

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    """Get a single user by email."""
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalars().first()

async def create_user(db: AsyncSession, *, obj_in: schemas.UserCreate) -> models.User:
    """Create a new user."""
    existing_user = await get_user_by_email(db, email=obj_in.email)
    if existing_user:
        logger.warning(f"Attempted to create user with duplicate email: {obj_in.email}")
        raise ValueError(f"User with email '{obj_in.email}' already exists.")
        
    db_user = models.User(**obj_in.dict())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"Created user '{db_user.email}' (ID: {db_user.id})")
    return db_user

async def remove_user(db: AsyncSession, *, user_id: int) -> Optional[models.User]:
    """Delete a user by ID."""
    # Note: This doesn't automatically handle related objects like APITokens or UserPlan
    # depending on cascade rules. Add checks if necessary.
    db_user = await get_user(db, user_id=user_id)
    if db_user:
        logger.warning(f"Deleting user '{db_user.email}' (ID: {user_id}). Associated tokens/plan may need manual cleanup or cascade.")
        # Add checks here: e.g., ensure UserPlan is removed first?
        await db.delete(db_user)
        await db.commit()
        logger.info(f"Deleted user ID: {user_id}")
        return db_user
    logger.warning(f"Attempted to delete non-existent user ID: {user_id}")
    return None 