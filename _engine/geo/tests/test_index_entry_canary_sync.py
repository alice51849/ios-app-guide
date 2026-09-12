#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨 repo 同步契約:Growth `geo/` 與 Guide `_engine/geo/` 必須一致。

雲端跑的是 Guide repo 的鏡像副本。以前只靠「改完記得同步」的口頭約定,忘了就會
出現「權威副本已修、雲端還在跑舊邏輯」而且**沒有任何東西會失敗**的狀態。
這支把它變成會 fail 的檢查:

  • 權威側(本 repo):三個檔案的 sha256 必須等於契約值。改了檔案就必須同時
    更新契約 —— 否則契約會變成一張過期的紙。
  • 鏡像側:`geo/pages/_engine/geo/` 存在時,同樣三個檔案必須等於同一組值,
    不一致就 FAIL。這就是「未同步時 fail」。
  • 鏡像不存在時 SKIP 並說明原因(隔離 worktree 沒有巢狀站台 repo 是正常的),
    但絕不因此改成永遠通過。
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import unittest

GEO = Path(__file__).resolve().parent.parent
CONTRACT_PATH = GEO / "index_entry_canary_sync_contract.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
PAIRS = CONTRACT["pairs"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_root() -> Path:
    """權威副本的 repo 根目錄(geo/ 的上一層)。"""
    return GEO.parent


def _mirror_root() -> Path | None:
    """Guide 鏡像的 `_engine/geo`;不存在就回 None。

    只找**本 checkout 內**的 `geo/pages/_engine/geo`,不去摸其他 worktree 共用的
    站台副本 —— 那份可能停在很舊的 commit,拿它來判斷同步與否會得到假警報。
    需要對特定 checkout 驗證時用 ``GEO_MIRROR_ENGINE`` 明確指定。
    """
    override = os.environ.get("GEO_MIRROR_ENGINE", "").strip()
    if override:
        candidate = Path(override).expanduser()
        return candidate if candidate.is_dir() else None
    candidate = _repo_root() / "geo" / "pages" / "_engine" / "geo"
    return candidate if candidate.is_dir() else None


class ContractShapeTest(unittest.TestCase):
    def test_contract_declares_three_pairs(self) -> None:
        self.assertEqual(len(PAIRS), 3)
        for pair in PAIRS:
            with self.subTest(pair["growth"]):
                self.assertTrue(pair["growth"].startswith("geo/"))
                self.assertTrue(pair["guide"].startswith("_engine/geo/"))
                self.assertRegex(pair["sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(pair["role"].strip())

    def test_mirror_path_matches_growth_path(self) -> None:
        """兩側路徑必須是同一個相對位置,只差前綴,避免對錯檔案。"""
        for pair in PAIRS:
            with self.subTest(pair["growth"]):
                self.assertEqual(pair["growth"].removeprefix("geo/"),
                                 pair["guide"].removeprefix("_engine/geo/"))

    def test_parity_mode_is_byte(self) -> None:
        self.assertEqual(CONTRACT["parity_mode"], "byte")
        self.assertTrue(CONTRACT["parity_ration"].strip())

    def test_enforcement_rules_are_explicit(self) -> None:
        enforcement = CONTRACT["enforcement"]
        self.assertIn("FAIL", enforcement["authoritative_side_rule"])
        self.assertIn("FAIL", enforcement["mirror_side_rule"])
        self.assertIn("SKIP", enforcement["mirror_absent_rule"])

    def test_limitations_are_stated(self) -> None:
        blob = " ".join(CONTRACT["known_limitations"])
        self.assertIn("gitlink", blob)
        self.assertIn("重新產生", blob)


class AuthoritativeSideTest(unittest.TestCase):
    def test_every_declared_file_exists(self) -> None:
        for pair in PAIRS:
            with self.subTest(pair["growth"]):
                self.assertTrue((_repo_root() / pair["growth"]).is_file(),
                                f"契約指向不存在的檔案:{pair['growth']}")

    def test_hashes_match_the_contract(self) -> None:
        """改了檔案卻沒更新契約 → 這裡 fail,契約不會過期。"""
        for pair in PAIRS:
            path = _repo_root() / pair["growth"]
            with self.subTest(pair["growth"]):
                self.assertEqual(_sha256(path), pair["sha256"],
                                 f"{pair['growth']} 已變更但契約 sha256 未更新")


class MirrorSideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mirror = _mirror_root()
        if self.mirror is None:
            raise unittest.SkipTest(
                "找不到 Guide 鏡像(geo/pages/_engine/geo);隔離 worktree 沒有巢狀站台 repo 屬正常,"
                "但有鏡像時本檢查一定會跑並且會因不同步而失敗")

    def test_mirror_files_exist(self) -> None:
        for pair in PAIRS:
            name = pair["guide"].removeprefix("_engine/geo/")
            with self.subTest(name):
                self.assertTrue((self.mirror / name).is_file(),
                                f"鏡像缺少 {pair['guide']} → 未同步")

    def test_mirror_hashes_match_the_contract(self) -> None:
        for pair in PAIRS:
            name = pair["guide"].removeprefix("_engine/geo/")
            path = self.mirror / name
            if not path.is_file():
                continue
            with self.subTest(name):
                self.assertEqual(_sha256(path), pair["sha256"],
                                 f"{pair['guide']} 與權威副本不同步")

    def test_both_sides_are_byte_identical(self) -> None:
        for pair in PAIRS:
            name = pair["guide"].removeprefix("_engine/geo/")
            growth = _repo_root() / pair["growth"]
            guide = self.mirror / name
            if not (growth.is_file() and guide.is_file()):
                continue
            with self.subTest(name):
                self.assertEqual(growth.read_bytes(), guide.read_bytes(),
                                 f"{name} 兩側 byte 不同")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
