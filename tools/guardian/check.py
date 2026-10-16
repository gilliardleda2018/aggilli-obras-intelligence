#!/usr/bin/env python3
"""Em Obras Guardian: deterministic, offline repository safety checks.

Read-only. No network, AWS credentials, database or application execution.
"""
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".agents/skills/emobras-guardian/SKILL.md"
REQUIRED = [
    "AGENTS.md",
    ".agents/skills/emobras-guardian/SKILL.md",
    ".agents/skills/emobras-guardian/references/checklist.md",
    ".agents/skills/emobras-guardian/references/handoff.md",
    ".agents/skills/emobras-guardian/references/parallel-agents.md",
    ".agents/skills/emobras-guardian/references/production-gates.md",
    "docs/GUARDIAN-OPERACAO-AGENTES.md",
]
CRITICAL_PREFIXES = (
    "backend/app/", "backend/migrations/", "frontend/app/",
    "frontend/lib/", ".github/workflows/", "infra/",
)
CRITICAL_FILES = {"backend/data/tuntum_2026-08-28.json", "backend/Dockerfile", "AGENTS.md"}


def check_files(root=ROOT):
    errors = []
    for path in REQUIRED:
        if not (root / path).is_file():
            errors.append("Arquivo obrigatório ausente: " + path)
    if errors:
        return errors
    text = (root / ".agents/skills/emobras-guardian/SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\nname: emobras-guardian\n"):
        errors.append("SKILL.md precisa de frontmatter e nome oficial")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("https://", "http://", "#")):
            continue
        if not (root / ".agents/skills/emobras-guardian" / target).resolve().is_file():
            errors.append("Link local quebrado em SKILL.md: " + target)
    if "emobras-guardian" not in (root / "AGENTS.md").read_text(encoding="utf-8"):
        errors.append("AGENTS.md não referencia Guardian")
    return errors


def check_scope(changed, scope):
    """Detect critical paths outside explicitly declared prefix allowlist."""
    if not changed:
        return []
    if not scope:
        return ["Informe --allow-prefix para avaliar mudanças críticas"]
    errors = []
    for path in changed:
        if path.startswith("/") or ".." in Path(path).parts:
            errors.append("Caminho inválido: " + path)
        elif (path.startswith(CRITICAL_PREFIXES) or path in CRITICAL_FILES) and not any(
            path == prefix.rstrip("/") or path.startswith(prefix) for prefix in scope
        ):
            errors.append("Mudança crítica fora do escopo declarado: " + path)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--allow-prefix", action="append", default=[])
    args = parser.parse_args(argv)
    errors = check_files() + check_scope(args.changed_file, args.allow_prefix)
    for error in errors:
        print("GUARDIAN_FAIL:", error)
    if errors:
        return 1
    print("GUARDIAN_OK: arquivos, links e escopo declarados validados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
