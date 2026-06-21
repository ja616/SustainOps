"""
FastAPI endpoints for agent queries and recommendation lifecycle.

Routes:
  POST /api/v1/agents/query         → run Decision Agent, persist recommendation
  PATCH /api/v1/agents/{id}/approve → approve a recommendation
  PATCH /api/v1/agents/{id}/reject  → reject a recommendation
"""
import json
import re
import sys
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Make agents/ importable from the backend's Python path
sys.path.insert(0, "/agents")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'agents'))

from app.api.deps import get_db
from app.db.models import Recommendation

router = APIRouter()


# ── Request / Response schemas ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)


class TraceStep(BaseModel):
    step: int
    type: str           # "tool_call" | "tool_result" | "llm_response"
    tool_name: Optional[str] = None
    input: Optional[dict] = None
    output: Optional[str] = None


class Candidate(BaseModel):
    name: str
    status: str  # "recommended" | "rejected"
    cost_score: Optional[int] = None
    delivery_score: Optional[int] = None
    risk_score: Optional[int] = None
    sustainability_score: Optional[int] = None
    location_score: Optional[int] = None
    final_score: Optional[int] = None
    cost_estimation: Optional[str] = None
    reasoning: str
    evidence_links: List[str] = []


class RecommendationResponse(BaseModel):
    id: str
    query: str
    alternative: str
    current_supplier: str
    reasoning: str
    cost_impact: str
    risk_impact: str
    sustainability_impact: str
    decision_score: Optional[int] = None
    cost_score: Optional[int] = None
    delivery_score: Optional[int] = None
    risk_score: Optional[int] = None
    sustainability_score: Optional[int] = None
    location_score: Optional[int] = None
    candidates: List[Candidate] = []
    evidence: List[str]
    sources: List[str]
    confidence: int
    status: str
    agent_trace: List[TraceStep] = []


class RecommendationSummary(BaseModel):
    id: str
    query: str
    alternative: str
    current_supplier: str
    status: str
    confidence: int
    sustainability_impact: str
    created_at: Optional[str]
    decided_at: Optional[str]


# ── Helper: extract JSON from LLM response ──────────────────────────────────

def _extract_json(text: str) -> dict:
    """Robustly extract a JSON object from a string that may have surrounding text."""
    # 1. Try direct parse
    try:
        return json.loads(text.strip(), strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Extract from markdown code block
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1), strict=False)
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Find first complete JSON object in text (handles nested braces)
    brace_depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if start is None:
                start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i+1], strict=False)
                except (json.JSONDecodeError, ValueError):
                    start = None

    raise ValueError(f"Could not extract JSON from agent response: {text[:300]}")


def _build_fallback_response(rec_id: str, query: str, raw_text: str) -> dict:
    """If JSON parsing fails, build a graceful fallback response."""
    return {
        "id": rec_id,
        "query": query,
        "alternative": "Analysis complete — see reasoning",
        "current_supplier": "Unknown",
        "reasoning": raw_text[:500] if raw_text else "Agent returned an unstructured response.",
        "cost_impact": "See reasoning",
        "risk_impact": "See reasoning",
        "sustainability_impact": "See reasoning",
        "evidence": [raw_text[:200]] if raw_text else ["No evidence available"],
        "sources": ["Decision Agent"],
        "confidence": 50,
        "status": "pending",
        "agent_trace": [],
    }

def _rec_to_response(rec: Recommendation) -> RecommendationResponse:
    """Map a SQLAlchemy Recommendation model to a Pydantic RecommendationResponse."""
    return RecommendationResponse(
        id=str(rec.id),
        query=rec.query,
        alternative=rec.alternative,
        current_supplier=rec.current_supplier,
        reasoning=rec.reasoning,
        cost_impact=rec.cost_impact,
        risk_impact=rec.risk_impact,
        sustainability_impact=rec.sustainability_impact,
        decision_score=rec.decision_score,
        cost_score=rec.cost_score,
        delivery_score=rec.delivery_score,
        risk_score=rec.risk_score,
        sustainability_score=rec.sustainability_score,
        location_score=rec.location_score,
        candidates=rec.candidates,
        evidence=rec.evidence or [],
        sources=rec.sources or [],
        confidence=rec.confidence,
        status=rec.status,
        agent_trace=[TraceStep(**t) for t in (rec.agent_trace or [])],
    )

# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/query", response_model=RecommendationResponse)
async def run_agent_query(
    query: str = Form(..., min_length=3, max_length=1000),
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a natural language procurement query.
    The Decision Agent analyzes the supply chain and returns a structured,
    persisted recommendation with full agent trace.
    """
    try:
        from core_agents.decision_agent import run_agent_with_trace
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Agent initialization failed: {str(e)}. Ensure AWS credentials are configured.",
        )

    # Read and parse uploaded files
    file_contents = []
    for f in files:
        if f.filename:
            content = await f.read()
            try:
                text = content.decode("utf-8")
                file_contents.append(f"--- File: {f.filename} ---\n{text}\n")
            except UnicodeDecodeError:
                file_contents.append(f"--- File: {f.filename} ---\n[Binary file - text extraction limited]\n")
                
    context_data = "\n".join(file_contents)

    try:
        from starlette.concurrency import run_in_threadpool
        raw_text, trace = await run_in_threadpool(run_agent_with_trace, query, context_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}",
        )

    # Parse agent response into structured format
    rec_id = None
    try:
        payload = _extract_json(raw_text)
        decision_score = payload.get("decision_score")
        cost_score = payload.get("cost_score")
        delivery_score = payload.get("delivery_score")
        risk_score = payload.get("risk_score")
        sustainability_score = payload.get("sustainability_score")
        location_score = payload.get("location_score")
        candidates = payload.get("candidates", [])

        # Persist to database
        rec = Recommendation(
            query=query,
            alternative=payload.get("alternative", "Analysis complete — see reasoning"),
            current_supplier=payload.get("current_supplier", "Unknown"),
            status="pending",
            reasoning=payload.get("reasoning", str(payload)),
            cost_impact=payload.get("cost_impact", "See reasoning"),
            risk_impact=payload.get("risk_impact", "See reasoning"),
            sustainability_impact=payload.get("sustainability_impact", "See reasoning"),
            decision_score=decision_score if isinstance(decision_score, int) else None,
            cost_score=cost_score if isinstance(cost_score, int) else None,
            delivery_score=delivery_score if isinstance(delivery_score, int) else None,
            risk_score=risk_score if isinstance(risk_score, int) else None,
            sustainability_score=sustainability_score if isinstance(sustainability_score, int) else None,
            location_score=location_score if isinstance(location_score, int) else None,
            candidates=candidates,
            evidence=payload.get("evidence", []),
            sources=payload.get("sources", ["Decision Agent"]),
            confidence=int(payload.get("confidence", 75)),
            agent_trace=[t for t in trace],
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        rec_id = str(rec.id)

        return RecommendationResponse(
            id=rec_id,
            query=query,
            alternative=rec.alternative,
            current_supplier=rec.current_supplier,
            reasoning=rec.reasoning,
            cost_impact=rec.cost_impact,
            risk_impact=rec.risk_impact,
            sustainability_impact=rec.sustainability_impact,
            decision_score=rec.decision_score,
            cost_score=rec.cost_score,
            delivery_score=rec.delivery_score,
            risk_score=rec.risk_score,
            sustainability_score=rec.sustainability_score,
            location_score=rec.location_score,
            candidates=rec.candidates,
            evidence=rec.evidence,
            sources=rec.sources,
            confidence=rec.confidence,
            status=rec.status,
            agent_trace=[TraceStep(**t) for t in (rec.agent_trace or [])],
        )

    except (ValueError, KeyError, TypeError) as e:
        # Persist a fallback recommendation
        fallback = _build_fallback_response("", query, raw_text)
        rec = Recommendation(
            query=query,
            alternative=fallback["alternative"],
            current_supplier=fallback["current_supplier"],
            status="pending",
            reasoning=fallback["reasoning"],
            cost_impact=fallback["cost_impact"],
            risk_impact=fallback["risk_impact"],
            sustainability_impact=fallback["sustainability_impact"],
            evidence=fallback["evidence"],
            sources=fallback["sources"],
            confidence=fallback["confidence"],
            agent_trace=[t for t in trace],
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)

        fallback["id"] = str(rec.id)
        return RecommendationResponse(**fallback)


@router.patch("/{recommendation_id}/approve", response_model=RecommendationResponse)
async def approve_recommendation(recommendation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Approve a pending recommendation.
    Sets status to 'approved' and records the decision timestamp.
    """
    try:
        uid = UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation ID")

    result = await db.execute(select(Recommendation).where(Recommendation.id == uid))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Recommendation is already '{rec.status}'")

    rec.status = "approved"
    rec.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rec)

    return _rec_to_response(rec)


@router.patch("/{recommendation_id}/reject", response_model=RecommendationResponse)
async def reject_recommendation(recommendation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Reject a pending recommendation.
    Sets status to 'rejected' and records the decision timestamp.
    """
    try:
        uid = UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation ID")

    result = await db.execute(select(Recommendation).where(Recommendation.id == uid))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Recommendation is already '{rec.status}'")

    rec.status = "rejected"
    rec.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rec)

    return _rec_to_response(rec)


@router.get("/history", response_model=List[RecommendationSummary])
async def get_recommendation_history(db: AsyncSession = Depends(get_db), limit: int = 20):
    """List the most recent recommendations ordered by creation time descending."""
    result = await db.execute(
        select(Recommendation)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
    )
    recs = result.scalars().all()
    return [
        RecommendationSummary(
            id=str(r.id),
            query=r.query,
            alternative=r.alternative or "",
            current_supplier=r.current_supplier or "",
            status=r.status,
            confidence=r.confidence or 0,
            sustainability_impact=r.sustainability_impact or "",
            created_at=r.created_at.isoformat() if r.created_at else None,
            decided_at=r.decided_at.isoformat() if r.decided_at else None,
        )
        for r in recs
    ]


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation_detail(recommendation_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch the full detail of a single recommendation by ID."""
    try:
        uid = UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation ID")

    result = await db.execute(select(Recommendation).where(Recommendation.id == uid))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return _rec_to_response(rec)
