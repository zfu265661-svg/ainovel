# API Design

FastAPI entry point:

```powershell
python -m uvicorn interfaces.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Routes:

```text
GET  /health
GET  /projects
POST /projects
GET  /projects/{project_id}
GET  /projects/{project_id}/snapshot
GET  /projects/{project_id}/chapters
POST /projects/{project_id}/chapters/{chapter_id}/run
GET  /projects/{project_id}/chapters/{chapter_id}/trace
GET  /projects/{project_id}/chapters/{chapter_id}/context-audit
GET  /projects/{project_id}/chapters/{chapter_id}/consistency-report
GET  /projects/{project_id}/plot-threads
GET  /projects/{project_id}/foreshadows
GET  /projects/{project_id}/checkpoints
```

`POST /projects/{project_id}/chapters/{chapter_id}/run` accepts:

```json
{
  "dry_run": false,
  "review_before_commit": false
}
```
