import logging
from typing import List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from shared_models import billing_models, schemas

logger = logging.getLogger("admin_api.crud.plan")

async def get_plan(db: AsyncSession, plan_id: int) -> Optional[billing_models.Plan]:
    """Get a single plan by ID, including its model limits."""
    result = await db.execute(
        select(billing_models.Plan)
        .options(selectinload(billing_models.Plan.model_limits))
        .where(billing_models.Plan.id == plan_id)
    )
    return result.scalars().first()

async def get_plan_by_name(db: AsyncSession, name: str) -> Optional[billing_models.Plan]:
    """Get a single plan by name."""
    result = await db.execute(
        select(billing_models.Plan).where(billing_models.Plan.name == name)
    )
    return result.scalars().first()

async def get_multi_plan(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Type[billing_models.Plan]]:
    """Get multiple plans with pagination, including model limits."""
    result = await db.execute(
        select(billing_models.Plan)
        .options(selectinload(billing_models.Plan.model_limits))
        .offset(skip)
        .limit(limit)
        .order_by(billing_models.Plan.id)
    )
    return result.scalars().all()

async def create_plan_with_limits(db: AsyncSession, *, obj_in: schemas.PlanCreate) -> billing_models.Plan:
    """Create a new plan and its associated model limits."""
    # Check if plan name already exists
    existing_plan = await get_plan_by_name(db, name=obj_in.name)
    if existing_plan:
        logger.warning(f"Attempted to create plan with duplicate name: {obj_in.name}")
        # Consider raising a specific exception here for the route handler
        raise ValueError(f"Plan name '{obj_in.name}' already exists.")
        
    # Create Plan object (without limits first)
    plan_data = obj_in.dict(exclude={'model_limits'})
    db_plan = billing_models.Plan(**plan_data)
    db.add(db_plan)
    await db.flush() # Flush to get the db_plan.id for foreign keys

    # Create PlanModelLimit objects
    if obj_in.model_limits:
        for limit_in in obj_in.model_limits:
            db_limit = billing_models.PlanModelLimit(
                **limit_in.dict(), 
                plan_id=db_plan.id
            )
            db.add(db_limit)
            
    await db.commit()
    await db.refresh(db_plan, attribute_names=['model_limits']) # Refresh to load limits
    logger.info(f"Created plan '{db_plan.name}' (ID: {db_plan.id}) with {len(db_plan.model_limits)} limits.")
    return db_plan

async def update_plan(
    db: AsyncSession, 
    *, 
    db_obj: billing_models.Plan, 
    obj_in: schemas.PlanUpdate
) -> billing_models.Plan:
    """Update an existing plan. Model limits are NOT handled here (simplification)."""
    # Update standard fields
    update_data = obj_in.dict(exclude_unset=True)
    
    # Check for name conflict if name is being changed
    if "name" in update_data and update_data["name"] != db_obj.name:
        existing_plan = await get_plan_by_name(db, name=update_data["name"])
        if existing_plan and existing_plan.id != db_obj.id:
            logger.warning(f"Attempted to update plan ID {db_obj.id} with duplicate name: {update_data['name']}")
            raise ValueError(f"Plan name '{update_data['name']}' already exists.")
            
    for field in update_data:
        if hasattr(db_obj, field):
            setattr(db_obj, field, update_data[field])
            
    # Note: This simple update doesn't handle adding/removing/updating model_limits.
    # A more complex implementation would be needed for that (e.g., delete existing limits, add new ones).
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    logger.info(f"Updated plan '{db_obj.name}' (ID: {db_obj.id}).")
    return db_obj

async def remove_plan(db: AsyncSession, *, plan_id: int) -> Optional[billing_models.Plan]:
    """Delete a plan by ID. Cascading delete handles limits."""
    result = await db.execute(
        select(billing_models.Plan).where(billing_models.Plan.id == plan_id)
    )
    db_obj = result.scalars().first()
    if db_obj:
        logger.warning(f"Deleting plan '{db_obj.name}' (ID: {plan_id}). Ensure no users are assigned.")
        # Add check here: Ensure no UserPlan records reference this plan_id before deleting?
        # user_assignments = await db.execute(select(billing_models.UserPlan).where(billing_models.UserPlan.plan_id == plan_id))
        # if user_assignments.scalars().first():
        #     raise ValueError(f"Cannot delete plan ID {plan_id} as it is still assigned to users.")
            
        await db.delete(db_obj)
        await db.commit()
        logger.info(f"Deleted plan ID: {plan_id}")
        return db_obj
    logger.warning(f"Attempted to delete non-existent plan ID: {plan_id}")
    return None 