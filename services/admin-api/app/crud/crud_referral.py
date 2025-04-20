import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import billing_models, schemas, models

logger = logging.getLogger("admin_api.crud.referral")

async def create_referral_data(
    db: AsyncSession, 
    *, 
    user: models.User, 
    obj_in: schemas.InternalReferralLogRequest
) -> billing_models.ReferralData:
    """Creates a new referral data entry for a given user."""
    # Check user exists (redundant if user object is passed, but good practice)
    if not user:
         logger.error("Attempted to log referral data for a null user object.")
         raise ValueError("Valid user object required to log referral data.")
         
    logger.info(f"Creating referral data entry for user {user.id}")
    db_obj = billing_models.ReferralData(
        user_id=user.id,
        **obj_in.dict(exclude_unset=True) # Use validated data from schema
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    logger.info(f"Successfully created referral data entry ID {db_obj.id} for user {user.id}")
    return db_obj 