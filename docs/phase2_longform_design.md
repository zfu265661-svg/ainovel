# Phase 2 Longform Design

当前阶段只做两件事：

- 冻结现有 `Phase 1` 基线，确保旧项目结构和运行逻辑不被 longform 改动影响。
- 新增 `loop_state.json` 流程状态层，为后续 5 章连续写作做可恢复基础。

## 设计边界

- 不修改 `app.py`、`phase1_cli.py`、`core/workflow_service.py`、`prompts/*`
- `loop_state.json` 只管理流程进度，不管理 `characters.json`、`timeline.json`、`foreshadow.json`
- `review_service` 本阶段不接入主流程
- `chapter_context_service` 暂不实现，仅保留骨架

## loop_state 最小字段

```json
{
  "version": 1,
  "status": "ready",
  "start_chapter_no": 1,
  "target_chapter_count": 5,
  "next_chapter_no": 1,
  "last_completed_chapter_no": 0,
  "current_chapter_no": null
}
```

## resume 语义

- `resume` 永远从 `next_chapter_no` 继续。
- 只有章节完整提交成功后，才允许把 `next_chapter_no` 向前推进。
- `current_chapter_no` 只是观测字段，不代表正式故事状态已经提交。
- 正式故事状态仍然由现有 `characters/timeline/foreshadow` 文件管理。
