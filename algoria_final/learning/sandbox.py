"""
Real Coding Playground: runs student Python in a locked-down subprocess,
and turns any traceback into a friendly "Why did my code fail?" explanation.

Sandboxing notes (read before deploying publicly):
  - Each run is a separate `python -I` (isolated mode) subprocess, so it
    can't see this project's environment, installed packages or files.
  - A CPU-time limit, memory limit and wall-clock timeout are applied.
  - Common ways to reach outside the sandbox (network sockets, spawning
    more processes, deleting files, `ctypes`) are blocked from inside the
    child process itself, before the student's code runs.
  - This is *best-effort* isolation suitable for a trusted classroom
    setting, not a hardened multi-tenant sandbox — for public internet
    deployment, run it inside an additional container/VM boundary too.
"""

import subprocess
import sys
import tempfile
import textwrap

TIMEOUT_SECONDS = 5
MAX_OUTPUT_CHARS = 4000

# Runs *inside* the child process, before the student's own code.
_SANDBOX_PRELUDE = textwrap.dedent("""
    import sys as _sys, builtins as _builtins

    try:
        import resource as _resource
        _resource.setrlimit(_resource.RLIMIT_CPU, (5, 5))
        _resource.setrlimit(_resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    except Exception:
        pass

    _BLOCKED_MODULES = {
        "socket", "subprocess", "multiprocessing", "ctypes", "ftplib",
        "smtplib", "telnetlib", "shutil", "webbrowser",
    }

    class _BlockImports:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in _BLOCKED_MODULES:
                raise ImportError(f"'{name}' is disabled in the Algoria Playground.")
            return None

    _sys.meta_path.insert(0, _BlockImports())

    def _blocked(*a, **k):
        raise PermissionError("This operation is disabled in the Algoria Playground.")

    import os as _os
    for _name in ("system", "popen", "remove", "unlink", "rmdir", "rename",
                   "fork", "kill", "execv", "execve"):
        if hasattr(_os, _name):
            setattr(_os, _name, _blocked)

    _builtins.exit = _blocked
    _builtins.quit = _blocked
    # --- end sandbox prelude ---
""")


def run_python(code, stdin_text=""):
    """Run `code` in the sandbox. Returns a dict:
    {success, output, error, error_kind, timed_out}
    """
    full_source = _SANDBOX_PRELUDE + "\n" + code

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full_source)
        path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, "-I", path],
            input=stdin_text, capture_output=True, text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = proc.stdout[:MAX_OUTPUT_CHARS]
        error = proc.stderr[:MAX_OUTPUT_CHARS]
        return {
            "success": proc.returncode == 0 and not error,
            "output": output,
            "error": error,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "output": "", "timed_out": True,
            "error": f"Your program didn't finish within {TIMEOUT_SECONDS} seconds "
                     f"(possible infinite loop).",
        }
    finally:
        try:
            import os
            os.unlink(path)
        except OSError:
            pass


# ------------------------------------------------- "Why did my code fail?" --
_EXPLANATIONS = [
    ("IndentationError", "Indentation error",
     "Python uses indentation (spaces at the start of a line) to know which lines "
     "belong inside a block, like the body of an `if`, `for` or `def`. One of your "
     "lines doesn't line up the way Python expects.",
     "Check the line the error points to and the line above it — make sure they use "
     "the same number of spaces, and that lines after `:` are indented one level in."),
    ("SyntaxError", "Syntax error",
     "Python couldn't understand the structure of a line — often a missing colon `:`, "
     "a missing closing bracket, or a typo in a keyword.",
     "Look at the line number in the error. Check for a missing `:` after `if`/`for`/`def`, "
     "and make sure every `(`, `[` and `{` has a matching closing bracket."),
    ("NameError", "Unknown name",
     "Your code used a variable or function name that Python doesn't recognize — "
     "usually because it was never created, or it was misspelled.",
     "Check the spelling matches exactly (Python is case-sensitive), and make sure "
     "the variable is assigned a value before you use it."),
    ("TypeError", "Type mismatch",
     "You tried to use two values together in a way their types don't support — like "
     "adding text and a number directly, or calling something that isn't a function.",
     "Check the types of the values involved (use `type(x)` to inspect them) and "
     "convert with `str()`, `int()` or `float()` if you're mixing text and numbers."),
    ("ValueError", "Invalid value",
     "A function received a value of the right type, but the value itself doesn't "
     "make sense for what it's being asked to do — like `int('abc')`.",
     "Check exactly what value is being passed in at that point, and make sure it's "
     "something that function can actually handle."),
    ("ZeroDivisionError", "Division by zero",
     "Your code tried to divide a number by zero, which is mathematically undefined.",
     "Before dividing, check whether the divisor is zero (e.g. `if b != 0:`) and "
     "handle that case separately."),
    ("IndexError", "Index out of range",
     "You tried to access a position in a list/string that doesn't exist — often "
     "one step past the last valid item.",
     "Remember indexing starts at 0 and the last valid index is `len(x) - 1`. Print "
     "`len(x)` to double-check how many items there really are."),
    ("KeyError", "Missing dictionary key",
     "You tried to look up a key in a dictionary that isn't actually there.",
     "Check the exact spelling of the key, or use `d.get(key)` instead of `d[key]` "
     "so a missing key returns `None` instead of crashing."),
    ("AttributeError", "Missing attribute or method",
     "You called a method or accessed a property that doesn't exist on that object "
     "— often a typo, or you're working with a different type than you expected.",
     "Print `type(x)` to confirm what kind of object you actually have, then check "
     "the correct method name for that type."),
    ("ModuleNotFoundError", "Module not available",
     "Your code tried to import a module that isn't available in the Playground.",
     "The Playground only allows Python's standard library, and a few modules are "
     "disabled for safety (like `socket` and `subprocess`). Try a different approach."),
    ("ImportError", "Import not available",
     "Your code tried to import something that isn't available in the Playground.",
     "The Playground only allows Python's standard library, and a few modules are "
     "disabled for safety. Try a different approach."),
    ("PermissionError", "Operation not allowed here",
     "Your code tried to do something the Playground blocks for safety, like running "
     "another program or touching the filesystem.",
     "The Playground is for practicing Python logic, not system operations — try "
     "solving the problem with regular Python code instead."),
    ("RecursionError", "Too much recursion",
     "A function kept calling itself without ever stopping, until Python ran out of "
     "call-stack space.",
     "Check that your recursive function has a base case that actually gets reached, "
     "and that each call moves closer to it."),
]


def explain_error(stderr_text):
    """Turn a Python traceback's stderr text into a friendly explanation.
    Returns a dict with title/what/why/how, or None if there's no error."""
    if not stderr_text.strip():
        return None

    last_line = stderr_text.strip().splitlines()[-1]
    for err_type, title, why, how in _EXPLANATIONS:
        if err_type in last_line:
            return {
                "error_type": err_type, "title": title,
                "what_happened": last_line,
                "why": why, "how_to_fix": how,
            }

    return {
        "error_type": "Error", "title": "Something went wrong",
        "what_happened": last_line,
        "why": "Python stopped running your program because of the error shown above.",
        "how_to_fix": "Read the last line of the error message closely — it usually "
                       "names the problem and the line number it happened on.",
    }
