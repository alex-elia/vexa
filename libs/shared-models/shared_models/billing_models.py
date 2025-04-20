import sqlalchemy # Keep top-level import if needed
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, Float, ForeignKey, Index, UniqueConstraint, Boolean, Numeric
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

# Import Base from the database file
from .database import Base 
# REMOVE User import to break cycle
# from .models import User # Keep User import if needed for FK relationship

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    max_concurrent_bots = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    model_limits = relationship("PlanModelLimit", back_populates="plan", cascade="all, delete-orphan")
    user_assignments = relationship("UserPlan", back_populates="plan")

class PlanModelLimit(Base):
    __tablename__ = "plan_model_limits"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    model_identifier = Column(String(100), nullable=False, index=True) # e.g., "faster-whisper-medium"
    monthly_included_hours = Column(Integer, nullable=True) # Null means unlimited for this model
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan = relationship("Plan", back_populates="model_limits")

    __table_args__ = (UniqueConstraint('plan_id', 'model_identifier', name='_plan_model_uc'),)

class UserPlan(Base):
    __tablename__ = "user_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True) # Use string reference
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    billing_cycle_anchor = Column(DateTime(timezone=True), nullable=False, server_default=func.now()) # When the cycle renews
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True) # When the plan assignment ends
    status = Column(String(50), nullable=False, default='active') # e.g., active, cancelled, pending
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User") # SQLAlchemy resolves this based on ForeignKey
    plan = relationship("Plan", back_populates="user_assignments")

class ReferralData(Base):
    __tablename__ = "referral_data"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) # Use string reference
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)
    referer_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User") # SQLAlchemy resolves this based on ForeignKey