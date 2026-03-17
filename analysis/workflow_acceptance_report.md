# 小说 Agent 主流程验收报告

## 验收范围

本次仅基于代码与现有测试，对以下主流程做验收：

- CLI 入口：`app.py`
- 流程编排：`core/workflow_service.py`
- 总纲生成：`core/outline_service.py`
- 章节规划：`core/chapter_service.py`
- 正文生成：`core/draft_service.py`
- 可选润色：`core/rewrite_service.py`
- 可选存储：`core/storage.py`
- 相关测试：`tests/test_app.py`、`tests/test_app_cli.py`、`tests/test_basic_workflow_integration.py`、`tests/test_workflow_service.py`、`tests/test_outline_service.py`、`tests/test_chapter_service.py`、`tests/test_draft_service.py`、`tests/test_rewrite_service.py`、`tests/test_storage.py`、`tests/test_llm_client.py`、`tests/test_prompt_loader.py`

说明：

- 本次没有修改任何 Python 代码、prompt 模板或 README。
- 本次验收是“代码层面 + 测试层面”的主流程验收，不包含真实外部 LLM 接口联调结果。
- 已执行最小相关测试：`pytest tests/test_workflow_service.py tests/test_basic_workflow_integration.py tests/test_outline_service.py tests/test_chapter_service.py tests/test_draft_service.py tests/test_rewrite_service.py tests/test_storage.py tests/test_app.py tests/test_app_cli.py tests/test_llm_client.py tests/test_prompt_loader.py -q`
- 测试结果：`35 passed in 1.00s`

## 结论概览

结论：当前仓库已经具备一个“从总纲到正文”的最小主流程，代码调用链是完整的，且被测试覆盖到基础串联层；但它仍然只是单章、单轮、最小 MVP 级流程，不应视为“完整小说生产管线”。

更具体地说：

- `app.py` 已能收集 3 个最小输入参数，并调用 `run_basic_workflow(...)` 执行主流程。
- `core/workflow_service.py` 已把 `outline -> chapter_plan -> draft -> optional rewrite -> optional save` 串起来。
- `outline/chapter/draft/rewrite/storage` 各阶段都有基本异常处理或输出校验。
- 现有 CLI 足以演示“输入题材/风格/目标后生成一章正文”的 MVP。
- 但当前流程仍有明显断点：只支持第 1 章、没有章节循环、没有前情摘要累积、没有角色/设定状态回写、没有真正意义上的“从总纲稳定推进到整本书”。

## 当前主流程是否完整

### 结论

“最小单章主流程”完整；“整书主流程”不完整。

### 依据

1. `app.py:54-66` 已作为 CLI 主入口，收集输入后直接调用 `run_basic_workflow(...)`。
2. `core/workflow_service.py:29-63` 已顺序执行：
   - `generate_outline(...)`
   - `generate_chapter_plan(...)`
   - `generate_draft(...)`
   - `_run_optional_rewrite(...)`
3. `core/workflow_service.py:66-80` 提供了结果持久化入口 `save_workflow_result(...)`，可调用 `core.storage.save_json(...)`。
4. `tests/test_workflow_service.py` 与 `tests/test_basic_workflow_integration.py` 证明这条调用链在测试替身下可以完整跑通。

### 边界

以下能力当前并不存在，因此不能说“整书主流程完整”：

- 多章节连续生成
- 上一章摘要传递到下一章
- 角色/伏笔/时间线状态在章节间持续演化
- 失败重试、断点续跑、任务恢复
- 导出可发布稿件或整书结构化产物

## 已经能串起来的步骤

### 1. CLI 输入到主流程入口

`app.py:13-18` 收集 `topic/style/target`，`app.py:58-63` 把输入送入 `run_basic_workflow(...)`，并打印结果、尝试保存。

判断：已串通，可演示。

### 2. 总纲生成

`core/outline_service.py:28-36` 会：

- 加载 `prompts/outline.txt`
- 调用 `LLMClient().generate_text(...)`
- 把结果解析为 JSON 对象
- 校验必要字段 `title/core_hook/theme/protagonist/conflict/volume_plan`

判断：代码层面完整，且有解析/字段校验。

### 3. 章节规划生成

