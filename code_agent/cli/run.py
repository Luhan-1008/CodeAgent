# Copyright (c) Alibaba, Inc. and its affiliates.
import argparse
import asyncio
import os

from code_agent.config import Config
from code_agent.utils import strtobool
from code_agent.utils.constants import (AGENT_CONFIG_FILE, DEFAULT_YAML,
                                        WORKFLOW_CONFIG_FILE)

from .base import CLICommand


def subparser_func(args):
    """Function which will be called for a specific sub parser."""
    return RunCMD(args)


class RunCMD(CLICommand):
    name = 'run'

    def __init__(self, args):
        self.args = args

    @staticmethod
    def define_args(parsers: argparse.ArgumentParser):
        """Define args for run command."""
        parser: argparse.ArgumentParser = parsers.add_parser(RunCMD.name)
        parser.add_argument(
            '--query',
            required=False,
            type=str,
            help=(
                'The query or prompt to send to the LLM. '
                'If not set, will enter an interactive mode.'
            ))
        parser.add_argument(
            '--config',
            required=False,
            type=str,
            default=None,
            help=('The directory, local yaml file, or the repo id of the '
                  'config file. If omitted, CodeAgent will first look for '
                  '`agent.yaml` or `workflow.yaml` in the current directory, '
                  'then fall back to the built-in simple agent task.'))
        parser.add_argument(
            '--trust_remote_code',
            required=False,
            type=str,
            default='false',
            help='Trust the code belongs to the config file, default False')
        parser.add_argument(
            '--load_cache',
            required=False,
            type=str,
            default='false',
            help=(
                'Load previous step histories from cache, this is useful when '
                'a query fails and retry'))
        parser.add_argument(
            '--mcp_config',
            required=False,
            type=str,
            default=None,
            help='The extra mcp server config')
        parser.add_argument(
            '--mcp_server_file',
            required=False,
            type=str,
            default=None,
            help='An extra mcp server file.')
        parser.add_argument(
            '--openai_api_key',
            required=False,
            type=str,
            default=None,
            help='API key for accessing an OpenAI-compatible service.')
        parser.add_argument(
            '--modelscope_api_key',
            required=False,
            type=str,
            default=None,
            help='API key for accessing ModelScope api-inference services.')
        parser.add_argument(
            '--animation_mode',
            required=False,
            type=str,
            choices=['auto', 'human'],
            default=None,
            help=(
                'Animation mode for video_generate project: '
                'auto (default) or human.'))
        parser.set_defaults(func=subparser_func)

    def _resolve_default_config(self) -> str:
        """Return a reasonable default config path or repo id.

        Resolution order when ``--config`` is not provided:

        1. ``./agent.yaml`` in the current working directory.
        2. ``./workflow.yaml`` in the current working directory.
        3. Built-in simple agent task id defined by ``DEFAULT_YAML``
           (will be downloaded via ``modelscope.snapshot_download``).
        """
        current_dir = os.getcwd()

        # 这里体现了“本地优先”策略：优先使用你当前目录下的配置，便于项目内调试。
        for filename in (AGENT_CONFIG_FILE, WORKFLOW_CONFIG_FILE):
            candidate = os.path.join(current_dir, filename)
            if os.path.exists(candidate):
                return candidate

        # 本地没有配置时，回落到默认远程任务。
        return DEFAULT_YAML

    def execute(self):
        # 第一步：确定配置来源（本地路径或远程 repo id）。
        if not self.args.config:
            self.args.config = self._resolve_default_config()
        elif not os.path.exists(self.args.config):
            # 配置路径不存在时，按“远程任务 id”处理并下载。
            from modelscope import snapshot_download
            self.args.config = snapshot_download(self.args.config)

        # 第二步：把字符串布尔值统一转换，避免后续逻辑分支歧义。
        self.args.trust_remote_code = strtobool(
            self.args.trust_remote_code)  # noqa
        self.args.load_cache = strtobool(self.args.load_cache)

        # 通过环境变量把运行模式传给下游执行模块。
        if getattr(self.args, 'animation_mode', None):
            os.environ['MS_ANIMATION_MODE'] = self.args.animation_mode

        # 第三步：读取 YAML/任务配置，得到统一 Config 对象。
        config = Config.from_task(self.args.config)

        # 第四步：根据配置类型选择执行引擎（单 Agent 或 Workflow）。
        if Config.is_workflow(config):
            from code_agent.workflow.loader import WorkflowLoader
            engine = WorkflowLoader.build(
                config_dir_or_id=self.args.config,
                config=config,
                mcp_server_file=self.args.mcp_server_file,
                load_cache=self.args.load_cache,
                trust_remote_code=self.args.trust_remote_code)
        else:
            from code_agent.agent.loader import AgentLoader
            engine = AgentLoader.build(
                config_dir_or_id=self.args.config,
                config=config,
                mcp_server_file=self.args.mcp_server_file,
                load_cache=self.args.load_cache,
                trust_remote_code=self.args.trust_remote_code)

        # 第五步：进入异步运行主循环。
        # 你后续学习 asyncio 时，可以把这里当作“异步执行入口”。
        asyncio.run(engine.run(self.args.query))
