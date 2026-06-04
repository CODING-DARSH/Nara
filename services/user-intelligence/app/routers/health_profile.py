from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_neon_db
from app.dependencies.auth import CurrentUserId
from app.models.intelligence import UserHealthProfile
from app.schemas.intelligence import (
    HealthProfileCreate,
    HealthProfileUpdate,
    HealthProfileResponse,
    MessageResponse,
)

router = APIRouter(prefix="/v1/health-profile", tags=["health-profile"])


@router.post("", response_model=HealthProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_health_profile(
    body: HealthProfileCreate,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """
    Create health profile for the user.
    Deactivates any existing active profile (versioning).
    """
    # Deactivate existing active profile
    result = await db.execute(
        select(UserHealthProfile).where(
            UserHealthProfile.user_id == current_user_id,
            UserHealthProfile.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()
    new_version = 1

    if existing:
        existing.is_active = False
        new_version = existing.version + 1
        await db.flush()

    profile = UserHealthProfile(
        user_id=current_user_id,
        version=new_version,
        declared_conditions=body.declared_conditions,
        dietary_restrictions=body.dietary_restrictions,
        nutritional_goals=body.nutritional_goals,
        allergies=body.allergies,
        cuisine_preferences=body.cuisine_preferences,
        budget_preferences=body.budget_preferences,
        activity_level=body.activity_level,
        age=body.age,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        gender=body.gender,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("", response_model=HealthProfileResponse)
async def get_health_profile(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """Get the currently active health profile."""
    result = await db.execute(
        select(UserHealthProfile).where(
            UserHealthProfile.user_id == current_user_id,
            UserHealthProfile.is_active == True,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No health profile found. Create one first.",
        )
    return profile


@router.put("", response_model=HealthProfileResponse)
async def update_health_profile(
    body: HealthProfileUpdate,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """
    Update health profile — creates a new version.
    Old profile kept for audit trail.
    """
    result = await db.execute(
        select(UserHealthProfile).where(
            UserHealthProfile.user_id == current_user_id,
            UserHealthProfile.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()
    new_version = (existing.version + 1) if existing else 1

    if existing:
        existing.is_active = False
        await db.flush()

    profile = UserHealthProfile(
        user_id=current_user_id,
        version=new_version,
        declared_conditions=body.declared_conditions,
        dietary_restrictions=body.dietary_restrictions,
        nutritional_goals=body.nutritional_goals,
        allergies=body.allergies,
        cuisine_preferences=body.cuisine_preferences,
        budget_preferences=body.budget_preferences,
        activity_level=body.activity_level,
        age=body.age,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        gender=body.gender,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("", response_model=MessageResponse)
async def delete_health_profile(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """Soft delete — deactivates profile, keeps data."""
    result = await db.execute(
        select(UserHealthProfile).where(
            UserHealthProfile.user_id == current_user_id,
            UserHealthProfile.is_active == True,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No active health profile found")

    profile.is_active = False
    await db.commit()
    return MessageResponse(message="Health profile deactivated")


@router.get("/history", response_model=list[HealthProfileResponse])
async def get_profile_history(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """Get all historical versions of health profile."""
    result = await db.execute(
        select(UserHealthProfile)
        .where(UserHealthProfile.user_id == current_user_id)
        .order_by(UserHealthProfile.version.desc())
    )
    profiles = result.scalars().all()
    return profiles
