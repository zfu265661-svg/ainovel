# CLI Usage

## Recommended Entry Points

- `phase1_cli.py`
- `phase2_cli.py`

`app.py` remains a compatibility entry.

## Phase 1 Commands

Create a project:

```bash
python phase1_cli.py create-project --root "<project_root>" --title "<title>" --topic "<topic>" --style "<style>" --target "<target>"
```

New projects include the original Phase 1 state files plus:

- `story_bible.json`
- `plot_threads.json`
- `locations.json`
- `organizations.json`
- `style_guide.json`
- `scenes.json`
- `exports/`

Generate plans:

```bash
python phase1_cli.py plan-novel --root "<project_root>"
```

Write one chapter:

```bash
python phase1_cli.py write-chapter --root "<project_root>" --chapter 1
```

Commit one suggestion:

```bash
python phase1_cli.py commit-suggestion --root "<project_root>" --chapter 1
```

## Phase 2 Commands

Initialize the 5-chapter loop:

```bash
python phase2_cli.py init-loop --root "<project_root>"
```

Show status:

```bash
python phase2_cli.py show-status --root "<project_root>"
```

Status now includes formal state health, missing/corrupt files, `can_continue`,
`next_action`, and a compact `narrative_state_machine` overview.

Inspect the context selected for one chapter without generating text:

```bash
python phase2_cli.py inspect-context --root "<project_root>" --chapter 1
```

Inspect Story Bible and enhanced state health:

```bash
python phase2_cli.py inspect-story-bible --root "<project_root>"
```

Inspect plot thread status and future graph-oriented fields:

```bash
python phase2_cli.py inspect-plot-threads --root "<project_root>"
```

Run the regression loop:

```bash
python phase2_cli.py run-five --root "<project_root>"
```

## Long-Term CLI Direction

Future commands may include `run`, `resume`, `recover`, `export`, `build-bible`, `plan-scene`, `write-scene`, and `check-style`. They should reuse existing services rather than moving business logic into CLI modules.
