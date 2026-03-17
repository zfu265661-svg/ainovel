# 测试补强规划

## 1. 当前测试现状

- 已阅读范围：`tests/` 全部现有测试、`core/` 全部业务模块、`app.py`
- 当前测试运行结果：`pytest -q` 为 `64 passed, 3 failed`
- 当前失败测试：
  - `tests/test_app.py` 仍然基于旧版 CLI 入口，假设 `app.py` 暴露 `generate_outline` 和 `save_json`
  - 现有 `app.py` 实际改为调用 `run_basic_workflow` 和 `save_workflow_result`
  - 这说明 `app.py` 相关测试里存在一组“过时但仍被计入覆盖”的样例，覆盖价值较低

## 2. 已覆盖内容

### 2.1 CLI / 工作流主路径

- `tests/test_app_cli.py`
  - 已覆盖 `app.main`
  - 已覆盖主流程成功输出
  - 已覆盖工作流抛错时返回 `1`
- `tests/test_basic_workflow_integration.py`
  - 已覆盖 `core.workflow_service.run_basic_workflow` 的主路径调用顺序
  - 已覆盖可选重写模块存在时的分支
- `tests/test_workflow_service.py`
  - 已覆盖 `run_basic_workflow` 的完整返回值
  - 已覆盖缺失可选重写模块时 `rewritten_draft is None`
  - 已覆盖 outline 阶段异常被包装为 `WorkflowServiceError`

### 2.2 LLM 驱动服务

- `core.outline_service.generate_outline`
  - 已覆盖 JSON 解析成功
  - 已覆盖非法 JSON
  - 已覆盖缺字段
- `core.chapter_service.generate_chapter_plan`
  - 已覆盖 JSON 解析成功
  - 已覆盖非法 JSON
  - 已覆盖缺字段
  - 已覆盖 `beats` 非列表
- `core.draft_service.generate_draft`
  - 已覆盖成功生成
  - 已覆盖空文本响应
  - 已覆盖 LLM 异常包装
- `core.checker_service.check_consistency`
  - 已覆盖成功解析
  - 已覆盖非法 JSON
  - 已覆盖缺字段
  - 已覆盖 `issues` 非列表
- `core.rewrite_service.rewrite_text`
  - 已覆盖成功生成
  - 已覆盖空输入
  - 已覆盖空响应
  - 已覆盖 LLM 异常包装
- `core.summarizer.summarize_previous_chapter`
  - 已覆盖成功生成
  - 已覆盖空输入
  - 已覆盖空响应
  - 已覆盖 LLM 异常包装
- `core.llm_client.LLMClient.generate_text`
  - 已覆盖字符串响应成功路径
  - 已覆盖 API 抛错包装
  - 已覆盖空白字符串响应

### 2.3 本地存储与数据管理

- `core.storage`
  - 已覆盖 JSON 保存/读取
  - 已覆盖文本保存/读取
  - 已覆盖缺文件报错
  - 已覆盖非法 JSON 报错
- `core.export_service.export_chapter_text`
  - 已覆盖默认路径导出
  - 已覆盖自定义路径导出
  - 已覆盖空文本报错
- `core.character_service`
  - 已覆盖保存/读取
  - 已覆盖按名查询成功
  - 已覆盖缺字段
  - 已覆盖重名冲突
- `core.timeline_service`
  - 已覆盖保存/读取
  - 已覆盖按章节过滤
  - 已覆盖缺字段
  - 已覆盖新增重复 `id`
- `core.foreshadow_service`
  - 已覆盖新增并读取
  - 已覆盖标记已回收
  - 已覆盖缺字段
  - 已覆盖找不到 `id`

## 3. 薄弱测试点

### 3.1 最高风险薄弱点

- `app.py` 的辅助函数几乎未被直接覆盖
  - `prompt_user`
  - `render_section`
  - `render_workflow_result`
  - `persist_result`
- `core.workflow_service` 只测到了 outline 阶段的异常包装，其他关键分支没测
  - `save_workflow_result`
  - `_build_character_info`
  - `_load_optional_module`
  - chapter/draft/rewrite 各阶段异常包装
- `core.llm_client._extract_text` 的复杂分支未覆盖
  - `message.content` 为列表
  - 列表元素为 `dict`
  - 列表元素为对象
  - `choices` 缺失 / 空列表
  - `message` 缺失

### 3.2 中等风险薄弱点

