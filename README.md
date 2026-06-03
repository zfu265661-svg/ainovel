# AI Novel

这是一个面向“项目驱动长篇小说写作”的 agent kernel，不是一次性章节生成器。

当前仓库的默认主链已经稳定到 Stage 1~5，重点不是扩到 100 章，而是先把真实 5 章闭环跑稳、跑清楚、跑得可恢复。

Phase 3 MVP 在这个基础上开始把项目壳升级为可演进的 Agent Kernel：

- 新项目会创建 `story_bible.json`、`plot_threads.json`、`locations.json`、`organizations.json`、`style_guide.json`、`scenes.json`
- 章节 context assembler 会读取这些增强状态，并写入 `context_audit`
- `show-status` 会显示 formal state health、缺失/损坏文件、`can_continue` 和 `next_action`
- review / commit / snapshot 仍然只提交当前受控的 `characters.json`、`timeline.json`、`foreshadow.json`

## 当前主入口

推荐入口：

- `phase1_cli.py`
- `phase2_cli.py`

兼容入口：

- `app.py`

`app.py` 仍然保留，但不再是推荐主入口。

## 当前主链能力

### Phase 1

`phase1_cli.py` 提供：

- `create-project`
- `plan-novel`
- `write-chapter`
- `commit-suggestion`

Phase 1 负责把项目推进到“可规划、可写单章、可显式提交状态”的最小闭环。

### Phase 2

`phase2_cli.py` 提供：

- `init-loop`
- `show-status`
- `run-five`

Phase 2 在 Phase 1 之上提供可恢复的顺序推进能力，当前目标固定为跑到第 5 章。

## 当前默认工作流

当前主链已经显式化为：

`plan -> draft -> rewrite -> summarize -> suggest -> review -> consistency_check -> commit`

其中：

- `commit_suggestion()` 仍是唯一公开提交入口
- Phase 1 的 `commit-suggestion` 走这条链
- Phase 2 的自动推进也走这条链

## Stage 1~5 已落地能力

### 1. Context Assembler

- 章节上下文组装已从 `workflow_service` 中显式抽到 `chapter_context_service`
- `chapter 1`、缺失 previous summary、timeline 截断、open foreshadow 过滤都有固定规则

### 2. Suggestion -> Review -> Commit

- 两条主链都会先生成 canonical review artifact，再进入 commit
- `reviews/chXXX.review.json` 记录 commit 的显式依据
- Phase 2 仍然自动提交，不新增人工步骤

### 3. Lightweight Deterministic Checks

- review 上会写入 `consistency_check`
- 默认主流程只接 cheap / deterministic checks
- LLM checker 没有接入默认主链

### 4. Recoverable Commit

- formal state 提交前会创建 `snapshots/chXXX.snapshot.json`
- 正式状态写入或 marker 写入中途失败时，会触发 restore
- rerun 同章前会先处理 unresolved snapshot
- stale snapshot 会被识别并清理；清理失败会显式报错

### 5. Status / Diagnostics

- `show-status` 会聚合 `loop_state`、checkpoint、review、suggestion、snapshot
- `run-five` 失败时会提示先看 checkpoint
- Phase 1 的 `commit-suggestion` 成功/失败都会输出 review / snapshot 诊断线索

## 关键 artifact

主链运行时会涉及这些文件：

- `loop_state.json`
  - 只表示流程状态，不承载正式故事状态
- `suggestions/chXXX.suggestion.json`
  - 原始 AI proposal
- `reviews/chXXX.review.json`
  - 显式 commit 依据，包含 `approved_suggestion` 和 `consistency_check`
- `checkpoints/chXXX.checkpoint.json`
  - 单章尝试结果、失败阶段、artifact 索引
- `snapshots/chXXX.snapshot.json`
  - formal commit 前的恢复快照；成功提交后会删除
- `characters.json`
- `timeline.json`
- `foreshadow.json`
  - 三个 canonical 正式状态文件
- `story_bible.json`
- `plot_threads.json`
- `locations.json`
- `organizations.json`
- `style_guide.json`
- `scenes.json`
  - Phase 3 agent project state；当前进入 context assembly 和 status diagnostics，但不会被 LLM suggestion 直接提交

## 当前 show-status 会展示什么

`phase2_cli.py show-status` 当前会输出：

- 当前 workflow 状态
- 当前写到哪一章
- `loop_state` 视角的最近完成章
- artifact scan 视角的最近成功提交章
- 最近尝试的是哪一章、状态如何
- 最近失败在哪个阶段
- 是否存在 unresolved / stale snapshot
- 当前 focus chapter 的 checkpoint / review / suggestion / snapshot 路径
- `artifact_relation_status`
- `formal_state_health`
- `formal_state_missing_files`
- `formal_state_required_missing_files`
- `formal_state_corrupt_files`
- `can_continue`
- `next_action`

## 推荐使用顺序

最小闭环：

```bash
python phase1_cli.py create-project --root "<project_root>" --title "<title>" --topic "<topic>" --style "<style>" --target "<target>"
python phase1_cli.py plan-novel --root "<project_root>"
python phase2_cli.py init-loop --root "<project_root>"
python phase2_cli.py show-status --root "<project_root>"
python phase2_cli.py run-five --root "<project_root>"
```

如果只想单独验证一章：

```bash
python phase1_cli.py write-chapter --root "<project_root>" --chapter 1
python phase1_cli.py commit-suggestion --root "<project_root>" --chapter 1
```

## 推荐排障顺序

当 `run-five` 或 `commit-suggestion` 失败时，推荐按这个顺序看：

1. 先看 `checkpoint`
   - 优先确认 `failure_stage`、`error`、`artifacts`
2. 如果有 `snapshot_path`，或 `show-status` 显示 unresolved / stale snapshot
   - 再看 `snapshot`
3. 再看 `review`
   - 重点看 `committed`、`consistency_check`、`approved_suggestion`
4. 最后看 `suggestion`
   - 确认原始 proposal 和 review 是否对得上

如果只是想快速判断现在能不能继续跑，先执行：

```bash
python phase2_cli.py show-status --root "<project_root>"
```

## 相关文档

- `docs/phase1.md`
- `docs/phase2_longform_usage.md`
- `docs/phase2_longform_design.md`
- `docs/architecture.md`
- `docs/agent_design.md`
- `docs/story_bible.md`
- `docs/workflow.md`
- `docs/recoverability.md`
- `docs/cli_usage.md`
