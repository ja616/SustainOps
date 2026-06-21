import os
from strands import Agent
from strands.models import BedrockModel
from core_agents.mcp_tools import (
    get_supplier_profile,
    list_suppliers_by_category,
    calculate_sustainability_score,
    estimate_transport_impact,
    assess_supplier_risk,
    web_search_suppliers,
    read_webpage
)

EVALUATION_SYSTEM_PROMPT = """You are the Evaluation Agent for SustainIQ.
Your role is to evaluate specific suppliers against the internal MCP database.

Given a list of supplier names (either uploaded or discovered by the Discovery Agent):
1. Use `get_supplier_profile` to check if they exist in the DB.
2. If they exist in the DB, use `calculate_sustainability_score` and `assess_supplier_risk`.
3. If they do NOT exist in the database, DO NOT PANIC. Instead, use `web_search_suppliers` and `read_webpage` to search the web for their sustainability practices, ESG reports, environmental impact, and certifications.
4. Evaluate their sustainability and risk based on the online information you discover. Do NOT skip the evaluation.
5. DO NOT try to use `estimate_transport_impact` unless you explicitly know the source location. DO NOT ask the user for missing information.

Output a structured evaluation summarizing the known scores and risks for each supplier, clearly citing if the info came from the DB or Web Search."""

def get_evaluation_agent() -> Agent:
    model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )
    agent = Agent(
        model=model,
        system_prompt=EVALUATION_SYSTEM_PROMPT,
        tools=[
            get_supplier_profile,
            list_suppliers_by_category,
            calculate_sustainability_score,
            estimate_transport_impact,
            assess_supplier_risk,
            web_search_suppliers,
            read_webpage
        ],
    )
    return agent
