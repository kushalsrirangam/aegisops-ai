import { lazy, Suspense, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Route, Routes } from 'react-router-dom'
import { Shell } from './layouts/Shell'
import { Login } from './pages/Login'
import { api } from './services/api'
const Overview = lazy(() => import('./pages/Overview').then(m => ({ default: m.Overview })))
const Incidents = lazy(() => import('./pages/Incidents').then(m => ({ default: m.Incidents })))
const IncidentDetail = lazy(() => import('./pages/IncidentDetail').then(m => ({ default: m.IncidentDetail })))
const Agents = lazy(() => import('./pages/Agents').then(m => ({ default: m.Agents })))
const Knowledge = lazy(() => import('./pages/Knowledge').then(m => ({ default: m.Knowledge })))
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })))
export default function App() {
  const queryClient = useQueryClient()
  const [token, setToken] = useState(() => sessionStorage.getItem('aegisops_token'))
  const me = useQuery({ queryKey: ['me', token], queryFn: api.me, enabled: !!token, retry: false })
  useEffect(() => {
    if (me.isError) {
      sessionStorage.removeItem('aegisops_token')
      queryClient.clear()
    }
  }, [me.isError, queryClient])
  function signedIn(value: string) {
    sessionStorage.setItem('aegisops_token', value)
    queryClient.clear()
    setToken(value)
  }
  async function signedOut() {
    try { await api.logout() } catch { /* clear the local token even if the server is unavailable */ }
    sessionStorage.removeItem('aegisops_token')
    queryClient.clear()
    setToken(null)
  }
  if (!token || me.isError) return <Login onSuccess={signedIn} expired={!!token && me.isError}/>
  if (me.isLoading || !me.data) return <div role="status" className="panel muted">Checking access…</div>
  return <Suspense fallback={<div role="status" className="panel muted">Loading page…</div>}><Routes>
    <Route element={<Shell user={me.data} onSignOut={signedOut}/> }>
      <Route index element={<Overview/>}/>
      <Route path="incidents" element={<Incidents/>}/>
      <Route path="incidents/:id" element={<IncidentDetail/>}/>
      <Route path="agents" element={<Agents/>}/>
      <Route path="knowledge" element={<Knowledge/>}/>
      <Route path="settings" element={<Settings/>}/>
    </Route>
  </Routes></Suspense>
}
