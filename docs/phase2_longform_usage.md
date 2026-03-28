# Phase 2 Longform Usage

## 当前目标与边界

Phase 2 当前的目标不是重写整个项目，而是在已有 Phase 1 能力之上，提供一个最小可用的长篇连续写作 workflow：

- 初始化流程状态
- 从当前 `next_chapter_no` 继续运行
- 顺序推进到第 5 章
- 在失败时保留足够状态，便于继续恢复

当前不覆盖：

- 通用无限循环
- review 主流程接入
- 复杂上下文检索
- 自动扩展更多章节规划

## Phase 1 与 Phase 2 的区别

Phase 1 负责“单步能力”：

- 创建项目
- 生成规划
- 写单章
- 提交 suggestion

Phase 2 负责“连续推进”：

- 管理 `loop_state.json`
- 把单章闭环固化成可恢复步骤
- 从当前状态顺序推进到第 5 章

Phase 2 不替代 Phase 1，而是复用 Phase 1。

## 前置条件

使用 Phase 2 之前，应先确保：

1. 已安装依赖并配置好 `.env`
2. 已通过 Phase 1 创建项目
3. 已通过 `plan-novel` 生成好章节规划

最小前置命令：

```bash
python phase1_cli.py create-project --root <project_root> --title <title> --topic <topic> --style <style> --target <target>
python phase1_cli.py plan-novel --root <project_root>
```

## 命令说明

### 1. 初始化 loop_state

```bash
python phase2_cli.py init-loop --root <project_root>
```

作用：

- 创建 `loop_state.json`
- 创建 `checkpoints/`
- 创建 `reviews/` 预留目录

当前固定目标章节数为 5。

### 2. 查看状态

```bash
python phase2_cli.py show-status --root <project_root>
```

当前会显示的关键字段包括：

- `status`
- `start_chapter_no`
- `target_chapter_count`
- `next_chapter_no`
- `last_completed_chapter_no`
- `current_chapter_no`

### 3. 顺序运行到第 5 章

```bash
python phase2_cli.py run-five --root <project_root>
```

作用：

- 从当前 `loop_state.next_chapter_no` 开始
- 顺序调用现有单章闭环
- 成功则继续下一章
- 某一章失败则立即停止

不需要单独的 `resume` 命令；再次执行 `run-five` 即可按当前状态继续。

## 最小使用示例

```bash
python phase1_cli.py create-project --root "D:/AI novel/workspace/demo_novel" --title "Demo Novel" --topic "玄幻复仇" --style "冷峻、克制、偏网文节奏" --target "男频长篇"
python phase1_cli.py plan-novel --root "D:/AI novel/workspace/demo_novel"
python phase2_cli.py init-loop --root "D:/AI novel/workspace/demo_novel"
python phase2_cli.py show-status --root "D:/AI novel/workspace/demo_novel"
python phase2_cli.py run-five --root "D:/AI novel/workspace/demo_novel"
```

如果中途失败，直接再次执行：

```bash
python phase2_cli.py run-five --root "D:/AI novel/workspace/demo_novel"
```

## loop_state / resume 语义

`loop_state.json` 只管理流程进度，不管理正式故事状态。

它不替代：

- `characters.json`
- `timeline.json`
- `foreshadow.json`

关键字段说明：

- `next_chapter_no`
  - 下次恢复时应从哪一章开始
- `last_completed_chapter_no`
  - 最近一章已经完整提交成功的章节号
- `current_chapter_no`
  - 当前尝试执行的章节号，失败时可用于定位
- `status`
  - `ready`、`failed`、`completed` 等流程状态

当前 resume 规则：

- 只有在该章 `suggestion` 提交成功后，才推进 `next_chapter_no`
- 如果 `write_chapter` 或 `commit_suggestion` 失败，则不推进 `next_chapter_no`
- 再次运行 `run-five` 时，默认从 `next_chapter_no` 继续

## 运行产物

Phase 2 在项目目录下额外使用这些文件和目录：

- `loop_state.json`
- `checkpoints/chXXX.checkpoint.json`
- `reviews/` 预留目录

单章成功后，仍然主要复用 Phase 1 产物：

- `docs/chXXX.draft.md`
- `docs/chXXX.rewrite.md`
- `docs/chXXX.summary.md`
- `suggestions/chXXX.suggestion.json`

## 当前已知限制

- 当前只支持固定跑到第 5 章
- 不支持通用无限循环
- 不接入 `review_service`
- 不做复杂上下文检索
- 不自动新建更多章节规划
- `reviews/` 当前只是预留目录，未进入主流程

## 建议测试命令

最小相关测试：

```bash
python -m pytest tests/longform/test_phase2_cli.py tests/longform/test_serial_workflow_service.py tests/longform/test_chapter_runner_service.py tests/longform/test_loop_state_service.py tests/longform/test_project_state_repository.py
```

如果要带 Phase 1 关键链路一起验证：

```bash
python -m pytest tests/test_workflow_write_chapter.py tests/test_workflow_commit_suggestion.py tests/test_suggestion_service.py tests/longform/test_phase2_cli.py tests/longform/test_serial_workflow_service.py tests/longform/test_chapter_runner_service.py
```
