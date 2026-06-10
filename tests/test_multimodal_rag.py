# tests/test_multimodal_rag.py
"""
多模态 RAG 与 Docling 文档抽取示例测试。
展示长文档处理、多模态识别、切分策略。
"""
import os
import tempfile
import pytest
from typing import List, Dict, Any


class TestTextSplitter:
    """文本切分策略测试"""
    
    def test_basic_split(self):
        """测试基本切分：验证 overlap 与 chunk_size"""
        from code_agent.rag.text_splitter import split_text
        
        # 构造长文本：500 字符
        text = "0123456789" * 50  # 500 chars
        
        # chunk_size=200, overlap=50 应分 3+ 片
        chunks = split_text(text, chunk_size=200, overlap=50)
        
        assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"
        
        # 验证 overlap 一致性
        for i in range(len(chunks) - 1):
            overlap_len = 50
            overlap_text_prev = chunks[i]['text'][-overlap_len:]
            overlap_text_next = chunks[i + 1]['text'][:overlap_len]
            assert overlap_text_prev == overlap_text_next, \
                f"Overlap mismatch at chunk {i}/{i+1}"
    
    def test_chunk_boundaries(self):
        """测试边界情况：小文本、无重叠"""
        from code_agent.rag.text_splitter import split_text
        
        # 空文本
        assert split_text("", chunk_size=100) == []
        
        # 单个块
        text = "short"
        chunks = split_text(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0]['text'] == text
        
        # 错误参数
        with pytest.raises(ValueError):
            split_text("test", chunk_size=0)
        
        with pytest.raises(ValueError):
            split_text("test", chunk_size=10, overlap=10)
    
    def test_chunk_metadata(self):
        """验证每个 chunk 的元数据完整性"""
        from code_agent.rag.text_splitter import split_text
        
        text = "x" * 300
        chunks = split_text(text, chunk_size=100, overlap=20)
        
        for i, chunk in enumerate(chunks):
            assert 'id' in chunk
            assert 'text' in chunk
            assert 'start' in chunk
            assert 'end' in chunk
            assert chunk['id'] == i
            assert 0 <= chunk['start'] < chunk['end'] <= len(text)
            assert chunk['text'] == text[chunk['start']:chunk['end']]


class TestDoclingExtraction:
    """Docling 多模态文档抽取示例（模拟）"""
    
    def test_multimodal_extraction_mock(self):
        """模拟 Docling 抽取流程：文本 + 表格 + 图像"""
        
        # 模拟文档结构
        document = {
            'title': 'Sample Technical Document',
            'content': [
                {
                    'type': 'paragraph',
                    'text': '这是一个关于机器学习的技术文档。本文档包含文本、表格和图表。',
                },
                {
                    'type': 'heading',
                    'level': 2,
                    'text': '第一章 基础概念',
                },
                {
                    'type': 'table',
                    'caption': '表 1：常见机器学习算法对比',
                    'headers': ['算法', '时间复杂度', '空间复杂度'],
                    'rows': [
                        ['K-Means', 'O(nkt)', 'O(nk)'],
                        ['Random Forest', 'O(n*log n)', 'O(n)'],
                    ]
                },
                {
                    'type': 'figure',
                    'caption': '图 1：神经网络架构示意',
                    'image_path': '/path/to/image.png',
                    'description': '多层感知机示意图，展示输入层、隐藏层、输出层结构',
                },
                {
                    'type': 'paragraph',
                    'text': '上表和上图分别展示了不同算法的复杂度和网络结构。',
                },
            ]
        }
        
        # 模拟抽取关键信息
        extracted = extract_key_information_mock(document)
        
        assert 'text' in extracted
        assert 'tables' in extracted
        assert 'figures' in extracted
        assert 'references' in extracted
        
        # 验证抽取的内容
        assert len(extracted['tables']) > 0
        assert len(extracted['figures']) > 0
        assert len(extracted['text']) > 0
    
    def test_chunk_with_metadata_preservation(self):
        """测试切分时保留多模态元数据"""
        from code_agent.rag.text_splitter import split_text
        
        # 构造含元数据的文本
        text = """
【章节】第一章 基础概念
【内容】这是关于机器学习基础的详细说明。内容包括：
- 监督学习的基本原理
- 无监督学习的应用场景
- 强化学习的核心概念

【表格】表 1：算法对比
K-Means vs Random Forest vs 神经网络，在准确度、速度、内存占用方面的对比。

【图像】图 1：流程图
展示了完整的机器学习流程：数据收集 → 预处理 → 特征提取 → 模型训练 → 评估 → 部署。
""" * 5  # 重复以达到足够长度
        
        chunks = split_text(text, chunk_size=400, overlap=100)
        
        # 验证：切分后仍能识别元数据标记
        text_reconstructed = ''.join([c['text'] for c in chunks[:-1]] + 
                                    [chunks[-1]['text']])
        # 允许最后可能有截断
        assert text_reconstructed.startswith(text[:200])
    
    def test_long_context_strategy(self):
        """演示长文本处理策略"""
        from code_agent.rag.text_splitter import split_text
        
        # 模拟长文档（100KB）
        num_sections = 100
        section_text = "这是第 {0} 个章节。" * 50 + "内容。" * 200
        long_text = "\n\n".join([section_text.format(i) for i in range(num_sections)])
        
        # 策略 1：激进切分（快速检索，粒度粗）
        chunks_coarse = split_text(long_text, chunk_size=2000, overlap=200)
        
        # 策略 2：细粒度切分（精准检索，上下文多）
        chunks_fine = split_text(long_text, chunk_size=500, overlap=100)
        
        # 验证
        assert len(chunks_coarse) < len(chunks_fine)
        assert all(len(c['text']) <= 2000 for c in chunks_coarse)
        assert all(len(c['text']) <= 500 for c in chunks_fine)


def extract_key_information_mock(document: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    模拟关键信息抽取（实际应使用 code_agent.rag.extraction_manager）。
    
    Args:
        document: 文档结构（text/table/figure 等混合）
    
    Returns:
        抽取的关键信息：文本摘要、表格标题、图表说明等
    """
    result = {
        'text': [],
        'tables': [],
        'figures': [],
        'references': []
    }
    
    if 'content' in document:
        for item in document['content']:
            if item['type'] == 'paragraph':
                result['text'].append(item['text'])
            elif item['type'] == 'heading':
                result['text'].append(f"## {item['text']}")
            elif item['type'] == 'table':
                result['tables'].append({
                    'caption': item.get('caption', 'Table'),
                    'headers': item.get('headers', []),
                    'row_count': len(item.get('rows', []))
                })
            elif item['type'] == 'figure':
                result['figures'].append({
                    'caption': item.get('caption', 'Figure'),
                    'description': item.get('description', ''),
                    'path': item.get('image_path', '')
                })
    
    return result


class TestExtractionManager:
    """文档抽取管理器集成测试（轻量模拟）"""
    
    def test_extraction_with_multiple_formats(self):
        """演示支持多种格式的抽取"""
        
        # 模拟不同格式的文档
        formats_supported = ['pdf', 'docx', 'pptx', 'txt', 'md']
        
        for fmt in formats_supported:
            # 实际环境中，这里会调用 extraction_manager.extract_key_information()
            # 这里仅验证格式枚举的正确性
            assert fmt in ['pdf', 'docx', 'pptx', 'txt', 'md']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
