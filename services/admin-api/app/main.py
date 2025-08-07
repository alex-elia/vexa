import logging
import secrets
import string
import os
import json
import hmac
import hashlib
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Security, Response, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, attributes
from typing import List # Import List for response model
from datetime import datetime # Import datetime
from sqlalchemy import func
from pydantic import BaseModel, HttpUrl

# Import shared models and schemas
from shared_models.models import User, APIToken, Base, Meeting # Import Base for init_db and Meeting
from shared_models.schemas import UserCreate, UserResponse, TokenResponse, UserDetailResponse, UserBase, UserUpdate, MeetingResponse # Import UserBase for update and UserUpdate schema

# Database utilities (needs to be created)
from shared_models.database import get_db, init_db # New import

# Logging configuration
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("admin_api")

# App initialization
app = FastAPI(title="Vexa Admin API")

# --- Pydantic Schemas for new endpoint ---
class WebhookUpdate(BaseModel):
    webhook_url: HttpUrl

class MeetingUserStat(MeetingResponse): # Inherit from MeetingResponse to get meeting fields
    user: UserResponse # Embed UserResponse

class PaginatedMeetingUserStatResponse(BaseModel):
    total: int
    items: List[MeetingUserStat]

# Security - Reuse logic from bot-manager/auth.py for admin token verification
API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key", auto_error=False) # Use a distinct header
USER_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False) # For user-facing endpoints
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN") # Read from environment
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") # Stripe webhook secret

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

async def get_current_user(api_key: str = Security(USER_API_KEY_HEADER), db: AsyncSession = Depends(get_db)) -> User:
    """Dependency to verify user API key and return user object."""
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API Key")

    result = await db.execute(
        select(APIToken).where(APIToken.token == api_key).options(selectinload(APIToken.user))
    )
    db_token = result.scalars().first()

    if not db_token or not db_token.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")
    
    return db_token.user

# Router setup (all routes require admin token verification)
admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_token)]
)

# New router for user-facing actions
user_router = APIRouter(
    prefix="/user",
    tags=["User"],
    dependencies=[Depends(get_current_user)]
)

