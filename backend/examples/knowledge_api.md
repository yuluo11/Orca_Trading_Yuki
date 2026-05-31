# Knowledge API adapter

The backend knowledge API is an optional FastAPI layer over the plain Python
route handlers in `backend.src.routes.knowledge`.

Install the optional API dependencies when you want to expose HTTP endpoints:

```bash
pip install -e 'backend[api]'
```

Start the API from the repository root:

```bash
python -m uvicorn backend.src.api.knowledge_api:create_app --factory --reload
```

Useful first checks:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/knowledge/search \
  -H 'content-type: application/json' \
  -d '{"query":"NVDA catalyst", "datasets":["dynamic"], "k":3}'
```

The adapter intentionally accepts plain JSON payloads. Request validation stays
close to the framework-neutral route handlers so a future frontend, CLI, or
desktop surface can share the same backend behavior.
