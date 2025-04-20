import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

# Import shared models and schemas
from shared_models import billing_models, schemas, models

# Database and Auth dependencies
from shared_models.database import get_db
from app.core.auth import get_current_user
# Import CRUD functions
from app.crud import crud_plan, crud_user_plan, crud_referral

logger = logging.getLogger("admin_api.routes.billing")

router = APIRouter()

# --- Plan Endpoints --- 

@router.post("/plans", response_model=schemas.PlanResponse, status_code=status.HTTP_201_CREATED, tags=["Billing - Plans"])
async def create_plan(plan: schemas.PlanCreate, db: AsyncSession = Depends(get_db)):
    try:
        created_plan = await crud_plan.create_plan_with_limits(db=db, obj_in=plan)
        return created_plan
    except ValueError as e:
        logger.warning(f"Failed to create plan '{plan.name}': {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating plan '{plan.name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/plans", response_model=List[schemas.PlanResponse], tags=["Billing - Plans"])
async def read_plans(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    plans = await crud_plan.get_multi_plan(db, skip=skip, limit=limit)
    return plans

@router.get("/plans/{plan_id}", response_model=schemas.PlanResponse, tags=["Billing - Plans"])
async def read_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    db_plan = await crud_plan.get_plan(db=db, plan_id=plan_id)
    if db_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return db_plan

@router.put("/plans/{plan_id}", response_model=schemas.PlanResponse, tags=["Billing - Plans"])
async def update_plan(plan_id: int, plan_in: schemas.PlanUpdate, db: AsyncSession = Depends(get_db)):
    db_plan = await crud_plan.get_plan(db=db, plan_id=plan_id)
    if db_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    try:
        updated_plan = await crud_plan.update_plan(db=db, db_obj=db_plan, obj_in=plan_in)
        return updated_plan
    except ValueError as e: # Handles potential name conflict
        logger.warning(f"Failed to update plan ID {plan_id}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating plan ID {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Billing - Plans"])
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    try:
        deleted_plan = await crud_plan.remove_plan(db=db, plan_id=plan_id)
        if deleted_plan is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e: # Handles potential check failure (e.g., users assigned)
        logger.warning(f"Failed to delete plan ID {plan_id}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting plan ID {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- UserPlan Endpoints --- 

@router.post("/users/{user_id}/plan", response_model=schemas.UserPlanResponse, status_code=status.HTTP_201_CREATED, tags=["Billing - User Plans"])
async def assign_plan_to_user(user_id: int, user_plan: schemas.UserPlanCreate, db: AsyncSession = Depends(get_db)):
    if user_plan.user_id != user_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID mismatch in path and body")
    try:
        assigned_plan = await crud_user_plan.assign_or_update_user_plan(db=db, user_id=user_id, obj_in=user_plan)
        # Need to fetch the plan details for the response if not loaded by default
        assigned_plan = await crud_user_plan.get_user_plan_by_user(db=db, user_id=user_id)
        return assigned_plan
    except ValueError as e:
        # Handles user not found or plan not found errors from CRUD
        logger.warning(f"Failed to assign plan {user_plan.plan_id} to user {user_id}: {e}")
        # Determine appropriate status code based on error (e.g., 404 if user/plan not found)
        status_code = status.HTTP_404_NOT_FOUND if ("not found" in str(e).lower()) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error assigning plan {user_plan.plan_id} to user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/users/{user_id}/plan", response_model=schemas.UserPlanResponse, tags=["Billing - User Plans"])
async def read_user_plan(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user_plan = await crud_user_plan.get_user_plan_by_user(db=db, user_id=user_id)
    if db_user_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User plan assignment not found")
    return db_user_plan

@router.put("/users/{user_id}/plan", response_model=schemas.UserPlanResponse, tags=["Billing - User Plans"])
async def update_user_plan_assignment(user_id: int, user_plan_in: schemas.UserPlanUpdate, db: AsyncSession = Depends(get_db)):
    db_user_plan = await crud_user_plan.get_user_plan_by_user(db=db, user_id=user_id)
    if db_user_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User plan assignment not found")
    try:
        updated_assignment = await crud_user_plan.update_user_plan_assignment(
            db=db, db_obj=db_user_plan, obj_in=user_plan_in
        )
        # Re-fetch to ensure plan details are loaded if needed by response model
        updated_assignment = await crud_user_plan.get_user_plan_by_user(db=db, user_id=user_id)
        return updated_assignment
    except ValueError as e:
        logger.warning(f"Failed to update plan for user {user_id}: {e}")
        status_code = status.HTTP_404_NOT_FOUND if ("not found" in str(e).lower()) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating plan for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/users/{user_id}/plan", status_code=status.HTTP_204_NO_CONTENT, tags=["Billing - User Plans"])
async def remove_user_plan_assignment(user_id: int, db: AsyncSession = Depends(get_db)):
    deleted_assignment = await crud_user_plan.remove_user_plan_by_user(db=db, user_id=user_id)
    if deleted_assignment is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User plan assignment not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Internal Referral Logging Endpoint --- 

@router.post(
    "/internal/log_referral", 
    status_code=status.HTTP_204_NO_CONTENT, 
    tags=["Billing - Internal"],
    summary="Log Referral/UTM Data (Internal)",
    description="Internal endpoint called by the frontend to log UTM parameters and referer for a user."
)
async def log_referral_data(
    request: Request, 
    referral_data: schemas.InternalReferralLogRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # Auth handled here
):
    """
    Logs UTM and referral information for the authenticated user.
    Requires standard user authentication, not admin token.
    """
    try:
        await crud_referral.create_referral_data(db=db, user=current_user, obj_in=referral_data)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e: # Should not happen if current_user is valid
        logger.error(f"ValueError logging referral data for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error logging referral data for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Placeholder for Future Billing/Internal Endpoints ---
# @router.get("/internal/check_limits", ...)
# @router.get("/usage/quote", ...) 