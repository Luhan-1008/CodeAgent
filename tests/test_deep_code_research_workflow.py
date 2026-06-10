# tests/test_deep_code_research_workflow.py
"""
最小 e2e 测试：验证 DeepCodeResearch DagWorkflow 能正常加载。
"""
import os
import pytest
from code_agent.config import Config
from code_agent.workflow.loader import WorkflowLoader


def test_deep_code_research_workflow_load():
    """Test that the DeepCodeResearch DagWorkflow config can be loaded without errors."""
    
    # Get the path to the deep_code_research project config
    config_dir = os.path.join(
        os.path.dirname(__file__),
        '../projects/deep_code_research'
    )
    
    assert os.path.exists(config_dir), f"Config directory not found: {config_dir}"
    
    # Load the workflow config
    config = Config.from_task(config_dir)
    
    # Verify it's a workflow (not an agent)
    assert Config.is_workflow(config), "deep_code_research should be a workflow"
    
    # Verify workflow type is DagWorkflow
    assert hasattr(config, 'type'), "Config should have a 'type' field"
    assert config.type.lower() == 'dagworkflow', f"Expected DagWorkflow, got {config.type}"
    
    # Verify all expected nodes exist
    expected_nodes = ['research', 'design', 'codegen', 'build_test', 'fix', 'report']
    for node in expected_nodes:
        assert hasattr(config, node), f"Missing node: {node}"
    
    # Verify node connections (simple sanity check)
    assert hasattr(config.research, 'agent_config'), "research node should have agent_config"
    assert hasattr(config.research, 'next'), "research node should have next"
    assert 'design' in config.research.next, "research should point to design"


def test_deep_code_research_workflow_builder():
    """Test that WorkflowLoader can instantiate the DagWorkflow."""
    
    config_dir = os.path.join(
        os.path.dirname(__file__),
        '../projects/deep_code_research'
    )
    
    # Load and build the workflow
    config = Config.from_task(config_dir)
    workflow = WorkflowLoader.build(
        config_dir_or_id=config_dir,
        config=config,
        trust_remote_code=False
    )
    
    # Verify workflow was built successfully
    assert workflow is not None, "Workflow should be instantiated"
    assert hasattr(workflow, 'workflow_chains'), "Workflow should have workflow_chains attribute"
    
    # Verify the workflow chain is in topological order
    expected_chain = ['research', 'design', 'codegen', 'build_test', 'fix', 'report']
    assert workflow.topo_order == expected_chain, \
        f"Expected chain {expected_chain}, got {workflow.topo_order}"


def test_deep_code_research_mcp_config():
    """Test that MCP servers example config exists and is valid JSON."""
    import json
    
    mcp_config_path = os.path.join(
        os.path.dirname(__file__),
        '../projects/deep_code_research/mcp_servers.example.json'
    )
    
    assert os.path.exists(mcp_config_path), f"MCP config not found: {mcp_config_path}"
    
    # Parse the JSON
    with open(mcp_config_path, 'r') as f:
        mcp_config = json.load(f)
    
    # Verify structure
    assert 'mcpServers' in mcp_config, "mcpServers key should exist"
    assert isinstance(mcp_config['mcpServers'], dict), "mcpServers should be a dict"
    
    # Verify example servers are present
    expected_servers = ['fetch', 'search', 'code_runner']
    for server in expected_servers:
        assert server in mcp_config['mcpServers'], f"Missing MCP server: {server}"


def test_agent_configs_exist():
    """Test that all agent configs for each node exist."""
    
    base_path = os.path.join(
        os.path.dirname(__file__),
        '../projects/deep_code_research/agents'
    )
    
    expected_agents = ['research', 'design', 'codegen', 'build_test', 'fix', 'report']
    
    for agent in expected_agents:
        agent_yaml = os.path.join(base_path, agent, 'agent.yaml')
        assert os.path.exists(agent_yaml), f"Agent config not found: {agent_yaml}"
        
        # Verify it can be parsed as a valid YAML
        from omegaconf import OmegaConf
        agent_config = OmegaConf.load(agent_yaml)
        assert agent_config is not None, f"Failed to load {agent}"
        assert hasattr(agent_config, 'type'), f"{agent} should have type field"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
