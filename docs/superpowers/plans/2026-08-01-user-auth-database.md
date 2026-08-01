# User Auth & PostgreSQL Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the DataMind backend a real PostgreSQL database with a full schema (users, projects, frameworks, datasets, workflow state, reports/citations, RAG paper library with pgvector embeddings) and an email+password login mechanism using Flask-Login session cookies.

**Architecture:** SQLAlchemy models live in `backend/models/`, one file per table group, all registered on a shared `db` instance from `backend/extensions.py`. Alembic manages schema migrations, one migration per task so each task's tables land independently. Auth is Flask-Login backed by a signed session cookie (no separate sessions table) with bcrypt-hashed passwords. Postgres runs as a new `docker-compose.yml` service using the `pgvector/pgvector` image so the vector extension is available out of the box.

**Tech Stack:** PostgreSQL 16 + pgvector, SQLAlchemy 2.0-style models via Flask-SQLAlchemy, Alembic, Flask-Login, bcrypt, uv (existing package manager).

## Global Constraints

- Python `>=3.10,<3.12` (from `backend/pyproject.toml`) — `str | None` union syntax is fine, this is not Python 3.9
- Dependencies are managed with `uv`, not raw `pip` — always use `uv add <package>` from `backend/`, never edit `pyproject.toml`'s dependency list by hand and never run bare `pip install`
- No unit test framework is configured in `backend/` — verification is standalone Python scripts run directly with `python`, `curl` against a running dev server, and direct `psql` queries
- `CitationStyle` enum values are exactly `'apa' | 'ieee' | 'mla'` (matching the already-shipped frontend feature in `frontend/src/constants/reportData.ts`)
- pgvector embedding dimension is exactly `384` (matches the existing `BAAI/bge-small-zh-v1.5` model, documented in `backend/docs/rag-paper-generation.md`)
- Flask app factory pattern: all blueprints are registered inside `create_app()` in `backend/apps/__init__.py` — follow this existing pattern, don't introduce a different wiring style
- Design spec: `docs/superpowers/specs/2026-08-01-user-auth-database-design.md`; technical schema reference: `backend/docs/database-architecture.md`
- Out of scope, do not implement: frontend login/register UI, `@login_required` applied to any existing route, data migration scripts moving current localStorage/JSON data into the new tables, Google OAuth, forgot-password/email verification

---

### Task 1: Environment scaffold — Postgres service, dependencies, SQLAlchemy/Flask-Login wiring

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/pyproject.toml` (via `uv add`, not hand-edited)
- Create: `backend/extensions.py`
- Modify: `backend/apps/__init__.py`
- Modify: `backend/.env` (local file, not committed)

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: `db` (a `flask_sqlalchemy.SQLAlchemy` instance) and `login_manager` (a `flask_login.LoginManager` instance), both importable from `backend/extensions.py` — every later task's models and routes import `db` from here; Task 6 imports `login_manager` from here

- [ ] **Step 1: Add the Postgres service to docker-compose.yml**

Replace:

```yaml
  n8n:
    image: n8nio/n8n:latest
    container_name: datamind-n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_SECURE_COOKIE=false
      - WEBHOOK_URL=https://ideally-strewn-papyrus.ngrok-free.dev
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  whisper-cache:
  n8n_data:
  frontend_node_modules:
  backend_venv:
```

With:

```yaml
  n8n:
    image: n8nio/n8n:latest
    container_name: datamind-n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_SECURE_COOKIE=false
      - WEBHOOK_URL=https://ideally-strewn-papyrus.ngrok-free.dev
    volumes:
      - n8n_data:/home/node/.n8n

  postgres:
    image: pgvector/pgvector:pg16
    container_name: datamind-postgres
    environment:
      POSTGRES_USER: datamind
      POSTGRES_PASSWORD: datamind
      POSTGRES_DB: datamind
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  whisper-cache:
  n8n_data:
  frontend_node_modules:
  backend_venv:
  postgres_data:
```

(The password is a plain local-dev default here, matching how this file already handles other local-only settings like `N8N_SECURE_COOKIE=false` — not a secret worth `.env`-templating for a docker-compose file that's already checked into git with other plaintext dev config.)

- [ ] **Step 2: Start Postgres and verify it's reachable**

Run: `docker compose up -d postgres`
Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "SELECT 1;"`
Expected: prints a row with `1`, confirming the container is up and accepting connections.

