"""tools/test_tools.py —— 跑测试的封装工具

⚠️ 重要：本地开发阶段这里用 subprocess 跑 pytest 只是过渡。
真正"安全地让 DevMate 跑测试"要在沙箱里（第 6 章）——绝不能在生产宿主机上直接跑模型生成的命令。
"""
import asyncio
from langchain.tools import tool


@tool  # 装饰器，标记该函数为一个工具函数
async def run_pytest(path: str = "tests/") -> str:
    """运行 pytest 跑测试，返回测试结果摘要。path 指定测试目录/文件。
    用于在改完代码后验证是否通过测试。"""
    # 创建一个异步子进程来运行 pytest 命令
    # path 参数指定测试目录或文件，默认为 "tests/"
    # "-q" 参数表示安静模式，减少输出
    proc = await asyncio.create_subprocess_exec(
        "pytest", path, "-q",
        stdout=asyncio.subprocess.PIPE,  # 捕获标准输出
        stderr=asyncio.subprocess.STDOUT,  # 将标准错误合并到标准输出
    )
    # 等待进程完成并获取输出
    out, _ = await proc.communicate()
    return out.decode()[-3000:]  # 截断，避免过长结果灌爆上下文
