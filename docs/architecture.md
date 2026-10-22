# Architecture

FastAPI controllers validate and serialize requests, while `services/incidents.py` owns transactions and invokes the LangGraph graph. SQLAlchemy stores the incident lifecycle and run state. The graph itself has pure deterministic nodes in demo mode, apart from the optional Bedrock investigation adapter. Every agent step is copied into `agent_steps` for display. The approval route rehydrates the last graph state from `agent_runs.state`, supplies the decision, and routes directly to validation.

The current database migration creates the schema from the versioned model metadata. Future revisions should use explicit Alembic operations. PostgreSQL uses a native `vector(64)` column; SQLite tests use JSON vectors. No Redis is required.
