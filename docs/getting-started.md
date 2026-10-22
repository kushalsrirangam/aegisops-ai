# Getting started

Run `Copy-Item .env.example .env` in PowerShell or `cp .env.example .env` in Bash, then `docker compose up --build`. Open `http://localhost:5173`, select the seeded checkout incident, and run the investigation. The review panel provides approval and rejection controls. Swagger is at `http://localhost:8000/docs`. If Compose fails, check that Docker Desktop is running and ports 5173/8000 are available.