`core/workflow_service.py:40-47` 使用上一步的 `outline` 调用 `generate_chapter_plan(...)`。`core/chapter_service.py:28-45` 会加载 `prompts/chapter_plan.txt`，要求输出包含 `chapter_no/title/goal/conflict/beats/ending_hook`。

判断：总纲到章节规划已串通。

### 4. 章节规划到正文生成

`core/workflow_service.py:48-55` 调用 `generate_draft(...)`。其中：

- `chapter_plan` 直接传入正文生成
- `character_info` 仅来自 `outline["protagonist"]`，见 `core/workflow_service.py:101-105`
- `style_rules` 直接复用 CLI 输入的 `style`

`core/draft_service.py:13-34` 负责加载 `prompts/draft.txt` 并请求 LLM。

判断：章节规划到正文已串通，但输入上下文偏弱。

### 5. 正文到润色

`core/workflow_service.py:92-98` 会尝试动态加载 `core.rewrite_service`；若模块存在，则调用 `rewrite_text(...)`。

`core/rewrite_service.py:15-31` 已能加载 `prompts/rewrite.txt` 并请求 LLM。

判断：正文到润色可串通，但属于可选链路，不是强依赖。

### 6. 结果持久化

`app.py:42-51` 调用 `save_workflow_result(...)`；`core/workflow_service.py:66-80` 再委托 `core.storage.save_json(...)`；`core/storage.py:31-38` 会自动创建父目录后写 JSON。

判断：结果保存链路可用。

## 当前存在的断点或弱连接

### 1. 流程只跑第 1 章，没有真正的章节编排循环

`core/workflow_service.py:29-34` 虽然提供了 `chapter_no` 参数，但 `app.py:58-60` 固定只跑一次；没有章节迭代器，也没有“从卷纲到多章”的调度层。

影响：当前只能演示“生成一章”，不能证明“从总纲推进到整本正文”。

### 2. `previous_summary` 被硬编码为空字符串

`core/workflow_service.py:42-46` 调用章节规划时写死 `previous_summary=""`。

影响：章节之间没有连续性输入，后一章无法利用前一章结果，主流程只能算单章 smoke path，不是连续创作流程。

### 3. 正文生成只吃到主角信息，没吃到完整世界观/设定/卷纲

`core/workflow_service.py:101-105` 仅从 `outline["protagonist"]` 提取 `character_info`，没有把 `theme/conflict/volume_plan` 或更完整角色群像传给 `draft_service`。

影响：即使单章能生成，正文对总纲的继承关系仍较弱，容易出现“总纲存在但正文未充分使用”的弱连接。

### 4. Rewrite/Storage 被设计成“可选模块”，但当前仓库里其实是实存模块

`core/workflow_service.py:92-98` 与 `66-80` 都通过动态导入做“可选”处理。当前仓库里 `core/rewrite_service.py` 和 `core/storage.py` 确实存在，因此运行时通常会走这两步；但从流程语义上看，主流程对这两步并没有强约束。

影响：如果后续部署环境缺模块，主流程仍会“成功”，但行为会悄悄降级为“不润色/不保存”。这对 MVP 演示问题不大，但对验收透明度不够。

### 5. CLI 交互文案存在明显乱码迹象

从 `app.py:15-17`、`app.py:24`、`app.py:35-37`、`app.py:47`、`app.py:51`、`app.py:61`、`app.py:65` 以及 `tests/test_app_cli.py` 的断言文本看，中文输出当前呈现为乱码字符串。

影响：即使主链路可跑，CLI 的演示观感和可用性会明显受损，尤其在中文项目场景下。

说明：这里只报告现象，不判断是源码编码问题、终端编码问题还是历史文本已损坏；但对 MVP 演示来说，这已经是实际问题。

## 当前 CLI 是否足以演示 MVP

### 结论

足以演示“最小单章小说生成 MVP”，不足以演示“可持续写整本书的小说 Agent”。

### 原因

CLI 已覆盖以下最小闭环：

- 输入题材、风格、目标读者/篇幅方向
- 生成总纲
- 生成第 1 章章纲
- 生成正文
- 可选润色
- 保存结果到 `data/book.json`

