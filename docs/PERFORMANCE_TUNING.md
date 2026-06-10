# 性能与并发参数指南

## 核心参数表

| 模块 | 参数 | 默认值 | 说明 | 调优建议 |
|------|------|--------|------|---------|
| **ToolManager** | `MAX_CONCURRENT_TOOLS` | 20 | 并发工具调用数 | 受限于 LLM 上下文，通常 10-30；搜索密集可降至 5-10 |
| | `TOOL_CALL_TIMEOUT` | 30s | 单个工具调用超时 | MCP 搜索 60-120s；代码执行 180s；网络差则增加 |
| **LLMAgent** | `max_chat_round` | 20 | 最大对话轮数 | 代码生成建议 8-16；搜索建议 4-8；避免超 30 |
| | `stream` | false | 流式输出 | true 时响应渐进，适合 UI；false 降低延迟 |
| **ResearchWorkflow** | `max_concurrent_searches` | 2 | 并发搜索数 | 网络良好可增至 3-4；受搜索 API 限制 |
| | `max_concurrent_llm_calls` | 8 | 并发 LLM 调用数 | 受账户配额限制，通常 4-16 |
| | `max_concurrent_extractions` | 1 | 文档抽取并发数 | Ray 进程密集，单机通常保持 1；集群可增至 2-4 |
| **MCPClient** | `CONNECTION_TIMEOUT` | 120s | MCP 连接超时 | 云端推理 60-180s；本地 10-30s |
| | `DEFAULT_HTTP_TIMEOUT` | 5s | HTTP 基础超时 | 不建议改；用 server 级 timeout 调优 |
| | `DEFAULT_SSE_READ_TIMEOUT` | 300s | SSE 读取超时 | 长连接，适合流式响应；改为 60-120s 加快失败检测 |
| **Memory** | `max_tokens` | 2000 | 摘要最大 token 数 | 记忆更新频率与质量平衡 |
| **CodeExecutor** | `timeout` | 30s | 代码执行超时 | 测试轻 30s；构建改 180s；避免无限循环 |
| | `memory_limit` | 2g | 容器内存限制 | 大数据处理改 4-8g；小环境改 512m-1g |
| | `cpu_limit` | 2.0 | CPU 核心数 | 并行度，通常 1-4；高负载改 0.5-1.0 降低抢占 |

## 场景调优

### 场景 1：快速原型（响应优先）
```yaml
llm:
  generation_config:
    stream: true
    temperature: 0.2

max_chat_round: 4  # 快速决策

tools:
  mcp: true
  # 禁用低优先级工具

memory: null  # 关闭记忆

rag:
  enable: false  # 跳过 RAG
```

### 场景 2：深度研究（质量优先，时间充足）
```yaml
max_chat_round: 12  # 充分思考

research:
  max_concurrent_searches: 4
  max_concurrent_llm_calls: 12
  max_concurrent_extractions: 2

rag:
  name: llama_index_rag
  chunk_size: 1000
  overlap: 200
```

### 场景 3：代码生成与测试循环（稳定性优先）
```yaml
max_chat_round: 8

build_test:
  timeout: 180
  memory_limit: "4g"

fix:
  max_retries: 3  # 修复重试次数

tools:
  code_executor:
    timeout: 180
    memory_limit: "2g"
    cpu_limit: 2.0
```

## 性能基准（单机测试示例）

| 操作 | 输入规模 | 平均延迟 | 内存占用 | 网络 I/O |
|------|---------|----------|----------|----------|
| LLM 调用（Qwen3-235B） | 1k token | 2-5s | ~200MB | ~10KB 上行 |
| Web 搜索（MCP） | 1 查询 | 3-8s | ~50MB | ~500KB 下行 |
| 文档抽取（Docling，单页 PDF） | ~5MB | 2-10s | ~300MB | - |
| 文本切分（text_splitter，100KB） | chunk_size=1000 | <100ms | ~10MB | - |
| 代码执行（Python 脚本） | 简单 | 1-3s | ~200MB | - |
| 并发 5 搜索 + 8 LLM 调用 | - | ~15-30s | ~1GB | ~5MB 下行 |

## 故障恢复

### 超时处理
- MCP 超时 → 自动重试（默认 2 次），见 `@async_retry` 装饰器。
- LLM 超时 → 可调 `generation_config` 中的 `timeout` 参数（若支持）。
- 代码执行超时 → 杀进程，返回部分输出或错误信息。

### 内存压力
- 激活内存管理：配置 `memory.max_tokens` 裁剪历史。
- 启用 Mem0 LLM 总结：压缩长对话到关键要点。
- 降低并发数：减少同时运行的任务。

### 网络中断
- 断点续传：`--load_cache true` 复用上轮结果。
- 本地缓存：工具结果缓存在 `output/<tag>/` 下。
- MCP 重连：自动重试连接，可调 `CONNECTION_TIMEOUT`。

## 监测与日志

启用详细日志观测性能：
```bash
export PYTHONUNBUFFERED=1  # 实时输出
export MS_LOG_LEVEL=DEBUG  # 启用 debug 日志

PYTHONPATH=. python code_agent/cli/cli.py run ... 2>&1 | tee run.log
```

关键日志行：
- `[Tool Manager] Tool concurrency limit set to ...` → 并发数
- `[LLM] generate() call ...` → LLM 调用时间
- `[MCP] Connected to server ...` → MCP 连接状态
- `[Memory] Add memories ...` → 记忆更新频率

## 参考命令

### 快速干跑（无真实工具调用）
```bash
PYTHONPATH=. python code_agent/cli/cli.py run \
  --config projects/deep_code_research \
  --query "dry run" \
  --mcp_server_file /dev/null \
  --trust_remote_code true
```

### 本地并发基准（可选）
```bash
# tests/benchmark_concurrent_tools.py (需自行编写)
# 测试不同并发数下的吞吐量与延迟
```

## 常见问题

**Q: 如何避免 LLM 调用超时？**  
A: 增加 `generation_config.timeout`（如支持），或降低 `max_chat_round` 早期决策；可用 `stream: true` 获得更快反馈。

**Q: 并发数越多越快吗？**  
A: 否。超过系统容量会导致 CPU/内存争用、调度开销大幅增加。建议从默认开始，逐步调增观测实际吞吐。

**Q: 如何处理长研究任务的内存爆炸？**  
A: 启用 mem0 总结；降低 `max_concurrent_extractions`；定期落地中间结果到磁盘。

**Q: 代码执行工具需要的 Docker/Enclave 配置？**  
A: 参考 `code_agent/tools/code/code_executor.py` 与 `ms-enclave` 官方文档；简单情况下可禁用，改用本地 subprocess。
