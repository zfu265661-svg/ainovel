# Phase 1 使用说明

## 目标

Phase 1 负责把一个小说项目从空目录推进到：

- 已完成项目初始化
- 已完成规划
- 可写单章
- 可通过显式 `review -> consistency_check -> commit` 链路提交 structured state

Phase 1 不负责连续跑到第 5 章；那部分由 Phase 2 负责。

## 当前主入口

推荐入口：

- `phase1_cli.py`

兼容但不推荐：

- `app.py`

## 当前命令

### 创建项目

```bash
python phase1_cli.py create-project --root "<project_root>" --title "<title>" --topic "<topic>" --style "<style>" --target "<target>"
```

典型输出：

- `<project_root>/project.json`
- `<project_root>/chapters.json`
- `<project_root>/characters.json`
- `<project_root>/timeline.json`
- `<project_root>/foreshadow.json`
- `<project_root>/docs/`
- `<project_root>/suggestions/`

### 生成规划

```bash
python phase1_cli.py plan-novel --root "<project_root>"
```

典型输出：

- `docs/outline.md`
- `docs/volumes.md`
- `chapters.json`
- `docs/ch001.plan.md` 到 `docs/chXXX.plan.md`

### 写单章

```bash
python phase1_cli.py write-chapter --root "<project_root>" --chapter 1
```

典型输出：

- `docs/ch001.draft.md`
- `docs/ch001.rewrite.md`
- `docs/ch001.summary.md`
- `suggestions/ch001.suggestion.json`

### 提交 suggestion

```bash
python phase1_cli.py commit-suggestion --root "<project_root>" --chapter 1
```

当前真实链路不是“直接 suggestion 覆盖正式状态”，而是：

`suggestion -> review -> consistency_check -> snapshot -> commit`

提交成功后会更新：

- `characters.json`
- `timeline.json`
- `foreshadow.json`
- `suggestions/ch001.suggestion.json`
- `reviews/ch001.review.json`

CLI 还会输出：

- `review_path`
- `snapshot_path`
- `artifact_relation_status`

说明：

- 成功提交后，snapshot 会被清理掉，所以 `snapshot_path` 可能只是 canonical path，不代表文件仍存在
- 如果提交失败，review 会保留，snapshot 也可能保留或被标记为 restored，供后续排障或 rerun 使用

## 当前主链能力

### Context Assembler

`write-chapter` 使用显式 context assembler，而不是把上下文逻辑继续埋在 `workflow_service` 里。

### Review Artifact

`commit-suggestion` 会先生成或刷新 `reviews/chXXX.review.json`，再从 review 的 `approved_suggestion` 做 commit。

### Deterministic Consistency Check

review 上会写入 `consistency_check`：

- `blockers` 会阻止 commit
- `warnings` 不阻止 commit，但会保留在 review 中

### Recoverable Commit

正式状态写入前会创建 `snapshots/chXXX.snapshot.json`：

- formal write 或 marker write 失败时，会恢复 formal state
- rerun 同章前会先尝试处理 unresolved snapshot

## 最小使用顺序

```bash
python phase1_cli.py create-project --root "D:/AI novel/workspace/demo_novel" --title "Demo Novel" --topic "玄幻复仇" --style "冷系、克制、偏网文章节节奏" --target "男频长篇"
python phase1_cli.py plan-novel --root "D:/AI novel/workspace/demo_novel"
python phase1_cli.py write-chapter --root "D:/AI novel/workspace/demo_novel" --chapter 1
python phase1_cli.py commit-suggestion --root "D:/AI novel/workspace/demo_novel" --chapter 1
```

## 推荐排障顺序

如果 `commit-suggestion` 失败，推荐按这个顺序看：

1. 先看 CLI 输出里的 `failure_stage`
2. 再看 `review_path`
3. 如果 CLI 给出了 `snapshot_path`
   - 再看 snapshot 是否存在、是 `pending` 还是 `restored`
4. 最后看 `suggestion_path`

排障目标通常是先判断：

- 是不是 consistency blocker
- 是不是 formal state write 中途失败
- 是不是 snapshot cleanup 或 stale snapshot cleanup 失败

## 当前边界

Phase 1 当前不做：

- 连续 5 章自动推进
- 人工 approve/reject review
- LLM consistency checker 默认接入
- 新 workflow 或额外 CLI

## 相关文档

- `README.md`
- `docs/phase2_longform_usage.md`
- `docs/phase2_longform_design.md`