# --- Helper Functions --- 
def generate_secure_token(length=40):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature."""
    try:
        # Parse the signature header - Stripe signatures can have multiple parts
        # Format: t=timestamp,v1=signature1,v2=signature2,...
        signature_parts = signature.split(',')
        
        # Extract timestamp
        timestamp = None
        received_signature = None
        
        for part in signature_parts:
            if part.startswith('t='):
                timestamp = part.split('=')[1]
            elif part.startswith('v1='):
                received_signature = part.split('=')[1]
        
        if not timestamp or not received_signature:
            logger.error(f"Invalid signature format: {signature}")
            return False
        
        # Create the expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            f"{timestamp}.{payload.decode('utf-8')}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Log signature details for debugging
        logger.info(f"🔍 [Webhook] Signature verification details:")
        logger.info(f"🔍 [Webhook] Timestamp: {timestamp}")
        logger.info(f"🔍 [Webhook] Received signature: {received_signature[:20]}...")
        logger.info(f"🔍 [Webhook] Expected signature: {expected_signature[:20]}...")
        logger.info(f"🔍 [Webhook] Secret used: {secret[:20]}...")
        
        signature_match = hmac.compare_digest(received_signature, expected_signature)
        if not signature_match:
            logger.error(f"❌ [Webhook] Signature mismatch!")
            logger.error(f"❌ [Webhook] Received: {received_signature}")
            logger.error(f"❌ [Webhook] Expected: {expected_signature}")
        
        return signature_match
    except Exception as e:
        logger.error(f"Error verifying Stripe signature: {e}")
        return False

async def update_user_from_subscription(subscription_data: dict, db: AsyncSession):
    """Update user data based on subscription information."""
    try:
        # Extract customer email from subscription
        customer_id = subscription_data.get('customer')
        if not customer_id:
            logger.error("No customer ID in subscription data")
            return
        
        # Debug: Log the full subscription data to see what's available
        logger.info(f"🔍 [Webhook] Full subscription data: {json.dumps(subscription_data, indent=2)}")
        
        # Check if customer email is directly in the subscription data
        customer_email = None
        
        # First, try to get customer email from the subscription data itself
        if 'customer_details' in subscription_data:
            customer_email = subscription_data['customer_details'].get('email')
            logger.info(f"🔍 [Webhook] Found customer email in customer_details: {customer_email}")
        
        # If not found, try to get it from metadata
        if not customer_email and 'metadata' in subscription_data:
            customer_email = subscription_data['metadata'].get('userEmail')
            logger.info(f"🔍 [Webhook] Found customer email in metadata: {customer_email}")
        
        # If still not found, try to get it from the customer object if it's expanded
        if not customer_email and 'customer' in subscription_data and isinstance(subscription_data['customer'], dict):
            customer_email = subscription_data['customer'].get('email')
            logger.info(f"🔍 [Webhook] Found customer email in customer object: {customer_email}")
        
        # If we still don't have an email, use the old fallback method
        if not customer_email:
            logger.info(f"🔍 [Webhook] No email found in webhook data, using fallback for customer {customer_id}")
            # For testing purposes, map test customer IDs to test emails
            customer_email_mapping = {
                'cus_test_bot_limit': 'test@example.com',
                'cus_test_webhook': 'test@example.com',
            }
            
            # Use mapping for test customers, otherwise create a fallback email
            customer_email = customer_email_mapping.get(customer_id, f"{customer_id}@stripe.customer")
            logger.info(f"🔍 [Webhook] Using fallback email: {customer_email}")
        else:
            logger.info(f"🔍 [Webhook] Using customer email from webhook data: {customer_email}")

        # Find or create user
        result = await db.execute(select(User).where(User.email == customer_email))
        user = result.scalars().first()
        
        if not user:
            # Create new user
            user = User(
                email=customer_email,
                name=customer_email.split('@')[0],
                max_concurrent_bots=1
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"Created new user for subscription: {customer_email}")
        
        # Extract subscription information
        subscription_id = subscription_data.get('id')
        status = subscription_data.get('status', 'unknown')
        cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
        current_period_end = subscription_data.get('current_period_end')
        
        # Calculate bot count from subscription items
        items = subscription_data.get('items', {}).get('data', [])
        bot_count = 0
        
        # Handle different subscription statuses and cancellation scenarios
        if status in ['active', 'trialing']:
            # For active subscriptions, use the quantity from items
            if items:
                bot_count = items[0].get('quantity', 0)
            
            # Check if subscription is scheduled to cancel
            if cancel_at_period_end:
                logger.info(f"🔍 [Webhook] Active subscription scheduled to cancel - bot count: {bot_count}")
                logger.info(f"🔍 [Webhook] Subscription will end at: {current_period_end}")
                # Change status to 'scheduled_to_cancel' for active subscriptions that are scheduled to cancel
                status = 'scheduled_to_cancel'
            else:
                logger.info(f"🔍 [Webhook] Active subscription - bot count: {bot_count}")
                
        elif status in ['canceled', 'cancelled', 'incomplete_expired', 'past_due', 'unpaid']:
            # For cancelled/failed subscriptions, set bot count to 0
            bot_count = 0
            logger.info(f"🔍 [Webhook] Cancelled/failed subscription - setting bot count to 0")
        else:
            # For other statuses, try to get quantity but default to 0
            if items:
                bot_count = items[0].get('quantity', 0)
            logger.info(f"🔍 [Webhook] Other subscription status '{status}' - bot count: {bot_count}")
        
        # Update user data consistently for all subscription events
        if user.data is None:
            user.data = {}
        
        # Always update all subscription-related fields
        user.data.update({
            'stripe_subscription_id': subscription_id,
            'subscription_status': status,  # This will be 'scheduled_to_cancel' for active subscriptions scheduled to cancel
            'max_concurrent_bots': bot_count,
            'updated_by_webhook': datetime.utcnow().isoformat(),
        })
        
        # Add cancellation metadata if subscription is scheduled to cancel
        if cancel_at_period_end and subscription_data.get('status') in ['active', 'trialing']:
            user.data.update({
                'subscription_scheduled_to_cancel': True,
                'subscription_cancel_at_period_end': True,
                'subscription_current_period_end': current_period_end,
                'subscription_cancellation_date': datetime.fromtimestamp(current_period_end).isoformat() if current_period_end else None,
            })
            logger.info(f"🔍 [Webhook] Added cancellation metadata for scheduled cancellation")
        else:
            # Clear cancellation metadata if not scheduled to cancel
            user.data.update({
                'subscription_scheduled_to_cancel': False,
                'subscription_cancel_at_period_end': False,
                'subscription_current_period_end': None,
                'subscription_cancellation_date': None,
            })
        
        # Also update the main max_concurrent_bots field
        user.max_concurrent_bots = bot_count
        
        # Flag the data field as modified
        attributes.flag_modified(user, "data")
        
        await db.commit()
        await db.refresh(user)
        
        # Log the update with cancellation context
        if cancel_at_period_end and subscription_data.get('status') in ['active', 'trialing']:
            logger.info(f"✅ Updated user {user.email} with subscription {subscription_id}, status: {status}, bots: {bot_count} (SCHEDULED TO CANCEL)")
        else:
            logger.info(f"✅ Updated user {user.email} with subscription {subscription_id}, status: {status}, bots: {bot_count}")
        
    except Exception as e:
        logger.error(f"Error updating user from subscription: {e}")
        await db.rollback()
        raise

# --- Stripe Webhook Endpoint ---
@app.post("/webhook/stripe",
         summary="Handle Stripe webhook events",
         description="Process Stripe webhook events and update user data accordingly.")
async def handle_stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events."""
    logger.info("🔔 [Webhook] === STRIPE WEBHOOK CALL RECEIVED ===")
    
    try:
        # Get the raw body
        body = await request.body()
        signature = request.headers.get('stripe-signature')
        
        logger.info(f"🔔 [Webhook] Body length: {len(body)}")
        logger.info(f"🔔 [Webhook] Has signature: {bool(signature)}")
        
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("❌ [Webhook] STRIPE_WEBHOOK_SECRET is not configured!")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe webhook secret is not configured."
            )
        
        if not signature:
            logger.error("❌ [Webhook] No stripe-signature header provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No stripe-signature header provided."
            )
        
        # Verify signature
        logger.info("🔔 [Webhook] Verifying webhook signature...")
        if not verify_stripe_signature(body, signature, STRIPE_WEBHOOK_SECRET):
            logger.error("❌ [Webhook] Invalid signature")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature."
            )
        
        logger.info("✅ [Webhook] Signature verified successfully")
        
        # Parse the event
        event_data = json.loads(body.decode('utf-8'))
        event_type = event_data.get('type')
        event_id = event_data.get('id')
        
        logger.info(f"🔔 [Webhook] Event type: {event_type}")
        logger.info(f"🔔 [Webhook] Event ID: {event_id}")
        
        # Handle different event types
        if event_type == 'customer.subscription.updated':
            logger.info("🎯 [Webhook] === SUBSCRIPTION UPDATED EVENT ===")
            subscription = event_data.get('data', {}).get('object', {})
            await update_user_from_subscription(subscription, db)
            
        elif event_type == 'customer.subscription.created':
            logger.info("🎯 [Webhook] === SUBSCRIPTION CREATED EVENT ===")
            subscription = event_data.get('data', {}).get('object', {})
            await update_user_from_subscription(subscription, db)
            
        elif event_type == 'customer.subscription.deleted':
            logger.info("🎯 [Webhook] === SUBSCRIPTION DELETED/CANCELLED EVENT ===")
            subscription = event_data.get('data', {}).get('object', {})
            # Process cancellation event consistently with other events
            # The update_user_from_subscription function will handle the status properly
            await update_user_from_subscription(subscription, db)
            
        elif event_type == 'checkout.session.completed':
            logger.info("🎯 [Webhook] === CHECKOUT SESSION COMPLETED ===")
            session = event_data.get('data', {}).get('object', {})
            # Handle checkout completion if needed
            logger.info(f"Checkout completed for session: {session.get('id')}")
            
        else:
            logger.info(f"🔔 [Webhook] Unhandled event type: {event_type}")
        
        logger.info("✅ [Webhook] Event processed successfully")
        return {"received": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Webhook] Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook Error: {str(e)}"
        )

