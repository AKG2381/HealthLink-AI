# HealthLink Frontend

A Vite + React single-page app for HealthLink. Talks to the FastAPI backend at
`/api/v1`.

## Local development

```bash
# 1. start the backend (from the project root, in another terminal)
uvicorn main:app --reload          # serves http://localhost:8000

# 2. start the frontend
cd frontend
npm install
npm run dev                        # serves http://localhost:3000
```

In dev, Vite proxies `/api` to `http://localhost:8000` (configurable with
`VITE_PROXY_TARGET`), so there are no CORS issues and the app uses relative URLs.

## Production build

```bash
cd frontend
# point the bundle at your deployed backend (baked in at build time)
VITE_API_BASE=https://healthlink-xxxxxx.asia-south1.run.app npm run build
# output is in frontend/dist/ — static files you can host anywhere
npm run preview                    # optional: preview the build on :4173
```

If you leave `VITE_API_BASE` empty, the app calls relative `/api/...` — use that
when the frontend is served behind the same origin as the backend (e.g. via the
nginx proxy in the Docker image).

## Docker

```bash
# build (bake in the backend URL)
docker build --build-arg VITE_API_BASE=https://YOUR_BACKEND -t healthlink-frontend .

# OR build without it and let nginx proxy /api to the backend at runtime:
docker build -t healthlink-frontend .
docker run -p 8080:8080 -e BACKEND_URL=http://your-backend:8000 healthlink-frontend
```

Serves on port 8080 (Cloud Run friendly).

## Deploy to Cloud Run

```bash
gcloud run deploy healthlink-frontend \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8080
```

Then whitelist the frontend's URL on the backend by setting the `CORS_ORIGINS`
env var (comma-separated) on the backend service:

```bash
gcloud run services update healthlink --region asia-south1 \
  --update-env-vars CORS_ORIGINS=https://healthlink-frontend-xxxxxx.run.app
```

## Configuration

| Variable          | When        | Purpose                                            |
| ----------------- | ----------- | -------------------------------------------------- |
| `VITE_API_BASE`   | build time  | Backend base URL baked into the bundle             |
| `VITE_PROXY_TARGET` | dev only  | Backend the Vite dev server proxies `/api` to      |
| `BACKEND_URL`     | runtime (Docker) | Backend nginx proxies `/api` to               |
