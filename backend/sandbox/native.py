"""Compile and run C++ test drivers.

Native code can't be guarded by the Python audit hook, so each run gets:
rlimits (CPU, file size, core dumps; address space where the OS allows it),
a wall-clock timeout that kills the process group, a throwaway working
directory, and on macOS `sandbox-exec` denying network access.
Compiled binaries are cached by source hash so re-running tests is instant.
"""

import asyncio
import hashlib
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sandbox.executor import _kill_group, _limit_resources

_BUILD_DIR = Path(tempfile.gettempdir()) / "codelens-cpp"
_MAC_PROFILE = "(version 1)(allow default)(deny network*)"


@dataclass(frozen=True)
class NativeResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


def find_compiler() -> str | None:
    """$CXX, then clang++ (macOS default), then g++."""
    for cand in (os.environ.get("CXX"), "clang++", "g++", "c++"):
        if cand and shutil.which(cand):
            return cand
    return None


async def _run(argv: list[str], timeout_s: float, memory_mb: int | None, cwd: Path) -> NativeResult:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd),
        preexec_fn=(lambda: _limit_resources(int(timeout_s) + 1, memory_mb)) if memory_mb else os.setsid,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        _kill_group(proc.pid)
        await proc.wait()
        return NativeResult("", "", -1, True)
    # stderr carries the trace JSON (can be several MB for big inputs) — keep it whole
    return NativeResult(out[:2_000_000].decode("utf-8", "replace"), err[:32_000_000].decode("utf-8", "replace"),
                        proc.returncode if proc.returncode is not None else -1, False)


async def compile_cpp(source: str, shim_header: str, opt: str = "-O2") -> tuple[Path | None, str]:
    """Compile `source`; returns (binary, diagnostics). Binary is None on failure.

    Traces use `-O0` (compiles ~2x faster; speed of the traced run doesn't matter).
    """
    cxx = find_compiler()
    if cxx is None:
        return None, "No C++ compiler found. On macOS run: xcode-select --install"
    digest = hashlib.sha256((opt + source).encode()).hexdigest()[:20]
    work = _BUILD_DIR / digest
    binary = work / "solution"
    if binary.exists():
        return binary, ""
    (work / "include" / "bits").mkdir(parents=True, exist_ok=True)
    (work / "include" / "bits" / "stdc++.h").write_text(shim_header)
    (work / "main.cpp").write_text(source)
    res = await _run([cxx, "-std=c++17", opt, "-w", "-I", "include", "main.cpp", "-o", "solution"],
                     timeout_s=60, memory_mb=None, cwd=work)
    if res.timed_out:
        return None, "Compilation timed out."
    if res.returncode != 0:
        shutil.rmtree(work, ignore_errors=True)
        return None, _clean_diagnostics(res.stderr)
    return binary, ""


def _clean_diagnostics(stderr: str, limit: int = 25) -> str:
    """Keep the first errors, pointing at the user's file."""
    lines = [ln for ln in stderr.splitlines() if "solution.cpp" in ln or not ln.startswith(("In file", "main.cpp"))]
    return "\n".join(lines[:limit]).strip() or stderr[:2000]


async def run_binary(binary: Path, arg: str, timeout_s: float, memory_mb: int) -> NativeResult:
    argv = [str(binary), arg]
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        argv = ["sandbox-exec", "-p", _MAC_PROFILE, *argv]
    with tempfile.TemporaryDirectory(prefix="codelens-run-") as cwd:
        return await _run(argv, timeout_s, memory_mb, Path(cwd))
