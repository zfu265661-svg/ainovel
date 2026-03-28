# Phase 1 使用说明

## 目标

Phase 1 负责把一个小说项目从“空目录”推进到“已完成规划、可写单章、可提交状态建议”的最小闭环。

它不负责连续多章自动推进；那部分由 Phase 2 处理。

## 当前能力

- 创建项目目录与基础状态文件
- 生成总纲、分卷规划、章节规划
- 按指定章节生成初稿、改写稿、摘要、状态建议
- 将状态建议提交到正式故事状态文件

核心入口都在 `core/workflow_service.py`：

- `create_project(project_root, title, topic, style, target)`
- `plan_novel(project_root)`
- `write_chapter(project_root, chapter_no)`
- `commit_suggestion(project_root, chapter_no)`

## CLI 命令

### 创建项目

```bash
python phase1_cli.py create-project --root <project_root> --title <title> --topic <topic> --style <style> --target <target>
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
python phase1_cli.py plan-novel --root <project_root>
```

典型输出：

- `docs/outline.md`
- `docs/volumes.md`
- `chapters.json`
- `docs/ch001.plan.md` 到 `docs/chXXX.plan.md`

### 写单章

```bash
python phase1_cli.py write-chapter --root <project_root> --chapter 1
```

典型输出：

- `docs/ch001.draft.md`
- `docs/ch001.rewrite.md`
- `docs/ch001.summary.md`
- `suggestions/ch001.suggestion.json`

### 提交状态建议

```bash
python phase1_cli.py commit-suggestion --root <project_root> --chapter 1
```

典型更新：

- `characters.json`
- `timeline.json`
- `foreshadow.json`
- `suggestions/ch001.suggestion.json` 会写入 `committed: true`

## 最小使用顺序

```bash
python phase1_cli.py create-project --root "D:/AI novel/workspace/demo_novel" --title "Demo Novel" --topic "玄幻复仇" --style "冷峻、克制、偏网文节奏" --target "男频长篇"
python phase1_cli.py plan-novel --root "D:/AI novel/workspace/demo_novel"
python phase1_cli.py write-chapter --root "D:/AI novel/workspace/demo_novel" --chapter 1
python phase1_cli.py commit-suggestion --root "D:/AI novel/workspace/demo_novel" --chapter 1
```

## 与旧入口的关系

- `phase1_cli.py` 是当前推荐的 Phase 1 入口
- `app.py` 仍保留，但不建议作为当前主链路使用

## 当前边界

- 默认 CLI 不接入 review/checker 主流程
- 不做人工逐条确认
- 不做多章自动推进
- 不做复杂冲突解决或回滚

## 建议测试

```bash
python -m pytest tests/test_phase1_e2e.py tests/test_phase2_commit_e2e.py
```

如果要补充回归：

```bash
python -m pytest tests/test_workflow_write_chapter.py tests/test_workflow_commit_suggestion.py tests/test_suggestion_service.py
```
