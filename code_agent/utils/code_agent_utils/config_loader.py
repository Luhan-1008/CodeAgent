"""
Utility functions for loading configuration files and substituting environment variables.
"""

import os
import re
import yaml
from typing import Dict, Any
from dotenv import load_dotenv


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load a YAML configuration file and substitute environment variables.

    Args:
        path (str): Path to the YAML config file. Defaults to "config.yaml" at project root.

    Returns:
        dict: The loaded configuration with environment variables substituted.
    """
    load_dotenv()

    if not os.path.isabs(path):
        cwd = os.getcwd()
        path = os.path.join(cwd, path)

    if not os.path.isfile(path):
        print(f"Config file not found")
        return {}

    # Load the YAML file
    with open(path, "r") as file:
        config = yaml.safe_load(file)

    # Substitute environment variables
    config = _substitute_env_vars(config)

    return config


def _substitute_env_vars(obj: Any) -> Any:
    """
    Recursively substitute environment variables in strings within an object.

    Args:
        obj: The object to process (can be a dict, list, or scalar value)

    Returns:
        The processed object with environment variables substituted
    """
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Pattern matches ${VAR_NAME}
        pattern = r"\$\{([^}]+)\}"

        def replace_env_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return re.sub(pattern, replace_env_var, obj)
    else:
        return obj


def extract_agent_llm_config(agent_name: str, config: dict) -> dict:
    """
    Extract LLM configuration for a specific agent from the config file.

    Args:
        agent_name (str): Name of the agent
        config (dict): Configuration dictionary

    Returns:
        Dictionary containing the LLM configuration for the agent
    """
    config = config or {}

    default_config = config.get("default") or {}
    default_llm_config = default_config.get("llm") or {}
    defalt_base_url = default_llm_config.get("api_base_url")
    default_model = default_llm_config.get("model")

    workflow_config = config.get("workflow") or {}
    agent_config = workflow_config.get(agent_name) or {}
    agent_base_url = agent_config.get("api_base_url") or defalt_base_url
    agent_api_key = agent_config.get("api_key") or None
    agent_model = agent_config.get("model") or default_model

    return {
        "llm_api_key": agent_api_key,
        "llm_base_url": agent_base_url,
        "model": agent_model,
    }
