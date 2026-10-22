import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

describe('navigation', () => {
  beforeEach(() => { sessionStorage.setItem('aegisops_token', 'test-token') })
  afterEach(() => { cleanup(); vi.unstubAllGlobals() })
  it('shows the demo boundary on settings', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: string) => ({ ok: true, json: async () =>
      input.endsWith('/auth/me') ? { email: 'admin@example.test', role: 'admin' } : { status: 'ok', mode: 'demo' }
    } as Response)))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/settings']}><App/></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Runtime configuration')).toBeTruthy()
    expect(await screen.findByText(/no agent can run shell commands/i)).toBeTruthy()
  })

  it('creates an incident through the API from the incidents page', async () => {
    const calls: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? 'GET'} ${input}`)
      const body = input.endsWith('/auth/me') ? { email: 'admin@example.test', role: 'admin' }
        : input.endsWith('/incidents') && init?.method === 'POST'
        ? { id: 2, title: 'Payments failing', description: 'Payments fail after a deploy', service: 'payments', severity: 'unknown', status: 'open', mode: 'demo', created_at: new Date().toISOString() }
        : input.endsWith('/incidents') ? [] : { status: 'ok', mode: 'demo' }
      return { ok: true, json: async () => body } as Response
    }))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/incidents']}><App/></MemoryRouter></QueryClientProvider>)
    fireEvent.click(await screen.findByRole('button', { name: /new incident/i }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Payments failing' } })
    fireEvent.change(screen.getByLabelText('Service identifier'), { target: { value: 'payments' } })
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Payments fail after a deploy' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create incident' }))
    await waitFor(() => expect(calls).toContain('POST /api/v1/incidents'))
  })

  it('requires sign in when no session exists', async () => {
    sessionStorage.removeItem('aegisops_token')
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><App/></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeTruthy()
  })

  it('signs in and sends the bearer token to protected routes', async () => {
    sessionStorage.removeItem('aegisops_token')
    const calls: RequestInit[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
      if (input.endsWith('/auth/me')) calls.push(init ?? {})
      const body = input.endsWith('/auth/login')
        ? { access_token: 'signed-in-token', user: { email: 'admin@example.test', role: 'admin' } }
        : input.endsWith('/auth/me') ? { email: 'admin@example.test', role: 'admin' }
          : input.endsWith('/incidents') ? [] : { status: 'ok', mode: 'demo' }
      return { ok: true, json: async () => body } as Response
    }))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><App/></MemoryRouter></QueryClientProvider>)
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'admin@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'strong-test-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(sessionStorage.getItem('aegisops_token')).toBe('signed-in-token'))
    await waitFor(() => expect(calls.some(call => (call.headers as Record<string, string>)?.Authorization === 'Bearer signed-in-token')).toBe(true))
  })
})
