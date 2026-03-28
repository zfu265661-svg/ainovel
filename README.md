# 小说写作 Agent

这是一个基于 Python 的小说写作 Agent 项目，当前已经打通两条可运行主链路：

- Phase 1：创建项目、生成总纲与章节规划、生成单章正文、提交状态建议
- Phase 2：在已有 Phase 1 项目上，按 `loop_state` 连续推进到第 5 章

当前仓库的目标不是一次性解决几百章长篇自动化，而是先把“可规划、可写单章、可连续跑 5 章、可恢复”的最小闭环做稳定。

## 当前已实现能力

### Phase 1

- `create-project`：创建项目目录和最小状态文件
- `plan-novel`：生成并落盘 `outline.md`、`volumes.md`、`chapters.json`、`chXXX.plan.md`
- `write-chapter`：基于已有章节规划生成正文初稿、改写稿、摘要、状态建议
- `commit-suggestion`：将某一章的 suggestion 提交到正式状态文件

### Phase 2

- `init-loop`：初始化 `loop_state.json`
- `show-status`：查看连续写作流程状态
- `run-five`：从当前 `next_chapter_no` 顺序运行到第 5 章或失败位置

## 环境准备

推荐步骤：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
python -m pip install -r requirements.txt
```

当前依赖很少：

- `python-dotenv`
- `openai`
- `pytest`

## .env 配置说明

项目通过 `.env` 读取 OpenAI 兼容接口配置。最小必需项：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
MODEL_NAME=your_model_name
```

如果你使用 DeepSeek，当前真实跑通配置示例是：

```env
OPENAI_API_KEY=<your_deepseek_api_key>
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

说明：

- `OPENAI_BASE_URL` 应指向兼容接口的根地址
- DeepSeek 建议显式使用 `/v1`
- `MODEL_NAME` 需要与所用提供方的可用模型一致

## 快速开始

下面是一条从零开始的最小复现路径。

### 1. 创建项目

```bash
python phase1_cli.py create-project --root "D:/AI novel/workspace/demo_novel" --title "Demo Novel" --topic "玄幻复仇" --style "冷峻、克制、偏网文节奏" --target "男频长篇"
```

### 2. 生成规划

```bash
python phase1_cli.py plan-novel --root "D:/AI novel/workspace/demo_novel"
```

预期产物：

- `docs/outline.md`
- `docs/volumes.md`
- `chapters.json`
- `docs/ch001.plan.md` 等章节规划文件

### 3. 写第 1 章并提交状态

```bash
python phase1_cli.py write-chapter --root "D:/AI novel/workspace/demo_novel" --chapter 1
python phase1_cli.py commit-suggestion --root "D:/AI novel/workspace/demo_novel" --chapter 1
```

### 4. 初始化 Phase 2 连续写作状态

```bash
python phase2_cli.py init-loop --root "D:/AI novel/workspace/demo_novel"
```

### 5. 运行到第 5 章

```bash
python phase2_cli.py run-five --root "D:/AI novel/workspace/demo_novel"
```

查看当前状态：

```bash
python phase2_cli.py show-status --root "D:/AI novel/workspace/demo_novel"
```

## Phase 1 命令示例

```bash
python phase1_cli.py create-project --root <project_root> --title <title> --topic <topic> --style <style> --target <target>
python phase1_cli.py plan-novel --root <project_root>
python phase1_cli.py write-chapter --root <project_root> --chapter 1
python phase1_cli.py commit-suggestion --root <project_root> --chapter 1
```

Phase 1 推荐阅读：

- `docs/phase1.md`

## Phase 2 命令示例

```bash
python phase2_cli.py init-loop --root <project_root>
python phase2_cli.py show-status --root <project_root>
python phase2_cli.py run-five --root <project_root>
```

Phase 2 推荐阅读：

- `docs/phase2_longform_usage.md`
- `docs/phase2_longform_design.md`

## 目录结构

仓库层级：

```text
AI novel/
├─ core/                  # 核心服务与 workflow
├─ docs/                  # 使用说明与设计文档
├─ prompts/               # 提示词模板
├─ tests/                 # pytest 测试
├─ workspace/             # 本地小说项目示例或运行产物
├─ app.py                 # 旧入口，保留
├─ phase1_cli.py          # Phase 1 CLI
├─ phase2_cli.py          # Phase 2 CLI
├─ config.py              # 配置加载
└─ README.md
```

单个小说项目目录大致如下：

```text
<project_root>/
├─ project.json
├─ chapters.json
├─ characters.json
├─ timeline.json
├─ foreshadow.json
├─ loop_state.json              # Phase 2 流程状态
├─ docs/
│  ├─ outline.md
│  ├─ volumes.md
│  ├─ ch001.plan.md
│  ├─ ch001.draft.md
│  ├─ ch001.rewrite.md
│  └─ ch001.summary.md
├─ suggestions/
│  └─ ch001.suggestion.json
├─ checkpoints/
│  └─ ch001.checkpoint.json
└─ reviews/                     # 预留目录，当前未接主流程
```

## 当前限制

- `app.py` 仍保留，但不是当前推荐主入口
- Phase 2 当前只实现固定 5 章 workflow，不支持通用无限循环
- 未接入 `review_service`
- 未实现复杂上下文检索或长期记忆系统
- 连续写作恢复语义目前完全依赖 `loop_state.json`
- 仍然依赖模型较稳定地返回 JSON；虽然已做最小兼容，但不是通用鲁棒解析框架

## 建议测试命令

Phase 1 最小回归：

```bash
python -m pytest tests/test_phase1_e2e.py tests/test_phase2_commit_e2e.py
```

Phase 2 最小回归：

```bash
python -m pytest tests/longform/test_phase2_cli.py tests/longform/test_serial_workflow_service.py tests/longform/test_chapter_runner_service.py tests/longform/test_loop_state_service.py tests/longform/test_project_state_repository.py
```

相关链路一起验证：

```bash
python -m pytest tests/test_workflow_write_chapter.py tests/test_workflow_commit_suggestion.py tests/test_suggestion_service.py tests/longform/test_phase2_cli.py tests/longform/test_serial_workflow_service.py tests/longform/test_chapter_runner_service.py
```

## 后续计划

当前建议的后续方向是保守演进，而不是推翻现有链路：

- 继续提高 Phase 2 在真实环境下的稳定性
- 在不破坏旧主流程的前提下扩展更长的连续写作编排
- 把 review 能力以旁路方式接入，而不是先改主链路
- 逐步增强上下文压缩、状态更新和错误可观测性
