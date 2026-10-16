"""Pure scope policy checks."""
import importlib.util
from pathlib import Path

script = Path(__file__).resolve().parents[2] / "tools/guardian/pr_scope.py"
spec = importlib.util.spec_from_file_location("guardian_scope", script)
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


def test_guardian_only_scope_passes():
    assert scope.evaluate(["tools/guardian/check.py", ".github/workflows/guardian.yml"],
                          ["tools/guardian/", ".github/workflows/guardian.yml"]) == []


def test_unrelated_finance_and_auth_changes_are_rejected():
    result = scope.evaluate(["backend/app/imports.py", "frontend/app/login/page.tsx"], ["tools/guardian/"])
    assert len(result) == 2


def test_docs_changes_need_no_critical_scope():
    assert scope.evaluate(["docs/ROADMAP.md"], []) == []


def test_exact_path_and_prefix_are_distinct():
    assert scope.evaluate([".github/workflows/guardian.yml"], [".github/workflows/guardian.yml"]) == []
    assert scope.evaluate([".github/workflows/deploy.yml"], [".github/workflows/guardian.yml"])
