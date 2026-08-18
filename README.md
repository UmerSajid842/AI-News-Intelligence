# AI News Intelligence Platform

A demo-first news intelligence application that ingests article records, prevents duplicate URLs, classifies content into topical categories, and presents the results through a FastAPI API and Streamlit dashboard.

The project is designed as a portfolio-quality foundation for an ML Engineer or Data Scientist workflow: the default experience is deterministic and free to run locally, while an optional live mode integrates NewsAPI with Celery and Redis for background ingestion.

## Why this project is useful

This project demonstrates a practical end-to-end ML application rather than an isolated notebook. It combines API design, database modeling, authentication, data-quality safeguards, classification, background jobs, dashboarding, containerization, and automated tests.

| Capability | Implementation |
| --- | --- |
| API layer | FastAPI with OpenAPI documentation |
| Persistence | SQLAlchemy with SQLite by default and configurable SQLAlchemy database URLs |
| Classification | Deterministic keyword fallback with optional Hugging Face zero-shot classification |
| Ingestion | Local demo fixtures by default; optional NewsAPI live mode |
| Background processing | Celery with Redis in live/containerized mode |
| Dashboard | Streamlit analytics and article feed |
| Authentication | Environment-configured demo credentials and short-lived PyJWT bearer tokens |
| Quality controls | Duplicate URL protection, bounded pagination, protected mutations, and pytest coverage |
| Deployment | Dockerfiles and Docker Compose configuration |

## Architecture

```text
                         +----------------------+
                         |  Streamlit dashboard |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | FastAPI application  |
                         | auth / articles API |
                         +----+------------+----+
                              |            |
                              v            v
                       +-------------+  +------------------+
                       | SQLAlchemy  |  | Classifier       |
                       | SQLite/DB   |  | keyword or HF    |
                       +-------------+  +------------------+
                              ^
                              |
             demo fixtures --+-- live NewsAPI -> Celery -> Redis
```

## Demo mode: the recommended first run

`NEWS_MODE=demo` is the safe default. It inserts three clearly labeled local fixtures, classifies them without a network request, and skips the Celery/Redis requirement for the fetch action. Repeating the fetch is idempotent because the service checks each article URL before inserting it.

The fixture text is synthetic portfolio-demo data and **must not be presented as live news**. Live ingestion is opt-in and requires `NEWS_MODE=live`, a NewsAPI key, Redis, and a running Celery worker.

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/auth.py              # Demo login and current-user endpoint
│   │   ├── api/articles.py          # Article listing, fetch, detail, classification
│   │   ├── services/classifier.py   # Optional HF model plus deterministic fallback
│   │   ├── services/news_fetcher.py # Local demo fixture ingestion
│   │   ├── database.py              # SQLAlchemy engine and session factory
│   │   ├── models.py                # Article model and constraints
│   │   ├── schemas.py               # Pydantic response schemas
│   │   ├── security.py              # PyJWT token creation and validation
│   │   ├── worker.py                # Celery tasks and optional live ingestion
│   │   └── main.py                  # FastAPI application entrypoint
│   └── requirements.txt
├── dashboard/app.py                 # Streamlit dashboard
├── tests/                            # API and service tests
├── .env.example                     # Safe configuration template
├── docker-compose.yml                # API, dashboard, worker, and Redis stack
└── TODO.md                           # Follow-up engineering ideas
```

## Local setup

The following commands assume Python 3.11 or newer.

```bash
git clone https://github.com/UmerSajid842/AI-News-Intelligence.git
cd AI-News-Intelligence
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1

