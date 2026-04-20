/**
 * Thin client for the FastAPI backend.
 * Base URL comes from NEXT_PUBLIC_API_URL (defaults to localhost:8000).
 */
import type { AnalysisRequest, AnalysisResponse, CompListResponse, RegulationResponse, PortfolioResponse } from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    cache: 'no-store',
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

export const api = {
  createAnalysis: (body: AnalysisRequest) =>
    request<AnalysisResponse>('/api/feasibility/analyze', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getAnalysis: (id: string) =>
    request<AnalysisResponse>(`/api/feasibility/${id}`),

  listAnalyses: () =>
    request<AnalysisResponse[]>('/api/feasibility/?limit=50'),

  getComps: (id: string) =>
    request<CompListResponse>(`/api/comps/${id}`),

  getRegulation: (id: string) =>
    request<RegulationResponse>(`/api/regulations/${id}`),

  getPortfolio: (id: string) =>
    request<PortfolioResponse>(`/api/portfolio/${id}`),
};

export { BASE as API_BASE };
