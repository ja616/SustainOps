/// <reference types="vite/client" />
import React, { useState } from 'react';
import {
  ExternalLink, CheckCircle2, AlertTriangle,
  Search, ChevronDown, ChevronUp, Terminal, ArrowRight,
  CheckCheck, XCircle, Clock, Loader2, Database, Globe, Zap
} from 'lucide-react';
import type { RecommendationData, TraceStep } from '../types/recommendation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface RecommendationProps {
  data: RecommendationData;
  onUpdate?: (updated: RecommendationData) => void;
}

// ── Markdown Helper ───────────────────────────────────────────────────────────
const renderReasoning = (text: string) => {
  const sections = text.split('###').filter(Boolean);
  if (sections.length <= 1) return <p className="text-slate-300 text-sm whitespace-pre-wrap">{text}</p>;
  return (
    <div className="space-y-4">
      {sections.map((sec, i) => {
        const lines = sec.trim().split('\n');
        const title = lines[0];
        const body = lines.slice(1).join('\n').trim();
        return (
          <div key={i} className="bg-dark-bg/30 rounded-lg p-4 border border-dark-border/50">
            <h5 className="text-brand-400 font-semibold text-sm mb-2 pb-2 border-b border-dark-border/50">{title.trim()}</h5>
            <p className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">{body}</p>
          </div>
        );
      })}
    </div>
  );
};

// ── Score Ring Component ──────────────────────────────────────────────────────
const ScoreRing: React.FC<{ score: number | undefined; label: string; color: string }> = ({ score, label, color }) => {
  const displayScore = score ?? 0;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (displayScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2 group">
      <div className="relative w-20 h-20 flex items-center justify-center">
        <svg className="transform -rotate-90 w-full h-full">
          <circle cx="40" cy="40" r={radius} stroke="currentColor" strokeWidth="6" fill="transparent" className="text-dark-border" />
          <circle 
            cx="40" cy="40" r={radius} stroke="currentColor" strokeWidth="6" fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`text-${color}-500 transition-all duration-1000 ease-out group-hover:scale-105 transform origin-center drop-shadow-[0_0_8px_rgba(var(--tw-colors-${color}-500),0.5)]`}
          />
        </svg>
        <span className="absolute text-lg font-bold text-slate-200">{displayScore}</span>
      </div>
      <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</span>
    </div>
  );
};

