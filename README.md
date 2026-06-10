# CodeAgent: 自主探索的复杂代码生成智能体

<p align="center">
    <br>
    <img src="docs/zh/_static/images/logo.png" width="300"/>
    <br>
<p>

<p align="center">
<img src="https://img.shields.io/badge/python-%E2%89%A53.10-5be.svg">
<a href="https://github.com/modelscope/ms-agent/blob/main/LICENSE"><img src="https://img.shields.io/github/license/modelscope/ms-agent"></a>
<a href="https://github.com/modelscope/ms-agent/pulls"><img src="https://img.shields.io/badge/PR-welcome-55EB99.svg"></a>
<a href="https://pypi.org/project/ms-agent/"><img src="https://badge.fury.io/py/ms-agent.svg"></a>
</p>

## 简介
CodeAgent是一个可以进行自主探索的复杂代码生成的智能体，能够利用自主探索的能力生成高质量的仓库级代码。它使用灵活且可扩展的架构，并能够通过多模态需求分析、自主探索、代码编写、测试、审查修复等流程实现软件开发的全流程，并实现了基于MCP（模型调用协议）的通用工具调用。

### 特性

- **通用多智能体**：基于MCP的工具调用能力与智能体聊天。
- **深度研究**：启用自主探索和复杂任务执行的高级能力。
- **代码生成**：支持带有工件的代码生成任务。
- **Agent Skills**：兼容Anthropic-Agent-Skills协议，实现智能体技能模块。
- **流程闭环可保障**：通过测试与审查形成代码生成的闭环，并保证代码质量。

## 快速开始

### Agent 对话
该项目支持通过 MCP（模型上下文协议）与模型进行交互。以下是一个完整的示例，展示了如何配置和运行支持 MCP 的 LLMAgent。

