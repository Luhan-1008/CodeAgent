# DeepCodeResearch 架构速览（草案）

本文把现有代码与赛题打分点对齐，并指出扩展位。偏工程落地，便于后续补全。

## 系统分层
- **Workflow 层**（`code_agent/workflow`）：`ChainWorkflow` / `DagWorkflow` 组织任务图；节点是 Agent。可串研究→设计→代码生成→构建/测试→修复的全链路。
- **Agent 层**（`code_agent/agent`）：`LLMAgent`（规划、工具、记忆、RAG、回调）与 `CodeAgent`（执行钩子）；`AgentLoader` 支持本地/远程配置、`trust_remote_code` 插件加载。
- **工具 & MCP**（`code_agent/tools`）：`ToolManager` 汇聚 MCP 服务 + 内置工具（代码执行、文件系统、拆任务、金融数据），有并发/超时控制；`MCPClient` 支持 streamable_http/SSE/WebSocket/stdio 传输。
- **记忆**（`code_agent/memory`）：可插拔，含 `mem0`，支持会话/程序性记忆，配置时可启用 LLM 总结。
- **RAG / 多模态**（`code_agent/rag`, `workflow/deep_research`）：抽取、文本切分、docling/OCR 适配；`ResearchWorkflow`/`ResearchWorkflowBeta` 提供深度研究（搜索重写、关键信息抽取、报告）。
- **回调 Hooks**（`code_agent/callbacks`）：生命周期钩子 `on_task_begin/end`、`on_generate_response`、`on_tool_call`、`after_tool_call`，便于日志/监控/自定义逻辑。
- **技能/任务**（`code_agent/skill`, `stage`, `task`）：兼容 Anthropic-Agent-Skills，支持技能/任务定义复用。
- **执行**（`code_agent/execution`）：执行器/runner 框架（含多模态脚手架）。

## 预期端到端数据流（对应赛题）
1) **输入**：用户目标 + 可选文档/URL（多模态 RAG 入口）。
2) **深度研究**：搜索重写 → web search（MCP 工具）→ 文档获取 → 抽取（`extraction_manager`, `text_splitter`）→ 关键信息+引用。
3) **设计**：生成 PRD/模块设计，形成结构化 TODO/计划（可用 `split_task` 工具或设计 Agent）。
4) **代码生成**：按文件组执行代码生成 Agent；需要时用代码执行工具即时校验。
5) **构建与测试**：编译/测试阶段，收集错误。
6) **自我修复**：错误轨迹 → bug-shooting 提示 → 补丁 → 复测，循环直至通过或达预算上限。
7) **汇报/交付**：总结改动、测试、性能要点；存入记忆供后续轮次使用。

## 可扩展点
- **工具**：配置里注册 MCP server；通过 `tools.ms_plugins` 加插件工具（需 `trust_remote_code`）。
- **记忆**：配置切换/叠加记忆后端；可指定 user_id；可替换总结模型。
- **RAG**：可调切分参数，启用 docling/OCR；经由 `rag_mapping` 插拔新抽取器。
- **Workflow**：分支用 `DagWorkflow`；每节点指向一个 agent 配置目录。
- **回调**：自定义 callback 做观测/风控。
- **LLM 后端**：`llm` 配置支持 ModelScope/OpenAI/DeepSeek/Claude 等。

## 与赛题打分点的已具备项
- Planner/Executor/Memory/Tools/RAG 的模块化分层已在代码中落地。
- 基于 MCP 的通用工具调用，支持多传输。
- 深度研究流程（含 beta）已有：搜索→抽取→报告，且有 Gradio 文档研究入口。
- 长短期记忆（含 mem0）已支持。
- 生命周期 Hooks 已有。

## 需要补齐的关键缺口
- 落地一份可运行的 **DagWorkflow 配置**：串起 search → deep research → design → codegen → build/test → self-fix → report，并给出可执行命令。
- 提供 **ModelScope MCP 工具预设**（fetch/search/code-run 等）与环境变量指引。
- 增加 **自动构建/测试 + 错误驱动重试** 的节点，实现自愈一轮。
- 补充 **docling/OCR 示例与测试**，并说明长上下文策略。
- 增加 **E2E + 单元测试** 覆盖 workflow/tool/memory/skills，提供最小 CI。
- 在 README 标注 **性能/并发/超时** 旋钮，并给一个轻量基准脚本。
- 在代码生成/审阅阶段增加 **人类在环触点**（CLI/Gradio 确认/审阅）。

## 快速开始草图（待补充实参路径）
- 定义 `projects/deep_code_research/config.yaml`，使用 `DagWorkflow`，节点示例：
  - `research`：`LLMAgent` 调用 MCP 搜索 + `ResearchWorkflowBeta` 逻辑。
  - `design`：生成 PRD/模块方案。
  - `codegen`：按文件组生成代码；可调 `code_executor` 工具。
  - `build_test`：调用构建/pytest 工具。
  - `fix`：读取错误，生成补丁，再次分发。
  - `report`：汇总输出/测试结果。
- 运行示例：
  - `PYTHONPATH=. python code_agent/cli/cli.py run --config projects/deep_code_research --query "<目标>" --trust_remote_code true`

## 运行指南（DeepCodeResearch 工作流）

### 依赖与环境
- Python ≥ 3.10；确保网络可访问 ModelScope 推理。
- 环境变量：`MODELSCOPE_API_KEY`（必填），可在 modelscope.cn 获取。
- MCP：示例文件 `projects/deep_code_research/mcp_servers.example.json`，请将其中的 `<your_mcp_uuid>` 替换为你的 MCP 服务 UUID；如有自建工具，可按同格式添加。
- 如启用 `code_executor`，需本机具备 Docker/ms-enclave 运行环境。

