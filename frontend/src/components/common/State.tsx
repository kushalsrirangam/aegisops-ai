export function Loading() { return <div className="panel muted" role="status">Loading operational data…</div> }
export function ErrorState({ error }: { error: Error }) { return <div className="panel error" role="alert">{error.message}. Check that the backend is running.</div> }
export function Empty({ children }: { children: React.ReactNode }) { return <div className="panel muted">{children}</div> }
