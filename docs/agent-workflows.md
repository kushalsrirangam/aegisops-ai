# Agent workflow

The initial graph starts at triage and proceeds through investigation and knowledge. Supervisor routes to remediation if confidence is at least 0.6, otherwise escalation. Security checks proposals for a small list of destructive phrases; blocked proposals escalate. A safe proposal ends the graph at `awaiting_approval`. After a reviewer posts approve or reject, the service invokes the graph again with the persisted state and decision. Validation writes a simulated outcome or an unverified real-mode note. The API uses `recursion_limit=16`.

This is a demonstration of explicit graph state, conditional edges, and human decision resumption. It does not use native LangGraph checkpointers or automatic retries. A production system should add durable checkpoints, idempotency keys, background workers, and a policy engine.
