import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

describe('navigation', () => {
  it('shows the demo boundary on settings', async () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/settings']}><App/></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Runtime configuration')).toBeTruthy()
    expect(await screen.findByText(/no agent can run shell commands/i)).toBeTruthy()
  })

  it('creates an incident through the API from the incidents page', async () => {
    const calls: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? 'GET'} ${input}`)
      const body = input.endsWith('/incidents') && init?.method === 'POST'
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
})
