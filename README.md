# FIXORA

> **AI-assisted application validation and document verification for AICTE Extension of Approval (EoA) applications.**
>
> **DECISION SUPPORT ONLY**: The system flags issues with evidence; authorised humans decide. No endpoint or UI path may approve, reject, or penalise an application automatically. Prototype uses synthetic data and mock integrations.

---

## Architecture & Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Chart.js, Lucide Icons
- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2 (asyncpg), Alembic, Pydantic v2
- **Datastores**: PostgreSQL 16 (relational statutory state) + MongoDB 7 (document store & OCR evidence vault)
- **Document & ML Pipeline**: Tesseract OCR (with English and Hindi language packs: `eng` + `hin`), PyMuPDF, OpenCV, spaCy, sentence-transformers, FAISS
- **Infrastructure**: Docker Compose, GitHub Actions CI

---

## Repository Layout

```text
Fixora/
├── backend/
│   ├── app/
│   │   ├── core/         # Settings, structured logging, database engines
│   │   ├── models/       # SQLAlchemy 2 declarative models
│   │   ├── schemas/      # Pydantic v2 schemas and request/response contracts
│   │   ├── routers/      # API routes (all under /api)
│   │   ├── services/     # Business logic & pipeline execution
│   │   ├── workers/      # Asynchronous document processing workers
│   │   ├── adapters/     # External integrations & simulated source adapters
│   │   └── rules/        # Deterministic YAML rule pack loaders and evaluators
│   ├── tests/            # Pytest test suite
│   ├── Dockerfile        # Python 3.11 + Tesseract (eng+hin) container
│   ├── requirements.txt  # Python package dependencies
│   └── pyproject.toml    # Tool configurations (pytest, ruff)
├── frontend/
│   ├── src/              # React components, pages, types, styling
│   ├── Dockerfile        # Vite development container
│   ├── package.json      # Frontend dependencies
│   └── vite.config.ts    # Vite bundler & reverse proxy config
├── data/
│   ├── aph/              # AICTE Approval Process Handbook guidelines & norms
│   ├── synthetic/        # Synthetic applications and evaluation datasets
│   └── rulepacks/        # Deterministic YAML rule definitions
├── infra/                # Infrastructure configurations & deployment manifests
├── storage/              # Private, immutable uploaded documents & OCR artifacts (git-ignored)
├── .github/workflows/    # GitHub Actions CI workflow (linting + pytest)
├── docker-compose.yml    # Multi-container local orchestration
├── Makefile              # Developer task runner (up, down, test, seed, eval, lint)
├── .env.example          # Environment variable template
├── RULES.md              # Statutory guidelines and architecture rules
└── CLAUDE.md             # Developer instruction ("Read RULES.md before every task")
```

---

## Quickstart with Docker Compose

### 1. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. Start Services
Run the entire stack with hot-reloading for both backend and frontend:
```bash
make up
# or:
docker compose up -d --build
```

### 3. Verify System Health
Once services are running:
- **Frontend Dashboard**: Open [http://localhost:5173](http://localhost:5173) in your browser.
- **Backend API Docs (Swagger)**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

Example `/api/health` JSON response:
```json
{
  "status": "ok",
  "environment": "development",
  "timestamp": "2026-10-23T05:15:00.000000+00:00",
  "postgres": {
    "status": "connected",
    "details": "PostgreSQL 16 connection operational",
    "latency_ms": 1.45
  },
  "mongodb": {
    "status": "connected",
    "details": "MongoDB 7 connection operational",
    "latency_ms": 0.92
  }
}
```

---

## Demo Accounts & Statutory Roles

Fixora includes pre-seeded accounts for every statutory role in [RULES.md](file:///c:/Users/Vaidik%20Dubey/Desktop/Fixora/RULES.md) plus cross-institution isolation testing.

| Role | Email | Password | Institution Code & Name | Permissions Scope |
| :--- | :--- | :--- | :--- | :--- |
| **`admin`** | `admin@aicte.gov.in` | `Admin@Fixora2026!` | *Global AICTE System* | Full system administration, user management, and rule pack governance |
| **`scrutiny_officer`** | `scrutiny@aicte.gov.in` | `Scrutiny@Fixora2026!` | *AICTE Scrutiny Bureau* | Cross-institution review of applications in `READY_FOR_SCRUTINY`, officer actions |
| **`verification_officer`** | `verification@aicte.gov.in` | `Verification@Fixora2026!` | *AICTE Verification Bureau* | External registry comparisons, manual verification queue confirmations |
| **`institution` (1)** | `principal@gecpune.edu.in` | `Inst1@Fixora2026!` | `1-33276541` - Govt. Eng. College Pune | Own applications & documents only (`APP-EOA-2024-00001`, `D-001`) |
| **`institution` (2)** | `director@mitmumbai.edu.in` | `Inst2@Fixora2026!` | `1-44589210` - Maharashtra Inst. of Tech. | Own applications & documents only (`APP-EOA-2024-00002`, `D-002`) |

> [!NOTE]
> **Authentication Specifications**:
> - Token type: JWT signed with HS256, access token expiration of **60 minutes**.
> - Rate Limiting: Max 5 login attempts per 60 seconds per IP/email. Exceeding triggers HTTP 429 (`RATE_LIMIT_EXCEEDED`).
> - Statutory Institution Scoping: Attempting cross-institution document or application access immediately returns HTTP 403 Forbidden with standard envelope:
>   `{"error": {"code": "FORBIDDEN", "message": "Access forbidden: cross-institution resource access is strictly prohibited."}}`
> - PII Data Masking: Personal identifiers (Aadhaar, PAN, phone numbers, contact emails) are masked across institutional responses and backend structured logs.

---

## Development Commands (`Makefile`)

| Command | Action |
| :--- | :--- |
| `make up` | Build and start all services via Docker Compose |
| `make down` | Stop all running containers |
| `make test` | Run the backend pytest test suite |
| `make seed` | Trigger synthetic demo data seeding (`POST /api/demo/seed`) |
| `make eval` | Execute statutory rulepack & model evaluation suite |
| `make lint` | Run Ruff linter on backend and TypeScript check on frontend |

---

## Local Development (Without Docker)

### Backend
1. Create a Python 3.11 virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Start local PostgreSQL and MongoDB instances, then run:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
4. Run tests:
   ```bash
   pytest backend/tests/
   ```

### Frontend
1. Navigate to `frontend`:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```

---

## Conventions & Rules

- **API Contract**: All endpoints live under `/api`.
- **JSON Format**: Strict `snake_case`.
- **Errors**: Uniform envelope: `{"error": {"code": "...", "message": "..."}}`.
- **Lists**: Uniform pagination: `{"items": [], "total": 0, "page": 1, "page_size": 20}`.
- **Timestamps**: ISO-8601 UTC.
- **Language**: Never use the words *fake*, *forged*, or *fraud*. Anomaly findings carry the label *"Preliminary indicator - human verification required"*.
