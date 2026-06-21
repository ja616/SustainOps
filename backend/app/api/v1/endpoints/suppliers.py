"""
FastAPI endpoint for suppliers — list and search the supplier database.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel

from app.api.deps import get_db
from app.db.models import Supplier, RiskProfile

router = APIRouter()


class SupplierSummary(BaseModel):
    id: str
    name: str
    industry: Optional[str]
    location: Optional[str]
    base_sustainability_score: Optional[float]
    concentration_risk: Optional[float]
    certifications: List[str] = []

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SupplierSummary])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    industry: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    limit: int = Query(50, le=200),
):
    """List suppliers with optional filters."""
    query = (
        select(Supplier)
        .options(selectinload(Supplier.certifications), selectinload(Supplier.risk_profile))
        .limit(limit)
    )
    if industry:
        query = query.where(Supplier.industry.ilike(f"%{industry}%"))
    if min_score is not None:
        query = query.where(Supplier.base_sustainability_score >= min_score)
    query = query.order_by(Supplier.base_sustainability_score.desc())

    result = await db.execute(query)
    suppliers = result.scalars().all()

    return [
        SupplierSummary(
            id=str(s.id),
            name=s.name,
            industry=s.industry,
            location=s.location,
            base_sustainability_score=s.base_sustainability_score,
            concentration_risk=s.risk_profile.concentration_risk if s.risk_profile else None,
            certifications=[c.name for c in s.certifications],
        )
        for s in suppliers
    ]
