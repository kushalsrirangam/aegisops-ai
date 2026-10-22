import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Plus, Search } from 'lucide-react'
import { api } from '../services/api'
import { Empty, ErrorState, Loading } from '../components/common/State'

export function Incidents() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['incidents'], queryFn: api.incidents })
  const create = useMutation({ mutationFn: api.create, onSuccess: () => { client.invalidateQueries({ queryKey: ['incidents'] }); setOpen(false) } })
  const [open, setOpen] = useState(false)
  const [severity, setSeverity] = useState('all')
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [form, setForm] = useState({ title: '', description: '', service: '' })
  const filtered = (query.data ?? []).filter(i => (severity === 'all' || i.severity === severity) && (status === 'all' || i.status === status) && `${i.title} ${i.service}`.toLowerCase().includes(search.toLowerCase()))
  function submit(e: FormEvent) { e.preventDefault(); create.mutate(form) }
  return <><div className="page-head"><div><div className="eyebrow accent">INCIDENT MANAGEMENT</div><h1>Incidents</h1><p>Track investigations from first alert through human review and validation.</p></div><button className="button primary" onClick={() => setOpen(!open)}><Plus size={16}/> New incident</button></div>
    {open && <form className="panel form-panel" onSubmit={submit}><h2>Create an incident</h2><div className="form-grid"><label>Title<input required minLength={5} maxLength={200} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}/></label><label>Service identifier<input required pattern="[a-zA-Z0-9-]{2,100}" value={form.service} onChange={e => setForm({ ...form, service: e.target.value })}/></label></div><label>Description<textarea required minLength={10} maxLength={5000} rows={3} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}/></label>{create.error && <p className="error" role="alert">{create.error.message}</p>}<div className="button-row"><button className="button primary" disabled={create.isPending}>Create incident</button><button type="button" className="button secondary" onClick={() => setOpen(false)}>Cancel</button></div></form>}
    <div className="panel"><div className="filters"><label className="search-field"><Search size={17}/><input aria-label="Search incidents" placeholder="Search incidents or services" value={search} onChange={e => setSearch(e.target.value)}/></label><label className="select-label">Severity<select value={severity} onChange={e => setSeverity(e.target.value)}><option value="all">All</option><option value="critical">Critical</option><option value="high">High</option><option value="unknown">Unknown</option></select></label><label className="select-label">Status<select value={status} onChange={e => setStatus(e.target.value)}><option value="all">All</option><option value="open">Open</option><option value="awaiting_approval">Awaiting review</option><option value="complete">Complete</option><option value="rejected">Rejected</option></select></label></div>
      {query.isLoading ? <Loading/> : query.error ? <ErrorState error={query.error}/> : filtered.length === 0 ? <Empty>No incidents match these filters.</Empty> : <div className="table-wrap"><table><thead><tr><th>Incident</th><th>Service</th><th>Severity</th><th>Status</th><th>Opened</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{filtered.map(i => <tr key={i.id}><td><Link className="table-title" to={`/incidents/${i.id}`}>{i.title}</Link><small>INC-{String(i.id).padStart(4, '0')}</small></td><td>{i.service}</td><td><span className={`severity ${i.severity}`}>{i.severity}</span></td><td>{i.status.replaceAll('_', ' ')}</td><td>{new Date(i.created_at).toLocaleDateString()}</td><td><Link aria-label={`Open ${i.title}`} to={`/incidents/${i.id}`}><ArrowRight size={17}/></Link></td></tr>)}</tbody></table></div>}</div></>
}
