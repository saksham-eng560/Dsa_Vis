# Sandbox guard — prepended to every sandboxed program (see executor.py).
#
# Installs a PEP 578 audit hook that denies capabilities user code never needs
# for algorithm visualisation: network, processes, filesystem writes, native
# code loading and introspection escapes. Audit hooks cannot be removed once
# installed, so user code cannot disable this.
import sys as _sys

_DENIED_PREFIXES = (
    "socket.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.fork",
    "os.posix_spawn", "os.kill", "os.remove", "os.unlink", "os.rename",
    "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.truncate", "os.symlink",
    "os.link", "os.putenv", "os.unsetenv", "shutil.", "ctypes.", "urllib.",
    "http.", "ftplib.", "smtplib.", "webbrowser.", "winreg.", "code.__new__",
    "pty.", "fcntl.", "resource.setrlimit", "signal.",
)
_DENIED_IMPORTS = frozenset({
    "socket", "subprocess", "ctypes", "multiprocessing", "threading", "asyncio",
    "urllib", "http", "ftplib", "smtplib", "ssl", "shutil", "pty", "signal",
    "_posixsubprocess", "importlib.util", "webbrowser", "pickle", "marshal",
})
_GUARD = {"armed": False}


def _codelens_audit(event, args):
    """Reject denied events once the harness has armed the guard."""
    if not _GUARD["armed"]:
        return
    if event == "import" and args and str(args[0]).split(".")[0] in _DENIED_IMPORTS:
        raise PermissionError(f"Import of '{args[0]}' is disabled in the sandbox")
    if event == "open":
        mode = args[1] if len(args) > 1 and isinstance(args[1], str) else "r"
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        if any(c in mode for c in "wax+") or flags & 0o3:  # O_WRONLY | O_RDWR
            raise PermissionError("Writing files is disabled in the sandbox")
        return
    if event.startswith(_DENIED_PREFIXES):
        raise PermissionError(f"'{event}' is disabled in the sandbox")


_sys.addaudithook(_codelens_audit)


def _codelens_arm():
    """Called by the harness right before user code runs."""
    _GUARD["armed"] = True