### 启动命令（最小示例）
```bash
PYTHONPATH=. MODELSCOPE_API_KEY=xxx \
python code_agent/cli/cli.py run \
  --config projects/deep_code_research \
  --query "请基于附件完成XXX系统的设计与代码生成" \
  --mcp_server_file projects/deep_code_research/mcp_servers.example.json \
  --trust_remote_code true
```

### 参数说明
- `--config`：工作流目录（内含 workflow.yaml 与 agents/*）。
- `--query`：任务描述，可包含文档/URL 指示。
- `--mcp_server_file`：MCP servers 配置；若有额外工具，放入同一 JSON。
- `--trust_remote_code`：使用外部/插件代码时需置 `true`。
- `--load_cache true`：可复用上轮历史，失败重试时使用。

### 常见问题
- 401/鉴权失败：检查 `MODELSCOPE_API_KEY` 是否导出、MCP UUID 是否替换正确。
- MCP 超时：调大 `mcp_servers.example.json` 中 `timeout/sse_read_timeout`，或检查网络。
- 代码执行工具不可用：确认 Docker/ms-enclave 已安装且当前用户有权限，或暂时移除 `code_executor` 配置。
- 输出位置：默认在 `output/<tag>`（见 `DEFAULT_OUTPUT_DIR`），历史与日志会写入其中。

## 自我反思与错误修复（Self-Healing）

### 快速验证
可通过单元测试验证工作流加载正确：
```bash
PYTHONPATH=. python -m pytest tests/test_deep_code_research_workflow.py -v
```

测试覆盖：
- DagWorkflow 配置加载
- 工作流链拓扑排序
- MCP servers 配置有效性
- 所有 agent 节点配置存在

### 自愈示例
参考脚本 `projects/deep_code_research/self_healing_example.py` 展示了自动构建/测试与错误驱动修复的完整链路：

```bash
cd projects/deep_code_research
python self_healing_example.py
```

**流程**：
1. 代码生成阶段产生初始代码
2. 自动运行 `pytest` + 语法检查
3. 解析错误日志，提炼根因
4. 生成修复提示（包含错误类型、上下文、代码片段）
5. 修复 Agent 基于提示生成补丁，循环直至通过或达预算上限

**核心模块**：
- `BuildTestResult`：结果封装
- `run_build_and_test()`：执行构建/测试
- `parse_pytest_errors()`：错误解析
- `generate_fix_prompt()`：修复提示生成

可在实际工作流中的 `build_test` 或 `fix` 节点集成类似逻辑。

## 多模态 RAG 与文档处理

### 长文档切分策略
文本切分是 RAG 的关键，见 `code_agent/rag/text_splitter.py`：

```python
from code_agent.rag.text_splitter import split_text

# 基础使用：500 字符文本，200 字符块，50 字符重叠
chunks = split_text(text, chunk_size=200, overlap=50)
# 返回 [{'id': 0, 'text': '...', 'start': 0, 'end': 200}, ...]
```

**参数调优**：
- `chunk_size` 越小，粒度越细，搜索精准度高但块数多。  
- `overlap` 跨度：建议 10-20% 的 `chunk_size`，保持上下文连贯。  
- 典型：文档检索 `1000/200`；代码分析 `500/100`；短文本摘要 `2000/300`。

### 多模态抽取与 Docling 集成
`code_agent/rag/extraction_manager.py` 支持多格式文档（PDF/DOCX/PPT/TXT），自动识别：
- **文本段落**与标题
- **表格**：保留结构与标题引用
- **图表**：OCR 提取标题、描述与链接

示例验证：
```bash
PYTHONPATH=. python -m pytest tests/test_multimodal_rag.py -v
```

测试覆盖：
- 文本切分一致性（overlap 验证）
- 多格式抽取（表格/图像识别）
- 长文档处理策略（粗粒度 vs 细粒度）

### 性能参数
参考 `docs/PERFORMANCE_TUNING.md`，并发 extraction 受限单机（建议 `max_concurrent_extractions: 1`），Ray 加速见环境变量 `RAG_EXTRACT_USE_RAY`。

## 人类在环（Human-in-the-loop）

### 交互触点示例
- **设计评审**：在 `design` 节点生成 PRD/架构后，提示用户确认或补充需求，再进入 codegen。
- **变更确认**：在 `codegen` 节点输出 patch/文件列表后，询问是否应用；用户可选择跳过/修改文件。
- **测试结果决策**：在 `build_test` 节点失败时，询问是否继续自动修复或手动介入。

### 如何启用
- 在 agent 配置中启用 `input_callback`（已默认），即可在需要时等待用户输入。
- 在自定义 prompt 中明确“若不确定或需要确认，请暂停并询问”。
- CLI 模式下，模型输出询问后直接在终端输入；Gradio 场景可复用 `doc_research` 的交互框架。

### 最小示例（设计阶段确认）
在 `projects/deep_code_research/agents/design/agent.yaml` 的 prompt 中添加指引：
```
  system: |
    ...
    如果需求存在不确定性，请列出待确认问题并询问用户，获得确认后再输出最终 PRD/架构。
```

### 最佳实践
- 把人类输入视作高置信度信号：记录到记忆/上下文，避免重复询问。
- 限制交互频次：关键决策点（设计确认、变更确认、修复放行）才询问，减少打断。
- 输出明确选项：如“输入 1 应用全部变更 / 2 仅应用安全变更 / 3 放弃本次补丁”。
