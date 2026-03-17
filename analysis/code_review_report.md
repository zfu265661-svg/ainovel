# 小说 Agent 静态代码审查报告

## 审查范围

- `app.py`
- `core/`
- `tests/`

本次仅做静态分析，未修改任何现有 Python 代码，也未调整 `prompts/` 模板。

## 总体评价

项目整体结构清晰，已经按 `core` 服务层、CLI 入口、测试目录做了初步分层，基础的 JSON 存储、LLM 调用、工作流编排和若干领域服务也都有独立测试覆盖。  
但当前代码存在几类比较明显的问题：

1. CLI 与部分提示拼接文本出现编码异常，已经直接影响可读性与可用性。
2. 异常体系和命名体系没有收敛到同一套约定，导致错误边界不统一。
3. 一部分测试与当前实现已经脱节，存在“测试文件还在，但已不能真实保护实现”的风险。
4. 路径处理与 prompt 读取存在边界控制不足的问题。
5. 若干数据服务存在明显重复逻辑，可维护性一般。

整体判断：**可以作为原型继续演进，但在编码一致性、异常治理和测试可靠性上需要尽快收口。**

## 主要优点

- 模块职责大体明确。`outline/chapter/draft/checker/workflow/storage` 的边界比较容易理解。
- 大多数文件都提供了较清晰的 docstring，阅读成本不高。
- `core/storage.py` 对 JSON 与文本读写做了基础封装，减少了调用点散落的文件操作。
- `core/workflow_service.py` 通过 `_run_stage()` 统一包装阶段性错误，思路是对的。
- 多数服务已有对应测试文件，说明项目已经有“先验证再迭代”的意识。

## 主要问题

### 1. 编码异常已经影响 CLI 文案和一致性检查 Prompt

问题位置：

- `app.py:15`
- `app.py:16`
- `app.py:17`
- `app.py:24`
- `app.py:35`
- `app.py:36`
- `app.py:37`
- `app.py:47`
- `app.py:51`
- `app.py:61`
- `app.py:65`
- `core/checker_service.py:50`
- `core/checker_service.py:51`
- `core/checker_service.py:52`
- `core/checker_service.py:53`

说明：

- `app.py` 中的交互提示、成功提示、错误提示和章节标题都出现了明显乱码。
- `core/checker_service.py` 中拼接给模型的段落标签也出现乱码，意味着不仅是 CLI 显示问题，还可能影响模型对上下文结构的理解。
- 该问题已经超出“代码风格”范围，属于直接影响运行输出和提示质量的功能性问题。

影响：

- 终端交互体验差，用户难以判断输入含义。
- 一致性检查 prompt 的结构标签不可靠，可能降低模型输出稳定性。
- 测试里也出现同类乱码文本，进一步增加维护难度。

### 2. `tests/test_app.py` 与当前 `app.py` 实现脱节，测试保护已经失真

问题位置：

- `tests/test_app.py:34`
- `tests/test_app.py:40`
- `tests/test_app.py:44`
- `tests/test_app.py:45`
- `tests/test_app.py:61`
- `tests/test_app.py:64`
- `tests/test_app.py:65`
- `tests/test_app.py:87`
- `tests/test_app.py:90`
- `app.py:7`
- `app.py:60`

说明：

- 当前 `app.py` 依赖的是 `run_basic_workflow` 和 `save_workflow_result`。
- 但 `tests/test_app.py` 仍在 monkeypatch `app.generate_outline` 与 `app.save_json`，这些符号在当前 `app.py` 中并不存在。
- 这类测试即使保留在仓库里，也不能证明当前入口逻辑是正确的；更糟的是，它们大概率在执行时直接失败。

影响：

- 入口层回归保护失效。
- 测试命名与真实覆盖范围不一致，容易让后续修改者误判风险。

### 3. 异常体系分裂，`core/errors.py` 与各服务自定义异常并行存在，命名不一致

问题位置：

- `core/errors.py:6`
- `core/errors.py:10`
- `core/errors.py:14`
- `core/errors.py:18`
- `core/errors.py:22`
- `core/errors.py:26`
- `core/errors.py:30`
- `core/errors.py:34`
- `core/errors.py:38`
- `core/errors.py:42`
- `config.py:12`
- `core/llm_client.py:10`
- `core/outline_service.py:20`
- `core/chapter_service.py:18`
- `core/draft_service.py:9`
- `core/checker_service.py:13`
- `core/rewrite_service.py:8`
- `core/workflow_service.py:12`

说明：

- 项目已经定义了一套共享异常基类 `NovelAgentError` 及多个子类，但实际业务代码几乎没有接入。
- 各模块又分别定义了 `ConfigError`、`LLMClientError`、`OutlineServiceError`、`DraftServiceError` 等互不关联的异常。
- 这会导致上层无法通过统一父类做聚合处理，也让错误命名出现“有的叫 `XxxError`，有的叫 `XxxServiceError`，有的叫 `XxxParseError`”的并行风格。

