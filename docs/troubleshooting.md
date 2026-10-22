# Troubleshooting

- **Docker API unavailable:** start Docker Desktop and wait for its engine.
- **Port 5173 or 8000 occupied:** stop the conflicting process or change the host side of the Compose port mapping.
- **Backend migration failure:** inspect `docker compose logs backend db`. `pgvector/pgvector:pg16` is required for the native vector column.
- **Frontend cannot reach API:** confirm `docker compose ps` shows a healthy backend; the Nginx `/api/` route proxies to the backend service.
- **Bedrock failure:** confirm AWS credentials/role, region, model access, and `bedrock:InvokeModel` permission. Demo mode needs none of these.
