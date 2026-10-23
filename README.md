# AegisOps AI

**A local-first, multi-agent incident investigation console with cited runbooks and human-approved remediation proposals.**

Cloud incident response often starts with scattered alerts, logs, deployment notes, and runbooks. AegisOps AI brings those signals into a traceable workflow. The local demo is synthetic and requires no AWS account or paid model. It is an engineering portfolio project, **not a production incident controller**.

## What it does

- Creates and persists incidents, events, agent runs, steps, proposals, decisions, reports, and audit records.
- Runs seven agent roles in a real LangGraph graph with conditional routing and a bounded execution limit.
- Finds relevant runbook chunks with deterministic local embeddings; PostgreSQL uses pgvector cosine search.
- Pauses LangGraph after security review, saves a PostgreSQL checkpoint, and resumes after a human approval or rejection.
- Displays evidence, citations, trace steps, proposal risk, and a clearly labeled simulated outcome. Bedrock approvals remain marked `needs_verification` until an operator checks real recovery.
- Optionally asks Claude through Amazon Bedrock for a structured root-cause hypothesis based on supplied evidence or read-only CloudWatch logs.

## Architecture

```mermaid
flowchart LR
  UI[React operations console] --> API[FastAPI v1]
  API --> DB[(PostgreSQL + pgvector)]
  API --> G[LangGraph workflow]
  G --> R[Runbook retrieval]
  G --> M[Mock observations]
  G -. optional .-> AWS[CloudWatch + Bedrock]
  API --> A[Approval and audit records]
```

```mermaid
flowchart LR
  T[Triage] --> I[Investigation] --> K[Knowledge] --> S[Supervisor]
  S -->|high confidence| R[Remediation] --> SEC[Security]
  S -->|low confidence| E[Escalation]
  SEC -->|safe proposal| H[Human decision]
  SEC -->|unsafe| E
  H --> V[Validation report]
```

The **supervisor** routes by evidence confidence. **Triage** classifies severity and service. **Investigation** correlates log evidence and forms a hypothesis. **Knowledge** supplies cited runbook excerpts. **Remediation** writes a proposal only. **Security** checks the proposal against a deny-by-default review catalog and requires human approval. **Validation** records a simulated result in demo mode; in Bedrock mode it explicitly leaves recovery unverified. The graph has a recursion limit of 16. PostgreSQL stores native LangGraph checkpoints for paused runs; relational run state and steps remain available for the dashboard. Approval resumes the same graph thread. Older pending runs created before checkpoints still use their saved relational state.

## Stack and layout

| Layer | Technology |
| --- | --- |
| UI | React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts |
| API | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Workflow | LangGraph with structured shared state |
| Data | PostgreSQL 16, pgvector; SQLite for isolated tests |
| Optional cloud | Boto3 CloudWatch read calls and Bedrock runtime |
| Quality | pytest, Vitest, ESLint, Ruff, GitHub Actions |

`frontend/` contains the dashboard, `backend/` contains the API, graph, services, models, and migrations, `data/` holds synthetic examples, `infrastructure/` holds the read-only IAM example, and `docs/` has deeper design notes.

## Prerequisites and quick start

Install Docker Desktop with Compose. On Windows, start Docker Desktop before running Compose. Ports **5173** and **8000** must be free.

```bash
git clone https://github.com/kushalsrirangam/aegisops-ai.git
cd aegisops-ai
cp .env.example .env
docker compose up --build
```

PowerShell:

```powershell
git clone https://github.com/kushalsrirangam/aegisops-ai.git
Set-Location aegisops-ai
Copy-Item .env.example .env
docker compose up --build
```

