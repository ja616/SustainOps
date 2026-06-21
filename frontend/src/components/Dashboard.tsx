/// <reference types="vite/client" />
import React, { useState, useEffect, useRef } from 'react';
import {
  Leaf, Activity, ShieldAlert, DollarSign, Bot, Send, AlertCircle,
  CheckCheck, XCircle, Clock, History, RefreshCw, ChevronRight, Paperclip, X
} from 'lucide-react';
import { RecommendationCard } from './RecommendationCard';
import type { RecommendationData, RecommendationSummary } from '../types/recommendation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Status icon helper ────────────────────────────────────────────────────────
const StatusIcon: React.FC<{ status: string; size?: string }> = ({ status, size = "w-3 h-3" }) => {
  if (status === 'approved') return <CheckCheck className={`${size} text-teal-400`} />;
  if (status === 'rejected') return <XCircle className={`${size} text-red-400`} />;
  return <Clock className={`${size} text-orange-400`} />;
};

// ── Past Decisions Sidebar Item ───────────────────────────────────────────────
const HistoryItem: React.FC<{ rec: RecommendationSummary; active: boolean; onClick: () => void }> = ({
  rec, active, onClick
}) => (
  <button
    onClick={onClick}
    className={`w-full text-left px-3 py-2.5 rounded-lg transition-all duration-150 group flex items-start gap-2 ${
      active
        ? 'bg-brand-500/15 border border-brand-500/30'
        : 'hover:bg-dark-bg border border-transparent hover:border-dark-border'
    }`}
  >
    <div className="mt-0.5 flex-shrink-0">
      <StatusIcon status={rec.status} size="w-3.5 h-3.5" />
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-xs text-slate-300 truncate leading-tight">
        {(rec.current_supplier === 'None' || rec.current_supplier === 'Unknown' || !rec.current_supplier) 
          ? <span className="text-brand-400">{rec.alternative}</span>
          : <>{rec.current_supplier} → <span className="text-brand-400">{rec.alternative}</span></>
        }
      </p>
      <p className="text-[10px] text-slate-500 truncate mt-0.5 leading-tight">
        {rec.query.length > 40 ? rec.query.slice(0, 40) + '…' : rec.query}
      </p>
    </div>
    <ChevronRight className={`w-3 h-3 text-slate-600 flex-shrink-0 mt-0.5 transition-transform ${active ? 'rotate-90' : 'group-hover:translate-x-0.5'}`} />
  </button>
);

