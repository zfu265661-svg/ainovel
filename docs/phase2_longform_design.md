# Phase 2 Longform Design

这份文档描述的是当前仓库已经落地的 Stage 1~5 主链设计快照，不是早期草案。

## 设计目标

当前设计目标不是扩成无限章节系统，而是稳定当前真实 5 章链路：

- 多章连续性更稳定
- state transition 显式且可审计
- 失败后 formal state 可恢复
- CLI 能把当前状态和排障入口讲清楚

## 当前推荐入口

- `phase1_cli.py`
- `phase2_cli.py`

`app.py` 仍保留，但只是兼容入口。

## 当前主链分层

### 内容生成层

- 规划
- 草稿生成
- 改写
- 摘要
- suggestion 生成

### state / review 层

- review artifact 显式化
- deterministic consistency checks
- formal state commit
- snapshot / restore

### 编排层

- Phase 1 的单章命令
- Phase 2 的 loop runner
- status / diagnostics 聚合

## 当前主链流程

单章主链当前是：

`plan -> draft -> rewrite -> summarize -> suggest -> review -> consistency_check -> commit`

其中：

- `write_chapter()` 负责前半段内容产物
- `commit_suggestion()` 是唯一公开提交入口
- Phase 1 `commit-suggestion` 和 Phase 2 自动推进都调用它

## Stage 1：Context Assembler

章节 context 已从 `workflow_service` 中抽出到独立 helper。

当前 context 组装原则：

- `chapter 1` 的 `previous_summary` 为空串
- 缺失 previous summary 时不报错，只按空串处理
- 历史 timeline 只带入前章内容，并做截断
- foreshadow 只带入 open 项

这保证了默认主链依赖 structured state + summary，而不是把整章正文直接喂回模型。

## Stage 2：Suggestion -> Review -> Commit

当前主链不再是 suggestion 直接覆盖正式状态。

真实提交顺序是：

1. 读取 canonical suggestion
2. 生成或刷新 canonical review
3. 从 review 的 `approved_suggestion` 作为 commit 输入
4. 成功后再标记 review / suggestion committed

这让两条主链都具备了最小可审计性，而且没有新增人工审批步骤。

## Stage 3：Deterministic Consistency Checks

review 上会写 `consistency_check`，当前只接 cheap / deterministic checks。

主链特性：

- blocker 阻止 formal commit
- warning 不阻止 commit
- committed review 不会重跑检查
- LLM checker 不在默认主链

这保证默认路径不会因为昂贵或不稳定的语义检查而变脆。

## Stage 4：Recoverable Commit

formal state 提交现在是“章节级可恢复提交”。

提交顺序固定为：

1. preflight snapshot handling
2. suggestion load
3. review creation
4. consistency check
5. review load
6. 计算完整 next formal state
7. 写 pending snapshot
8. 写 `characters.json`
9. 写 `timeline.json`
10. 写 `foreshadow.json`
11. 写 committed review marker
12. 写 committed suggestion marker
13. 删除 snapshot

关键点：

- `state_before` 保存 3 个 canonical formal state 文件的完整 JSON 原样副本
- formal write 或 marker write 中途失败时，会 restore formal state
- rerun 同章前会先处理 unresolved snapshot
- stale snapshot 只 cleanup，不回滚已成功提交的 formal state

## Stage 5：Status / Diagnostics

新增了只读诊断层：

- `build_project_status_report()`
- `build_chapter_diagnostic_report()`

它们会聚合：

- `loop_state.json`
- latest checkpoint
- canonical review / suggestion / snapshot

当前诊断层负责回答：

- 当前写到哪一章
- 最近成功提交到哪一章
- 最近失败在哪一步
- 是否有 unresolved snapshot
- 是否有 stale snapshot
- focus chapter 的 checkpoint / review / suggestion / snapshot 是否对得上

## 核心 artifact 语义

### `loop_state.json`

只管理流程进度，不承载正式故事状态。

### `characters.json` / `timeline.json` / `foreshadow.json`

唯一 canonical formal state。

### `suggestions/chXXX.suggestion.json`

原始 AI proposal。

### `reviews/chXXX.review.json`

显式 commit 依据，包含：

- `approved_suggestion`
- `consistency_check`
- `committed`

### `checkpoints/chXXX.checkpoint.json`

单章执行索引，包含：

- `status`
- `failure_stage`
- `artifacts`
- `error`

### `snapshots/chXXX.snapshot.json`

formal commit 前快照，用于中途失败后的 restore。

## 当前状态判定语义

### `last_successfully_committed_chapter_no`

优先按 canonical reviews / suggestions 扫描：

- 按 chapter 号递增
- 取双方都 `committed=true` 的最大 chapter

若无法可靠确定：

- 回退到 `loop_state_last_completed_chapter_no`
- 同时标记 `last_successfully_committed_source=loop_state_fallback`
- `commit_scan_status=unknown`
- 必要时显示 `commit_loop_drift`

### `artifact_relation_status`

- `aligned`
  - 已存在 artifact 彼此一致
- `partial`
  - 有部分缺失，但没发现冲突
- `mismatched`
  - 已存在 artifact 之间有明确冲突
- `unknown`
  - 因损坏或字段缺失无法可靠判断

## 推荐排障顺序

主链推荐排障顺序固定为：

1. `checkpoint`
2. `snapshot`
3. `review`
4. `suggestion`

理由：

- checkpoint 是总索引
- snapshot 决定是否存在未完成恢复问题
- review 才是 commit 的显式依据
- suggestion 只代表原始 proposal

## 当前不变项

Stage 5 没有改变以下语义：

- 不新增 CLI 命令
- 不改 prompt
- 不引入 LLM checker 到默认主链
- 不改 Stage 1~4 的核心 commit 语义

## 相关文档

- `README.md`
- `docs/phase1.md`
- `docs/phase2_longform_usage.md`
