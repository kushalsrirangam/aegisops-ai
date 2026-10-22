import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowRight, Bot, CircleAlert, Radio, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { ErrorState, Loading } from '../components/common/State'

export function Overview() {
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: api.incidents })
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary })
  if (incidents.isLoading || summary.isLoading) return <Loading />
  if (incidents.error || summary.error) return <ErrorState error={(incidents.error || summary.error) as Error} />
  const list = incidents.data ?? []
  const stats = summary.data!
  const chart = [{ name: 'Open', count: stats.by_status.open ?? 0 }, { name: 'Review', count: stats.by_status.awaiting_approval ?? 0 }, { name: 'Resolved', count: stats.by_status.complete ?? 0 }, { name: 'Rejected', count: stats.by_status.rejected ?? 0 }]
  return <><div className="page-head"><div><div className="eyebrow accent">OPERATIONS OVERVIEW</div><h1>Incident command center</h1><p>Investigate service disruptions with coordinated agents and human review.</p></div><Link to="/incidents" className="button primary">View incidents <ArrowRight size={16}/></Link></div>
    <div className="stats-grid"><div className="stat-card"><span><CircleAlert size={18}/> TOTAL INCIDENTS</span><strong>{stats.incidents}</strong><small>Recorded in this workspace</small></div><div className="stat-card"><span><Radio size={18}/> AWAITING REVIEW</span><strong>{stats.by_status.awaiting_approval ?? 0}</strong><small>Human approval required</small></div><div className="stat-card"><span><Bot size={18}/> AGENT RUNS</span><strong>{stats.agent_runs}</strong><small>Traceable executions</small></div><div className="stat-card"><span><ShieldCheck size={18}/> COMPLETED</span><strong>{stats.by_status.complete ?? 0}</strong><small>Simulated validations</small></div></div>
    <div className="overview-grid"><section className="panel chart-panel"><div className="section-head"><div><div className="eyebrow">WORKFLOW HEALTH</div><h2>Incident status</h2></div><span className="subtle">Current snapshot</span></div><ResponsiveContainer width="100%" height={250}><AreaChart data={chart}><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#34d5b0" stopOpacity={0.4}/><stop offset="100%" stopColor="#34d5b0" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#263547" vertical={false}/><XAxis dataKey="name" stroke="#8fa1b5"/><YAxis allowDecimals={false} stroke="#8fa1b5"/><Tooltip contentStyle={{ background: '#172332', border: '1px solid #354659', borderRadius: 8 }}/><Area type="monotone" dataKey="count" stroke="#34d5b0" strokeWidth={3} fill="url(#fill)"/></AreaChart></ResponsiveContainer></section>
      <section className="panel"><div className="section-head"><div><div className="eyebrow">LATEST SIGNALS</div><h2>Recent incidents</h2></div><Link to="/incidents" className="text-link">All incidents →</Link></div><div className="incident-list">{list.slice(0, 5).map(item => <Link to={`/incidents/${item.id}`} className="incident-row" key={item.id}><span className={`severity ${item.severity}`}>{item.severity}</span><span><strong>{item.title}</strong><small>{item.service} · {item.status.replaceAll('_', ' ')}</small></span><ArrowRight size={16}/></Link>)}</div></section></div>
    <div className="notice"><ShieldCheck size={18}/><span><strong>Safe by design:</strong> all observations and recoveries in this local workspace are simulated. Remediation is a proposal requiring human approval.</span></div></>
}
