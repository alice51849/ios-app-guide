"""geo-daily 以點路徑從 repo 根目錄執行的測試模組，必須不靠 PYTHONPATH 就能匯入。

2026-09-12 起 test_publisher_intent_catalog 改用頂層 `import market_contract_assertions`，
只有從 tests 目錄 discover 才找得到，geo-daily 的「Verify pre-materialization contracts」
因此連敗 7 天（ModuleNotFoundError）。本測試在乾淨子行程重現 workflow 的匯入方式。
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

TESTS = Path(__file__).resolve().parent
if TESTS.parent.parent.name == "_engine":
    ROOT = TESTS.parents[2]
    PACKAGE = "_engine.geo.tests"
    WORKFLOWS = (ROOT / ".github" / "workflows" / "geo-daily.yml",)
else:
    ROOT = TESTS.parents[1]
    PACKAGE = "geo.tests"
    WORKFLOWS = (ROOT / "geo" / "pages" / ".github" / "workflows" / "geo-daily.yml",)

# workflow 檔不在（例如 GrowthEngine 隔離 worktree 沒有 geo/pages）時的最低保證清單
PINNED_MODULES = ("test_publisher_intent_catalog", "test_publication_source_preflight")
DOTTED = re.compile(r"_engine\.geo\.tests\.(test_[A-Za-z0-9_]+)")


def dotted_modules() -> tuple[str, ...]:
    for workflow in WORKFLOWS:
        if workflow.is_file():
            names = set(DOTTED.findall(workflow.read_text(encoding="utf-8")))
            return tuple(sorted(names | set(PINNED_MODULES)))
    return PINNED_MODULES


class DottedPathImportTests(unittest.TestCase):
    def test_workflow_modules_import_from_repository_root_without_pythonpath(self):
        modules = [f"{PACKAGE}.{name}" for name in dotted_modules()]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib, sys\nfor name in sys.argv[1:]:\n    importlib.import_module(name)",
                *modules,
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        self.assertEqual(0, result.returncode, result.stderr[-4000:])


if __name__ == "__main__":
    unittest.main()