- [ ] **Step 3: Add the new Python dependencies**

Run (from `backend/`): `uv add flask-sqlalchemy flask-login alembic psycopg2-binary bcrypt pgvector`
Expected: exits 0; `backend/pyproject.toml`'s `dependencies` array now includes these 6 packages, and `backend/uv.lock` is updated.

- [ ] **Step 4: Create the shared extensions module**

Create `backend/extensions.py`:

```python
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
```

- [ ] **Step 5: Wire SQLAlchemy and Flask-Login into the app factory**

Replace (`backend/apps/__init__.py`):

```python
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    max_content_length_mb = int(os.getenv("MAX_CONTENT_LENGTH_MB", "100"))
    app.config["MAX_CONTENT_LENGTH"] = max_content_length_mb * 1024 * 1024

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_: RequestEntityTooLarge):
        return (
            jsonify(
                {
                    "error": "Request entity too large."
                    f" Increase MAX_CONTENT_LENGTH_MB if you need to upload bigger files.",
                }
            ),
            413,
        )

    cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
    CORS(app, resources={r"/api/*": {"origins": cors_origin}})

    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")

    @app.get("/")
    def root():
        return jsonify(
            {
                "name": "DataMind Backend",
                "message": "Backend service is running",
                "health": "/api/health",
                "stt": "/api/stt/transcribe",
                "rag": "/api/rag",
                "gemini": "/api/gemini",
                "mineru": "/api/mineru",
            }
        )

    return app
```

With:

```python
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from extensions import db, login_manager


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    max_content_length_mb = int(os.getenv("MAX_CONTENT_LENGTH_MB", "100"))
    app.config["MAX_CONTENT_LENGTH"] = max_content_length_mb * 1024 * 1024
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_: RequestEntityTooLarge):
        return (
            jsonify(
                {
                    "error": "Request entity too large."
                    f" Increase MAX_CONTENT_LENGTH_MB if you need to upload bigger files.",
                }
            ),
            413,
        )

    cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
    CORS(app, resources={r"/api/*": {"origins": cors_origin}}, supports_credentials=True)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")

    @app.get("/")
    def root():
        return jsonify(
            {
                "name": "DataMind Backend",
                "message": "Backend service is running",
                "health": "/api/health",
                "stt": "/api/stt/transcribe",
                "rag": "/api/rag",
                "gemini": "/api/gemini",
                "mineru": "/api/mineru",
            }
        )

    return app
```

`supports_credentials=True` is required so the browser will send the session cookie on cross-origin requests (frontend dev server and backend run on different ports) once a real login flow exists — it has no effect on today's cookie-less routes.

`login_manager.import`/blueprint registrations for auth come in Task 6; this step only wires the extensions themselves.

- [ ] **Step 6: Add required environment variables**

Add to `backend/.env` (create the file if it doesn't exist yet — it's gitignored):

```
DATABASE_URL=postgresql://datamind:datamind@localhost:5432/datamind
FLASK_SECRET_KEY=dev-secret-change-me-in-production
```

- [ ] **Step 7: Verify the app factory still starts cleanly**

Run (from `backend/`): `uv run python -c "from apps import create_app; app = create_app(); print('OK', app.name)"`
Expected: prints `OK apps` with no errors or tracebacks. (No models exist yet, so `db`/`login_manager` are wired but idle — this only confirms the factory itself doesn't crash.)

- [ ] **Step 8: Commit**

```bash
git add docker-compose.yml backend/pyproject.toml backend/uv.lock backend/extensions.py backend/apps/__init__.py
git commit -m "feat: add Postgres+pgvector service and wire SQLAlchemy/Flask-Login into the app factory"
```

---

### Task 2: `User`, `Framework`, `Project` models + first migration

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/user.py`
- Create: `backend/models/framework.py`
- Create: `backend/models/project.py`
- Create: `backend/migrations/` (via `alembic init`)
- Create: `backend/alembic.ini` (via `alembic init`)
- Modify: `backend/migrations/env.py`

**Interfaces:**
- Consumes: `db` from `backend/extensions.py` (Task 1)
- Produces: `User` (with `id`, `email`, `password_hash`, `display_name`, `is_admin`, `created_at`) importable from `models.user`; `Framework` importable from `models.framework`; `Project` (with `ProjectStatus` enum) importable from `models.project` — Task 3 imports `Project` for its `project_id` foreign keys; Task 6 imports `User` for auth routes

- [ ] **Step 1: Create the User model with its Flask-Login user loader**

Create `backend/models/user.py`:

```python
import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )


