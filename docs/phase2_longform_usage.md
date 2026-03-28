# Phase 2 Longform Usage

## 目标

Phase 2 的当前目标是把既有 Phase 1 单章闭环包装成一个：

- 可顺序推进到第 5 章
- 失败后可恢复
- 状态可读
- artifact 可审计

的最小长篇 workflow。

它不是无限循环器，也不是新的内容生成 workflow。

## 当前主入口

推荐入口：

- `phase2_cli.py`

Phase 2 会复用 Phase 1 的写作和提交能力，不会替代 `phase1_cli.py`。

## 前置条件

使用 Phase 2 之前，建议先完成：

```bash
python phase1_cli.py create-project --root "<project_root>" --title "<title>" --topic "<topic>" --style "<style>" --target "<target>"
python phase1_cli.py plan-novel --root "<project_root>"
python phase2_cli.py init-loop --root "<project_root>"
```

## 当前命令

### 初始化 loop state

```bash
python phase2_cli.py init-loop --root "<project_root>"
```

作用：

- 创建 `loop_state.json`
- 创建 `checkpoints/`
- 创建 `reviews/`

`snapshots/` 目录按需创建，不会在 `init-loop` 时预创建。

### 查看状态

```bash
python phase2_cli.py show-status --root "<project_root>"
```

当前会展示这些关键字段：

- `workflow_status`
- `start_chapter_no`
- `target_chapter_count`
- `current_chapter_no`
- `next_chapter_no`
- `loop_state_last_completed_chapter_no`
- `last_successfully_committed_chapter_no`
- `last_successfully_committed_source`
- `commit_scan_status`
- `commit_loop_drift`
- `last_attempted_chapter_no`
- `last_attempt_status`
- `last_failure_stage`
- `last_error`
- `unresolved_snapshot_exists`
- `unresolved_snapshot_chapters`
- `stale_snapshot_exists`
- `stale_snapshot_chapters`
- `artifact_focus_chapter_no`
- `artifact_relation_status`
- `checkpoint_path`
- `review_path`
- `suggestion_path`
- `snapshot_path`

其中：

- `last_successfully_committed_chapter_no`
  - 优先来自 canonical review/suggestion 的 committed scan
  - 扫描无法可靠确定时，回退到 `loop_state_last_completed_chapter_no`
- `commit_loop_drift`
  - 表示 loop_state 视角和 artifact scan 视角出现偏差
- `artifact_relation_status`
  - `aligned`
  - `partial`
  - `mismatched`
  - `unknown`

### 顺序运行到第 5 章

```bash
python phase2_cli.py run-five --root "<project_root>"
```

作用：

- 从 `loop_state.next_chapter_no` 开始
- 顺序执行单章闭环
- 成功时推进到下一章
- 某章失败时立即停止

不需要单独的 `resume` 命令；再次执行 `run-five` 即会从当前可恢复位置继续。

## 当前真实主链

Phase 2 每章实际走的是：

`write_chapter -> commit_suggestion`

而 `commit_suggestion` 内部已经是：

`suggestion -> review -> consistency_check -> snapshot -> commit -> cleanup`

这意味着：

- review 已进入主链
- deterministic consistency checks 已进入主链
- snapshot / restore 已进入主链
- 但 CLI 命令面没有变化

## 当前 artifact 语义

### `loop_state.json`

流程状态，不承载正式故事状态。

### `checkpoints/chXXX.checkpoint.json`

单章尝试结果索引，当前包含：

- `chapter_no`
- `status`
- `failure_stage`
- `artifacts`
- `suggestion_committed`
- `error`
- `loop_state`

### `reviews/chXXX.review.json`

显式 commit 依据，包含：

- `approved_suggestion`
- `consistency_check`
- `committed`

### `suggestions/chXXX.suggestion.json`

原始 proposal。

### `snapshots/chXXX.snapshot.json`

formal commit 前的恢复快照。

成功提交后通常会被删除；如果失败恢复过，可能保留为 `restored` 供排障使用。

## 当前失败恢复语义

### unresolved snapshot

如果 rerun 前发现 snapshot 存在，且 review / suggestion 没有同时 committed：

- 视为上次 commit 未完成
- 会先尝试 restore
- restore 成功后，才继续本次 commit

### stale snapshot

如果 snapshot 存在，但 review / suggestion 都已经 committed：

- 视为 stale snapshot
- 不回滚 formal state
- 只尝试 cleanup
- cleanup 失败会显式报错，不会静默忽略

## 推荐排障顺序

如果 `run-five` 失败，推荐按这个顺序看：

1. 先看 CLI 输出里的 `checkpoint_path`
   - 它是总索引，优先定位 `failure_stage`、`error`、`artifacts`
2. 如果有 `snapshot_path`，或 `show-status` 显示 unresolved / stale snapshot
   - 再看 snapshot
3. 再看 `review_path`
   - 重点看 `committed`、`consistency_check`、`approved_suggestion`
4. 最后看 `suggestion_path`

如果你只想知道“现在应该继续跑还是先修状态”，先执行：

```bash
python phase2_cli.py show-status --root "<project_root>"
```

## 最小使用示例

```bash
python phase1_cli.py create-project --root "D:/AI novel/workspace/demo_novel" --title "Demo Novel" --topic "玄幻复仇" --style "冷系、克制、偏网文章节节奏" --target "男频长篇"
python phase1_cli.py plan-novel --root "D:/AI novel/workspace/demo_novel"
python phase2_cli.py init-loop --root "D:/AI novel/workspace/demo_novel"
python phase2_cli.py show-status --root "D:/AI novel/workspace/demo_novel"
python phase2_cli.py run-five --root "D:/AI novel/workspace/demo_novel"
```

中途失败后直接再跑：

```bash
python phase2_cli.py run-five --root "D:/AI novel/workspace/demo_novel"
```

## 当前边界

Phase 2 当前仍然不做：

- 超过第 5 章的泛化自动推进
- 新 CLI 命令
- LLM checker 默认接入
- 更丰富的报告导出格式

## 相关文档

- `README.md`
- `docs/phase1.md`
- `docs/phase2_longform_design.md`