The frontend is at [http://localhost:5173](http://localhost:5173), the API at [http://localhost:8000](http://localhost:8000), and Swagger at [http://localhost:8000/docs](http://localhost:8000/docs). The backend applies migrations, initializes LangGraph checkpoint tables, and loads one synthetic incident and runbook on startup. Create your first local admin account in another terminal:

```bash
docker compose exec backend python -m app.core.users_cli create-user --email you@example.com --role admin
```

The command prompts for a password of at least 12 characters; no shared password is shipped. Sign in at the frontend, open the seeded incident, select **Run investigation**, review the trace and proposal, then approve or reject it. Both paths persist a report. `docker compose down` stops services; `docker compose down -v` also removes local database data.

Five failed sign-ins for one account or 30 from one client IP within 15 minutes trigger a 15-minute cooldown. A local administrator can clear an account lock or set a new password, which revokes that account's sessions:

```bash
docker compose exec backend python -m app.core.users_cli unlock-user --email you@example.com
docker compose exec backend python -m app.core.users_cli reset-password --email you@example.com
```

The reset command prompts for the new password. The IP cooldown remains in force; wait for it to expire if the same client IP was also throttled.

## Configuration

`.env.example` documents `DATABASE_URL`, `APP_MODE`, AWS settings, and `CORS_ORIGINS`. Compose supplies local database values directly. No secrets are required for demo mode. Do not commit `.env`.

For backend development outside Docker, use a PostgreSQL URL for the `db` service on a published port, or use `DATABASE_URL=sqlite:///./aegisops.db` for lightweight local work. From `backend/`:

```bash
python -m venv .venv
# Activate the virtual environment for your shell.
pip install -e '.[dev]'
alembic upgrade head
python -m app.orchestration.checkpointing
python -m app.seed
uvicorn app.main:app --reload
```

From `frontend/`:

```bash
npm ci
npm run dev
```

Vite proxies `/api` to `localhost:8000`. For a standalone frontend production build, use `npm run build`.

## Sample API requests

```bash
curl http://localhost:8000/api/v1/incidents
curl -X POST http://localhost:8000/api/v1/incidents/1/analyze
curl http://localhost:8000/api/v1/agents/runs/1
curl http://localhost:8000/api/v1/incidents/1/proposal
curl -X POST http://localhost:8000/api/v1/approvals/1/approve \
  -H 'Content-Type: application/json' -d '{"actor":"local-operator","reason":"Reviewed runbook"}'
curl http://localhost:8000/api/v1/incidents/1/report
```

Use `/reject` instead of `/approve` for the rejection path. The API also supports incident filters and pagination, runbook ingestion and search, timeline, agent catalog, and summary metrics. See [API reference](docs/api-reference.md) or Swagger for schemas.

## Tests and evaluation

```bash
cd backend
ruff check app tests
python -m compileall -q app
pytest -q
cd ../frontend
npm run lint
npm test
npm run build
cd ..
docker compose config
```

Tests cover graph routes, checkpointed pause and resume, confidence escalation, blocked operations, cited retrieval, incident API, authenticated role checks, approval and rejection, failure responses, and a key UI disclosure. Backend CI also starts a fresh PostgreSQL 16 and pgvector service, applies Alembic migrations, initializes LangGraph tables, and tests vector search plus both decision paths and persisted records. The integration test runs locally when `INTEGRATION_DATABASE_URL` points to a separate migrated test database. [Evaluation notes](docs/evaluation.md) describe what these tests do and do not prove.

## Bedrock and AWS

Set `APP_MODE=bedrock` for a separate deployment of the backend, configure `AWS_REGION`, `BEDROCK_MODEL_ID`, and AWS credentials through standard AWS environment or role-based resolution. Grant `bedrock:InvokeModel` for the selected model, `logs:FilterLogEvents` for configured groups, and `cloudwatch:GetMetricStatistics` if using metrics; see the [IAM example](infrastructure/terraform/read-only-policy.json). CloudWatch log lookup targets `/ecs/aegisops/<service>`. To read a custom error-rate metric, set `AWS_ERROR_RATE_METRIC_NAMESPACE` to its namespace. The defaults expect a Percent-valued `ErrorRate` metric with dimension `Service=<incident service>`, sampled over the last five minutes. The latest one-minute average is converted to a fraction. Missing datapoints stop analysis with a clear error; an unconfigured metric is labeled unavailable in the trace. Logs or a fractional `error_rate` can be supplied in incident evidence instead. Bedrock is used for the investigation hypothesis; the other agents currently remain deterministic. Bedrock mode **does not verify recovery** or modify AWS resources. Model access, availability, cost, and permissions are the operator's responsibility.

## Security and approval model

This local demo requires sign-in. Operators can create incidents, run investigations, and add runbooks; reviewers can approve or reject; admins can do both. Passwords are salted and hashed with scrypt; bearer sessions expire after 12 hours and can be revoked by signing out. Failed-login limits and temporary lockouts persist in PostgreSQL. No default account is shipped. This is still **not a production identity system**: there is no SSO, MFA, or administrative user lifecycle API. Do not expose it publicly. API input is validated; model outputs are schema checked; retrieved runbooks are treated as data; AWS access is read-only; agents never execute shell or infrastructure operations. Approval creates an audit record and advances report generation, never a deployment. The security agent allows only a cataloged proposal for review; production execution would need separate authorization at the action boundary. See [security](docs/security.md).

## Demo versus production

| Capability | Current state |
| --- | --- |
| Local seeded scenario and full approval flow | Implemented |
| Persistent incidents, runs, approvals, reports | Implemented in PostgreSQL via Compose |
| Cited runbook retrieval | Implemented; deterministic embedding quality is limited |
| Bedrock hypothesis | Optional integration; requires AWS access |
| CloudWatch logs | Optional read-only integration; fixed log group convention |
| Live CloudWatch metric mapping | Optional, read-only custom Percent `ErrorRate`; requires explicit namespace and dimension mapping |
| Local authentication and RBAC | Implemented with temporary login lockouts and local recovery commands; SSO, MFA, and account lifecycle API remain open |
| Durable LangGraph checkpoint store | PostgreSQL checkpoints and native approval resume implemented; historical runs retain relational fallback |
| ECS/Fargate Terraform deployment | IAM policy generation module only; no deployable application stack |

## Deployment approach and next steps

The [deployment guide](docs/deployment.md) outlines the required VPC, ECS/Fargate, RDS pgvector, secret storage, and IAM boundaries. A production milestone should add SSO, MFA, rate limits, and reviewed policy rules. No Terraform apply or deployment is triggered by this repository.

See [architecture](docs/architecture.md), [workflow](docs/agent-workflows.md), [getting started](docs/getting-started.md), [troubleshooting](docs/troubleshooting.md), and [evaluation](docs/evaluation.md).

## License

[MIT](LICENSE).