@login_manager.user_loader
def load_user(user_id: str) -> "User | None":
    return db.session.get(User, int(user_id))
```

- [ ] **Step 2: Create the Framework model**

Create `backend/models/framework.py`:

```python
import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class Framework(db.Model):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variables: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paper_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    independent_vars: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    dependent_vars: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    hypotheses: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    workflow_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
```

- [ ] **Step 3: Create the Project model**

Create `backend/models/project.py`:

```python
import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class ProjectStatus(enum.Enum):
    draft = "draft"
    running = "running"
    completed = "completed"


class Project(db.Model):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"), nullable=True)
    dataset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"), default=ProjectStatus.draft, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    key_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )
```

- [ ] **Step 4: Create the models package init**

Create `backend/models/__init__.py`:

```python
from extensions import db
from models.framework import Framework
from models.project import Project
from models.user import User

__all__ = ["db", "User", "Framework", "Project"]
```

- [ ] **Step 5: Initialize Alembic**

Run (from `backend/`): `uv run alembic init migrations`
Expected: creates `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/` (empty).

- [ ] **Step 6: Point Alembic at the app's models and DATABASE_URL**

In `backend/migrations/env.py`, find this block near the top (generated by `alembic init`):

```python
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None
```

Replace it with:

```python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from alembic import context

from models import db  # noqa: E402  (import must follow sys.path insert above)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = db.metadata
```

- [ ] **Step 7: Generate and apply the first migration**

Run (from `backend/`): `uv run alembic revision --autogenerate -m "create users, frameworks, projects"`
Expected: creates a new file under `backend/migrations/versions/`; its `upgrade()` function should contain `op.create_table("users", ...)`, `op.create_table("frameworks", ...)`, `op.create_table("projects", ...)` (order may vary; Alembic resolves FK dependency order automatically).

Run: `uv run alembic upgrade head`
Expected: exits 0, no errors.

- [ ] **Step 8: Verify the tables exist with a direct query**

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "\d users" -c "\d frameworks" -c "\d projects"`
Expected: prints the column list for all three tables, matching the fields defined in the models above.

- [ ] **Step 9: Commit**

```bash
git add backend/models/ backend/migrations/ backend/alembic.ini
git commit -m "feat: add User, Framework, Project models and first migration"
```

---

### Task 3: `Dataset`, `WorkflowState` models + migration

**Files:**
- Create: `backend/models/dataset.py`
- Create: `backend/models/workflow_state.py`
- Modify: `backend/models/__init__.py`

**Interfaces:**
- Consumes: `db` from `extensions.py` (Task 1); `Project` from `models.project` (Task 2, for the `project_id` foreign key)
- Produces: `Dataset`, `WorkflowState` importable from `models` — no later task depends on these directly, but they must be registered on `db.metadata` before the migration in this task runs

- [ ] **Step 1: Create the Dataset model**

Create `backend/models/dataset.py`:

```python
import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class Dataset(db.Model):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
```

- [ ] **Step 2: Create the WorkflowState model**

Create `backend/models/workflow_state.py`:

```python
import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class WorkflowState(db.Model):
    __tablename__ = "workflow_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), unique=True, nullable=False
    )
    state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )
```

- [ ] **Step 3: Register the new models**

Replace (`backend/models/__init__.py`):

```python
from extensions import db
from models.framework import Framework
from models.project import Project
from models.user import User

__all__ = ["db", "User", "Framework", "Project"]
```

With:

```python
from extensions import db
from models.dataset import Dataset
from models.framework import Framework
from models.project import Project
from models.user import User
from models.workflow_state import WorkflowState

__all__ = ["db", "User", "Framework", "Project", "Dataset", "WorkflowState"]
```

- [ ] **Step 4: Generate and apply the migration**

Run (from `backend/`): `uv run alembic revision --autogenerate -m "create datasets, workflow_states"`
Expected: new file under `backend/migrations/versions/` with `op.create_table("datasets", ...)` and `op.create_table("workflow_states", ...)`.