影响：

- 错误边界不统一，调用方难以稳定捕获“项目内业务错误”。
- 审查和排障时，需要逐个模块记忆异常体系，增加维护成本。

### 4. `load_prompt()` 存在路径逃逸风险，Prompt 文件读取边界没有收紧

问题位置：

- `core/prompt_loader.py:9`
- `core/prompt_loader.py:11`
- `core/prompt_loader.py:12`

说明：

- `load_prompt(name)` 直接将入参拼到 `PROMPTS_DIR / name`。
- 代码没有限制 `name` 必须是纯文件名，也没有校验最终路径是否仍位于 `prompts/` 目录内。
- 如果上层未来把模板名暴露为外部输入，`../` 一类路径可直接越过 `prompts/` 目录。

影响：

- 存在读取非预期文件的隐患。
- 这类风险在 agent 项目里尤其需要提前收口，因为 prompt 名称往往会逐渐变成“配置项”或“运行参数”。

### 5. `rewrite_service` 绕过统一 Prompt 加载路径，造成路径处理和错误处理不一致

问题位置：

- `core/rewrite_service.py:12`
- `core/rewrite_service.py:20`
- `core/prompt_loader.py:9`

说明：

- `outline/chapter/draft/checker` 都通过 `load_prompt()` 读取模板。
- 只有 `rewrite_service` 直接使用 `PROMPT_PATH.read_text()`。
- 这会导致 prompt 加载策略分叉：一个模块走统一入口，一个模块自己拼路径、自己读文件、自己承担异常格式。

影响：

- 命名和实现模式不一致。
- 后续若统一做 prompt 目录切换、缓存、日志、异常包装，`rewrite_service` 会成为漏网点。

### 6. 角色/伏笔/时间线服务存在明显重复逻辑，可维护性偏低

问题位置：

- `core/character_service.py:24`
- `core/character_service.py:75`
- `core/foreshadow_service.py:31`
- `core/foreshadow_service.py:82`
- `core/timeline_service.py:24`
- `core/timeline_service.py:94`

说明：

- 三个服务都重复实现了：
  - 文件不存在时返回空列表
  - JSON 顶层必须为列表
  - 列表元素必须为字典
  - 必填字段校验
  - 空字符串判空
- 这些模式高度相似，但目前是复制式实现。

影响：

- 规则变更时容易出现“一个服务改了、另两个没改”的漂移。
- 新增类似服务时，复制粘贴概率很高，进一步放大维护成本。

### 7. `workflow_service` 对领域数据的传递过于简化，存在编排层与数据结构的隐式耦合

问题位置：

- `core/workflow_service.py:50`
- `core/workflow_service.py:52`
- `core/workflow_service.py:101`
- `core/workflow_service.py:102`
- `core/workflow_service.py:103`

说明：

- `generate_draft()` 需要 `character_info`，但工作流层只从 `outline["protagonist"]` 提取一个字典传下去。
- 这意味着草稿生成对“角色信息”的理解被硬编码为“只看主角字段”，而不是明确的数据契约。
- 一旦大纲结构调整，或后续需要多角色信息，问题会先在编排层暴露。

影响：

- 工作流层与 outline 数据结构耦合较深。
- 领域能力扩展时，编排层容易成为修改热点。

## 建议修复项

### 高优先级

1. 先修复 `app.py` 与 `core/checker_service.py` 的乱码文本，确保 CLI 与 prompt 标签恢复为可读中文。
2. 清理或重写 `tests/test_app.py`，使其对齐当前 `run_basic_workflow` / `save_workflow_result` 入口。
3. 给 `load_prompt()` 增加路径边界校验，禁止读取 `prompts/` 目录外文件。

### 中优先级

1. 决定异常体系只保留一套：
   - 要么统一继承 `NovelAgentError`
   - 要么删除 `core/errors.py`，避免“名义上的统一，实际上的分裂”
2. 让 `rewrite_service` 也走统一的 prompt 加载入口，减少路径与异常逻辑分叉。
3. 抽出通用的“列表型 JSON 仓储校验”辅助函数，减少 `character/foreshadow/timeline` 的重复实现。

### 低优先级

1. 重新定义 `workflow_service` 向 `generate_draft()` 传递的角色上下文契约，不要默认只取 `protagonist`。
2. 对重复度较高的测试做收敛，避免多个测试文件验证同一行为但断言风格不一致。

## 结论

这个项目已经具备继续迭代的骨架，但当前更像“能跑的初版”，还没有进入“可稳定演进”的状态。  
如果只做一轮最小治理，建议优先处理：

1. 文本编码异常
2. 失真的入口测试
3. Prompt 路径边界
4. 异常体系收口

以上四项处理完，项目的可维护性会明显提升。
