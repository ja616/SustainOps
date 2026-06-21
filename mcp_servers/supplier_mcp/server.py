"""
Supplier MCP Server — backed by real PostgreSQL database.
Tools: get_supplier_profile, get_supplier_certifications, list_suppliers_by_category, compare_suppliers
"""
import sys
import os
import asyncio
import json

# Allow importing backend app models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.db.models import Supplier, Certification
from app.core.config import settings

mcp = FastMCP("SupplierMCP")

_engine = None
_factory = None

def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _factory = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    return _factory


@mcp.tool()
async def get_supplier_profile(supplier_name: str) -> dict:
    """Get the full profile of a supplier from the database including location and sustainability score."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.certifications), selectinload(Supplier.risk_profile))
            .where(Supplier.name.ilike(f"%{supplier_name}%"))
        )
        supplier = result.scalars().first()
        if not supplier:
            return {"error": f"Supplier '{supplier_name}' not found"}
        return {
            "name": supplier.name,
            "industry": supplier.industry,
            "location": supplier.location,
            "base_sustainability_score": supplier.base_sustainability_score,
            "certifications": [c.name for c in supplier.certifications],
        }


@mcp.tool()
async def get_supplier_certifications(supplier_name: str) -> list:
    """Get the active certifications of a supplier from the database."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.certifications))
            .where(Supplier.name.ilike(f"%{supplier_name}%"))
        )
        supplier = result.scalars().first()
        if not supplier:
            return []
        return [
            {"name": c.name, "valid_until": c.valid_until.isoformat() if c.valid_until else None}
            for c in supplier.certifications
        ]


@mcp.tool()
async def list_suppliers_by_category(category: str) -> list:
    """List all suppliers in a given industry category ordered by sustainability score."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.risk_profile))
            .where(Supplier.industry.ilike(f"%{category}%"))
            .order_by(Supplier.base_sustainability_score.desc())
        )
        suppliers = result.scalars().all()
        return [
            {
                "name": s.name,
                "location": s.location,
                "sustainability_score": s.base_sustainability_score,
                "concentration_risk": s.risk_profile.concentration_risk if s.risk_profile else None,
            }
            for s in suppliers
        ]


@mcp.tool()
async def compare_suppliers(supplier_1: str, supplier_2: str) -> dict:
    """Compare two suppliers' profiles side by side from the database."""
    return {
        "supplier_1": await get_supplier_profile(supplier_1),
        "supplier_2": await get_supplier_profile(supplier_2),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