# --- User Endpoints ---
@user_router.put("/webhook",
             response_model=UserResponse,
             summary="Set user webhook URL",
             description="Set a webhook URL for the authenticated user to receive notifications.")
async def set_user_webhook(
    webhook_update: WebhookUpdate, 
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the webhook_url for the currently authenticated user.
    The URL is stored in the user's 'data' JSONB field.
    """
    if user.data is None:
        user.data = {}
    
    user.data['webhook_url'] = str(webhook_update.webhook_url)

    # Flag the 'data' field as modified for SQLAlchemy to detect the change
    attributes.flag_modified(user, "data")

    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Updated webhook URL for user {user.email}")
    
    return UserResponse.from_orm(user)

# --- Admin Endpoints (Copied and adapted from bot-manager/admin.py) --- 
@admin_router.post("/users",
             response_model=UserResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Find or create a user by email",
             responses={
                 status.HTTP_200_OK: {
                     "description": "User found and returned",
                     "model": UserResponse,
                 },
                 status.HTTP_201_CREATED: {
                     "description": "User created successfully",
                     "model": UserResponse,
                 }
             })
async def create_user(user_in: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()

    if existing_user:
        logger.info(f"Found existing user: {existing_user.email} (ID: {existing_user.id})")
        response.status_code = status.HTTP_200_OK
        return UserResponse.from_orm(existing_user)

    user_data = user_in.dict()
    db_user = User(
        email=user_data['email'],
        name=user_data.get('name'),
        image_url=user_data.get('image_url')
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"Admin created user: {db_user.email} (ID: {db_user.id})")
    return UserResponse.from_orm(db_user)

@admin_router.get("/users", 
            response_model=List[UserResponse], # Use List import
            summary="List all users")
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return [UserResponse.from_orm(u) for u in users]

@admin_router.get("/users/email/{user_email}",
            response_model=UserResponse, # Changed from UserDetailResponse
            summary="Get a specific user by email") # Removed ', including their API tokens'
async def get_user_by_email(user_email: str, db: AsyncSession = Depends(get_db)):
    """Gets a user by their email.""" # Removed ', eagerly loading their API tokens.'
    # Removed .options(selectinload(User.api_tokens))
    result = await db.execute(
        select(User)
        .where(User.email == user_email)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Return the user object. Pydantic will handle serialization using UserDetailResponse.
    return user

@admin_router.get("/users/{user_id}", 
            response_model=UserDetailResponse, # Use the detailed response schema
            summary="Get a specific user by ID, including their API tokens")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Gets a user by their ID, eagerly loading their API tokens."""
    # Eagerly load the api_tokens relationship
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.api_tokens))
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
        
    # Return the user object. Pydantic will handle serialization using UserDetailResponse.
    return user

