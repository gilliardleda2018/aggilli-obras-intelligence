"""Review changed paths against declared PR scope. Read-only, fail-closed for critical files."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import CRITICAL_FILES, CRITICAL_PREFIXES


def changed_paths(base: str, head: str = "HEAD") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRD", f"{base}...{head}"],
        cwd=ROOT, check=True, text=True, capture_output=True, timeout=20)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_critical(path: str) -> bool:
    return path in CRITICAL_FILES or path.startswith(CRITICAL_PREFIXES)


def evaluate(paths: list[str], scope: list[str]) -> list[str]:
    critical = [p for p in paths if is_critical(p)]
    if not critical:
        return []
    if not scope:
        return ["Arquivos críticos modificados sem escopo declarado: " + ", ".join(critical)]
    errors = []
    for path in critical:
        if not any(path.startswith(prefix) if prefix.endswith("/") else path == prefix for prefix in scope):
            errors.append("Fora do escopo: " + path)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Git base commit/ref fetched locally")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--scope-file", required=True, help="JSON with allow_prefixes array")
    args = parser.parse_args(argv)
    data = json.loads(Path(args.scope_file).read_text(encoding="utf-8"))
    prefixes = data.get("allow_prefixes", [])
    if not isinstance(prefixes, list) or any(not isinstance(p, str) or not p or p in ("/", ".") or p.startswith("/") or ".." in Path(p).parts for p in prefixes):
        print("GUARDIAN_SCOPE_FAIL: escopo inválido")
        return 1
    try:
        paths = changed_paths(args.base, args.head)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print("GUARDIAN_SCOPE_FAIL: não foi possível calcular o diff", str(exc))
        return 1
    errors = evaluate(paths, prefixes)
    for issue in errors:
        print("GUARDIAN_SCOPE_FAIL:", issue)
    if errors:
        return 1
    print(f"GUARDIAN_SCOPE_OK: {len(paths)} arquivos, {sum(map(is_critical, paths))} críticos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