对应代码见：

- `app.py:54-66`
- `core/workflow_service.py:29-63`

但它缺少以下 MVP 以上能力：

- 选择章节号
- 连续生成下一章
- 查看/复用历史产物
- 指定是否跳过润色
- 更细的失败信息与恢复动作

因此，如果把 MVP 定义为“现场证明主流程从输入到产出能走通”，答案是可以；如果把 MVP 定义为“可稳定演示整书写作过程”，答案是不够。

## 测试覆盖对验收结论的支撑

### 已覆盖部分

- `tests/test_outline_service.py`：总纲 JSON 解析与必填字段校验
- `tests/test_chapter_service.py`：章纲 JSON 解析、必填字段校验、`beats` 类型校验
- `tests/test_draft_service.py`：正文生成成功、空文本失败、LLM 异常包装
- `tests/test_rewrite_service.py`：润色成功、空输入失败、空输出失败、LLM 异常包装
- `tests/test_storage.py`：JSON/Text 读写与清晰报错
- `tests/test_workflow_service.py`：主流程串联与异常包装
- `tests/test_basic_workflow_integration.py`：基础调用顺序 smoke 验证
- `tests/test_app.py`、`tests/test_app_cli.py`：CLI 主入口、打印、保存、失败提示
- `tests/test_llm_client.py`：LLM 客户端请求和空响应保护
- `tests/test_prompt_loader.py`：prompt 文件读取与缺失报错

### 仍未真正覆盖的部分

- 真实 OpenAI/兼容接口联调
- 真实 prompt 与真实模型输出的兼容性
- 从第 1 章推进到第 N 章的连续性
- 保存后再加载并继续创作
- 长文本、异常网络、超时、限流等运行时问题

这意味着：当前测试足以证明“代码设计上的最小链路成立”，不足以证明“真实生产环境中整条创作流程稳定可用”。

## 最值得优先补的 5 个问题

### 1. 缺少多章节编排层

相关文件：`core/workflow_service.py`、`app.py`

优先级最高的原因：这是“单章工具”与“小说 agent”的核心分水岭。没有章节循环、章节状态和继续写机制，就无法证明从总纲到正文是“整书级链路”。

### 2. 缺少章节间上下文传递

相关文件：`core/workflow_service.py:42-46`

`previous_summary` 目前固定为空，导致章纲生成没有承接上一章结果。这会直接削弱剧情连续性，是主流程最明确的弱连接。

### 3. 总纲到正文的信息传递过弱

相关文件：`core/workflow_service.py:50-53`、`core/workflow_service.py:101-105`、`core/draft_service.py:13-24`

当前正文生成几乎只吃 `chapter_plan + protagonist + style`。这不足以让正文稳定继承主题、冲突、卷纲和更完整角色设定。

### 4. CLI 可演示性不足，尤其是中文输出乱码

相关文件：`app.py`、`tests/test_app_cli.py`

这不是“锦上添花”的问题，而是直接影响验收现场观感和输入输出可读性的问题。即使底层流程成立，CLI 演示效果也会打折。

### 5. 缺少真实联调验收

相关文件：`config.py`、`core/llm_client.py`

当前 `LLMClient` 与配置层已经接到真实 OpenAI 兼容接口，但现有测试全部依赖 mock。下一步最值得补的是一条可控的真实联调验收路径，否则“代码完整”与“真实可用”之间仍有空档。

## 最终验收判断

### 可以确认的

- 代码里确实存在一条最小主流程：总纲 -> 章纲 -> 正文 -> 可选润色 -> 可选保存。
- 这条链路已经通过测试验证，至少在 mock 条件下是完整可调用的。
- 当前 CLI 可以作为“单章生成”MVP 的演示入口。

### 不能夸大的

- 不能说项目已经具备“整书级小说 agent”能力。
- 不能说真实 LLM 环境下已经完成端到端联调。
- 不能说总纲对后续正文有足够强的约束和承接。

### 综合判断

当前项目更准确的定位是：

“一个已经具备最小单章主流程的小说生成原型，主链路在代码层面成立，适合做 MVP 演示；但距离稳定的整书写作 agent 还差章节编排、上下文延续和真实联调验收。”
