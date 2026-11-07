"""Sandboxed execution of untrusted Python in a throwaway subprocess.

Defence in depth (the guard is NOT a security boundary by itself — run the API
inside a container with no network for production deployments):

1. Separate process in isolated mode (`python -I`): no user site, no env vars.
2. POSIX resource limits: CPU seconds, address space, zero-byte file writes,
   no child processes.
3. Wall-clock timeout enforced by the parent; the process group is killed.
4. A PEP 578 audit hook inside the child (see `guard.py`) denies network,
   subprocess, filesystem writes and dangerous modules.
5. Output is size-capped before parsing.
"""

import asyncio
import os
import resource
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

_MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_GUARD_PATH = Path(__file__).with_name("guard.py")


@dataclass(frozen=True)
class ExecutionResult:
    """Raw outcome of a sandboxed run."""

    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


def _try_limit(kind: int, value: int) -> None:
    """Lower one limit; skip it where the OS refuses (macOS rejects RLIMIT_AS / NPROC)."""
    try:
        _, hard = resource.getrlimit(kind)
        cap = value if hard == resource.RLIM_INFINITY else min(value, hard)
        resource.setrlimit(kind, (cap, cap))
    except (ValueError, OSError):
        pass


def _limit_resources(cpu_s: int, memory_mb: int) -> None:
    """`preexec_fn`: applied in the child between fork and exec. Must never raise."""
    os.setsid()  # own process group so the timeout can kill everything
    _try_limit(resource.RLIMIT_CPU, cpu_s)
    _try_limit(resource.RLIMIT_AS, memory_mb * 1024 * 1024)
    _try_limit(resource.RLIMIT_FSIZE, 0)
    _try_limit(resource.RLIMIT_CORE, 0)
    if sys.platform != "darwin":  # macOS counts all of the user's processes here
        _try_limit(resource.RLIMIT_NPROC, 0)


async def run_python(
    script: str, stdin_data: str, timeout_s: float, memory_mb: int
) -> ExecutionResult:
    """Run `script` (trusted harness code) feeding `stdin_data` (untrusted payload).

    The guard module is prepended so its audit hook is installed before the
    harness runs; the harness itself decides when user code executes.
    """
    program = _GUARD_PATH.read_text() + "\n" + script
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-c",
        program,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=lambda: _limit_resources(int(timeout_s) + 1, memory_mb),
        env={"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"},
        cwd="/",
    )
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(stdin_data.encode()), timeout=timeout_s
        )
    except TimeoutError:
        _kill_group(proc.pid)
        await proc.wait()
        return ExecutionResult("", "Execution timed out", -1, timed_out=True)

    return ExecutionResult(
        stdout=out[:_MAX_OUTPUT_BYTES].decode("utf-8", "replace"),
        stderr=err[:65536].decode("utf-8", "replace"),
        returncode=proc.returncode if proc.returncode is not None else -1,
        timed_out=False,
    )


def _kill_group(pid: int) -> None:
    """Kill the child's whole process group, ignoring already-dead processes."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