✅ 使用 MCP 协议与 agent 对话：[MCP Playground](https://modelscope.cn/mcp/playground)

默认情况下，agent 使用 ModelScope 的 API 推理服务。在运行 agent 之前，请确保设置您的 ModelScope API 密钥。
```bash
export MODELSCOPE_API_KEY={your_modelscope_api_key}
```
您可以在 https://modelscope.cn/my/myaccesstoken 找到或生成您的 API 密钥。

```python
import asyncio

from code_agent import LLMAgent

# Configure MCP servers
mcp = {
  "mcpServers": {
    "fetch": {
      "type": "streamable_http",
      "url": "https://mcp.api-inference.modelscope.net/{your_mcp_uuid}/mcp"
    }
  }
}


async def main():
  # Use json to configure MCP
  llm_agent = LLMAgent(mcp_config=mcp)  # Run task
  await llm_agent.run('Introduce modelscope.cn')


if __name__ == '__main__':
  # Start
  asyncio.run(main())
```
----
💡 提示：您可以在 modelscope.cn/mcp 找到可用的 MCP 服务器配置。

例如：https://modelscope.cn/mcp/servers/@modelcontextprotocol/fetch。
将 `mcp["mcpServers"]["fetch"]` 中的 url 替换为您自己的 MCP 服务器端点。

<details><summary>记忆</summary>

我们通过使用 [mem0](https://github.com/mem0ai/mem0) 支持记忆功能！🎉

下面是一个简单的入门示例。

在运行智能体之前，请确保您已经为 LLM 设置了 ModelScope API 密钥。

**使用示例**

此示例演示了智能体如何使用持久记忆在会话间记住用户偏好：

```python
import uuid
import asyncio
from omegaconf import OmegaConf
from code_agent.agent.loader import AgentLoader


async def main():
  random_id = str(uuid.uuid4())
  default_memory = OmegaConf.create({
    'memory': [{
      'path': f'output/{random_id}',
      'user_id': 'awesome_me'
    }]
  })
  agent1 = AgentLoader.build(config_dir_or_id='CodeAgent/simple_agent', config=default_memory)
  agent1.config.callbacks.remove('input_callback')  # Disable interactive input for direct output

  await agent1.run('I am a vegetarian and I drink coffee every morning.')
  del agent1
  print('========== Data preparation completed, starting test ===========')
  agent2 = AgentLoader.build(config_dir_or_id='CodeAgent/simple_agent', config=default_memory)
  agent2.config.callbacks.remove('input_callback')  # Disable interactive input for direct output

  res = await agent2.run('Please help me plan tomorrow’s three meals.')
  print(res)
  assert 'vegan' in res[-1].content.lower() and 'coffee' in res[-1].content.lower()


asyncio.run(main())
```

</details>


### Agent Skills

** CodeAgent Skills** 模块是对 [**Anthropic-Agent-Skills**](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) 协议的实现，允许开发者轻松创建、管理和使用智能体技能，提升智能体在复杂任务上的表现。


#### 核心特性

- 📜 **标准技能协议**：完全兼容 [Anthropic Skills](https://github.com/anthropics/skills) 协议
- 🧠 **启发式上下文加载**：仅在需要时加载必要的上下文，如`References`、`Resources`和`Scripts`等
- 🤖 **自主执行**：智能体根据技能定义，自主分析、规划和决策执行哪些脚本和资源
- 🔍 **技能管理**：支持技能批量加载，可根据用户输入自动检索和发现相关技能
- 🛡️ **代码执行环境**：可选代码本地直接执行，或使用沙箱环境（[**ms-enclave**](https://github.com/modelscope/ms-enclave)），自动处理依赖项安装和环境隔离
- 📁 **多文件类型支持**：支持文档、脚本和资源文件
- 🧩 **可扩展设计**：对「技能」的数据结构进行了模块化设计，提供 `SkillSchema`、`SkillContext`等实现，便于扩展和定制


### Agentic Insight

#### - 轻量级、高效且可扩展的多模态深度研究模块

该项目提供了一个**深度研究**模块，使智能体能够自主探索和执行复杂任务。

#### 🌟 特性

- **自主探索** - 针对各种复杂任务的自主探索

- **多模态** - 能够处理多样化的数据模态，生成包含丰富文本和图像的研究报告。

- **轻量级与高效** - 支持"搜索后执行"模式，在几分钟内完成复杂的研究任务，显著减少token消耗。


### 文档研究

该项目提供了**文档研究**模块，使智能体能够自主探索和执行与文档分析和研究相关的复杂任务。

#### 特性

  - 🔍 **深度文档研究** - 支持文档的深度分析和总结
  - 📝 **多种输入类型** - 支持多文件上传和URL输入
  - 📊 **多模态报告** - 支持Markdown格式的文本和图像报告
  - 🚀 **高效率** - 利用强大的LLM进行快速准确的研究，利用关键信息提取技术进一步优化token使用

### Code Scratch

该项目提供了一个 **Code Scratch** 模块，使智能体能够自主生成代码项目。

#### 特性

  - 🎯 **复杂代码生成** - 支持复杂代码生成任务
  - 🔧 **可定制工作流** - 使用户能够自由开发针对特定场景的代码生成工作流
  - 🏗️ **多阶段架构** - 需求分析、自主探索、设计与编码阶段，然后是完善阶段，用于稳健的代码生成和错误修复
  - 📁 **智能文件分组** - 自动分组相关代码文件，以最小化依赖关系并减少错误

#### 演示

**AI 工作空间主页**

使用以下命令生成完整的 AI 工作空间主页：

```shell
PYTHONPATH=. openai_api_key=your-api-key openai_base_url=your-api-url python code_agent/cli/cli.py run --config projects/code_scratch --query 'Build a comprehensive AI workspace homepage' --trust_remote_code true
```

生成的代码将输出到当前目录的 `output` 文件夹中。

**架构工作流：**
- **设计阶段**：分析需求 → 自主探索-> 生成 PRD 和模块设计 → 创建实现任务
- **编码阶段**：在智能文件组中执行编码任务 → 生成完整的代码结构
- **完善阶段**：自动编译 → 错误分析 → 迭代错误修复 → 人工评估循环


## 未来计划

不断改进和扩展 CodeAgent 能力与支持模块，提升大模型和智能体的能力边界。未来的计划包括：

- [ ] 多模态检索增强生成 **Multimodal Agentic Search** - 支持大规模多模态文档检索和图文检索结果生成。
- [ ] 增强的 **Agent Skills** - 提供更多预定义的技能和工具，提升智能体技能边界，并支持多技能协作，完成复杂任务执行。
- [ ] 更大规模的代码生成，能够实现更加工程化的复杂代码，并进一步提高生成代码的速度与质量。


## 许可证
该项目基于 [Apache License (Version 2.0)](https://github.com/modelscope/modelscope/blob/master/LICENSE) 许可证。
