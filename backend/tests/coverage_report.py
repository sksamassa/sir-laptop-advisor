"""Statement coverage for the domain layers, using only the standard library.

pytest-cov cannot be installed here, so this script runs the database-free checks
under ``trace`` and reports the share of executable statements hit in the pure
domain modules. Run: python tests/coverage_report.py
"""

from __future__ import annotations

import ast
import sys
import threading
import trace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests")]

TARGETS = sorted(
    [
        *ROOT.glob("src/laptop_dss/ranking/domain/*.py"),
        *ROOT.glob("src/laptop_dss/catalog/domain/*.py"),
        *ROOT.glob("src/laptop_dss/profiles/domain/*.py"),
        *ROOT.glob("src/laptop_dss/shared/domain/*.py"),
    ]
)
THRESHOLD = 0.80


def executable_lines(path: Path) -> set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.lineno for node in ast.walk(tree) if isinstance(node, ast.stmt)}


def main() -> int:
    full = "--full" in sys.argv
    sys.argv = ["run_checks"] if full else ["run_checks", "--unit-only"]
    tracer = trace.Trace(count=True, trace=False)
    # Starlette's TestClient executes the app on a worker thread.
    threading.settrace(tracer.globaltrace)

    def run() -> None:
        import importlib

        module = importlib.import_module("run_checks")
        try:
            module.main()
        except SystemExit:
            pass

    tracer.runfunc(run)
    counts = tracer.results().counts

    total = 0
    covered = 0
    print()
    for path in TARGETS:
        if path.name in {"__init__.py", "criteria_generated.py"}:
            continue
        lines = executable_lines(path)
        if not lines:
            continue
        hit = {line for line in lines if counts.get((str(path), line), 0) > 0}
        total += len(lines)
        covered += len(hit)
        ratio = len(hit) / len(lines)
        print(f"{ratio * 100:6.1f}%  {path.relative_to(ROOT)}  ({len(hit)}/{len(lines)})")

    overall = covered / total if total else 0.0
    print(f"\ndomain statement coverage: {overall * 100:.1f}% ({covered}/{total})")
    print("PASS" if overall >= THRESHOLD else f"FAIL: below {THRESHOLD:.0%}")
    return 0 if overall >= THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
