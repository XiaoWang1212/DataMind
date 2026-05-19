# MinerU Local Deployment Guide

This project now uses MinerU as a local service, not a Docker service.

## What was changed

- `docker-compose.yml` no longer starts a `mineru` service.
- `backend/.env` defaults to `MINERU_BASE_URL=http://host.docker.internal:8000` for Docker-backed backend on macOS/Windows.
- This means the backend expects MinerU to already be running locally.

## How to run MinerU locally

### macOS

1. Install MinerU using the official macOS/native installation method.
2. Start the MinerU service so it listens on port `8000`.
3. Confirm the service is reachable from your Mac:

```bash
curl http://localhost:8000
```

### Windows

1. Install MinerU using the official Windows installation method.
2. Start the MinerU service so it listens on port `8000`.
3. Confirm the service is reachable from your PC:

```powershell
curl http://localhost:8000
```

## Backend configuration

### Run backend directly on your machine

In `backend/.env`, set:

```env
MINERU_BASE_URL=http://localhost:8000
MINERU_API_KEY=
MINERU_MODEL=mineru-default
MINERU_ANALYZE_PATH=/analyze
```

### Run backend inside Docker on macOS or Windows

In `backend/.env`, set:

```env
MINERU_BASE_URL=http://host.docker.internal:8000
MINERU_API_KEY=
MINERU_MODEL=mineru-default
MINERU_ANALYZE_PATH=/analyze
```

- If your local MinerU does not require authentication, leave `MINERU_API_KEY` empty.
- If it does require a key, set it here.

## Verify MinerU is reachable

From your host machine:

```bash
curl http://localhost:8000
```

From the backend container (Docker):

```bash
docker compose exec backend curl http://host.docker.internal:8000
```

If either command fails, MinerU is not running or not listening on port `8000`.

## Running the app

### Option A: Run backend locally

Use your existing Python environment and run the backend directly.

### Option B: Run frontend/backend with Docker

You can still use Docker for the frontend and backend, but MinerU must remain a local service.

1. Start MinerU locally.
2. Run Docker Compose for the app services:

```bash
docker compose up
```

## Notes

- macOS and Windows users should prefer native MinerU/OCR installation over Docker.
- Docker deployment for MinerU is not recommended on macOS.
- If MinerU is moved to Linux/WSL2 or a remote host, update `MINERU_BASE_URL` accordingly.
