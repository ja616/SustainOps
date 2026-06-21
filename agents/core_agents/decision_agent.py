"""
Decision Agent — primary orchestrator for SustainIQ.

Uses the real Strands Agents SDK (strands-agents on PyPI).
Model: amazon.nova-lite-v1:0 via AWS Bedrock Converse API.

Tools are registered via @tool decorator (see tools.py) so Strands can
discover and call them during the ReAct loop.
"""
import sys
import os
import json

# Ensure backend is importable from agents/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from strands import Agent
from strands.models import BedrockModel

from core_agents.discovery_agent import get_discovery_agent
from core_agents.evaluation_agent import get_evaluation_agent
from strands import tool


SYSTEM_PROMPT_TEMPLATE = """You are SustainIQ's Decision Orchestrator Agent.

Your purpose: Answer "What should we do next?" for enterprise procurement teams by orchestrating sub-agents.

You operate in two modes based on the presence of Uploaded Vendor Data:

--- MODE 1: UPLOADED VENDOR DATA AVAILABLE ---
If Uploaded Vendor Data is provided, you MUST:
1. Use `run_evaluation` to assess the uploaded suppliers against the MCP databases (Sustainability, Risk, etc).
2. Synthesize the evaluations into a final recommendation.
3. Clearly indicate "Based primarily on uploaded supplier quotations" in your reasoning.

--- MODE 2: NO VENDOR DATA PROVIDED ---
If no Uploaded Vendor Data is provided, you MUST:
1. First, use `run_discovery` to find SPECIFIC manufacturers, brands, or wholesale companies (NOT generic marketplaces).
2. Second, use `run_evaluation` to assess the specific discovered suppliers.
3. You MUST find and evaluate AT LEAST 3 candidate suppliers to compare side-by-side.
4. Validate geographic claims before presenting them.
5. Every sustainability claim must be linked to an actual evidence link (URL).
6. Estimate costs based on available online data or proxies.

--- SUB-AGENTS AVAILABLE (TOOLS) ---
- run_discovery: Deep web research to find exact manufacturers, links, and material sustainability.
- run_evaluation: Database risk and sustainability assessment.

--- OUTPUT REQUIREMENT ---
You must calculate integer scores (0-100) for Cost, Delivery, Risk, Sustainability, and Location based on the 
supplier's performance AND the weights you infer from the User's query.
Calculate a final weighted `decision_score` (0-100) for each candidate.

CRITICAL DECISION INTELLIGENCE RULES:
1. COST MATH: You MUST explicitly compute "Unit Price × Quantity + Shipping = Total Cost". If a budget is provided, compare the Total Cost to the budget and declare the delta. Do NOT just summarize costs.
2. LOCATION SCORING: You MUST explicitly parse any geographic constraints (e.g. "South India"). Penalize suppliers outside this bounds heavily in their `location_score`.
3. SUSTAINABILITY: You MUST base the `sustainability_score` strictly on verifiable metrics: ISO 14001 certification, use of recycled materials, local manufacturing, or CSR disclosures.
4. DELIVERY RISK: You MUST calculate `risk_score` based on lead time predictability, logistics complexity, and location advantage.

Your `reasoning` field MUST NOT be a simple LLM summary. It MUST be a highly structured Markdown Procurement Analyst Report that explicitly answers:
### Why was this supplier chosen?
### What alternatives were considered?
### What tradeoffs exist?
### What evidence supports the decision?
### Approximated Total Cost & Tradeoff Summary

CRITICAL JSON RULE: Do NOT use literal newlines inside your JSON strings. Use EXACTLY `\n` to represent line breaks in the `reasoning` field.

Your final answer MUST be valid JSON with these exact keys:
{{
  "alternative": "EXACT Name of the 1 recommended specific supplier",
  "current_supplier": "Name of current/existing supplier mentioned (or None)",
  "decision_score": 87,
  "cost_score": 82,
  "delivery_score": 94,
  "risk_score": 89,
  "sustainability_score": 83,
  "location_score": 95,
  "reasoning": "### Why was this supplier chosen?\\n...\\n### What alternatives were considered?\\n...\\n### What tradeoffs exist?\\n...\\n### What evidence supports the decision?\\n...\\n### Approximated Total Cost & Tradeoff Summary\\n...",
  "candidates": [
    {{
      "name": "Supplier A",
      "status": "recommended",
      "cost_score": 85,
      "delivery_score": 90,
      "risk_score": 78,
      "sustainability_score": 88,
      "location_score": 95,
      "final_score": 85,
      "cost_estimation": "200 units × $10/unit = $2,000 Total Cost (Under budget)",
      "reasoning": "Best overall tradeoff given the criteria...",
      "evidence_links": ["https://url-to-sustainability-report"]
    }},
    {{
      "name": "Supplier B",
      "status": "rejected",
      ...
    }}
  ],
  "cost_impact": "e.g. +5% Market Average",
  "risk_impact": "e.g. Lower concentration risk",
  "sustainability_impact": "e.g. +12 points Market Average",
  "evidence": ["fact 1 from data", "fact 2 from data"],
  "sources": ["Uploaded Data", "Risk MCP", "Discovery Agent", ...],
  "confidence": 85
}}

Be direct and data-driven. ONLY attribute sources you actually used.
NEVER output <thinking> tags in your final answer. NEVER ask the user questions. If information is missing, make a recommendation based on what you have.
Your final output MUST be ONLY the raw JSON object starting with {{ and ending with }}. Do NOT wrap it in markdown code blocks.

--- UPLOADED VENDOR DATA ---
{context_data}
"""