pip install -r backend/requirements.txt
cp .env.example .env
```

Before starting the API, replace the placeholder `AUTHJWT_SECRET_KEY` and `DEMO_PASSWORD` values in `.env`. The project reads the file automatically through `python-dotenv`.

Start the API from the repository root:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal, start the dashboard:

```bash
streamlit run dashboard/app.py --server.port 8501
```

Open <http://localhost:8501> for the dashboard and <http://localhost:8000/docs> for the interactive API documentation. Sign in using the `DEMO_USER` and `DEMO_PASSWORD` values from `.env`, then select **Fetch latest articles**.

## API examples

List articles without authentication:

```bash
curl "http://localhost:8000/api/articles/?limit=20"
```

Authenticate the configured local demo user:

```bash
curl -X POST "http://localhost:8000/api/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username":"admin","password":"replace-with-a-local-password"}'
```

Use the returned bearer token for protected actions:

```bash
curl -X POST "http://localhost:8000/api/articles/fetch" \\
  -H "Authorization: Bearer <ACCESS_TOKEN>"

curl -X POST "http://localhost:8000/api/articles/classify" \\
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Available routes include `GET /`, `GET /api/articles/`, `GET /api/articles/{article_id}`, `POST /api/articles/fetch`, `POST /api/articles/classify`, `POST /api/auth/login`, and `GET /api/auth/me`.

## Optional live mode

Live ingestion is deliberately separate from the default demo path. It is strictly opt-in: the API accepts only `NEWS_MODE=demo` or `NEWS_MODE=live`, and live mode refuses to start without a provider key and an HTTP(S) provider URL. It never silently falls back to synthetic fixtures when live mode is selected.

Configure the following values in `.env`:

```dotenv
NEWS_MODE=live
NEWS_API_KEY=your-newsapi-key
NEWS_PROVIDER_URL=https://newsapi.org/v2/top-headlines
REDIS_URL=redis://localhost:6379/0
```

Then start Redis and the Celery worker. With Docker Compose, use:

```bash
docker compose up --build
```

This starts Redis, the FastAPI service on port 8000, the Streamlit dashboard on port 8501, and the Celery worker. Use live mode only when a valid provider key and the required service capacity are available. The provider key is sent only as an outbound request parameter and is never returned in API responses or logs.

The live worker validates the provider response, uses a bounded request timeout, normalizes ISO-8601 publication timestamps to UTC, ignores malformed records, prevents duplicate URLs, commits inserts before queueing classification, and reports provider failures without exposing credentials.

## Tests and validation

Run syntax checks and the test suite from the repository root:

```bash
python -m compileall -q backend dashboard tests
pytest -q
```

The suite covers article listing and detail retrieval, duplicate URL protection, deterministic classification, successful and failed authentication, unauthenticated route rejection, authenticated demo fetch/classification, strict live-mode configuration, protected live-mode behavior, provider timestamp normalization, mocked provider ingestion, and live duplicate protection. The repository currently validates with 11 passing tests.

## Security and data-quality decisions

Authentication credentials are read from environment variables rather than committed source code. The JWT signing secret is also environment-driven, and tokens expire after a configurable interval. The default secret is intended only as a local-development fallback and must be replaced before deployment.

Mutating routes require a bearer token. Article pagination is bounded to prevent unreasonably large reads, and duplicate URLs are ignored during both demo and live ingestion. Live provider errors are handled without returning the provider key. No production claim is made for the synthetic demo fixtures or for the keyword fallback classifier.

## Current limitations

The default classifier is intentionally lightweight and deterministic. The optional Hugging Face zero-shot pipeline requires model downloads and additional compute, so it is disabled unless `ENABLE_HF_CLASSIFIER=true`. Live ingestion depends on NewsAPI, Redis, Celery, and the provider’s quota and availability; a live API key is not included in this repository and must be supplied by the operator. The demo authentication layer is suitable for a portfolio demonstration, not for multi-user production identity management.

The application currently focuses on ingestion and classification. It does not yet provide user accounts, persistent task monitoring, model evaluation dashboards, provider failover, or a production migration system such as Alembic.

## Roadmap

The next improvements are to add Alembic migrations, replace demo credentials with a proper identity provider, add structured logging and health checks, persist Celery task status, introduce model evaluation metrics, add provider-agnostic ingestion adapters, and deploy the API and dashboard with managed database and Redis services.

## License and attribution

This repository is maintained as a professional portfolio project by **Umer Sajid**. Review the repository history and source files for implementation details, experiments, and future work.
