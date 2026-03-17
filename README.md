# 小说写作 Agent

这是一个基于 Python 的小说写作 Agent 项目，支持总纲生成、章纲规划、正文生成、工作流编排，以及可选的一致性检查能力。

## 配置说明

项目使用兼容 OpenAI SDK 的提供方配置：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint
MODEL_NAME=your_model_name
```

这种方式可以在不修改服务层代码的前提下，切换不同的 OpenAI 兼容提供方。

## 如何切换到 DeepSeek API

将同样的环境变量替换为 DeepSeek 的配置即可：

```env
OPENAI_API_KEY=<DeepSeek API Key>
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

不需要修改业务层服务代码，`core/llm_client.py` 会继续读取当前配置中的 `base_url` 和 `model_name`。

## CLI 命令行运行方式

运行最小 CLI：

```bash
python app.py
```

CLI 默认走 `core/workflow_service.py` 中的基础工作流路径，不会调用可选的一致性检查 companion API。

## Workflow API 说明

`run_basic_workflow()` 是默认的编排路径，能力包括：
- 生成总纲
- 生成章纲
- 生成正文
- 当 `core.rewrite_service` 可用时，对正文进行可选改写
- 返回 `outline`、`chapter_plan`、`draft` 和 `rewritten_draft`

`run_basic_workflow_with_consistency_check()` 是一个供开发者显式调用的 companion API，能力包括：
- 先调用 `run_basic_workflow()`
- 优先使用 `rewritten_draft`，如果没有则回退到 `draft`，作为一致性检查的正文输入
- 在返回结果中追加 `consistency_check` 字段
- 不影响默认 CLI 路径

## 一致性检查上下文

当前 companion API 会将以下内容传入 `core.checker_service.check_consistency()`：
- `draft_text`：`rewritten_draft` 或 `draft`
- `outline`：workflow 生成的总纲结果
- `character_info`：当前仅使用从总纲中投影出的主角信息
- `timeline`：从 `data/timeline.json` 读取的历史时间线事件

时间线加载策略如下：
- 如果 `data/timeline.json` 不存在，companion API 会回退为 `[]`
- 如果时间线数据存在，只会将 `chapter_no` 小于当前章节号的历史事件传给 checker
- 如果时间线数据存在但内容非法，一致性检查路径会通过 workflow 的错误包装机制失败，而不是静默忽略脏数据

当前限制：
- `character_info` 目前仍然只包含主角投影，还没有接入完整角色库
- 默认 CLI 路径不会展示一致性检查结果
- companion API 的定位是开发者显式调用的增强路径，而不是默认运行路径

## 虚拟环境

在项目根目录创建虚拟环境：

```bash
python -m venv .venv
```

在 Git Bash 中激活：

```bash
source .venv/Scripts/activate
```

安装依赖：

```bash
python -m pip install -r requirements.txt
```

确认当前解释器：

```bash
python -c "import sys; print(sys.executable)"
```

## 测试

运行一组聚焦测试：

```bash
python -m pytest tests/test_config.py tests/test_llm_client.py
```

运行全部测试：

```bash
python -m pytest
```