def run_agent_with_trace(query: str, context_data: str = "") -> tuple:
    trace = []
    step_counter = {"n": 0}
    seen_tool_ids = set()

    class TraceCapture:
        def __call__(self, **kwargs):
            if kwargs.get("type") == "tool_use_stream" and "current_tool_use" in kwargs:
                current = kwargs["current_tool_use"]
                tool_id = current.get("toolUseId", "")
                if tool_id and tool_id not in seen_tool_ids:
                    seen_tool_ids.add(tool_id)
                    raw_input = current.get("input", {})
                    if isinstance(raw_input, str):
                        try:
                            raw_input = json.loads(raw_input)
                        except Exception:
                            raw_input = {"raw": raw_input}
                    step_counter["n"] += 1
                    trace.append({
                        "step": step_counter["n"],
                        "type": "tool_call",
                        "tool_name": current.get("name", "unknown"),
                        "input": raw_input,
                        "output": None,
                    })
            elif "message" in kwargs:
                msg = kwargs["message"]
                if isinstance(msg, str):
                    try:
                        msg = json.loads(msg)
                    except Exception:
                        msg = {}
                content_blocks = msg.get("content", []) if isinstance(msg, dict) else []
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        inner = block.get("content", "")
                        if isinstance(inner, list):
                            texts = [c.get("text", "") for c in inner if isinstance(c, dict)]
                            result_text = "\n".join(texts)
                        else:
                            result_text = str(inner)
                        for entry in reversed(trace):
                            if entry["type"] == "tool_call" and entry["output"] is None:
                                entry["output"] = result_text
                                break
            elif "result" in kwargs:
                result_text = str(kwargs["result"])
                if result_text.strip() and not result_text.startswith("{"):
                    # Only log intermediate LLM thoughts, not the final JSON block
                    step_counter["n"] += 1
                    trace.append({
                        "step": step_counter["n"],
                        "type": "llm_response",
                        "tool_name": None,
                        "input": None,
                        "output": result_text,
                    })

    trace_capture = TraceCapture()

    @tool
    def run_discovery(query: str) -> str:
        """Run the Discovery Agent to conduct deep web research for specific companies, URLs, and materials."""
        agent = get_discovery_agent()
        agent.callback_handler = trace_capture
        return str(agent(query))

    @tool
    def run_evaluation(suppliers: list) -> str:
        """Run the Evaluation Agent to assess a list of suppliers against MCP databases."""
        agent = get_evaluation_agent()
        agent.callback_handler = trace_capture
        return str(agent(f"Evaluate these suppliers: {suppliers}"))

    def get_decision_agent(context_data: str = "") -> Agent:
        """Return a configured Decision Agent with all tools attached."""
        model = BedrockModel(
            model_id="amazon.nova-lite-v1:0",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            max_tokens=4096,
        )
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT_TEMPLATE.format(context_data=context_data if context_data else "None provided."),
            tools=[run_discovery, run_evaluation],
        )
        return agent

    agent = get_decision_agent(context_data)
    agent.callback_handler = trace_capture

    result = agent(query)
    return str(result), trace
