# API reference

All `/api/v1` routes except `/health` and `/auth/login` require an `Authorization: Bearer <token>` header. `POST /auth/login` accepts an email and password and returns a 12-hour token. Failed logins return a generic 401 response; temporary account or client-IP throttling returns 429. `GET /auth/me` returns the account and role; `POST /auth/logout` revokes the token. Incident creation, analysis, and document ingestion require `operator` or `admin`; proposal approval and rejection require `reviewer` or `admin`. The server records the signed-in reviewer's email as the decision actor.

Base path: `/api/v1`. Interactive schemas are available at `/docs`.

| Resource | Operations |
| --- | --- |
| Health | `GET /health` |
| Incidents | `GET /incidents`, `POST /incidents`, `GET /incidents/{id}`, `POST /incidents/{id}/analyze`, `GET /incidents/{id}/timeline`, `GET /incidents/{id}/proposal`, `GET /incidents/{id}/report` |
| Agents | `GET /agents`, `GET /agents/runs`, `GET /agents/runs/{id}` |
| Approvals | `POST /approvals/{proposal_id}/approve`, `POST /approvals/{proposal_id}/reject` |
| Knowledge | `GET /knowledge/documents`, `POST /knowledge/documents`, `GET /knowledge/search?q=...` |
| Metrics | `GET /metrics/summary` |

Requests with invalid fields return 422, missing resources 404, repeated decisions or investigations pending approval 409. Local authentication and role checks are enabled, but SSO and MFA remain future work; keep the demo local.
