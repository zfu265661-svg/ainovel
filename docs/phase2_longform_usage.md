# Phase 2 Longform Usage

## 当前目标与边界

Phase 2 当前目标是提供一个最小可用的 longform workflow，用已有的 `Phase 1` 单章闭环能力，顺序推进到第 5 章。

当前只覆盖：

- 初始化 longform 流程状态
- 查看当前流程状态
- 从当前 `next_chapter_no` 继续运行，直到第 5 章或某一章失败

当前不覆盖：

- 替代旧主流程
- review 接入
- 复杂上下文检索
- 通用无限循环
- 自动新增章节规划

## Phase 1 与 Phase 2 的区别

`Phase 1` 关注单章和单次步骤：

- `create_project`
- `plan_novel`
- `write_chapter`
- `commit_suggestion`

`Phase 2` 关注“在已有项目上连续推进”：

- 用 `loop_state.json` 记录流程进度
- 用 `run_single_chapter()` 固化单章原子步骤
- 用 `run_five_chapter_loop()` 顺序推进到第 5 章

可以把 Phase 2 理解为：

- 不改写 `Phase 1`
- 只是在其上增加一个极薄的连续写作编排层

## 前置条件

使用 Phase 2 前，建议先具备以下条件：

1. 已创建小说项目根目录，且项目结构符合现有 `Phase 1` 约定。
2. 已完成基础规划，至少已有可供执行的章节规划。
3. 已配置运行环境与模型配置：
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `MODEL_NAME`
4. 已安装依赖：

```bash
python -m pip install -r requirements.txt
```

如果还没有项目，通常先走 `Phase 1`：

```bash
python phase1_cli.py create-project --root <project_root> --title <title> --topic <topic> --style <style> --target <target>
python phase1_cli.py plan-novel --root <project_root>
```

## 命令说明

### 初始化 loop_state

```bash
python phase2_cli.py init-loop --root <project_root>
```

用途：

- 创建 `loop_state.json`
- 初始化 `checkpoints/`
- 初始化 `reviews/` 目录占位

当前固定目标章节数为 5。

### 查看当前状态

```bash
python phase2_cli.py show-status --root <project_root>
```

用途：

- 查看当前 `loop_state` 的关键字段
- 判断当前会从哪一章继续

当前输出包含：

- `status`
- `start_chapter_no`
- `target_chapter_count`
- `next_chapter_no`
- `last_completed_chapter_no`
- `current_chapter_no`

### 顺序运行到第 5 章

```bash
python phase2_cli.py run-five --root <project_root>
```

用途：

- 从当前 `loop_state.next_chapter_no` 开始
- 顺序调用现有 longform workflow
- 成功则继续下一章
- 失败则立即停止

它不会从头重跑，也不需要单独的 `resume` 命令。

## 最小使用示例

假设项目目录为 `D:\novels\demo`。

先完成 Phase 1 项目初始化和规划：

```bash
python phase1_cli.py create-project --root D:\novels\demo --title Demo --topic xianxia --style cold --target serial
python phase1_cli.py plan-novel --root D:\novels\demo
```

然后初始化 Phase 2 loop：

```bash
python phase2_cli.py init-loop --root D:\novels\demo
```

查看状态：

```bash
python phase2_cli.py show-status --root D:\novels\demo
```

开始运行：

```bash
python phase2_cli.py run-five --root D:\novels\demo
```

如果运行到第 3 章失败，再次执行同一条命令：

```bash
python phase2_cli.py run-five --root D:\novels\demo
```

系统会从 `next_chapter_no` 对应章节继续，而不是从第 1 章重跑。

## loop_state / resume 语义

`loop_state.json` 只管理流程进度，不管理正式故事状态。

它不替代：

- `characters.json`
- `timeline.json`
- `foreshadow.json`

当前关键字段含义：

- `next_chapter_no`
  - 下次继续执行时应从哪一章开始
- `last_completed_chapter_no`
  - 最近一次已经完整提交成功的章节号
- `current_chapter_no`
  - 当前尝试执行的章节号；失败时可用于观察卡在哪一章
- `status`
  - 当前流程状态，例如 `ready`、`failed`、`completed`

当前 resume 规则：

- 只有在 `suggestion` 提交成功后，才推进 `next_chapter_no`
- 如果 `write_chapter` 或 `commit_suggestion` 失败，则不推进 `next_chapter_no`
- 再次运行 `run-five` 时，默认从 `next_chapter_no` 继续

## 当前已知限制

- 当前只支持最小 5 章 workflow
- 不支持通用无限循环
- 不接入 review_service
- 不做复杂上下文检索
- 不自动扩展章节规划
- 不替代旧 `app.py`
- 不替代旧 `phase1_cli.py`
- `reviews/` 目录当前只是预留，未进入主流程

## 建议测试命令

最小相关测试：

```bash
python -m pytest tests/longform/test_phase2_cli.py tests/longform/test_serial_workflow_service.py tests/longform/test_chapter_runner_service.py tests/longform/test_loop_state_service.py tests/longform/test_project_state_repository.py
```

带旧流程回归的建议测试：

```bash
python -m pytest tests/longform/test_phase2_cli.py tests/longform/test_serial_workflow_service.py tests/longform/test_chapter_runner_service.py tests/longform/test_loop_state_service.py tests/longform/test_project_state_repository.py tests/test_phase1_cli.py tests/test_phase1_e2e.py tests/test_phase2_commit_e2e.py
```
