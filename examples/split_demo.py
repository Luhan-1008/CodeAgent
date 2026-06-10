# examples/split_demo.py
# Demo 脚本：通过直接按文件路径加载模块，避免导入 package-level 初始化（减少依赖）
import importlib.util
import pathlib
import sys

# module file path: code_agent/rag/text_splitter.py
project_root = pathlib.Path(__file__).resolve().parent.parent
module_path = project_root / 'code_agent' / 'rag' / 'text_splitter.py'
if not module_path.exists():
    print('模块文件不存在:', module_path)
    sys.exit(1)

spec = importlib.util.spec_from_file_location('code_agent.rag.text_splitter', str(module_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
split_text = mod.split_text


def run(path: str = "examples/sample.txt"):
    p = pathlib.Path(path)
    if not p.exists():
        print("示例文件不存在:", p)
        return
    text = p.read_text(encoding="utf-8")
    chunks = split_text(text, chunk_size=400, overlap=80)
    print(f"共分成 {len(chunks)} 片")
    for c in chunks[:10]:
        preview = c['text'][:60].replace("\n", "\\n")
        print(f"id={c['id']}, start={c['start']}, end={c['end']}, preview={preview!r}")


if __name__ == "__main__":
    import sys as _sys
    arg = _sys.argv[1] if len(_sys.argv) > 1 else "examples/sample.txt"
    run(arg)
