import os
from strands import Agent
from strands.models import BedrockModel
from core_agents.mcp_tools import web_search_suppliers, read_webpage

DISCOVERY_SYSTEM_PROMPT = """You are the Discovery Agent for SustainIQ.
Your ONLY role is to conduct deep-dive web research to identify SPECIFIC manufacturers, brands, or wholesale suppliers for a given query.

Rules:
1. NEVER recommend generic marketplaces (e.g., "Amazon Business", "Flipkart", "IndiaMART"). You MUST find specific companies.
2. If you find a marketplace, you must search *within* the results or do further searches to find specific vendors selling the product.
3. Use `web_search_suppliers` to find URLs, and then use `read_webpage` to scrape the supplier's actual website.
4. Extract the exact company name, product links, material details, and sustainability conditions.
5. Provide a summary of the 2-3 best specific suppliers found, including their URLs and any sustainability info.

Output your findings clearly."""

def get_discovery_agent() -> Agent:
    model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )
    agent = Agent(
        model=model,
        system_prompt=DISCOVERY_SYSTEM_PROMPT,
        tools=[web_search_suppliers, read_webpage],
    )
    return agent
