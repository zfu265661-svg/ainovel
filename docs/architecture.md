# Architecture

The new architecture separates domain models, engine logic, application use cases, infrastructure adapters, and interfaces.

```text
domain/          JSON-serializable narrative models
engine/          context assembly, chapter pipeline, quality checks, runtime checkpoints
application/     use cases consumed by API, CLI, and Streamlit
infrastructure/  JSON persistence, future SQLite hooks, replaceable LLM adapter
interfaces/      FastAPI, CLI, Streamlit
data/projects/   canonical project storage
```

The first MVP keeps JSON persistence because it is transparent, easy to inspect, and sufficient for the acceptance path. SQLite is represented by an adapter placeholder and can be added without changing API routes or UI code.

Core flow:

```text
create project -> load snapshot -> assemble context -> run chapter pipeline
-> generate trace/audit/report -> commit snapshot -> checkpoint
```

The API layer contains no core business logic. It calls `application/use_cases`, which coordinate repository and engine services.
