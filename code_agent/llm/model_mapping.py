# Copyright (c) Alibaba, Inc. and its affiliates.
from code_agent.llm.anthropic_llm import Anthropic
from code_agent.llm.modelscope_llm import ModelScope
from code_agent.llm.openai_llm import OpenAI

all_services_mapping = {
    'modelscope': ModelScope,
    'openai': OpenAI,
    'anthropic': Anthropic,
}
