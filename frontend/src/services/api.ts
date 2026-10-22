import type { Agent, Document, Incident, Proposal, Report, Run, RunDetail, SearchResult, Summary } from '../types/api'

const base = '/api/v1'
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(base + path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!response.ok) {
    let detail = response.statusText
    try { detail = (await response.json()).detail ?? detail } catch { /* keep status text */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json() as Promise<T>
}
const post = <T,>(path: string, body: unknown = {}) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const api = {
  health: () => request<{ status: string; mode: string }>('/health'),
  incidents: () => request<Incident[]>('/incidents'),
  incident: (id: number) => request<Incident>(`/incidents/${id}`),
  create: (body: { title: string; description: string; service: string }) => post<Incident>('/incidents', body),
  analyze: (id: number) => post<{ run_id: number; status: string; proposal_id: number | null }>(`/incidents/${id}/analyze`),
  timeline: (id: number) => request<{ kind: string; message: string; created_at: string }[]>(`/incidents/${id}/timeline`),
  report: (id: number) => request<Report>(`/incidents/${id}/report`),
  proposal: (id: number) => request<Proposal>(`/incidents/${id}/proposal`),
  decide: (id: number, choice: 'approve' | 'reject', actor: string, reason: string) => post<Report>(`/approvals/${id}/${choice}`, { actor, reason }),
  agents: () => request<Agent[]>('/agents'),
  runs: () => request<Run[]>('/agents/runs'),
  run: (id: number) => request<RunDetail>(`/agents/runs/${id}`),
  documents: () => request<Document[]>('/knowledge/documents'),
  addDocument: (body: { title: string; content: string; source: string }) => post<Document>('/knowledge/documents', body),
  search: (q: string) => request<SearchResult[]>(`/knowledge/search?q=${encodeURIComponent(q)}`),
  summary: () => request<Summary>('/metrics/summary'),
}
