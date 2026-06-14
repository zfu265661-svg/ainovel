# 长篇小说叙事引擎

本项目是一个受 PlotPilot 启发的长篇小说写作引擎 MVP。它不是一次性聊天写作器：它负责管理叙事状态、装配分层上下文、运行可追溯的章节流水线、生成确定性的一致性检查报告，并对外提供 CLI、FastAPI 和 Streamlit 三种界面。

## 安装

```powershell
python -m pip install -r requirements.txt
```

## 初始化项目

```powershell
python -m interfaces.cli.main init-project --name "demo"
```

项目数据存放在 `data/projects/demo/` 目录下。

## 运行 CLI

```powershell
python -m interfaces.cli.main run-chapter --project-id demo --chapter-id 1
python -m interfaces.cli.main inspect-context --project-id demo --chapter-id 1
python -m interfaces.cli.main inspect-trace --project-id demo --chapter-id 1
python -m interfaces.cli.main inspect-report --project-id demo --chapter-id 1
```

## 启动 FastAPI

```powershell
python -m uvicorn interfaces.api.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：

```text
GET http://127.0.0.1:8000/health
```

## 启动 Streamlit

```powershell
python -m streamlit run interfaces/streamlit/app.py
```

工作台可以创建/选择项目、运行章节，并查看快照、各类账本、上下文审计、流水线追踪、一致性报告以及检查点。

## 运行测试

```powershell
python -m pytest
```

## 当前 MVP 能力

- 项目仓库以 JSON 形式存放在 `data/projects/{project_id}/`
- 领域模型覆盖：项目、章节、角色、地点、组织、Story Bible、伏线、伏笔、场景、快照、上下文包、追踪、报告、检查点
- 单章流水线：`prepare -> load_snapshot -> build_chapter_plan -> assemble_context -> draft -> rewrite -> summarize -> suggest_updates -> consistency_check -> review_gate -> commit_snapshot -> save_outputs -> checkpoint -> finish`
- 四层上下文装配：`mandatory`（强制）、`compressed`（压缩）、`recent`（近期）、`optional`（可选）
- 确定性一致性检查器，不依赖 LLM
- FastAPI 接口、CLI 与 Streamlit 工作台
- 全新 CLI

## 下一阶段

- 用可配置 provider 的生成器替换当前确定性的 LLM 适配器
- 在提交快照前加入显式的评审通过制品
- 在不改变 use case 接口的前提下加入 SQLite 仓库
- 扩展伏线图谱与伏笔生命周期状态转换
- 丰富编辑工作流和导出格式
