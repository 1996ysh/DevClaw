
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from infra.settings import get_settings
from infra.logging import get_logger
from sandbox.docker_sandbox import DockerSandbox

logger = get_logger()


async def _run(cmd: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await proc.communicate()
    return (proc.returncode if proc.returncode is not None else -1,
            out.decode("utf-8", errors="replace"))


async def create_one_sandbox() -> DockerSandbox:
    """以加固参数起一个常驻容器，返回 DockerSandbox。"""
    s = get_settings()
    name = f"syc-sbx-{uuid.uuid4().hex[:12]}"
    workdir = s.sandbox_workdir

    # tmpfs 工作目录：可写 + 可执行 + 限大小 + 属主对齐非 root 用户(uid=1000)
    tmpfs_opt = f"{workdir}:rw,exec,size=512m,uid=1000"

    code, out = await _run([
        "docker", "run", "-d", "--name", name,
        "--runtime", s.sandbox_runtime,             # ← 换它即换隔离级别
        "--network", "none",                        # 断网
        "--cap-drop", "ALL",                        # 丢能力
        "--security-opt", "no-new-privileges",      # 禁提权
        "--read-only",                              # 只读根
        "--tmpfs", tmpfs_opt,                       # 唯一可写区
        "--tmpfs", "/tmp:rw,exec,size=128m,uid=1000",  # 额外给 /tmp 可写(部分工具需要)
        "--memory", s.sandbox_mem_limit,
        "--memory-swap", s.sandbox_mem_limit,
        "--pids-limit", str(s.sandbox_pids_limit),
        "--cpus", s.sandbox_cpus,
        "--user", "1000:1000",                      # 非 root
        "-w", workdir,
        s.sandbox_image, "sleep", "infinity",       # 常驻，等 docker exec
    ])
    if code != 0:
        raise RuntimeError(f"起沙箱容器失败：{out}")
    logger.info("加固容器已起：{}（runtime={}）", name, s.sandbox_runtime)
    return DockerSandbox(container_id=name, workdir=workdir)


async def seed_project(
    sandbox: DockerSandbox,
    root: Path | None = None,
    subdirs: tuple[str, ...] = ("app", "tests", "skills"),
    extra_files: tuple[str, ...] = ("AGENTS.md",),
) -> None:
    """把宿主项目 seed 进容器工作目录（docker cp）。

    与第 6 章一致：不 seed 的话沙箱是空的，coder 写不进文件、skills 报 path_not_found。
    """
    root = root or Path(__file__).resolve().parent.parent
    cid = sandbox.container_id
    workdir = sandbox.workdir
    for sub in subdirs:
        p = root / sub
        if p.exists():
            await _run(["docker", "cp", str(p), f"{cid}:{workdir}/{sub}"])
    for f in extra_files:
        fp = root / f
        if fp.is_file():
            await _run(["docker", "cp", str(fp), f"{cid}:{workdir}/{f}"])
    # seed 进来的文件属主可能是 root，统一改成 agent(1000)，否则非 root 进程改不动
    await _run(["docker", "exec", "-u", "0", cid, "chown", "-R", "1000:1000", workdir])
    logger.info("项目已 seed 进容器 {}", cid)


async def destroy_sandbox(sandbox: DockerSandbox) -> None:
    """销毁容器（用完即弃）。tmpfs 工作目录随容器一起消失，不残留。"""
    await _run(["docker", "rm", "-f", sandbox.container_id])
    logger.info("容器已销毁：{}", sandbox.container_id)