- `core.checker_service._validate_result` 只测了 `issues` 非列表，未测：
  - `has_issue` 非布尔
  - `suggestions` 非列表
  - 顶层 JSON 不是对象
- `core.outline_service` / `core.chapter_service`
  - 未测顶层 JSON 为数组或字符串时的报错
- `core.storage.load_json`
  - 未测“JSON 合法但顶层不是对象/数组”，例如 `123`、`"abc"`
- `core.rewrite_service`
  - 未测提示词文件读取失败
  - 未测模板里不存在 `{text}` 占位符时是否仍按当前实现返回结果
- `core.export_service`
  - 未测目标目录不存在时的自动创建行为

### 3.3 低到中风险薄弱点

- `core.character_service`
  - 未测数据文件不是列表
  - 未测列表中存在非字典项
  - 未测新增角色时 `name` 或 `role` 为纯空白
  - 未测传入非字典对象
- `core.timeline_service`
  - 未测 `save_timeline` 对整表重复 `id` 的校验
  - 未测数据文件不是列表 / 列表项不是字典
  - 未测 `chapter_no` 为 `0`、负数、字符串时当前行为
- `core.foreshadow_service`
  - 未测数据文件不是列表 / 列表项不是字典
  - 未测 `status` 为空白时会被自动补成 `open`
  - 未测传入非字典对象
  - 未测重复 `id` 是否允许；当前实现允许，但缺少一个“显式锁定当前行为”的测试
- `core.summarizer`
  - 未测返回文本会被 `.strip()` 清理
  - 未测 `max_words` 为 `0`、负数时当前行为

## 4. 建议新增测试案例

| 优先级 | 模块/函数 | 建议测试案例 | 关注点 |
| --- | --- | --- | --- |
| P0 | `app.persist_result` | `save_workflow_result` 返回 `False` 时不打印“保存成功” | 锁定“可选存储模块缺失时静默跳过”的 CLI 行为 |
| P0 | `app.persist_result` | `save_workflow_result` 抛异常时打印失败信息但不再抛出 | 避免保存失败导致 CLI 成功路径被误判为失败 |
| P0 | `app.render_section` | `data is None`、`data is str`、`data is dict` 三种输入分别断言渲染结果 | 当前终端输出核心逻辑未被单测 |
| P0 | `core.workflow_service.save_workflow_result` | `_load_optional_module` 返回 `None` 时返回 `False` | 当前仅通过 `app.main` 间接覆盖，不足以定位失败原因 |
| P0 | `core.workflow_service.save_workflow_result` | `core.storage.save_json` 抛错时包装成 `WorkflowServiceError`，消息包含路径 | 这是文件落盘的关键异常分支 |
| P0 | `core.workflow_service.run_basic_workflow` | `generate_chapter_plan` 抛异常时，断言错误消息为 `Failed during chapter plan generation: ...` | 目前只覆盖 outline 阶段 |
| P0 | `core.workflow_service.run_basic_workflow` | `generate_draft` 抛异常时，断言错误消息为 `Failed during draft generation: ...` | 目前未测 |
| P0 | `core.workflow_service.run_basic_workflow` | `rewrite_text` 抛异常时，断言错误消息为 `Failed during draft rewrite: ...` | 可选模块路径最容易回归 |
| P1 | `core.workflow_service._build_character_info` | `outline["protagonist"]` 缺失、为字符串、为列表时都返回 `{}` | 锁定当前容错策略，避免后续 prompt 拼接收到脏结构 |
| P1 | `core.workflow_service._load_optional_module` | `ModuleNotFoundError.name == module_name` 返回 `None`；`name != module_name` 时继续抛出 | 这是“模块不存在”和“模块内部导入失败”的分界 |
| P1 | `core.llm_client._extract_text` | `message.content` 为 `[{"text": "A"}, {"text": "B"}]` 时返回 `"A\\nB"` | 兼容 responses 风格内容片段 |
| P1 | `core.llm_client._extract_text` | `message.content` 为对象列表且对象有 `.text` 属性时成功提取 | 当前 SDK 结构变化时最可能用到 |
| P1 | `core.llm_client.generate_text` | `choices=[]`、`message=None`、`content=[]` 时统一抛 `did not include any text content` | 覆盖所有空 payload 分支 |
| P1 | `core.checker_service.check_consistency` | `has_issue` 为 `"yes"` 时抛 `field 'has_issue' must be a boolean` | 当前漏掉最关键的类型校验 |
| P1 | `core.checker_service.check_consistency` | `suggestions` 为字符串时抛 `field 'suggestions' must be a list` | 当前仅测 `issues` |
| P1 | `core.checker_service.check_consistency` | LLM 返回 `[]` 或 `"text"` 时抛“response must be a JSON object” | 锁定顶层结构校验 |
| P1 | `core.outline_service.generate_outline` | LLM 返回 `[]` 时抛 `Outline response must be a JSON object` | 目前只测非法 JSON，不测合法但结构错误 |
| P1 | `core.chapter_service.generate_chapter_plan` | LLM 返回 `[]` 时抛 `Chapter plan response must be a JSON object` | 同上 |
| P1 | `core.storage.load_json` | 文件内容为 `123` 或 `"abc"` 时抛 `JSON file must contain an object or array` | 当前数据层边界没锁住 |
| P2 | `core.character_service.load_characters` | 文件顶层为对象时抛 `Character data file must contain a JSON array` | 当前角色文件容错不足 |
| P2 | `core.character_service.load_characters` | 列表内混入字符串时抛 `Each character entry must be a JSON object` | 避免脏数据静默进入流程 |
| P2 | `core.character_service.add_character` | `{"name": "  ", "role": "mentor"}`、非字典对象分别触发校验异常 | 补齐 `_is_missing_required_value` 分支 |
| P2 | `core.timeline_service.save_timeline` | 传入两个相同 `id` 的事件时抛 `TimelineConflictError` | 目前只测逐条新增，不测整表保存 |
| P2 | `core.timeline_service.load_timeline` | 文件顶层不是列表、列表项不是字典时分别抛校验异常 | 数据文件损坏时需要清晰失败 |
| P2 | `core.foreshadow_service.load_foreshadows` | 文件顶层不是列表、列表项不是字典时分别抛校验异常 | 与 character/timeline 一致补齐 |
| P2 | `core.foreshadow_service.add_foreshadow` | `status=""` 或 `"   "` 时自动写入 `open` | 当前只有缺省状态主路径，没测空白归一化 |
| P2 | `core.foreshadow_service.add_foreshadow` | 传入非字典对象时抛 `Foreshadow item must be a dictionary` | 补齐输入类型防线 |
| P2 | `core.export_service.export_chapter_text` | 默认路径父目录不存在时自动创建并成功写入 | 这是导出功能的实际部署场景 |
| P2 | `core.rewrite_service.rewrite_text` | `PROMPT_PATH.read_text` 抛 `FileNotFoundError` 时当前异常直出 | 明确记录当前行为，方便后续决定是否统一包装 |
| P2 | `core.summarizer.summarize_previous_chapter` | 模型返回前后空白时最终结果已被 `strip()` | 锁定输出清理行为 |

