# Real API Smoke Checklist

Use this checklist only when a real API verification is explicitly requested.

## Safety

- Check config without printing secrets:
  - `OPENAI_API_KEY exists: true/false`
  - `MODEL_NAME`
  - `OPENAI_BASE_URL exists: true/false`
- Do not print, copy, or store the API key.
- Do not commit `workspace/` smoke artifacts.
- Do not modify `prompts/` during a smoke run.
- Prefer a temporary project under `workspace/`.

## Minimal Flow

Run one chapter only:

```bash
python phase1_cli.py create-project --root ".\workspace\api_smoke_review_control" --title "<title>" --topic "<topic>" --style "<style>" --target "<target>"
python phase1_cli.py plan-novel --root ".\workspace\api_smoke_review_control"
python phase1_cli.py write-chapter --root ".\workspace\api_smoke_review_control" --chapter 1
python phase2_cli.py init-loop --root ".\workspace\api_smoke_review_control"
python phase2_cli.py inspect-context --root ".\workspace\api_smoke_review_control" --chapter 1
python phase2_cli.py prepare-review --root ".\workspace\api_smoke_review_control" --chapter 1
python phase2_cli.py approve-review --root ".\workspace\api_smoke_review_control" --chapter 1
python phase2_cli.py commit-approved --root ".\workspace\api_smoke_review_control" --chapter 1
python phase2_cli.py show-status --root ".\workspace\api_smoke_review_control"
```

Do not run `run-five` for a minimal API smoke unless the test explicitly needs it.

## JSON Notes

- LLM JSON parsing now retries narrow formatting repairs after strict parsing.
- UTF-8 BOM JSON files are accepted by `load_json`.
- If hand-writing JSON artifacts, no-BOM UTF-8 is still preferred.

## Manual Commit Drift

After `commit-approved`, `show-status` may report `commit_loop_drift=True` and
`artifact_relation_status=partial`. This can be expected for the manual review
path: `commit-approved` updates formal state and review/suggestion artifacts,
but does not advance `loop_state`. Check `commit_loop_drift_explanation`,
`manual_commit_note`, snapshot health, and `can_continue` before treating it as
a failure.