// ── Trace Step Card ───────────────────────────────────────────────────────────
const TraceStepCard: React.FC<{ step: TraceStep }> = ({ step }) => {
  const [expanded, setExpanded] = useState(false);

  const isToolCall = step.type === 'tool_call';
  const isLLM = step.type === 'llm_response';

  const icon = isToolCall
    ? <Database className="w-3.5 h-3.5" />
    : isLLM
      ? <Zap className="w-3.5 h-3.5" />
      : <ArrowRight className="w-3.5 h-3.5" />;

  const color = isToolCall ? 'brand' : isLLM ? 'teal' : 'slate';
  const label = isToolCall
    ? `Tool: ${step.tool_name}`
    : isLLM
      ? 'LLM Reasoning'
      : `Result: ${step.tool_name}`;

  // Try to pretty-print output JSON
  let outputDisplay = step.output || '';
  try {
    if (outputDisplay.trim().startsWith('{') || outputDisplay.trim().startsWith('[')) {
      outputDisplay = JSON.stringify(JSON.parse(outputDisplay), null, 2);
    }
  } catch {
    // keep raw
  }

  return (
    <div className={`relative border border-dark-border rounded-lg overflow-hidden transition-all duration-200 ${expanded ? 'bg-dark-bg/80' : 'bg-dark-bg/30 hover:bg-dark-bg/50'}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left"
      >
        {/* Step number */}
        <span className="w-5 h-5 flex items-center justify-center rounded-full bg-dark-card border border-dark-border text-[10px] text-slate-400 font-mono flex-shrink-0">
          {step.step}
        </span>
        {/* Icon */}
        <span className={`text-${color}-400 flex-shrink-0`}>{icon}</span>
        {/* Label */}
        <span className="text-sm text-slate-300 flex-1 truncate font-mono">{label}</span>
        {/* Input preview */}
        {step.input && Object.keys(step.input).length > 0 && (
          <span className="text-xs text-slate-500 font-mono truncate max-w-[200px] hidden md:block">
            ({Object.entries(step.input).map(([k, v]) => `${k}="${v}"`).join(', ')})
          </span>
        )}
        {/* Expand toggle */}
        {(step.output || step.input) && (
          <span className="text-slate-500 flex-shrink-0">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </span>
        )}
      </button>

      {expanded && (
        <div className="border-t border-dark-border px-4 py-3 space-y-2">
          {step.input && Object.keys(step.input).length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Input</p>
              <pre className="text-xs text-slate-300 font-mono bg-dark-bg rounded p-2 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(step.input, null, 2)}
              </pre>
            </div>
          )}
          {outputDisplay && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Output</p>
              <pre className="text-xs text-slate-400 font-mono bg-dark-bg rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-48">
                {outputDisplay}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Agent Trace Panel ─────────────────────────────────────────────────────────
const AgentTracePanel: React.FC<{ trace: TraceStep[] }> = ({ trace }) => {
  const [open, setOpen] = useState(false);
  const toolCalls = trace.filter(s => s.type === 'tool_call').length;

  if (trace.length === 0) return null;

  return (
    <div className="border border-dark-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 bg-dark-bg/40 hover:bg-dark-bg/60 transition-colors"
        id="agent-trace-toggle"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold text-slate-300">Agent Trace</span>
          <span className="px-2 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-[10px] text-brand-400 font-mono">
            {trace.length} steps · {toolCalls} tool calls
          </span>
        </div>
        <span className="text-slate-500">
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {open && (
        <div className="p-4 space-y-2 bg-dark-bg/20 max-h-96 overflow-y-auto">
          {/* Flow diagram */}
          <div className="flex items-center gap-1 flex-wrap mb-3">
            <span className="px-2 py-0.5 rounded bg-teal-900/30 border border-teal-500/20 text-teal-400 text-[10px] font-mono">Decision Agent</span>
            {trace.filter(s => s.type === 'tool_call').map((s, i) => (
              <React.Fragment key={i}>
                <ArrowRight className="w-3 h-3 text-slate-600" />
                <span className="px-2 py-0.5 rounded bg-brand-900/30 border border-brand-500/20 text-brand-400 text-[10px] font-mono">{s.tool_name}</span>
              </React.Fragment>
            ))}
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-600 text-slate-300 text-[10px] font-mono">Recommendation</span>
          </div>
          {trace.map((step, i) => (
            <TraceStepCard key={i} step={step} />
          ))}
        </div>
      )}
    </div>
  );
};

// ── Status Badge ──────────────────────────────────────────────────────────────
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'approved') return (
    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400 text-xs font-semibold">
      <CheckCheck className="w-3.5 h-3.5" /> Approved
    </span>
  );
  if (status === 'rejected') return (
    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold">
      <XCircle className="w-3.5 h-3.5" /> Rejected
    </span>
  );
  return (
    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/30 text-orange-400 text-xs font-semibold">
      <Clock className="w-3.5 h-3.5" /> Pending Decision
    </span>
  );
};

// ── Main Recommendation Card ──────────────────────────────────────────────────
export const RecommendationCard: React.FC<RecommendationProps> = ({ data, onUpdate }) => {
  const [status, setStatus] = useState(data.status);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleApprove = async () => {
    setIsApproving(true);
    setActionError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/agents/${data.id}/approve`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
        throw new Error(err.detail);
      }
      await res.json();
      setStatus('approved');
      onUpdate?.({ ...data, status: 'approved' });
    } catch (err: any) {
      setActionError(err.message || 'Failed to approve');
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    setActionError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/agents/${data.id}/reject`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
        throw new Error(err.detail);
      }
      setStatus('rejected');
      onUpdate?.({ ...data, status: 'rejected' });
    } catch (err: any) {
      setActionError(err.message || 'Failed to reject');
    } finally {
      setIsRejecting(false);
    }
  };

  const isPending = status === 'pending';

  return (
    <div className="glass-card w-full max-w-4xl mx-auto overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-brand-900/40 to-teal-900/40 border-b border-dark-border p-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="badge border-brand-500/30 bg-brand-500/10 text-brand-400">
              Alternative Discovery · Nova Lite
            </span>
            <span className="text-xs text-slate-400 flex items-center gap-1">
              Confidence: <span className="text-brand-400 font-bold">{data.confidence}%</span>
            </span>
            <StatusBadge status={status} />
          </div>
          <h2 className="text-2xl font-bold text-slate-100">
            Recommended: <span className="text-brand-400">{data.alternative}</span>
          </h2>
          {(data.current_supplier && data.current_supplier !== 'None' && data.current_supplier !== 'Unknown') && (
            <p className="text-slate-400 mt-1">
              Replaces current supplier: <span className="text-slate-300">{data.current_supplier}</span>
            </p>
          )}
        </div>
        <div className="p-3 bg-dark-bg/50 rounded-full flex-shrink-0">
          <CheckCircle2 className="w-8 h-8 text-brand-400" />
        </div>
      </div>

      {/* Market Averages */}
      <div className="grid grid-cols-3 divide-x divide-dark-border bg-dark-bg/40 border-b border-dark-border">
        <div className="p-4 text-center">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">Average Sustainability Gain</p>
          <p className="text-teal-400 font-semibold text-lg">{data.sustainability_impact}</p>
        </div>
        <div className="p-4 text-center">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">Average Cost Impact</p>
          <p className="text-orange-400 font-semibold text-lg">{data.cost_impact}</p>
        </div>
        <div className="p-4 text-center">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">System Confidence</p>
          <p className="text-brand-400 font-semibold text-lg">{data.confidence}%</p>
        </div>
      </div>

      {/* Decision Scores Board */}
      {data.decision_score !== undefined && (
        <div className="px-6 pt-4 pb-2 border-b border-dark-border/50 bg-dark-bg/20">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-1">Decision Score</p>
                <div className="text-5xl font-black bg-gradient-to-br from-brand-400 to-teal-400 bg-clip-text text-transparent drop-shadow-sm">
                  {data.decision_score}
                  <span className="text-2xl text-slate-600 font-medium">/100</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6 md:gap-10">
              <ScoreRing score={data.cost_score} label="Cost" color="orange" />
              <ScoreRing score={data.delivery_score} label="Delivery" color="blue" />
              <ScoreRing score={data.risk_score} label="Risk" color="brand" />
              <ScoreRing score={data.sustainability_score} label="Sustain" color="teal" />
            </div>
          </div>
        </div>
      )}

      {/* Reasoning Analyst Report */}
      <div className="px-6 pt-6 pb-0">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <Terminal className="w-4 h-4" /> Procurement Analyst Report
        </h3>
        {renderReasoning(data.reasoning)}
      </div>

      <div className="p-6">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
          <Terminal className="w-4 h-4" /> Comparative Analyst Matrix
        </h3>
        
        <div className="space-y-6">
          {/* Winner Detail (from main reasoning/evidence) */}
          <div className="bg-brand-900/10 border border-brand-500/20 rounded-xl p-5">
            <h4 className="text-brand-400 font-bold mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5" /> Recommended: {data.alternative}
            </h4>
            
            {data.candidates?.find(c => c.status === 'recommended')?.cost_estimation && (
              <p className="text-sm text-slate-300 mb-4 pb-4 border-b border-brand-500/10">
                <span className="text-slate-500 font-medium mr-2">Cost Estimate:</span>
                {data.candidates.find(c => c.status === 'recommended')?.cost_estimation}
              </p>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h5 className="text-xs uppercase tracking-wider text-slate-500 mb-2">Evidence & Reasoning</h5>
                <ul className="space-y-2">
                  {data.evidence.map((ev, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-500 mt-0.5 flex-shrink-0" />
                      {ev}
                    </li>
                  ))}
                </ul>
              </div>
              
              {data.candidates?.find(c => c.status === 'recommended')?.evidence_links && (
                <div>
                  <h5 className="text-xs uppercase tracking-wider text-slate-500 mb-2">Verified Claims</h5>
                  <div className="flex flex-wrap gap-2">
                    {data.candidates.find(c => c.status === 'recommended')?.evidence_links.map((link, idx) => (
                      <a key={idx} href={link} target="_blank" rel="noreferrer" className="px-3 py-1.5 bg-dark-bg border border-dark-border rounded-lg text-xs text-brand-400 flex items-center gap-1 hover:border-brand-500/50 transition-colors">
                        <ExternalLink className="w-3 h-3" /> View Source
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Supplier Comparison Table */}
          {data.candidates && data.candidates.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-brand-400" /> Supplier Comparison Matrix
              </h4>
              <div className="overflow-x-auto rounded-xl border border-dark-border">
                <table className="w-full text-left text-sm text-slate-300 whitespace-nowrap">
                  <thead className="bg-dark-bg/80 text-xs uppercase tracking-wider text-slate-500 border-b border-dark-border">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Supplier</th>
                      <th className="px-4 py-3 font-semibold">Total Cost Math</th>
                      <th className="px-4 py-3 font-semibold text-center">Cost</th>
                      <th className="px-4 py-3 font-semibold text-center">Delivery</th>
                      <th className="px-4 py-3 font-semibold text-center">Risk</th>
                      <th className="px-4 py-3 font-semibold text-center">Sustain</th>
                      <th className="px-4 py-3 font-semibold text-center">Location</th>
                      <th className="px-4 py-3 font-semibold text-right text-brand-400">Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border/50 bg-dark-bg/20">
                    {data.candidates.sort((a, b) => (b.final_score || 0) - (a.final_score || 0)).map((candidate, idx) => (
                      <tr key={idx} className={`hover:bg-dark-bg/40 transition-colors ${candidate.status === 'recommended' ? 'bg-brand-900/10' : ''}`}>
                        <td className="px-4 py-3 font-medium flex items-center gap-2">
                          {candidate.status === 'recommended' ? <CheckCircle2 className="w-4 h-4 text-brand-500" /> : <XCircle className="w-4 h-4 text-slate-600" />}
                          <span className={candidate.status === 'recommended' ? 'text-brand-300' : 'text-slate-300'}>{candidate.name}</span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400 max-w-[200px] whitespace-normal" title={candidate.cost_estimation}>
                          {candidate.cost_estimation || 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-center text-orange-400 font-medium">{candidate.cost_score || '-'}</td>
                        <td className="px-4 py-3 text-center text-blue-400 font-medium">{candidate.delivery_score || '-'}</td>
                        <td className="px-4 py-3 text-center text-brand-500 font-medium">{candidate.risk_score || '-'}</td>
                        <td className="px-4 py-3 text-center text-teal-400 font-medium">{candidate.sustainability_score || '-'}</td>
                        <td className="px-4 py-3 text-center text-purple-400 font-medium">{candidate.location_score || '-'}</td>
                        <td className="px-4 py-3 text-right text-brand-300 font-bold">{candidate.final_score || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 pt-0 space-y-6">
        {data.sources.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
                <Search className="w-4 h-4" /> Discovery Sources
              </h3>
              <div className="flex flex-wrap gap-2">
                {data.sources.map((src, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1.5 bg-dark-bg border border-dark-border rounded-lg text-sm text-slate-300 flex items-center gap-2 hover:border-brand-500/50 transition-colors"
                  >
                    {src.toLowerCase().includes('web') || src.toLowerCase().includes('search')
                      ? <Globe className="w-3 h-3 text-slate-500" />
                      : <Database className="w-3 h-3 text-slate-500" />}
                    {src}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="pt-2 space-y-3">
            {actionError && (
              <p className="text-red-400 text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> {actionError}
              </p>
            )}

            {isPending ? (
              <div className="flex justify-end gap-3">
                <button
                  id="btn-reject"
                  disabled={isRejecting || isApproving}
                  onClick={handleReject}
                  className="px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-slate-300 hover:bg-red-900/20 hover:border-red-500/40 hover:text-red-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isRejecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                  Reject & Reset
                </button>
                <button
                  id="btn-approve"
                  disabled={isApproving || isRejecting}
                  onClick={handleApprove}
                  className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isApproving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCheck className="w-4 h-4" />}
                  Approve Shift to {data.alternative}
                </button>
              </div>
            ) : (
              <div className="flex justify-end">
                <div className={`px-4 py-2 rounded-lg border flex items-center gap-2 text-sm font-medium ${
                  status === 'approved'
                    ? 'bg-teal-500/10 border-teal-500/30 text-teal-400'
                    : 'bg-red-500/10 border-red-500/30 text-red-400'
                }`}>
                  {status === 'approved'
                    ? <><CheckCheck className="w-4 h-4" /> Supplier shift approved and recorded</>
                    : <><XCircle className="w-4 h-4" /> Recommendation rejected and recorded</>
                  }
                </div>
              </div>
            )}
          </div>
        </div>

      {/* Agent Trace Panel */}
      {data.agent_trace && data.agent_trace.length > 0 && (
        <div className="px-6 pb-6">
          <AgentTracePanel trace={data.agent_trace} />
        </div>
      )}
    </div>
  );
};