## 5. 优先级排序

### 第一批：立即补

1. `app.persist_result` 与 `app.render_section`
2. `core.workflow_service.save_workflow_result`
3. `core.workflow_service` 的 chapter/draft/rewrite 异常包装
4. `core.llm_client._extract_text` 的列表内容分支
5. `core.checker_service` 的 `has_issue` / `suggestions` 类型校验

原因：
- 这些点位于 CLI 输出、核心流程编排和 LLM 响应解析的交界处，一旦回归，现有测试很难快速定位。

### 第二批：随后补

1. `core.outline_service` / `core.chapter_service` 顶层 JSON 结构错误
2. `core.storage.load_json` 顶层标量 JSON
3. `core.character_service` / `core.timeline_service` / `core.foreshadow_service` 的脏数据文件场景

原因：
- 这些用例属于“输入已合法 JSON 但业务结构错误”的真实故障模式，当前覆盖明显不足。

### 第三批：行为锁定类测试

1. `core.foreshadow_service` 空白 `status` 自动归一化
2. `core.export_service` 自动建目录
3. `core.summarizer` 输出 `strip`
4. `core.rewrite_service` 提示词文件读取失败时的当前行为

原因：
- 这些测试主要用于锁定当前实现，价值高于烟雾测试，但低于主流程异常保护。

## 6. 建议执行顺序

1. 先修订 `app.py` 相关测试策略
   - 保留 `tests/test_app_cli.py`
   - 替换或重写 `tests/test_app.py` 中基于旧接口的断言
2. 再补 `core.workflow_service` 和 `core.llm_client`
3. 最后补各数据服务的结构化边界测试

这样做的原因：
- 先处理入口层的失配测试，能避免后续覆盖统计被旧测试误导。
- 再补工作流编排与 LLM 解析，能最快提升对真实故障的拦截能力。
