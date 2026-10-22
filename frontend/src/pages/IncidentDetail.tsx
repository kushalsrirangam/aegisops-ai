import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, Play, X } from 'lucide-react'
import { api } from '../services/api'
import { ErrorState, Loading } from '../components/common/State'

export function IncidentDetail() {
  const id = Number(useParams().id)
  const client = useQueryClient()
  const [reason, setReason] = useState('')
  const me = useQuery({ queryKey: ['me', sessionStorage.getItem('aegisops_token')], queryFn: api.me })
  const canOperate = me.data?.role === 'operator' || me.data?.role === 'admin'
  const canReview = me.data?.role === 'reviewer' || me.data?.role === 'admin'
  const incident = useQuery({ queryKey: ['incident', id], queryFn: () => api.incident(id) })
  const runs = useQuery({ queryKey: ['runs'], queryFn: api.runs })
  const latest = runs.data?.find(r => r.incident_id === id)
  const run = useQuery({ queryKey: ['run', latest?.id], queryFn: () => api.run(latest!.id), enabled: !!latest })
  const proposal = useQuery({ queryKey: ['proposal', id], queryFn: () => api.proposal(id), enabled: incident.data?.status === 'awaiting_approval' })
  const report = useQuery({ queryKey: ['report', id], queryFn: () => api.report(id), enabled: ['complete', 'rejected', 'escalated', 'needs_verification'].includes(incident.data?.status ?? '') })
  const timeline = useQuery({ queryKey: ['timeline', id], queryFn: () => api.timeline(id) })
  const refresh = () => { for (const key of ['incident', 'incidents', 'summary', 'runs', 'run', 'proposal', 'report', 'timeline']) client.invalidateQueries({ queryKey: [key] }) }
  const analyze = useMutation({ mutationFn: () => api.analyze(id), onSuccess: refresh })
  const decide = useMutation({ mutationFn: (choice: 'approve' | 'reject') => api.decide(proposal.data!.id, choice, reason), onSuccess: refresh })
  if (incident.isLoading) return <Loading />
  if (incident.error || !incident.data) return <ErrorState error={incident.error ?? new Error('Incident not found')}/>
  const item = incident.data
  return <><Link to="/incidents" className="back-link"><ArrowLeft size={16}/> All incidents</Link><div className="page-head"><div><div className="eyebrow accent">INC-{String(id).padStart(4, '0')} · {item.service}</div><h1>{item.title}</h1><p>{item.description}</p><div className="pill-row"><span className={`severity ${item.severity}`}>{item.severity}</span><span className="status-pill">{item.status.replaceAll('_', ' ')}</span><span className="status-pill">{item.mode === 'demo' ? 'SIMULATED DATA' : 'BEDROCK ANALYSIS'}</span></div></div>{item.status === 'open' && canOperate && <button className="button primary" onClick={() => analyze.mutate()} disabled={analyze.isPending}><Play size={16}/>{analyze.isPending ? 'Investigating…' : 'Run investigation'}</button>}</div>
    {(analyze.error || decide.error) && <div className="panel error" role="alert">{(analyze.error || decide.error)?.message}</div>}
    <div className="detail-grid"><div className="detail-main"><section className="panel"><div className="section-head"><div><div className="eyebrow">AGENT EXECUTION</div><h2>Investigation trace</h2></div><span className="subtle">{run.data?.steps.length ?? 0} steps</span></div>{run.isLoading ? <Loading/> : run.data ? <div className="steps">{run.data.steps.map((step, index) => <div className="step" key={index}><span className="step-num">{String(index + 1).padStart(2, '0')}</span><div><strong>{step.agent}</strong><p>{Object.entries(step.result).filter(([key]) => !['citations', 'evidence'].includes(key)).map(([key, value]) => `${key}: ${String(value)}`).join(' · ')}</p>{Array.isArray(step.result.citations) && step.result.citations.map((c, n) => <div className="citation" key={n}>Source: {String((c as { source: string }).source)}</div>)}{Array.isArray(step.result.evidence) && step.result.evidence.map((e, n) => <div className="citation" key={n}>{String(e)}</div>)}</div></div>)}</div> : <p className="muted">Run an investigation to see each agent’s evidence and decisions.</p>}</section>
      {report.data && <section className="panel"><div className="eyebrow">FINAL REPORT</div><h2>Investigation outcome</h2><div className="report-grid"><div><span>Root-cause hypothesis</span><strong>{report.data.hypothesis}</strong></div><div><span>Confidence</span><strong>{Math.round((report.data.confidence ?? 0) * 100)}%</strong></div><div><span>Outcome</span><strong>{report.data.outcome}</strong></div><div><span>Mode</span><strong>{report.data.mode === 'demo' ? 'Simulated validation' : 'Bedrock analysis; recovery unverified'}</strong></div></div>{report.data.sources?.length > 0 && <p className="muted">Sources: {report.data.sources.map(s => s.source).join(', ')}</p>}</section>}</div>
      <div className="detail-side"><section className="panel"><div className="eyebrow">REMEDIATION</div><h2>Human review</h2>{proposal.data ? <><p className="proposal-action">{proposal.data.action}</p><p className="muted">{proposal.data.rationale}</p><div className="risk-row">Operational risk <span className="severity high">{proposal.data.risk}</span></div><div className="notice compact">This approval records a decision and simulates validation. It executes no infrastructure change.</div>{canReview ? <><p className="muted">Reviewer: {me.data?.email}</p><label>Reason (optional)<textarea rows={2} value={reason} onChange={e => setReason(e.target.value)}/></label><div className="button-row"><button className="button primary" disabled={decide.isPending} onClick={() => decide.mutate('approve')}><Check size={16}/> Approve</button><button className="button secondary" disabled={decide.isPending} onClick={() => decide.mutate('reject')}><X size={16}/> Reject</button></div></> : <p className="muted">A reviewer or admin account must make this decision.</p>}</> : <p className="muted">{item.status === 'open' ? 'Start an investigation to generate a reviewed proposal.' : 'No approval is pending.'}</p>}</section>
      <section className="panel"><div className="eyebrow">ACTIVITY</div><h2>Incident timeline</h2>{timeline.data?.map((event, n) => <div className="timeline-event" key={n}><span className="status-dot"/><div><strong>{event.message}</strong><small>{new Date(event.created_at).toLocaleString()}</small></div></div>)}</section></div></div></>
}
