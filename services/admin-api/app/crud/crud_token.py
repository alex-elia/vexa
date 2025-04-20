import logging
import secrets
import string
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from shared_models import models, schemas

logger = logging.getLogger("admin_api.crud.token")

def generate_secure_token(length=40):
    # Copied from core routes - consider moving to a shared util if used elsewhere
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

async def get_token_by_value(db: AsyncSession, token_value: str) -> Optional[models.APIToken]:
    """Get a token by its value."""
    result = await db.execute(select(models.APIToken).where(models.APIToken.token == token_value))
    return result.scalars().first()

async def create_token_for_user(db: AsyncSession, *, user: models.User) -> models.APIToken:
    """Create a new API token for a given user object."""
    if not user:
        logger.error("Attempted to create token for a null user object.")
        raise ValueError("Valid user object required to create token.")
        
    token_value = generate_secure_token()
    # Ensure uniqueness (highly unlikely collision, but good practice)
    while await get_token_by_value(db, token_value):
        token_value = generate_secure_token()
        
    db_token = models.APIToken(token=token_value, user_id=user.id)
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    logger.info(f"Created token for user {user.id} ('{user.email}')")
    return db_token

async def remove_token(db: AsyncSession, *, token_value: str) -> Optional[models.APIToken]:
    """Delete a token by its value."""
    db_token = await get_token_by_value(db, token_value=token_value)
    if db_token:
        logger.warning(f"Deleting token ending in '...{token_value[-6:]}' for user {db_token.user_id}")
        await db.delete(db_token)
        await db.commit()
        logger.info(f"Deleted token ending in '...{token_value[-6:]}'")
        return db_token
    logger.warning(f"Attempted to delete non-existent token value ending in '...{token_value[-6:]}'")
    return None 