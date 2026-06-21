"""
Risk MCP Server — backed by real PostgreSQL database.
Tools: assess_supplier_risk, compare_risk_profiles
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.db.models import Supplier
from app.core.config import settings

mcp = FastMCP("RiskMCP")

_engine = None
_factory = None

def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _factory = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    return _factory


@mcp.tool()
async def assess_supplier_risk(supplier_name: str) -> dict:
    """Assess concentration, operational, and geopolitical risk for a supplier from the database."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.risk_profile))
            .where(Supplier.name.ilike(f"%{supplier_name}%"))
        )
        supplier = result.scalars().first()
        if not supplier:
            return {"error": f"Supplier '{supplier_name}' not found"}
        if not supplier.risk_profile:
            return {"supplier": supplier_name, "error": "No risk profile on record"}
        rp = supplier.risk_profile
        overall = (rp.concentration_risk + rp.operational_risk + rp.geopolitical_risk) / 3
        status = "High" if overall > 0.6 else ("Medium" if overall > 0.35 else "Low")
        return {
            "supplier": supplier.name,
            "concentration_risk": round(rp.concentration_risk, 3),
            "operational_risk": round(rp.operational_risk, 3),
            "geopolitical_risk": round(rp.geopolitical_risk, 3),
            "overall_risk_score": round(overall, 3),
            "overall_status": status,
        }


@mcp.tool()
async def compare_risk_profiles(supplier_1: str, supplier_2: str) -> dict:
    """Compare risk profiles of two suppliers side by side."""
    return {
        "supplier_1": await assess_supplier_risk(supplier_1),
        "supplier_2": await assess_supplier_risk(supplier_2),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
