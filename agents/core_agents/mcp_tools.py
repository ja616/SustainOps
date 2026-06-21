import os
import sys
import json
import asyncio
from strands import tool

MCP_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mcp_servers"))

async def call_mcp_server(server_dir: str, tool_name: str, args: dict):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    
    server_path = os.path.join(MCP_BASE, server_dir, "server.py")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_path],
        env=os.environ.copy()
    )
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=args)
                texts = [c.text for c in result.content if c.type == "text"]
                return texts[0] if texts else "{}"
    except Exception as e:
        return json.dumps({"error": f"MCP Error in {server_dir}/{tool_name}: {str(e)}"})

# ── Supplier MCP Tools ──────────────────────────────────────────────────────

@tool
async def get_supplier_profile(supplier_name: str) -> str:
    """Get the full profile of a supplier from the Supplier MCP database including location and sustainability score."""
    return await call_mcp_server("supplier_mcp", "get_supplier_profile", {"supplier_name": supplier_name})

@tool
async def list_suppliers_by_category(category: str) -> str:
    """List all suppliers in a given industry category ordered by sustainability score from Supplier MCP."""
    return await call_mcp_server("supplier_mcp", "list_suppliers_by_category", {"category": category})

# ── Sustainability MCP Tools ────────────────────────────────────────────────

@tool
async def calculate_sustainability_score(supplier_name: str) -> str:
    """Calculate sustainability score (0-100) and rating for a supplier from Sustainability MCP."""
    return await call_mcp_server("sustainability_mcp", "calculate_sustainability_score", {"supplier_name": supplier_name})

@tool
async def estimate_transport_impact(source_location: str, dest_location: str = "United States") -> str:
    """Estimate transport emissions in kg CO2e based on source country from Sustainability MCP."""
    return await call_mcp_server("sustainability_mcp", "estimate_transport_impact", {
        "source_location": source_location,
        "dest_location": dest_location,
        "weight_kg": 1000.0
    })

# ── Risk MCP Tools ──────────────────────────────────────────────────────────

@tool
async def assess_supplier_risk(supplier_name: str) -> str:
    """Assess concentration, operational, and geopolitical risk for a supplier from Risk MCP."""
    return await call_mcp_server("risk_mcp", "assess_supplier_risk", {"supplier_name": supplier_name})

# ── Web Search / Alternative Discovery Tool ─────────────────────────────────

@tool
def web_search_suppliers(query: str) -> str:
    """Search the web for alternative suppliers, certifications, sustainability ratings, or market information.
    Use this proactively when NO vendor data is uploaded, or to enrich existing data.
    Returns a JSON array of search results with title, snippet, and url fields."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        hits = [{"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")} for r in results]
        return json.dumps(hits)
    except Exception as e:
        return json.dumps([{"error": f"Web search failed: {e}", "title": "", "snippet": "", "url": ""}])

@tool
def read_webpage(url: str) -> str:
    """Read and extract the text content of a specific webpage URL. 
    Use this to scrape specific manufacturer/supplier sites for product details, materials, and sustainability conditions."""
    import urllib.request
    import re
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Basic HTML tag stripping
            text = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
            text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL|re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            # Truncate to first 5000 chars to avoid overwhelming the context window
            return text[:5000]
    except Exception as e:
        return f"Failed to read webpage: {str(e)}"
