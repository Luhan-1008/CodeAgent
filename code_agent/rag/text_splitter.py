# code_agent/rag/text_splitter.py
# 简单的基于字符的 TextSplitter 实现（移动自顶层 rag）
from typing import List, Dict

def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
    """
    将长文本按字符分片，返回每片的信息列表。
    每片包含: id(int), text(str), start(int), end(int)

    参数:
      text: 输入文本（str）
      chunk_size: 每片最大字符数 (必须 > 0)
      overlap: 相邻片之间重叠的字符数 (0 <= overlap < chunk_size)
    """
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    idx = 0
    length = len(text)
    while start < length:
        end = start + chunk_size
        if end > length:
            end = length
        chunk_text = text[start:end]
        chunks.append({
            "id": idx,
            "text": chunk_text,
            "start": start,
            "end": end
        })
        idx += 1
        # 如果已经到达文本末尾，则退出循环
        if end >= length:
            break
        start = end - overlap
        if start < 0:
            start = 0
        if start >= length:
            break
    return chunks

# 脚本入口用于手动验证
if __name__ == "__main__":
    sample = "这是一个用于测试的长文本。" * 200
    res = split_text(sample, chunk_size=200, overlap=40)
    print(f"分得 {len(res)} 片, 前两片示例：")
    for c in res[:2]:
        print(c["id"], c["start"], c["end"], c["text"][:50])

