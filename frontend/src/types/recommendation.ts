// Shared TypeScript types matching the FastAPI RecommendationResponse schema

export interface TraceStep {
  step: number;
  type: 'tool_call' | 'tool_result' | 'llm_response';
  tool_name: string | null;
  input: Record<string, unknown> | null;
  output: string | null;
}

export interface Candidate {
  name: string;
  status: string; // 'recommended' | 'rejected'
  cost_score?: number;
  delivery_score?: number;
  risk_score?: number;
  sustainability_score?: number;
  location_score?: number;
  final_score?: number;
  cost_estimation?: string;
  reasoning: string;
  evidence_links: string[];
}

export interface RecommendationData {
  id: string;
  query: string;
  alternative: string;
  current_supplier: string;
  reasoning: string;
  cost_impact: string;
  risk_impact: string;
  sustainability_impact: string;
  decision_score?: number;
  cost_score?: number;
  delivery_score?: number;
  risk_score?: number;
  sustainability_score?: number;
  location_score?: number;
  candidates: Candidate[];
  evidence: string[];
  sources: string[];
  confidence: number;
  status: 'pending' | 'approved' | 'rejected';
  agent_trace: TraceStep[];
}

export interface RecommendationSummary {
  id: string;
  query: string;
  alternative: string;
  current_supplier: string;
  status: 'pending' | 'approved' | 'rejected';
  confidence: number;
  sustainability_impact: string;
  created_at: string | null;
  decided_at: string | null;
}

export interface ApiError {
  detail: string;
}
