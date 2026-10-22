import { NavLink, Outlet } from 'react-router-dom'
import { Activity, Bot, BookOpen, LayoutDashboard, Settings2, ShieldAlert } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

const nav = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/incidents', label: 'Incidents', icon: ShieldAlert },
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/knowledge', label: 'Knowledge', icon: BookOpen },
  { to: '/settings', label: 'Settings', icon: Settings2 },
]
export function Shell({ user, onSignOut }: { user: { email: string; role: string }; onSignOut: () => void }) {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health })
  const mode = health.data?.mode === 'bedrock' ? 'BEDROCK MODE' : 'DEMO MODE'
  return <div className="shell"><aside className="sidebar">
    <div className="brand"><span className="brand-mark"><Activity size={22}/></span><span>AegisOps <strong>AI</strong><small>OPERATIONS INTELLIGENCE</small></span></div>
    <div className="nav-caption">WORKSPACE</div>
    <nav aria-label="Primary navigation">{nav.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={18}/>{label}</NavLink>)}</nav>
    <div className="sidebar-foot"><span className="status-dot"/> {mode} <small>No automated cloud actions</small><small>{user.email} · {user.role}</small><button className="button secondary" onClick={onSignOut}>Sign out</button></div>
  </aside><div className="main-area"><header className="topbar"><div><span className="eyebrow">AEGISOPS CONTROL PLANE</span><span className="topbar-divider"/> <span className="topbar-context">Incident intelligence</span></div><span className="mode-badge">● {mode}</span></header><main><Outlet/></main></div></div>
}
