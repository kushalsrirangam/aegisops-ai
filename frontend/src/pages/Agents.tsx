import { useQuery } from '@tanstack/react-query'
import { Bot, CircleCheck } from 'lucide-react'
import { api } from '../services/api'
import { ErrorState, Loading } from '../components/common/State'

export function Agents() {
  const agents = useQuery({ queryKey: ['agents'], queryFn: api.agents })
  const runs = useQuery({ queryKey: ['runs'], queryFn: api.runs })
  if (agents.isLoading || runs.isLoading) return <Loading/>
  if (agents.error || runs.error) return <ErrorState error={(agents.error || runs.error) as Error}/>
  return <><div className="page-head"><div><div className="eyebrow accent">AGENT OPERATIONS</div><h1>Coordinated intelligence</h1><p>Seven bounded agents share evidence through an explicit workflow graph.</p></div></div><div className="agent-grid">{agents.data?.map((agent, i) => <article className="panel agent-card" key={agent.name}><div className="agent-icon"><Bot size={20}/></div><span className="eyebrow">AGENT {String(i + 1).padStart(2, '0')}</span><h2>{agent.name}</h2><p>{agent.responsibility}</p><span className="agent-available"><CircleCheck size={14}/> Available in demo mode</span></article>)}</div><section className="panel"><div className="section-head"><div><div className="eyebrow">EXECUTION HISTORY</div><h2>Recent runs</h2></div></div><div className="table-wrap"><table><thead><tr><th>Run</th><th>Incident</th><th>State</th><th>Started</th></tr></thead><tbody>{runs.data?.map(run => <tr key={run.id}><td>RUN-{run.id}</td><td>INC-{String(run.incident_id).padStart(4, '0')}</td><td>{run.status.replaceAll('_', ' ')}</td><td>{new Date(run.started_at).toLocaleString()}</td></tr>)}</tbody></table></div>{!runs.data?.length && <p className="muted">No agent runs yet. Analyze an incident to create one.</p>}</section></>
}
