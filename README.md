# BharatCrop Intelligence

Full-stack agricultural intelligence workspace: Next.js frontend + FastAPI backend, with historical APY/yield analytics, weather intelligence, research notebooks, model artifacts, and datasets.

## Layout

- `application/frontend` — Next.js 16 / React 19 client.
- `application/backend` — FastAPI service (`bharatcrop_foundation`).
- `models/`, `data/processed/`, `metadata/` — served datasets, model artifacts, provenance.
- `notebooks/`, `phase2c_*`, `phase2d_*`, `phase3b_*` — research workspaces and notebooks.
- `REQUIRED_EXTERNAL_DATA.md` — large assets intentionally kept out of Git.

## Local commands

Frontend (`application/frontend`):

```bash
pnpm install
pnpm dev      # http://127.0.0.1:3000
pnpm build
pnpm lint
pnpm typecheck
pnpm test
```

Backend (`application/backend`, Python 3.12–3.13):

```bash
uv sync
uvicorn bharatcrop_foundation.app:app --host 127.0.0.1 --port 8000
pytest tests/test_weather_ml.py -q
```

The frontend proxies `/api/*` and `/health/*` to `API_INTERNAL_BASE_URL` (default `http://127.0.0.1:8000`).

## Render notes

- Backend: Python service running `uvicorn bharatcrop_foundation.app:app` from `application/backend` after installing `pyproject.toml` deps.
- Frontend: Node service running `pnpm install --frozen-lockfile`, `pnpm build`, `pnpm start` from `application/frontend`.
- Set `API_INTERNAL_BASE_URL` on the frontend to the backend service URL.
- PostgreSQL is scaffolding only; the app currently serves CSV/Parquet/joblib assets and does not require a database.
- Large datasets listed in `REQUIRED_EXTERNAL_DATA.md` must be provided via external storage or Git LFS before the affected features work in deployment.
