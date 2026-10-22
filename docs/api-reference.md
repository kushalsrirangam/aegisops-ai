# API reference

Base path: `/api/v1`. Interactive schemas are available at `/docs`.

| Resource | Operations |
| --- | --- |
| Health | `GET /health` |
| Incidents | `GET /incidents`, `POST /incidents`, `GET /incidents/{id}`, `POST /incidents/{id}/analyze`, `GET /incidents/{id}/timeline`, `GET /incidents/{id}/proposal`, `GET /incidents/{id}/report` |
| Agents | `GET /agents`, `GET /agents/runs`, `GET /agents/runs/{id}` |
| Approvals | `POST /approvals/{proposal_id}/approve`, `POST /approvals/{proposal_id}/reject` |
| Knowledge | `GET /knowledge/documents`, `POST /knowledge/documents`, `GET /knowledge/search?q=...` |
| Metrics | `GET /metrics/summary` |

Requests with invalid fields return 422, missing resources 404, repeated decisions or investigations pending approval 409. The API currently has no authentication and must stay local.