@admin_router.patch("/users/{user_id}",
             response_model=UserResponse,
             summary="Update user details",
             description="Update user's name, image URL, max concurrent bots, or data.")
async def update_user(user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    """
    Updates specific fields of a user.
    Only provide the fields you want to change in the request body.
    Requires admin privileges.
    """
    print(f"=== ADMIN PATCH USER {user_id} CALLED ===")
    
    # Fetch the user to update
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalars().first()

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get the update data, excluding unset fields to only update provided values
    update_data = user_update.dict(exclude_unset=True)
    print(f"=== Raw update_data: {update_data} ===")
    logger.info(f"Admin PATCH for user {user_id}. Raw update_data: {update_data}")

    # Prevent changing email via this endpoint (if desired)
    if 'email' in update_data and update_data['email'] != db_user.email:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change user email via this endpoint.")
    elif 'email' in update_data:
         del update_data['email'] # Don't attempt to update email to the same value

    # Handle data field specially for JSONB
    updated = False
    if 'data' in update_data:
        new_data = update_data.pop('data')  # Remove from update_data to handle separately
        if new_data is not None:
            logger.info(f"Admin updating data field for user ID: {user_id}. Current: {db_user.data}, New: {new_data}")
            
            # Replace the data field entirely (rather than merging)
            db_user.data = new_data
            
            # Flag the 'data' field as modified for SQLAlchemy to detect the change
            attributes.flag_modified(db_user, "data")
            updated = True
            logger.info(f"Admin updated data field for user ID: {user_id}")
    else:
        logger.info(f"Admin PATCH for user {user_id}: 'data' not in update_data keys: {list(update_data.keys())}")

    # Update the remaining user object attributes
    for key, value in update_data.items():
        if hasattr(db_user, key) and getattr(db_user, key) != value:
            setattr(db_user, key, value)
            updated = True
            logger.info(f"Admin updated {key} for user ID: {user_id}")

    logger.info(f"Admin update for user ID: {user_id}, updated: {updated}")

    # If any changes were made, commit them
    if updated:
        try:
            await db.commit()
            await db.refresh(db_user)
            logger.info(f"Admin updated user ID: {user_id}")
        except Exception as e: # Catch potential DB errors (e.g., constraints)
            await db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user.")
    else:
        logger.info(f"Admin attempted update for user ID: {user_id}, but no changes detected.")

    return UserResponse.from_orm(db_user)

@admin_router.post("/users/{user_id}/tokens", 
             response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Generate a new API token for a user")
async def create_token_for_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    token_value = generate_secure_token()
    # Use the APIToken model from shared_models
    db_token = APIToken(token=token_value, user_id=user_id)
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    logger.info(f"Admin created token for user {user_id} ({user.email})")
    # Use TokenResponse for consistency with schema definition (datetime object)
    return TokenResponse.from_orm(db_token)

@admin_router.delete("/tokens/{token_id}", 
                status_code=status.HTTP_204_NO_CONTENT,
                summary="Revoke/Delete an API token by its ID")
async def delete_token(token_id: int, db: AsyncSession = Depends(get_db)):
    """Deletes an API token by its database ID."""
    # Fetch the token by its primary key ID
    db_token = await db.get(APIToken, token_id)
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Token not found"
        )
        
    # Delete the token
    await db.delete(db_token)
    await db.commit()
    logger.info(f"Admin deleted token ID: {token_id}")
    # No body needed for 204 response
    return 

# --- Usage Stats Endpoints ---
@admin_router.get("/stats/meetings-users",
            response_model=PaginatedMeetingUserStatResponse,
            summary="Get paginated list of meetings joined with users")
async def list_meetings_with_users(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a paginated list of all meetings, with user details embedded.
    This provides a comprehensive overview for administrators.
    """
    # First, get the total count of meetings for pagination headers
    count_result = await db.execute(select(func.count(Meeting.id)))
    total = count_result.scalar_one()

    # Then, fetch the paginated list of meetings, joining with users
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.user))
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    meetings = result.scalars().all()

    # Now, construct the response using Pydantic models
    response_items = [
        MeetingUserStat(
            **meeting.__dict__,
            user=UserResponse.from_orm(meeting.user)
        )
        for meeting in meetings if meeting.user
    ]
        
    return PaginatedMeetingUserStatResponse(total=total, items=response_items)

# App events
@app.on_event("startup")
async def startup_event():
    logger.info("Admin API starting up. Skipping automatic DB initialization.")
    # The 'migrate-or-init' Makefile target is now responsible for all DB setup.
    # await init_db()
    pass

# Include the admin router
app.include_router(admin_router)
app.include_router(user_router)

# Root endpoint (optional)
@app.get("/")
async def root():
    return {"message": "Vexa Admin API"}
