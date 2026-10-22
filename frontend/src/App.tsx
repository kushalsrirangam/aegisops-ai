import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Shell } from './layouts/Shell'
const Overview = lazy(() => import('./pages/Overview').then(m => ({ default: m.Overview })))
const Incidents = lazy(() => import('./pages/Incidents').then(m => ({ default: m.Incidents })))
const IncidentDetail = lazy(() => import('./pages/IncidentDetail').then(m => ({ default: m.IncidentDetail })))
const Agents = lazy(() => import('./pages/Agents').then(m => ({ default: m.Agents })))
const Knowledge = lazy(() => import('./pages/Knowledge').then(m => ({ default: m.Knowledge })))
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })))
export default function App() { return <Suspense fallback={<div role="status" className="panel muted">Loading page…</div>}><Routes><Route element={<Shell/>}><Route index element={<Overview/>}/><Route path="incidents" element={<Incidents/>}/><Route path="incidents/:id" element={<IncidentDetail/>}/><Route path="agents" element={<Agents/>}/><Route path="knowledge" element={<Knowledge/>}/><Route path="settings" element={<Settings/>}/></Route></Routes></Suspense> }
