import { FormEvent, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { api } from '../services/api'

export function Login({ onSuccess, expired = false }: { onSuccess: (token: string) => void; expired?: boolean }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      const response = await api.login(email, password)
      onSuccess(response.access_token)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Sign in failed')
    } finally {
      setPending(false)
    }
  }
  return <div className="login-screen"><form className="panel login-card" onSubmit={submit}>
    <div className="brand"><span className="brand-mark"><ShieldCheck size={22}/></span><span>AegisOps <strong>AI</strong></span></div>
    <div className="eyebrow accent">OPERATIONS ACCESS</div>
    <h1>Sign in</h1>
    <p>Use an account created by your local administrator.</p>
    {expired && <div role="alert" className="notice compact">Your session expired. Sign in again.</div>}
    <label>Email<input type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)}/></label>
    <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)}/></label>
    {error && <div role="alert" className="error">{error}</div>}
    <button className="button primary" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</button>
  </form></div>
}