Run: `uv run alembic upgrade head`
Expected: exits 0, no errors.

- [ ] **Step 5: Verify with a direct query**

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "\d datasets" -c "\d workflow_states"`
Expected: prints both tables' columns, matching the models above.

- [ ] **Step 6: Commit**

```bash
git add backend/models/dataset.py backend/models/workflow_state.py backend/models/__init__.py backend/migrations/versions/
git commit -m "feat: add Dataset, WorkflowState models and migration"
```

---

### Task 4: `Report`, `Citation` models + migration

**Files:**
- Create: `backend/models/report.py`
- Modify: `backend/models/__init__.py`

**Interfaces:**
- Consumes: `db` from `extensions.py` (Task 1); `Project` from `models.project` (Task 2)
- Produces: `Report` (with `CitationStyle` enum), `Citation` importable from `models` — no later task depends on these directly, but they must be registered before this task's migration runs

- [ ] **Step 1: Create the Report and Citation models**

Create `backend/models/report.py`:

```python
import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class CitationStyle(enum.Enum):
    apa = "apa"
    ieee = "ieee"
    mla = "mla"


class Report(db.Model):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    citation_style: Mapped[CitationStyle] = mapped_column(
        Enum(CitationStyle, name="citation_style"),
        default=CitationStyle.apa,
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )


class Citation(db.Model):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[str] = mapped_column(String(500), nullable=False)
    journal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 2: Register the new models**

Replace (`backend/models/__init__.py`):

```python
from extensions import db
from models.dataset import Dataset
from models.framework import Framework
from models.project import Project
from models.user import User
from models.workflow_state import WorkflowState

__all__ = ["db", "User", "Framework", "Project", "Dataset", "WorkflowState"]
```

With:

```python
from extensions import db
from models.dataset import Dataset
from models.framework import Framework
from models.project import Project
from models.report import Citation, Report
from models.user import User
from models.workflow_state import WorkflowState

__all__ = [
    "db",
    "User",
    "Framework",
    "Project",
    "Dataset",
    "WorkflowState",
    "Report",
    "Citation",
]
```

- [ ] **Step 3: Generate and apply the migration**

Run (from `backend/`): `uv run alembic revision --autogenerate -m "create reports, citations"`
Expected: new file with `op.create_table("reports", ...)` and `op.create_table("citations", ...)`.

Run: `uv run alembic upgrade head`
Expected: exits 0, no errors.

- [ ] **Step 4: Verify with a direct query**

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "\d reports" -c "\d citations"`
Expected: prints both tables' columns; `reports.citation_style` should show as a `citation_style` enum type with default `'apa'::citation_style`.

- [ ] **Step 5: Commit**

```bash
git add backend/models/report.py backend/models/__init__.py backend/migrations/versions/
git commit -m "feat: add Report, Citation models and migration"
```

---

### Task 5: `RagPaper`, `RagChunk` models (pgvector) + migration

**Files:**
- Create: `backend/models/rag_paper.py`
- Modify: `backend/models/__init__.py`
- Modify: the migration file generated in this task's Step 3 (to enable the pgvector extension)

**Interfaces:**
- Consumes: `db` from `extensions.py` (Task 1); `Project` from `models.project` (Task 2)
- Produces: `RagPaper`, `RagChunk`, `EMBEDDING_DIM = 384` importable from `models.rag_paper` — no later task in this plan depends on these, but future work (the deferred data-migration sub-project) will

- [ ] **Step 1: Create the RagPaper and RagChunk models**

Create `backend/models/rag_paper.py`:

```python
import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db

EMBEDDING_DIM = 384


class RagPaper(db.Model):
    __tablename__ = "rag_papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )


class RagChunk(db.Model):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("rag_papers.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 2: Register the new models**

Replace (`backend/models/__init__.py`):

```python
from extensions import db
from models.dataset import Dataset
from models.framework import Framework
from models.project import Project
from models.report import Citation, Report
from models.user import User
from models.workflow_state import WorkflowState

__all__ = [
    "db",
    "User",
    "Framework",
    "Project",
    "Dataset",
    "WorkflowState",
    "Report",
    "Citation",
]
```

With:

```python
from extensions import db
from models.dataset import Dataset
from models.framework import Framework
from models.project import Project
from models.rag_paper import RagChunk, RagPaper
from models.report import Citation, Report
from models.user import User
from models.workflow_state import WorkflowState

__all__ = [
    "db",
    "User",
    "Framework",
    "Project",
    "Dataset",
    "WorkflowState",
    "Report",
    "Citation",
    "RagPaper",
    "RagChunk",
]
```

- [ ] **Step 3: Generate the migration**

Run (from `backend/`): `uv run alembic revision --autogenerate -m "create rag_papers, rag_chunks"`
Expected: new file under `backend/migrations/versions/` with `op.create_table("rag_papers", ...)` and `op.create_table("rag_chunks", ...)`, including a `sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False)` (or equivalent import) on `rag_chunks`.

- [ ] **Step 4: Add the pgvector extension enable statement**

Open the migration file generated in Step 3. At the very top of the `upgrade()` function (before the first `op.create_table(...)` call), add:

```python
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

This must run before `rag_chunks` is created, since its `embedding` column uses the `vector` type the extension provides. Autogenerate does not add this line on its own — Alembic only tracks tables/columns, not extensions.

- [ ] **Step 5: Apply the migration**

Run: `uv run alembic upgrade head`
Expected: exits 0, no errors. If it fails with `type "vector" does not exist`, the Step 4 edit didn't land before the `rag_chunks` table creation — check the statement order in the migration file.

- [ ] **Step 6: Verify with a direct query, including a real vector insert**

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "\d rag_papers" -c "\d rag_chunks"`
Expected: `rag_chunks.embedding` shows as type `vector(384)`.

Create `backend/verify_pgvector_temp.py`:

```python
from apps import create_app
from extensions import db
from models.project import Project
from models.rag_paper import RagChunk, RagPaper
from models.user import User

app = create_app()
with app.app_context():
    user = User(email="pgvector-test@example.com", password_hash="x")
    db.session.add(user)
    db.session.flush()

    project = Project(user_id=user.id, name="pgvector test project")
    db.session.add(project)
    db.session.flush()

    paper = RagPaper(project_id=project.id, title="Test Paper", author="Test Author", year=2024)
    db.session.add(paper)
    db.session.flush()

    chunk = RagChunk(
        paper_id=paper.id,
        content="This is a test chunk.",
        embedding=[0.1] * 384,
        chunk_index=0,
    )
    db.session.add(chunk)
    db.session.commit()

    fetched = db.session.get(RagChunk, chunk.id)
    assert fetched is not None
    assert len(fetched.embedding) == 384, f"expected 384-dim vector, got {len(fetched.embedding)}"
    print("PASS: inserted and read back a 384-dim vector:", fetched.embedding[:3], "...")

    # cleanup
    db.session.delete(chunk)
    db.session.delete(paper)
    db.session.delete(project)
    db.session.delete(user)
    db.session.commit()
```

Run (from `backend/`): `uv run python verify_pgvector_temp.py`
Expected: `PASS: inserted and read back a 384-dim vector: [0.1, 0.1, 0.1] ...`

Delete the temp script: `rm backend/verify_pgvector_temp.py` (do not commit it).

- [ ] **Step 7: Commit**

```bash
git add backend/models/rag_paper.py backend/models/__init__.py backend/migrations/versions/
git commit -m "feat: add RagPaper, RagChunk models with pgvector and migration"
```

---

### Task 6: Auth routes — register, login, logout, me

**Files:**
- Create: `backend/routes/auth.py`
- Modify: `backend/apps/__init__.py`

**Interfaces:**
- Consumes: `User` from `models.user` (Task 2); `db` from `extensions.py` (Task 1)
- Produces: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` — no later task in this plan depends on these, but Task 8's verification exercises all four

- [ ] **Step 1: Create the auth blueprint**

Create `backend/routes/auth.py`:

```python
"""使用者註冊/登入/登出 API"""

import logging

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    email = data.get("email")
    password = data.get("password")
    display_name = data.get("displayName", "")

    if not email or not password:
        return jsonify({"success": False, "error": "email 和 password 為必填欄位"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "此 email 已被註冊"}), 409

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(email=email, password_hash=password_hash, display_name=display_name)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"success": True, "result": {"id": user.id, "email": user.email}})


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "error": "email 和 password 為必填欄位"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash:
        return jsonify({"success": False, "error": "帳號或密碼錯誤"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return jsonify({"success": False, "error": "帳號或密碼錯誤"}), 401

    login_user(user)
    return jsonify({"success": True, "result": {"id": user.id, "email": user.email}})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify(
        {
            "success": True,
            "result": {
                "id": current_user.id,
                "email": current_user.email,
                "displayName": current_user.display_name,
                "isAdmin": current_user.is_admin,
            },
        }
    )
```

`login_manager.login_view` is intentionally left unset — with no login view configured, Flask-Login's `@login_required` responds `401 Unauthorized` on an unauthenticated request instead of trying to redirect to a login page, which is correct for a JSON API with no server-rendered pages.

- [ ] **Step 2: Register the auth blueprint**

Replace (`backend/apps/__init__.py`):

```python
    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
```

With:

```python
    from routes.auth import auth_bp
    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
```

- [ ] **Step 3: Verify the full register → me → logout → me flow with curl**

Run (from `backend/`): `uv run python app.py` in one terminal (leave it running), then from another terminal:

```bash
curl -s -c /tmp/datamind-cookies.txt -X POST http://127.0.0.1:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test-auth@example.com","password":"testpass123","displayName":"Test User"}'
```

Expected: `{"result":{"email":"test-auth@example.com","id":...},"success":true}`

```bash
curl -s -b /tmp/datamind-cookies.txt http://127.0.0.1:5001/api/auth/me
```

Expected: `{"result":{"displayName":"Test User","email":"test-auth@example.com","id":...,"isAdmin":false},"success":true}`

```bash
curl -s -b /tmp/datamind-cookies.txt -X POST http://127.0.0.1:5001/api/auth/logout
```

Expected: `{"success":true}`

```bash
curl -s -b /tmp/datamind-cookies.txt -w "\n%{http_code}\n" http://127.0.0.1:5001/api/auth/me
```

Expected: HTTP status `401` (the trailing line printed by `-w`), confirming the session was actually cleared by logout.

Stop the `python app.py` process.

- [ ] **Step 4: Clean up the test user**

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "DELETE FROM users WHERE email = 'test-auth@example.com';"`
Expected: `DELETE 1`

- [ ] **Step 5: Commit**

```bash
git add backend/routes/auth.py backend/apps/__init__.py
git commit -m "feat: add register/login/logout/me auth routes"
```

---

### Task 7: Admin seed script

**Files:**
- Create: `backend/scripts/seed_admin.py`

**Interfaces:**
- Consumes: `create_app` from `apps` (existing); `db` from `extensions.py` (Task 1); `User` from `models.user` (Task 2)
- Produces: nothing consumed by later tasks in this plan

- [ ] **Step 1: Create the seed script**

Create `backend/scripts/seed_admin.py`:

```python
"""建立管理員測試帳號的種子腳本

用法（在 backend/ 目錄下執行）：
    python scripts/seed_admin.py

如果 users 表已經有任何資料，此腳本不會做任何事（避免重複建立）。
Email/密碼透過環境變數 ADMIN_EMAIL / ADMIN_PASSWORD 設定，未設定時使用預設值。
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

import bcrypt

from apps import create_app
from extensions import db
from models.user import User


def main():
    app = create_app()
    with app.app_context():
        if User.query.first() is not None:
            print("users 表已有資料，略過建立管理員帳號。")
            return

        email = os.getenv("ADMIN_EMAIL", "admin@datamind.local")
        password = os.getenv("ADMIN_PASSWORD", "changeme")
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        admin = User(
            email=email,
            password_hash=password_hash,
            display_name="Admin",
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        print(f"已建立管理員帳號：{email}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add the admin credential environment variables**

Add to `backend/.env`:

```
ADMIN_EMAIL=admin@datamind.local
ADMIN_PASSWORD=changeme-locally
```

- [ ] **Step 3: Run it and verify idempotency**

Run (from `backend/`): `uv run python scripts/seed_admin.py`
Expected: `已建立管理員帳號：admin@datamind.local`

Run it again: `uv run python scripts/seed_admin.py`
Expected: `users 表已有資料，略過建立管理員帳號。` (confirms it doesn't create a duplicate)

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "SELECT email, is_admin FROM users;"`
Expected: exactly one row, `admin@datamind.local | t`

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed_admin.py
git commit -m "feat: add admin account seed script"
```

---

### Task 8: Full verification pass

**Files:**
- No file modifications — this task only verifies the combined state of Tasks 1–7.

**Interfaces:**
- Consumes: the completed state of Tasks 1–7
- Produces: nothing (terminal task)

- [ ] **Step 1: Fresh-start the whole stack**

Run: `docker compose down -v postgres` (drops the volume too, so this is a genuinely clean slate — safe here because everything so far is test/seed data, not anything the user needs to keep)
Run: `docker compose up -d postgres`
Run (from `backend/`): `uv run alembic upgrade head`
Expected: applies all 4 migrations (from Tasks 2–5) cleanly against the fresh database, exits 0.

- [ ] **Step 2: Verify the complete schema matches the design doc**

Run: `docker exec datamind-postgres psql -U datamind -d datamind -c "\dt"`
Expected: lists all 9 tables — `users`, `projects`, `frameworks`, `datasets`, `workflow_states`, `reports`, `citations`, `rag_papers`, `rag_chunks` (if the count doesn't match, cross-check against `backend/docs/database-architecture.md` section 二 to find what's missing).

- [ ] **Step 3: Seed the admin account**

Run (from `backend/`): `uv run python scripts/seed_admin.py`
Expected: `已建立管理員帳號：admin@datamind.local`

- [ ] **Step 4: Full auth flow against the freshly-seeded database**

Run (from `backend/`): `uv run python app.py` in one terminal, then from another:

```bash
curl -s -c /tmp/datamind-admin-cookies.txt -X POST http://127.0.0.1:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@datamind.local","password":"changeme-locally"}'
```

Expected: `{"result":{"email":"admin@datamind.local","id":1},"success":true}`

```bash
curl -s -b /tmp/datamind-admin-cookies.txt http://127.0.0.1:5001/api/auth/me
```

Expected: `{"result":{"displayName":"Admin","email":"admin@datamind.local","id":1,"isAdmin":true},"success":true}`

Stop the `python app.py` process.

- [ ] **Step 5: Confirm existing routes are unaffected**

Run (from `backend/`): `uv run python app.py` in one terminal, then: `curl -s http://127.0.0.1:5001/api/health` (or whichever existing health-check path `routes/health.py` exposes — check the file if unsure).
Expected: the existing health endpoint responds exactly as it did before this plan — confirms the new `db.init_app`/`login_manager.init_app` wiring didn't break unrelated routes.

Stop the `python app.py` process.

- [ ] **Step 6: Stop Postgres**

Run: `docker compose stop postgres`

---

## Plan Self-Review

**Spec coverage:** 段落 A（技術選型）→ Task 1 (dependencies), Task 2 (Alembic). 段落 B（users）→ Task 2. 段落 C（projects）→ Task 2. 段落 D（既有檔案型資料歸屬原則）→ reflected in every table's `project_id` FK; RAG-per-project achieved by `rag_papers.project_id` in Task 5. 段落 E（frameworks）→ Task 2. 段落 F（datasets）→ Task 3. 段落 G（workflow_states）→ Task 3. 段落 H（reports/citations）→ Task 4. 段落 I（rag_papers/rag_chunks）→ Task 5. 段落 J（登入機制細節）→ Task 6 (bcrypt, Flask-Login), Task 7 (seed_admin.py). Non-goals (no frontend UI, no `@login_required` on existing routes, no data migration scripts, no OAuth, no forgot-password) — none of the 8 tasks touch any existing route's decorators, any frontend file, or write a migration script for old localStorage/JSON data.

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" — every step shows complete model code, complete migration-editing instructions, exact commands, and exact expected output (including full JSON response bodies for the curl checks).

**Type consistency:** `db` and `login_manager` (Task 1, `extensions.py`) are imported by name in every subsequent task — never redefined. `Project` (Task 2) is the exact FK target (`ForeignKey("projects.id")`) used by `Dataset`/`WorkflowState`/`Report`/`RagPaper` in Tasks 3–5. `CitationStyle` enum values (`'apa'/'ieee'/'mla'`, Task 4) match the Global Constraints and the already-shipped frontend feature. `User.password_hash`/`User.is_admin` (Task 2) are the exact fields Task 6's auth routes and Task 7's seed script read/write — no naming drift. `EMBEDDING_DIM = 384` (Task 5) matches the Global Constraints' stated dimension.