// ── Main Dashboard ────────────────────────────────────────────────────────────
export const Dashboard: React.FC = () => {
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // History state
  const [history, setHistory] = useState<RecommendationSummary[]>([]);
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Load history on mount and after each query
  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/agents/history`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch {
      // Silently fail — history is non-critical
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Scroll to bottom when recommendation arrives
  useEffect(() => {
    if (recommendation) {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [recommendation]);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const currentQuery = query.trim();
    setSubmittedQuery(currentQuery);
    setIsLoading(true);
    setRecommendation(null);
    setError(null);
    setActiveHistoryId(null);

    const formData = new FormData();
    formData.append('query', currentQuery);
    files.forEach(f => formData.append('files', f));

    try {
      const res = await fetch(`${API_URL}/api/v1/agents/query`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: `Server error ${res.status}` }));
        throw new Error(errData.detail || `Error ${res.status}`);
      }

      const data: RecommendationData = await res.json();
      setRecommendation(data);
      setActiveHistoryId(data.id);
      // Refresh history list
      await loadHistory();
    } catch (err: any) {
      setError(err.message || 'Failed to connect to SustainIQ backend.');
    } finally {
      setIsLoading(false);
      setQuery('');
      setFiles([]);
    }
  };

  const handleRecommendationUpdate = (updated: RecommendationData) => {
    setRecommendation(updated);
    // Update history list status inline
    setHistory(prev => prev.map(h => h.id === updated.id ? { ...h, status: updated.status } : h));
  };

  const handleHistoryClick = async (id: string) => {
    if (activeHistoryId === id && recommendation?.id === id) return;
    setActiveHistoryId(id);
    setError(null);
    setIsLoading(true);
    setSubmittedQuery('');
    try {
      // Fetch the full recommendation from history by finding in list first
      const found = history.find(h => h.id === id);
      if (found) setSubmittedQuery(found.query);

      const res = await fetch(`${API_URL}/api/v1/agents/${id}`);
      if (!res.ok) {
        throw new Error('Failed to load history record');
      }
      const data: RecommendationData = await res.json();
      setRecommendation(data);
    } catch (err: any) {
      setError(err.message || 'Error loading history record');
      setRecommendation(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-dark-border bg-dark-card flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-2 p-4 pb-3">
          <div className="p-2 bg-brand-500/20 rounded-lg">
            <Leaf className="w-5 h-5 text-brand-500" />
          </div>
          <span className="text-lg font-bold bg-gradient-to-r from-brand-400 to-teal-400 bg-clip-text text-transparent">
            SustainIQ
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-1 pb-3 overflow-y-auto">
          <a id="nav-decision" href="#" className="flex items-center gap-3 px-3 py-2 rounded-lg bg-dark-bg border border-dark-border text-brand-400 transition-colors">
            <Bot className="w-4 h-4" />
            <span className="text-sm">Decision Intelligence</span>
          </a>
          <button id="nav-sustainability" className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-500 cursor-default transition-colors">
            <Activity className="w-4 h-4 opacity-50" />
            <span className="text-sm">Sustainability</span>
          </button>
          <button id="nav-risk" className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-500 cursor-default transition-colors">
            <ShieldAlert className="w-4 h-4 opacity-50" />
            <span className="text-sm">Risk Profiles</span>
          </button>
          <button id="nav-procurement" className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-500 cursor-default transition-colors">
            <DollarSign className="w-4 h-4 opacity-50" />
            <span className="text-sm">Procurement</span>
          </button>

          {/* History Divider */}
          <div className="pt-3 pb-1">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Past Decisions</span>
              </div>
              <button
                onClick={loadHistory}
                disabled={historyLoading}
                className="text-slate-600 hover:text-slate-400 transition-colors"
                title="Refresh history"
              >
                <RefreshCw className={`w-3 h-3 ${historyLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* History Items */}
          {history.length === 0 && !historyLoading && (
            <p className="text-[10px] text-slate-600 px-3 py-1">No decisions yet. Submit a query above.</p>
          )}
          <div className="space-y-0.5">
            {history.map(rec => (
              <HistoryItem
                key={rec.id}
                rec={rec}
                active={activeHistoryId === rec.id}
                onClick={() => handleHistoryClick(rec.id)}
              />
            ))}
          </div>
        </nav>

        {/* Status Footer */}
        <div className="px-4 py-3 border-t border-dark-border">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-brand-500 rounded-full animate-pulse" />
            <span className="text-xs text-slate-400">Nova Lite · Live</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col bg-dark-bg relative overflow-hidden">
        {/* Background Gradients */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-brand-600/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] bg-teal-600/10 rounded-full blur-[100px] pointer-events-none" />

        {/* Chat Header */}
        <header className="p-6 border-b border-dark-border/50 backdrop-blur-sm z-10 flex-shrink-0">
          <h1 className="text-2xl font-semibold text-slate-100">Alternative Discovery Agent</h1>
          <p className="text-sm text-slate-400 mt-1">
            Ask any question to optimize your supply chain balancing cost, risk, and sustainability.
          </p>
        </header>

        {/* Chat Content Area */}
        <div className="flex-1 overflow-y-auto p-6 z-10 space-y-6 pb-40">

          {/* User message bubble */}
          {submittedQuery && (
            <div className="flex justify-end animate-fade-in">
              <div className="bg-brand-600 text-white px-4 py-2 rounded-2xl rounded-tr-none max-w-lg shadow-lg text-sm">
                {submittedQuery}
              </div>
            </div>
          )}

          {/* Agent Trace (replaces fake loading state) */}
          {recommendation?.agent_trace && (
            <div className="flex items-start gap-3 animate-fade-in mb-4">
              <div className="p-2 bg-dark-card border border-dark-border rounded-full flex-shrink-0">
                <Bot className="w-4 h-4 text-brand-400" />
              </div>
              <div className="bg-dark-card border border-dark-border rounded-xl p-4 space-y-2 max-w-2xl w-full">
                <p className="text-sm font-medium text-slate-200 border-b border-dark-border pb-2 mb-2">Agent Execution Trace</p>
                <div className="space-y-1">
                  {recommendation.agent_trace.map((step, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      {step.type === 'tool_call' ? (
                        <>
                          <span className="text-brand-400 mt-0.5">✓</span>
                          <span className="text-slate-300">
                            Called <span className="font-mono text-teal-400">{step.tool_name}</span> with {JSON.stringify(step.input)}
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="text-brand-500 mt-0.5">↳</span>
                          <span className="text-slate-400 italic truncate max-w-xl">
                            {step.output ? step.output.slice(0, 100) + (step.output.length > 100 ? '...' : '') : 'Synthesizing response...'}
                          </span>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="flex items-start gap-3 animate-pulse">
              <div className="p-2 bg-dark-card border border-dark-border rounded-full flex-shrink-0">
                <Bot className="w-4 h-4 text-brand-400" />
              </div>
              <div className="bg-dark-card border border-dark-border rounded-xl p-4 space-y-2 max-w-sm">
                <p className="text-sm text-slate-400">Agent is executing workflow...</p>
              </div>
            </div>
          )}

          {/* Error state */}
          {error && !isLoading && (
            <div className="flex items-start gap-3 p-4 bg-red-900/20 border border-red-500/30 rounded-xl animate-fade-in max-w-2xl">
              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-red-400 font-medium text-sm">Agent Error</p>
                <p className="text-slate-400 text-sm mt-1">{error}</p>
                {error.includes('AWS') || error.includes('Bedrock') || error.includes('credentials') ? (
                  <p className="text-slate-500 text-xs mt-2">
                    Check that your AWS credentials are set in <code className="text-slate-400">.env</code> and
                    that Nova Lite model access is enabled in your AWS Bedrock console.
                  </p>
                ) : null}
              </div>
            </div>
          )}

          {/* Recommendation result */}
          {recommendation && !isLoading && (
            <div className="animate-slide-up">
              <RecommendationCard data={recommendation} onUpdate={handleRecommendationUpdate} />
            </div>
          )}

          {/* Initial empty state */}
          {!submittedQuery && !recommendation && !error && !isLoading && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-6 animate-fade-in">
              <div className="p-4 bg-dark-card border border-dark-border rounded-full shadow-2xl hover:scale-105 transition-transform duration-300">
                <Bot className="w-12 h-12 text-brand-400" />
              </div>
              <div>
                <h2 className="text-xl font-medium text-slate-200 mb-2">
                  How can I optimize your supply chain today?
                </h2>
                <p className="text-slate-400 text-sm">
                  Try:{' '}
                  <button
                    onClick={() => setQuery('We currently source office chairs from Supplier A. Can we do better?')}
                    className="text-brand-400 italic hover:underline hover:text-brand-300 transition-colors"
                  >
                    "We currently source office chairs from Supplier A. Can we do better?"
                  </button>
                </p>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  {[
                    'Find greener laptop suppliers',
                    'Assess risk of Supplier D',
                    'Which electronics suppliers are ISO certified?',
                    'Compare Supplier B and Supplier C',
                  ].map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setQuery(suggestion)}
                      className="text-left px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:border-brand-500/40 transition-all"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Input Box */}
        <div className="p-6 bg-dark-bg/80 backdrop-blur-md border-t border-dark-border z-10 flex-shrink-0">
          {files.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3 max-w-4xl mx-auto">
              {files.map((f, i) => (
                <div key={i} className="flex items-center gap-1.5 bg-dark-card border border-dark-border px-2.5 py-1 rounded-md text-xs text-slate-300">
                  <Paperclip className="w-3 h-3 text-slate-500" />
                  <span className="truncate max-w-[150px]">{f.name}</span>
                  <button type="button" onClick={() => setFiles(fs => fs.filter((_, idx) => idx !== i))} className="text-slate-500 hover:text-red-400 ml-1">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <form onSubmit={handleQuery} className="max-w-4xl mx-auto relative group">
            <div className="absolute inset-0 bg-brand-500/20 rounded-xl blur-md group-focus-within:bg-brand-500/30 transition-all duration-300" />
            <div className="relative flex items-center bg-dark-card border border-dark-border rounded-xl shadow-lg overflow-hidden transition-all duration-300 group-focus-within:border-brand-500/50">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-3 ml-2 text-slate-400 hover:text-brand-400 transition-colors"
                title="Attach files (Quotations, PDFs, CSVs)"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                type="file"
                multiple
                ref={fileInputRef}
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) {
                    setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
                  }
                  e.target.value = '';
                }}
              />
              <input
                id="query-input"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask SustainIQ — e.g. 'Find a greener supplier for office chairs'"
                className="flex-1 bg-transparent border-none outline-none px-6 py-4 text-slate-200 placeholder-slate-500 text-sm"
                disabled={isLoading}
              />
              <button
                id="btn-submit-query"
                type="submit"
                disabled={isLoading || !query.trim()}
                className="p-3 mr-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};
