import { FormEvent, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Plus, Search } from 'lucide-react'
import { api } from '../services/api'
import { ErrorState, Loading } from '../components/common/State'

export function Knowledge() {
  const client = useQueryClient()
  const docs = useQuery({ queryKey: ['documents'], queryFn: api.documents })
  const [q, setQ] = useState('')
  const [submitted, setSubmitted] = useState('')
  const results = useQuery({ queryKey: ['search', submitted], queryFn: () => api.search(submitted), enabled: submitted.length >= 2 })
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ title: '', source: '', content: '' })
  const add = useMutation({ mutationFn: api.addDocument, onSuccess: () => { client.invalidateQueries({ queryKey: ['documents'] }); setOpen(false); setForm({ title: '', source: '', content: '' }) } })
  function submit(e: FormEvent) { e.preventDefault(); add.mutate(form) }
  return <><div className="page-head"><div><div className="eyebrow accent">OPERATIONAL MEMORY</div><h1>Knowledge base</h1><p>Runbooks are chunked, indexed, and cited in investigations.</p></div><button className="button primary" onClick={() => setOpen(!open)}><Plus size={16}/> Add runbook</button></div>
    {open && <form className="panel form-panel" onSubmit={submit}><h2>Ingest a runbook</h2><div className="form-grid"><label>Title<input required minLength={3} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}/></label><label>Source reference<input required minLength={3} placeholder="runbooks/service.md" value={form.source} onChange={e => setForm({ ...form, source: e.target.value })}/></label></div><label>Content<textarea required rows={7} value={form.content} onChange={e => setForm({ ...form, content: e.target.value })}/></label>{add.error && <p className="error" role="alert">{add.error.message}</p>}<div className="button-row"><button className="button primary" disabled={add.isPending}>Ingest document</button><button className="button secondary" type="button" onClick={() => setOpen(false)}>Cancel</button></div></form>}
    <div className="knowledge-grid"><section className="panel"><div className="eyebrow">RETRIEVAL</div><h2>Search runbooks</h2><form className="search-form" onSubmit={e => { e.preventDefault(); setSubmitted(q.trim()) }}><label className="search-field"><Search size={17}/><input aria-label="Search runbooks" minLength={2} placeholder="e.g. HTTP 500 migration" value={q} onChange={e => setQ(e.target.value)}/></label><button className="button primary">Search</button></form>{results.isLoading && <Loading/>}{results.error && <ErrorState error={results.error}/>}<div className="results">{results.data?.map((result, i) => <div className="result" key={i}><strong>{result.title}</strong><span className="subtle">Score {result.score.toFixed(2)}</span><p>{result.excerpt}</p><small>Source: {result.source}</small></div>)}{submitted && results.data?.length === 0 && <p className="muted">No matching runbook chunks.</p>}</div></section><section className="panel"><div className="eyebrow">INDEXED DOCUMENTS</div><h2>Runbooks</h2>{docs.isLoading ? <Loading/> : docs.error ? <ErrorState error={docs.error}/> : docs.data?.map(doc => <div className="document-row" key={doc.id}><BookOpen size={19}/><div><strong>{doc.title}</strong><small>{doc.source}</small></div></div>)}</section></div><div className="notice"><BookOpen size={18}/><span>Local retrieval uses deterministic token hashing. Search scores are approximate; production semantic retrieval needs a configured embedding service and vector index.</span></div></>
}
