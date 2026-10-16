"""No network, database or AWS required."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/guardian/check.py"
spec = importlib.util.spec_from_file_location("guardian_check", SCRIPT)
guardian = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardian)


def test_guardian_files_and_links():
    assert guardian.check_files() == []


def test_critical_change_requires_scope():
    assert guardian.check_scope(["backend/app/portfolio.py"], []) != []
    assert guardian.check_scope(["backend/app/portfolio.py"], ["backend/app/"]) == []


def test_unrelated_docs_do_not_trigger_critical_scope():
    assert guardian.check_scope(["docs/ROADMAP.md"], ["backend/app/"]) == []


def test_guardian_rejects_traversal_and_unrelated_critical_change():
    assert guardian.check_scope(["../secret"], ["backend/"])
    assert guardian.check_scope(["frontend/app/page.tsx"], ["backend/app/"])


def test_guardian_cli_smoke():
    assert guardian.main([]) == 0
    assert guardian.main(["--changed-file", "backend/app/portfolio.py"]) == 1
