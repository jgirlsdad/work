import ast, json, subprocess, sys, tempfile, re
from pathlib import Path
from typing import Dict, Any, Tuple, List

DANGEROUS_IMPORTS = {"os","subprocess","sys","shutil","socket","http","requests","urllib","ftplib","paramiko","psutil","ctypes","multiprocessing","pathlib","pickle"}
DANGEROUS_NAMES = {"system","popen","spawn","fork","remove","unlink","rmtree","rmdir","chmod","chown","open","eval","exec","compile","execfile","kill","killpg","killall","mkfifo","mknod"}
SAFE_IMPORT_ROOTS = {"pandas","numpy","matplotlib","sklearn","statsmodels","math","statistics"}

def lint_proposed_code(code: str) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"SyntaxError: {e}"]
    class V(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in DANGEROUS_IMPORTS:
                    issues.append(f"Dangerous import: {alias.name}")
                elif root not in SAFE_IMPORT_ROOTS:
                    issues.append(f"Warning: importing unknown module '{alias.name}'")
        def visit_ImportFrom(self, node: ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in DANGEROUS_IMPORTS:
                issues.append(f"Dangerous import from: {node.module}")
            elif root and root not in SAFE_IMPORT_ROOTS:
                issues.append(f"Warning: importing unknown module '{node.module}'")
        def visit_Call(self, node: ast.Call):
            target = ""
            if isinstance(node.func, ast.Name): target = node.func.id
            elif isinstance(node.func, ast.Attribute): target = node.func.attr
            if target in DANGEROUS_NAMES:
                issues.append(f"Dangerous call: {target}()")
            self.generic_visit(node)
    V().visit(tree)
    for p in ["import os","import subprocess","eval(","exec(","open(","requests.","socket.","shutil."]:
        if p in code: issues.append(f"Pattern flagged: {p}")
    ok = not any(msg.startswith("Dangerous") for msg in issues)
    return ok, issues

def sandbox_test_function(code: str, func_name: str, kwargs: Dict[str, Any], timeout: int = 25) -> Dict[str, Any]:
    """Execute a SINGLE function (not decorated) in a temporary directory.
    Returns dict: {ok, stdout, stderr, returncode, result?}
    """
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        # Ensure just a function; strip decorators if any
        code_sanitized = re.sub(r"@\w+\([^\)]*\)\s*def", "def", code, flags=re.S)
        (tdir / "draft_tool.py").write_text(code_sanitized, encoding="utf-8")
        (tdir / "kwargs.json").write_text(json.dumps(kwargs, default=str), encoding="utf-8")
        runner = f"""
import json, traceback
ns = {{}}
src = open("draft_tool.py","r",encoding="utf-8").read()
try:
    exec(src, ns, ns)
    fn = ns.get("{func_name}")
    if not callable(fn): raise RuntimeError("Function '{func_name}' not found after exec.")
    kwargs = json.load(open("kwargs.json","r",encoding="utf-8"))
    out = fn(**kwargs)
    print("===RESULT===")
    try:
        print(json.dumps(out, default=str))
    except Exception:
        print(json.dumps({{"repr": str(out)}}))
except Exception as e:
    print("===ERROR===")
    print(str(e))
    print(traceback.format_exc())
"""
        (tdir / "run_test.py").write_text(runner, encoding="utf-8")
        import subprocess, sys
        proc = subprocess.run([sys.executable, "run_test.py"], cwd=tdir, capture_output=True, text=True, timeout=timeout)
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        result = {"ok": False, "stdout": stdout[-4000:], "stderr": stderr[-4000:], "returncode": rc}
        if "===RESULT===" in stdout:
            try:
                payload = stdout.split("===RESULT===")[-1].strip()
                import json as _json
                result_obj = _json.loads(payload)
                result.update({"ok": True, "result": result_obj})
            except Exception as e:
                result.update({"ok": False, "parse_error": str(e)})
        elif "===ERROR===" in stdout:
            result.update({"ok": False})
        return result
