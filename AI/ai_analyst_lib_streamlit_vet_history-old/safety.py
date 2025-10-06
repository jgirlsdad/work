# safety.py
"""
Lightweight safety & sandbox helpers for vetting proposed tools.

This is NOT a perfect sandbox. It provides:
- Static lint (AST) to block dangerous imports and calls.
- Pattern denylist.
- Subprocess execution in an isolated temp working directory with timeout.
"""

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, List

DANGEROUS_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "socket", "http", "requests",
    "urllib", "ftplib", "paramiko", "psutil", "ctypes", "multiprocessing",
    "pathlib", "pickle"
}
DANGEROUS_NAMES = {
    "system", "popen", "spawn", "fork", "remove", "unlink", "rmtree",
    "rmdir", "chmod", "chown", "open", "eval", "exec", "compile", "execfile",
    "kill", "killpg", "killall", "mkfifo", "mknod"
}
# allowlist of import roots typically safe for data analysis
SAFE_IMPORT_ROOTS = {"pandas", "numpy", "matplotlib", "sklearn", "statsmodels", "math", "statistics"}

def lint_proposed_code(code: str) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"SyntaxError: {e}"]

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in DANGEROUS_IMPORTS:
                    issues.append(f"Dangerous import: {alias.name}")
                elif root not in SAFE_IMPORT_ROOTS:
                    # Warn (not block) unknown roots
                    issues.append(f"Warning: importing unknown module '{alias.name}'")
        def visit_ImportFrom(self, node: ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in DANGEROUS_IMPORTS:
                issues.append(f"Dangerous import from: {node.module}")
            elif root and root not in SAFE_IMPORT_ROOTS:
                issues.append(f"Warning: importing unknown module '{node.module}'")
        def visit_Call(self, node: ast.Call):
            # flag eval/exec/compile, os.system-like
            target = ""
            if isinstance(node.func, ast.Name):
                target = node.func.id
            elif isinstance(node.func, ast.Attribute):
                target = node.func.attr
            if target in DANGEROUS_NAMES:
                issues.append(f"Dangerous call: {target}()")
            self.generic_visit(node)

    Visitor().visit(tree)

    # quick pattern scan
    deny_patterns = ["import os", "import subprocess", "eval(", "exec(", "open(", "requests.", "socket.", "shutil."]
    for p in deny_patterns:
        if p in code:
            issues.append(f"Pattern flagged: {p}")

    ok = not any(msg.startswith("Dangerous") for msg in issues)  # block only on "Dangerous" findings
    return ok, issues

def sandbox_test_tool(code: str, tool_name: str, kwargs: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    """
    Runs proposed tool code in an isolated temp directory.
    - Writes code to tmp file with @tool decorator stub bypassed (no registry write during test).
    - Creates a minimal runner that execs the code into a local dict and calls the function.
    - Captures stdout/stderr and JSON-serializable result.
    """
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)

        # write code
        code_path = tdir / "proposed_tool.py"
        # Replace decorator usage during test (strip @tool(...) lines)
        import re
        code_sanitized = re.sub(r"@tool\([^)]*\)\s*def", "def", code, flags=re.S)
        code_path.write_text(code_sanitized, encoding="utf-8")

        runner = tdir / "run_test.py"
        runner.write_text(f"""
import json, traceback
from pathlib import Path

ns = {{}}
src = Path("proposed_tool.py").read_text(encoding="utf-8")
try:
    exec(src, ns, ns)
    fn = ns.get("{tool_name}")
    if not callable(fn):
        raise RuntimeError("Function '{tool_name}' not found after exec.")
    kwargs = json.loads(Path("kwargs.json").read_text(encoding="utf-8"))
    out = fn(**kwargs)
    print("===RESULT===")
    print(json.dumps(out, default=str))
except Exception as e:
    print("===ERROR===")
    print("\\n".join([str(e), traceback.format_exc()]))
""", encoding="utf-8")

        (tdir / "kwargs.json").write_text(json.dumps(kwargs, default=str), encoding="utf-8")

        proc = subprocess.run([sys.executable, "run_test.py"], cwd=tdir, capture_output=True, text=True, timeout=timeout)
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        result = {"ok": False, "stdout": stdout[-4000:], "stderr": stderr[-4000:], "returncode": rc}

        if "===RESULT===" in stdout:
            try:
                payload = stdout.split("===RESULT===")[-1].strip()
                result_obj = json.loads(payload)
                result.update({"ok": True, "result": result_obj})
            except Exception as e:
                result.update({"ok": False, "parse_error": str(e)})
        elif "===ERROR===" in stdout:
            result.update({"ok": False})

        return result