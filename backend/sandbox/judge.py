# Judge harness — trusted code executed inside the sandbox subprocess.
#
# Reads {"code", "prelude", "tests": [{"setup", "call"}], "timeout"} from stdin,
# runs the user's code once, then evaluates each test with its own stdout
# capture and a per-test time limit (SIGALRM via setitimer). Writes one JSON
# document {"fatal", "results": [{"output", "error", "stdout", "ms"}]}.
import builtins
import io
import json
import signal
import sys
import time


class _TimeLimit(BaseException):
    """BaseException so user `except Exception:` blocks can't swallow it."""


def _on_alarm(signum, frame):
    raise _TimeLimit


def _jsonable(value):
    try:
        json.dumps(value)
        return value, None
    except (TypeError, ValueError):
        return None, f"Return value is not JSON-serialisable: {repr(value)[:200]}"


def _main():
    payload = json.loads(sys.stdin.read())
    ns = {"__name__": "__main__", "__builtins__": builtins}
    exec(compile(payload["prelude"], "<prelude>", "exec"), ns)
    signal.signal(signal.SIGALRM, _on_alarm)
    results, fatal = [], None
    sys.stdin = io.StringIO("")
    try:
        compiled = compile(payload["code"], "<user_code>", "exec")
        tests = [(compile(t["setup"], "<setup>", "exec"), compile(t["call"], "<test>", "eval"))
                 for t in payload["tests"]]
    except SyntaxError as exc:
        fatal = f"SyntaxError on line {exc.lineno}: {exc.msg}"
        tests = []
    if fatal is None:
        _codelens_arm()  # noqa: F821 - defined by guard.py, prepended at runtime
        sys.stdout = io.StringIO()
        try:
            exec(compiled, ns)
        except BaseException as exc:
            fatal = f"{type(exc).__name__}: {exc}"
    for setup, call in tests if fatal is None else []:
        out = sys.stdout = io.StringIO()
        scope = dict(ns)  # fresh globals so one test's inputs can't leak into the next
        value, error = None, None
        start = time.perf_counter()
        signal.setitimer(signal.ITIMER_REAL, float(payload["timeout"]))
        try:
            exec(setup, scope)
            value, error = _jsonable(eval(call, scope))
        except _TimeLimit:
            error = "Time Limit Exceeded"
        except RecursionError:
            error = "RecursionError: maximum recursion depth exceeded"
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        results.append({"output": value, "error": error, "stdout": out.getvalue()[:4000],
                        "ms": round((time.perf_counter() - start) * 1000, 2)})
    sys.stdout = sys.__stdout__
    sys.__stdout__.write(json.dumps({"fatal": fatal, "results": results}))


_main()
