import logging
from typing import Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from shared_models import billing_models, schemas, models

logger = logging.getLogger("admin_api.crud.user_plan")

async def get_user_plan_by_user(db: AsyncSession, *, user_id: int) -> Optional[billing_models.UserPlan]:
    """Get the plan assignment for a specific user, including the nested Plan details."""
    result = await db.execute(
        select(billing_models.UserPlan)
        .options(selectinload(billing_models.UserPlan.plan).selectinload(billing_models.Plan.model_limits))
        .where(billing_models.UserPlan.user_id == user_id)
    )
    return result.scalars().first()

async def assign_or_update_user_plan(
    db: AsyncSession, 
    *, 
    user_id: int, 
    obj_in: schemas.UserPlanCreate # Use Create schema, contains user_id
) -> billing_models.UserPlan:
    """Assigns a plan to a user. If a plan exists, it updates it."""
    # Check if user exists (optional, depends on if user creation is separate)
    user = await db.get(models.User, user_id)
    if not user:
        logger.error(f"Attempted to assign plan to non-existent user ID: {user_id}")
        raise ValueError(f"User with ID {user_id} not found.")
        
    # Check if plan exists
    plan = await db.get(billing_models.Plan, obj_in.plan_id)
    if not plan:
        logger.error(f"Attempted to assign non-existent plan ID: {obj_in.plan_id}")
        raise ValueError(f"Plan with ID {obj_in.plan_id} not found.")
        
    db_obj = await get_user_plan_by_user(db=db, user_id=user_id)
    
    if db_obj:
        # Update existing assignment
        logger.info(f"Updating existing plan assignment for user {user_id} to plan {obj_in.plan_id}")
        update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
    else:
        # Create new assignment
        logger.info(f"Creating new plan assignment for user {user_id} with plan {obj_in.plan_id}")
        db_obj = billing_models.UserPlan(**obj_in.dict())
        db.add(db_obj)
        
    await db.commit()
    await db.refresh(db_obj, attribute_names=['plan']) # Refresh to load plan details
    return db_obj

async def update_user_plan_assignment(
    db: AsyncSession, 
    *, 
    db_obj: billing_models.UserPlan, 
    obj_in: schemas.UserPlanUpdate # Use Update schema
) -> billing_models.UserPlan:
    """Updates specific fields of a user's plan assignment (e.g., status, end_date)."""
    update_data = obj_in.dict(exclude_unset=True)
    
    # If updating plan_id, check if the new plan exists
    if "plan_id" in update_data and update_data["plan_id"] != db_obj.plan_id:
        new_plan = await db.get(billing_models.Plan, update_data["plan_id"])
        if not new_plan:
            logger.error(f"Attempted to update user plan assignment with non-existent plan ID: {update_data['plan_id']}")
            raise ValueError(f"Plan with ID {update_data['plan_id']} not found.")
            
    for field in update_data:
         if hasattr(db_obj, field):
            setattr(db_obj, field, update_data[field])
            
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    logger.info(f"Updated plan assignment ID {db_obj.id} for user {db_obj.user_id}. New status: {db_obj.status}")
    return db_obj

async def remove_user_plan_by_user(db: AsyncSession, *, user_id: int) -> Optional[billing_models.UserPlan]:
    """Delete a user plan assignment by user ID."""
    db_obj = await get_user_plan_by_user(db=db, user_id=user_id)
    if db_obj:
        logger.warning(f"Deleting plan assignment ID {db_obj.id} for user {user_id}. Current plan: {db_obj.plan_id}")
        await db.delete(db_obj)
        await db.commit()
        logger.info(f"Deleted plan assignment for user ID: {user_id}")
        return db_obj
    logger.warning(f"Attempted to delete non-existent plan assignment for user ID: {user_id}")
    return None 