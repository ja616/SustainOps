"""
Sustainability MCP Server — backed by real PostgreSQL database.
Tools: calculate_sustainability_score, estimate_transport_impact, estimate_scope3_proxy
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

mcp = FastMCP("SustainabilityMCP")

_engine = None
_factory = None

def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _factory = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    return _factory


@mcp.tool()
async def calculate_sustainability_score(supplier_name: str) -> dict:
    """Calculate sustainability score (0-100) and rating for a supplier from the database."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.certifications))
            .where(Supplier.name.ilike(f"%{supplier_name}%"))
        )
        supplier = result.scalars().first()
        if not supplier:
            return {"error": f"Supplier '{supplier_name}' not found", "score": 0}
        score = supplier.base_sustainability_score or 0.0
        certs = [c.name for c in supplier.certifications]
        rating = "Excellent" if score >= 80 else ("Good" if score >= 60 else ("Fair" if score >= 40 else "Poor"))
        return {
            "supplier": supplier.name,
            "score": score,
            "rating": rating,
            "certifications": certs,
            "iso14001_certified": "ISO 14001" in certs,
        }


@mcp.tool()
async def estimate_transport_impact(source_location: str, dest_location: str = "United States", weight_kg: float = 1000.0) -> dict:
    """Estimate transport emissions in kg CO2e based on source country and shipment weight."""
    source_lower = source_location.lower()
    if any(x in source_lower for x in ["china", "korea", "japan"]):
        base_emissions = 0.52  # kg CO2e per kg per shipment
        complexity = "High"
        notes = "Long ocean/air freight across Pacific"
    elif any(x in source_lower for x in ["india", "bangladesh", "vietnam"]):
        base_emissions = 0.43
        complexity = "Medium"
        notes = "Optimized sea route, lower geopolitical exposure"
    elif any(x in source_lower for x in ["mexico", "canada"]):
        base_emissions = 0.12
        complexity = "Low"
        notes = "Near-shore, road/rail primary transport"
    else:
        base_emissions = 0.30
        complexity = "Medium"
        notes = "Standard international freight"
    total_emissions = round(base_emissions * weight_kg, 1)
    return {
        "source": source_location,
        "destination": dest_location,
        "weight_kg": weight_kg,
        "emissions_kg_co2e": total_emissions,
        "emissions_per_kg": base_emissions,
        "logistics_complexity": complexity,
        "notes": notes,
    }


@mcp.tool()
async def estimate_scope3_proxy(supplier_name: str) -> dict:
    """Estimate scope 3 emissions proxy for a supplier based on their sustainability score and location."""
    factory = _get_factory()
    async with factory() as session:
        result = await session.execute(
            select(Supplier).where(Supplier.name.ilike(f"%{supplier_name}%"))
        )
        supplier = result.scalars().first()
        if not supplier:
            return {"supplier": supplier_name, "scope3_proxy_kg": None, "confidence": "Low", "error": "Not found"}
        # Inverse relationship: higher sustainability score → lower scope3 emissions
        score = supplier.base_sustainability_score or 50.0
        proxy = round(2000 * (1 - score / 100), 1)
        confidence = "High" if score > 70 else ("Medium" if score > 40 else "Low")
        return {
            "supplier": supplier.name,
            "scope3_proxy_kg": proxy,
            "basis": f"Sustainability score: {score}/100",
            "confidence": confidence,
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
