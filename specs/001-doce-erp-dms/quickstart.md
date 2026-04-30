# Quickstart: DocERP — Development Setup

**Phase**: 1 — Design  
**Date**: 2026-04-29  
**Related**: [plan.md](./plan.md) | [contracts/rest-api.md](./contracts/rest-api.md)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| uv | latest | Python dependency management |
| Node.js | 20 LTS | Frontend build tooling |
| Docker + Docker Compose | 24+ | PostgreSQL 16, Redis 7, local dev stack |
| Git | 2.40+ | Version control |

---

## 1. Clone & Environment Setup

```bash
git clone <internal-gerrit-or-github-url> docerp
cd docerp

# Copy environment template
cp backend/.env.example backend/.env
# Edit backend/.env — set DB_URL, REDIS_URL, LDAP_URL, LLM_API_KEY, etc.
```

---

## 2. Start Infrastructure (PostgreSQL + Redis)

```bash
docker compose up -d postgres redis
```

Services will start at:
- PostgreSQL: `localhost:5432` (db: `docerp`, user: `docerp`, pass: from `.env`)
- Redis: `localhost:6379`

---

## 3. Backend Setup

```bash
cd backend

# Install dependencies with uv
uv sync

# Run database migrations
uv run alembic upgrade head

# (Optional) Seed baseline FMEDA failure mode library
uv run python scripts/seed_fmeda_library.py

# Start API server (development)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (dependency engine + cascade lock)
uv run celery -A app.tasks worker -Q cascade_lock,dependency,export,maintenance --loglevel=info

# Start Celery beat scheduler (daily maintenance tasks)
uv run celery -A app.tasks beat --loglevel=info
```

API available at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server (proxies /api to localhost:8000)
npm run dev
```

App available at: `http://localhost:5173`

---

## 5. Run Tests

```bash
# Backend — unit + integration
cd backend
uv run pytest tests/ -v

# Backend — contract tests only
uv run pytest tests/contract/ -v

# Frontend — unit tests
cd frontend
npm run test

# E2E (requires both backend and frontend running)
npm run test:e2e
```

---

## 6. LDAP / AD Development Stub

For local development without an LDAP server, set:

```env
LDAP_ENABLED=false
```

The backend will skip LDAP bind and allow any username/password combination with a local account lookup. Do **not** use this mode in any staging or production environment.

---

## 7. Docker Compose Full Stack (Optional)

```bash
# Start all services including backend + frontend
docker compose up --build

# Access at http://localhost:3000
```

---

## 8. Key Configuration Variables (`backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async DSN | `postgresql+asyncpg://docerp:pass@localhost:5432/docerp` |
| `REDIS_URL` | Redis DSN | `redis://localhost:6379/0` |
| `LDAP_URL` | LDAP server URL | `ldap://ad.siliconmotion.internal:389` |
| `LDAP_BIND_DN` | Service account DN | `cn=docerp-svc,ou=service,dc=siliconmotion,dc=internal` |
| `LDAP_BIND_PASSWORD` | Service account password | (secret) |
| `LDAP_USER_BASE_DN` | User search base | `ou=users,dc=siliconmotion,dc=internal` |
| `LLM_API_KEY` | Cloud LLM API key | (secret) |
| `LLM_API_BASE_URL` | LLM endpoint | `https://api.openai.com/v1` |
| `LLM_MAX_CONTEXT_TOKENS` | Context cap per query (FR-033) | `2000` |
| `AUDIT_PACKAGE_STORAGE_PATH` | On-premise filesystem path | `/data/docerp/audit-packages` |
| `AUDIT_PACKAGE_VOLUME_GB` | Storage quota threshold baseline | `100` |
| `SECRET_KEY` | JWT signing secret | (generate with: `openssl rand -hex 32`) |

---

## 9. First-Time Admin Setup

1. Navigate to `http://localhost:5173/admin/setup`
2. Create the first local admin account (used only when LDAP is unavailable).
3. Import the org hierarchy (CSV or JSON) via `Admin → Organisation → Import`.
4. Configure the active CodeBeamer schema version under `Admin → Export → CodeBeamer Schema`.
5. Assign BU-scoped roles to users via `Admin → Roles`.

---

## Key Workflows to Verify

| Workflow | Steps |
|----------|-------|
| Project creation | PM logs in → AI Wizard → 6–8 questions → document framework generated |
| Spec editing + AI consult | RD opens Spec → clicks AI Consult → reviews suggestions → Accept/Reject |
| Cascade Lock | Architect saves top-level Spec → dependent Specs show LOCKED banner → owner reviews diff → marks Reviewed |
| QRA approval | Safety-critical Spec in PENDING_QRA → QRA auditor approves → APPROVED auto-set |
| Audit export | PM/Auditor triggers export → xlsx downloaded → validation report shown |
| Git commit | RD clicks Commit in DocERP → SHA returned — verify in Gerrit/GitHub |
