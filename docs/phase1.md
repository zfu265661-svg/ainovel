# Phase 1 开发说明

当前仓库已经打通 Phase 1 最小闭环，核心入口位于 [core/workflow_service.py](/D:/AI novel/core/workflow_service.py)：

- `create_project(project_root, title, topic, style, target)`
- `plan_novel(project_root)`
- `write_chapter(project_root, chapter_no)`
- `commit_suggestion(project_root, chapter_no)`

## 当前已实现的能力

- 创建项目目录和最小状态文件。
- 生成并落盘总纲、分卷规划、章节规划。
- 基于已有章节规划生成正文初稿、改写稿、章节摘要、状态建议。
- 将 suggestion 以最小规则提交到正式状态文件。
- 将文档和结构化状态分开保存：
  - 文档产物在 `docs/`
  - 结构化状态在项目根目录 JSON
  - 建议产物在 `suggestions/`

## 当前 Phase 1 的边界

- 不改旧 [app.py](/D:/AI novel/app.py)。
- 不接 checker 默认链路。
- 不做逐条人工确认。
- 不做复杂冲突解决。
- 不做回滚 / 撤销。
- 不做多章自动推进。

## 最小验证方式

```bash
python -m pytest tests/test_phase1_e2e.py
python -m pytest tests/test_phase2_commit_e2e.py
python -m pytest
```

其中：

- `tests/test_phase1_e2e.py` 覆盖 `create_project -> plan_novel -> write_chapter`
- `tests/test_phase2_commit_e2e.py` 覆盖 `create_project -> plan_novel -> write_chapter -> commit_suggestion`

## Phase 1 CLI

当前已新增独立入口 [phase1_cli.py](/D:/AI novel/phase1_cli.py)，用于调用 Phase 1 工作流。  
这是新入口，不替代旧 [app.py](/D:/AI novel/app.py)。

可用命令：

```bash
python phase1_cli.py create-project --root <project_root> --title <title> --topic <topic> --style <style> --target <target>
python phase1_cli.py plan-novel --root <project_root>
python phase1_cli.py write-chapter --root <project_root> --chapter 1
python phase1_cli.py commit-suggestion --root <project_root> --chapter 1
```

职责范围：

- `create-project`：创建项目目录和最小状态文件。
- `plan-novel`：生成并落盘总纲、分卷、章节规划。
- `write-chapter`：生成并落盘正文初稿、改写稿、摘要、状态建议。
- `commit-suggestion`：将某一章的 suggestion 以最小规则提交到正式状态。

当前 CLI 不做：

- checker 接线
- 人工确认交互
- 替代旧 CLI 入口

## Suggestion 提交

当前已支持最小的 suggestion 提交流程：

```bash
python phase1_cli.py commit-suggestion --root <project_root> --chapter 1
```

对应入口：

- [core/workflow_service.py](/D:/AI novel/core/workflow_service.py) 中的 `commit_suggestion(project_root, chapter_no)`
- [phase1_cli.py](/D:/AI novel/phase1_cli.py) 中的 `commit-suggestion`

当前支持的最小规则：

- `character_updates`
  - `add`：不存在则创建最小角色条目
  - `update`：存在则将 `content` 追加到 `current_state`；不存在则创建最小角色条目
- `timeline_updates`
  - 追加写入 `timeline.json`
- `foreshadow_updates`
  - `add`：新增最小伏笔条目
  - `update`：存在则更新 `status`；不存在则新增最小伏笔条目

当前不支持：

- 逐条人工编辑
- 回滚 / 撤销
- 复杂冲突解决
- 多章批量提交

为什么这是最小实现：

- 只解决“建议如何进入正式状态”这一件事
- 规则明确，可测试
- 不引入交互阻塞点

重复提交防护：

- 成功提交后，会在对应的 `suggestions/chXXX.suggestion.json` 中写入 `committed: true`
- 同一章 suggestion 再次提交会被拒绝

## 连续写作上下文增强

这部分是当前版本对“连续写作质量”的一轮最小增强。  
目标不是彻底解决长篇连续性问题，而是让 `write_chapter()` 已经读取到的上下文，真正进入正文生成阶段。

### 当前 `write_chapter()` 的上下文来源

在 [core/workflow_service.py](/D:/AI novel/core/workflow_service.py) 的 `write_chapter()` 中，正文生成前会读取：

- `project.json`
- `docs/outline.md`
- `chapters.json`
- `docs/chXXX.plan.md`
- 上一章 `docs/chXXX.summary.md`（不存在则为空）
- `characters.json`
- `timeline.json`
- `foreshadow.json`

其中与连续写作直接相关的上下文是：

- 总纲 `outline`
- 上一章摘要 `previous_summary`
- 人物状态 `characters`
- 时间线 `timeline`
- 伏笔状态 `foreshadow`

### 当前如何整理这些上下文

`write_chapter()` 在传给正文生成前，会通过以下内部 helper 整理上下文：

- `_build_draft_context(...)`
- `_compact_character_context(...)`
- `_select_recent_timeline_events(...)`
- `_select_active_foreshadow_items(...)`

这是内部实现细节增强，没有改变：

- `write_chapter()` 的对外接口
- `create_project()` / `plan_novel()` / `commit_suggestion()`
- Phase 1 CLI 命令

### timeline 过滤规则

时间线不会再全量原样送入正文生成，而是按以下规则过滤：

- 只保留 `chapter_no < 当前章号` 的历史事件
- 只取最近 `N=5` 条

这样做的原因：

- 避免把当前章或未来章事件误传给正文生成
- 避免时间线随着章节增长无限膨胀
- 优先保留最近连续写作最相关的历史上下文

### foreshadow 过滤规则

伏笔不会再全量原样送入正文生成，而是只保留活跃项：

- 优先按 `status == "open"` 判断

这样做的原因：

- 已解决伏笔通常不应继续占用正文生成上下文
- 活跃伏笔更适合被“轻度推进”或“再次呼应”
- 提升输入信噪比

### characters 整理规则

角色信息当前不做复杂相关性排序，但会先整理成更稳定的最小结构：

- `name`
- `role`
- `traits`
- `current_state`

补充规则：

- 没有 `name` 的角色项会被跳过
- 其他无关字段不会传给正文 prompt

这样做的原因：

- 先降低角色状态输入噪声
- 保留当前章最基础、最稳定的角色上下文
- 不在这一轮引入复杂的人物筛选逻辑

### draft prompt 如何消费上下文

当前 [prompts/draft.txt](/D:/AI novel/prompts/draft.txt) 已从主要依赖：

- `{chapter_plan}`
- `{character_info}`
- `{style_rules}`

调整为主要依赖：

- `{chapter_plan}`
- `{context_bundle}`
- `{style_rules}`

这意味着正文生成阶段现在会明确消费：

- 总纲
- 上一章摘要
- 历史时间线
- 活跃伏笔
- 当前角色状态

这样做的目的不是增加更多输入字段，而是把已有上下文收敛成一个更稳定的连续写作入口，避免多个散字段并行带来的重复和混乱。

### 当前增强的边界

这一轮只是“最小增强”，仍然没有做：

- 更高质量的摘要结构化
- 角色相关性排序
- 伏笔重要性排序
- 更复杂的 timeline 检索
- checker 介入正文生成前链路

结论：

- 当前系统已经从“收集上下文但正文阶段基本没吃到”前进到“正文阶段开始实际消费连续写作上下文”
- 但它仍然只是一个最小可用版本，不应视为已经完全解决长篇连续写作问题
