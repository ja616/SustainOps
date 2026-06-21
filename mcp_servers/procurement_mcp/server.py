"""
Procurement MCP Server — backed by real PostgreSQL database.
Tools: analyze_spend, identify_hotspots, get_top_suppliers_by_sustainability
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.db.models import Supplier, Product, Order
from app.core.config import settings

mcp = FastMCP("ProcurementMCP")

_engine = None
_factory = None

def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _factory = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    return _factory


@mcp.tool()
async def analyze_spend(category: str) -> dict:
    """Analyze historical spend and identify the primary supplier in a given category from the database."""
    factory = _get_factory()
    async with factory() as session:
        # Find suppliers in category
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.risk_profile))
            .where(Supplier.industry.ilike(f"%{category}%"))
            .order_by(Supplier.base_sustainability_score.asc())  # lowest score = highest risk
        )
        suppliers = result.scalars().all()
        if not suppliers:
            return {"category": category, "total_spend_ytd": 0, "primary_supplier": None, "supplier_count": 0}
        # Primary = lowest sustainability score (most at-risk incumbent)
        primary = suppliers[0]
        return {
            "category": category,
            "supplier_count": len(suppliers),
            "primary_supplier": primary.name,
            "primary_supplier_location": primary.location,
            "primary_sustainability_score": primary.base_sustainability_score,
            "note": "Spend data not yet ingested — counts based on supplier records only.",
        }


@mcp.tool()
async def identify_hotspots() -> list:
    """Identify procurement categories with low average sustainability scores — high improvement potential."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(
                Supplier.industry,
                sqlfunc.avg(Supplier.base_sustainability_score).label("avg_score"),
                sqlfunc.count(Supplier.id).label("supplier_count"),
            )
            .where(Supplier.industry.isnot(None))
            .group_by(Supplier.industry)
            .order_by(sqlfunc.avg(Supplier.base_sustainability_score).asc())
        )
        rows = result.all()
        return [
            {
                "category": row.industry,
                "avg_sustainability_score": round(row.avg_score, 1),
                "supplier_count": row.supplier_count,
                "reason": f"Low average sustainability score ({row.avg_score:.0f}/100) across {row.supplier_count} suppliers",
            }
            for row in rows
        ]


@mcp.tool()
async def get_top_suppliers_by_sustainability(category: str, limit: int = 5) -> list:
    """Return the top N most sustainable suppliers in a given category."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.certifications))
            .where(Supplier.industry.ilike(f"%{category}%"))
            .order_by(Supplier.base_sustainability_score.desc())
            .limit(limit)
        )
        suppliers = result.scalars().all()
        return [
            {
                "rank": i + 1,
                "name": s.name,
                "location": s.location,
                "sustainability_score": s.base_sustainability_score,
                "certifications": [c.name for c in s.certifications],
            }
            for i, s in enumerate(suppliers)
        ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
