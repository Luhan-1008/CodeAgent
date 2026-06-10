# projects/deep_code_research/self_healing_example.py
"""
自愈构建/测试示例：展示代码生成 Agent 如何自动运行构建、捕获错误、生成修复建议。

这是一个参考实现，展示"自我反思"能力。可在 build_test/fix 节点中集成类似逻辑。
"""
import json
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


class BuildTestResult:
    """构建/测试执行结果"""
    def __init__(self):
        self.success: bool = True
        self.stdout: str = ""
        self.stderr: str = ""
        self.errors: List[Dict] = []  # 解析出的错误
    
    def to_dict(self):
        return {
            'success': self.success,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'errors': self.errors
        }


def run_build_and_test(project_dir: str) -> BuildTestResult:
    """
    运行项目构建与测试（假设 Python 项目 with setup.py 或 requirements.txt）。
    
    Args:
        project_dir: 项目目录路径
    
    Returns:
        BuildTestResult 包含执行结果与错误信息
    """
    result = BuildTestResult()
    
    # Step 1: 运行 pytest（如果存在 tests/）
    try:
        print(f"[Build] Running pytest in {project_dir}...")
        proc = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        result.stdout += proc.stdout
        result.stderr += proc.stderr
        
        if proc.returncode != 0:
            result.success = False
            # 解析错误
            errors = parse_pytest_errors(proc.stdout + proc.stderr)
            result.errors.extend(errors)
    except subprocess.TimeoutExpired:
        result.success = False
        result.errors.append({
            'type': 'timeout',
            'message': 'pytest execution timed out after 60 seconds'
        })
    except FileNotFoundError:
        print("[Build] pytest not available, skipping tests")
    except Exception as e:
        result.success = False
        result.errors.append({
            'type': 'exception',
            'message': str(e)
        })
    
    # Step 2: 运行 Python 语法检查（可选）
    try:
        print("[Build] Running syntax check...")
        proc = subprocess.run(
            [sys.executable, '-m', 'py_compile', '-b', 'code_agent/'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        if proc.returncode != 0:
            result.success = False
            result.errors.append({
                'type': 'syntax_error',
                'message': proc.stderr
            })
    except Exception as e:
        pass  # 非关键，跳过
    
    return result


def parse_pytest_errors(output: str) -> List[Dict]:
    """
    从 pytest 输出中提取错误信息。
    
    Args:
        output: pytest 的 stdout + stderr
    
    Returns:
        错误列表，每项包含类型、位置、消息
    """
    errors = []
    lines = output.split('\n')
    
    for i, line in enumerate(lines):
        if 'FAILED' in line or 'ERROR' in line or 'AssertionError' in line:
            # 简单启发式：收集失败行及其前后几行作为上下文
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 3)
            context = '\n'.join(lines[context_start:context_end])
            
            errors.append({
                'type': 'test_failure',
                'line_number': i,
                'context': context
            })
    
    return errors


def generate_fix_prompt(build_result: BuildTestResult, code_snippet: str) -> str:
    """
    基于构建/测试失败，生成修复提示，供后续 LLM Agent 处理。
    
    Args:
        build_result: 构建结果
        code_snippet: 生成的代码片段（供上下文）
    
    Returns:
        修复提示字符串
    """
    prompt = "## 构建/测试失败，请修复\n\n"
    
    if build_result.errors:
        prompt += "### 检测到的错误\n"
        for err in build_result.errors:
            prompt += f"- **类型**: {err.get('type', 'unknown')}\n"
            prompt += f"  **详情**: {err.get('message', err.get('context', 'N/A'))}\n\n"
    
    if build_result.stderr:
        prompt += "### 错误日志\n```\n"
        prompt += build_result.stderr[:500] + ("..." if len(build_result.stderr) > 500 else "")
        prompt += "\n```\n\n"
    
    prompt += "### 生成的代码\n```python\n"
    prompt += code_snippet[:500] + ("..." if len(code_snippet) > 500 else "")
    prompt += "\n```\n\n"
    
    prompt += "请分析错误根因，并给出修复方案。"
    
    return prompt


def example_workflow():
    """
    示例工作流：代码生成 -> 构建/测试 -> 错误检测 -> 修复提示生成。
    
    这个函数展示如何在实际 Agent 中集成自愈逻辑。
    """
    print("[Example] DeepCodeResearch Self-Healing Workflow")
    print("=" * 60)
    
    # 假设项目目录
    project_dir = "."
    
    # 第一轮：生成代码（这里用示例）
    generated_code = """
def hello_world():
    print("Hello, World!")
    return 42

if __name__ == "__main__":
    result = hello_world()
    assert result == 42, "Expected 42"
    print(f"Result: {result}")
"""
    
    print("\n[Gen] Generated code:")
    print(generated_code)
    
    # 第二轮：构建/测试
    print("\n[Build] Running build and tests...")
    build_result = run_build_and_test(project_dir)
    
    print(f"[Build] Success: {build_result.success}")
    if build_result.errors:
        print(f"[Build] Errors found: {len(build_result.errors)}")
        for err in build_result.errors:
            print(f"  - {err}")
    
    # 第三轮：如果失败，生成修复提示
    if not build_result.success:
        print("\n[Fix] Generating fix prompt...")
        fix_prompt = generate_fix_prompt(build_result, generated_code)
        print(fix_prompt)
        
        # 这个提示会被送给修复 Agent (fix node)
        print("\n[Fix] This prompt would be sent to the fix agent:")
        print("-" * 60)
        print(fix_prompt)
    else:
        print("\n[Build] All checks passed!")
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print("[Summary] Build Result:")
    print(json.dumps(build_result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    example_workflow()
