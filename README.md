# Kyronix Core

Kyronix Core is Kyronix LLC's employee system, deployed at https://core.kyronix.ai.

## Phase 0 constraints

- Product name: Kyronix Core (use this in all UI text)
- Employer legal name: Kyronix LLC
- Time zone: America/Los_Angeles (Pacific Time)
- All documents are generated as PDFs
- All access is role-based (EMPLOYEE vs ADMIN)
- All document access and generation events are logged
- v1 excludes advanced analytics and benefits features

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React + Vite + TypeScript
- Database: Postgres

## Local development

1) Copy environment files
- `backend/.env.example` -> `backend/.env`
- `frontend/.env.example` -> `frontend/.env`

2) Start services
```sh
docker compose up --build
```

3) Initialize the database (first run only)
```sh
docker compose exec backend python -m app.db.init_db
```

4) Open the app
- Frontend: http://localhost:5173
- API health: http://localhost:8000/api/health

Default admin credentials are read from `backend/.env`.
