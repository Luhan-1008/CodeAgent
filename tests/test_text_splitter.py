# tests/test_text_splitter.py
import importlib.util
import pathlib

# 动态加载 code_agent/rag/text_splitter.py，避免触发 package 级初始化
module_path = pathlib.Path(__file__).resolve().parent.parent / 'code_agent' / 'rag' / 'text_splitter.py'
spec = importlib.util.spec_from_file_location('code_agent.rag.text_splitter', str(module_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
split_text = mod.split_text


def test_split_basic():
    # 500 字符左右，chunk_size=200 overlap=50 应分成至少 3 片
    text = "0123456789" * 50  # 500 chars
    chunks = split_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 3

    # 验证 overlap 区域文本一致性（至少前两片）
    if len(chunks) >= 2:
        first = chunks[0]
        second = chunks[1]
        overlap_len = 50
        assert first["text"][-overlap_len:] == second["text"][:overlap_len]


def test_split_edge_cases():
    # 空文本返回空列表
    assert split_text("", chunk_size=100) == []
    # chunk_size <= 0 抛错
    import pytest
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=0)
    # overlap >= chunk_size 抛错
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=10, overlap=10)
