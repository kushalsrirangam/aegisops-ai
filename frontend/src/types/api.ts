export interface Incident { id: number; title: string; description: string; service: string; severity: string; status: string; mode: string; created_at: string }
export interface Summary { incidents: number; by_status: Record<string, number>; by_severity: Record<string, number>; agent_runs: number }
export interface Agent { name: string; responsibility: string }
export interface Run { id: number; incident_id: number; status: string; started_at: string }
export interface Step { agent: string; result: Record<string, unknown>; created_at: string }
export interface RunDetail extends Run { steps: Step[] }
export interface Proposal { id: number; action: string; rationale: string; risk: string; status: string }
export interface Document { id: number; title: string; source: string; created_at: string }
export interface SearchResult { score: number; title: string; source: string; excerpt: string; document_id: number }
export interface Report { mode: string; severity: string; hypothesis: string; confidence: number; sources: { source: string; title: string }[]; recommendation: string; risk: string; decision: string | null; outcome: string | null; status: string }
