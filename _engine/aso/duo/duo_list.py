#!/usr/bin/env python3
"""iPhone Duo 驗證清單（ops/company/duo_verified.json）的唯一讀取入口：推廣文字包、精選提名都用這裡。

本機推的格式：{"verified": [...], "needs_duo_run": [...], "not_live": [...]}，每款
{key（本機資料夾名）, asc_app_id, verdict, pass_version, pass_build, live_version, live_build, via, evidence}。
via＝direct：驗證通過的建置就是線上建置；via＝carry_forward：線上建置和通過的建置之間只差版號／字串／測試
（本機逐款比對 git 差異，差異含程式或資源的款放在 needs_duo_run，不在 verified）。

可以宣稱的款（全部要成立）：在 verified、verdict 是 pass、有線上版本與建置號；direct 要 pass_build == live_build；
carry_forward 要附 evidence。名冊 key 與商店英文名用 asc_app_id 對 geo/live_app_manifest.json 取。
needs_duo_run、not_live 一律不宣稱。另一份 duo-verified/v1 草案格式（apps[]）也讀，條件同 ops/company/duo_claim_rules.md。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIED_PATH = ROOT / "ops" / "company" / "duo_verified.json"
MANIFEST_PATH = ROOT / "geo" / "live_app_manifest.json"


def _manifest_by_id(manifest_path):
    try:
        apps = json.loads(Path(manifest_path).read_text(encoding="utf-8")).get("apps", {})
    except (OSError, ValueError):
        return {}
    return {str(v.get("app_id")): (k, v.get("name") or "") for k, v in apps.items() if v.get("app_id")}


def _check_local(entry):
    if entry.get("verdict") != "pass":
        return "verdict_not_pass"
    live_version, live_build = str(entry.get("live_version") or ""), str(entry.get("live_build") or "")
    if not live_version or not live_build:
        return "not_live"
    via = entry.get("via")
    if via == "direct":
        if str(entry.get("pass_build") or "") != live_build or str(entry.get("pass_version") or "") != live_version:
            return "direct_but_pass_build_is_not_live_build"
    elif via == "carry_forward":
        if not entry.get("evidence"):
            return "carry_forward_without_evidence"
    else:
        return f"unknown_via:{via!r}"
    return None


def _check_v1(entry):
    if entry.get("inner_full_screen") is not True:
        return "inner_full_screen_not_verified"
    parts = str(entry.get("sdk") or "").split(".")
    if not all(p.isdigit() for p in parts) or tuple(int(p) for p in parts) < (27, 1):
        return f"sdk_below_27.1:{entry.get('sdk')!r}"
    if not entry.get("live_version") or str(entry.get("verified_version")) != str(entry.get("live_version")):
        return "verified_version_is_not_live_version"
    if not entry.get("live_build") or str(entry.get("verified_build")) != str(entry.get("live_build")):
        return "verified_build_is_not_live_build"
    return None


def load(verified_path=VERIFIED_PATH, manifest_path=MANIFEST_PATH):
    """(apps, rejected, error)。apps：可宣稱的款 [{slug, app_id, app_name, live_version, live_build, via,
    postures, source_key}]；rejected：[{source_key, app_id, reason}]；error：清單讀不了或格式不對（檔不存在＝None）。"""
    path = Path(verified_path)
    if not path.exists():
        return [], [], None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [], [], f"讀不了 {path.name}：{exc}"
    if not isinstance(doc, dict):
        return [], [], f"{path.name} 不是物件"
    if isinstance(doc.get("verified"), list):
        rows, check = doc["verified"], _check_local
        id_of = lambda e: str(e.get("asc_app_id") or "")
        rejected = [{"source_key": e.get("key"), "app_id": id_of(e), "reason": group}
                    for group in ("needs_duo_run", "not_live") for e in (doc.get(group) or []) if isinstance(e, dict)]
    elif doc.get("schema") == "duo-verified/v1" and isinstance(doc.get("apps"), list):
        rows, check = doc["apps"], _check_v1
        id_of = lambda e: str(e.get("app_id") or "")
        rejected = []
    else:
        return [], [], f"{path.name} 格式不認得（要有 verified 清單，或 schema duo-verified/v1 的 apps）"
    by_id = _manifest_by_id(manifest_path)
    apps, seen = [], set()
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        app_id = id_of(entry)
        reason = check(entry) or (None if app_id in by_id else "app_id_not_in_live_app_manifest")
        if reason is None and app_id in seen:
            reason = "duplicate_app_id"
        if reason:
            rejected.append({"source_key": entry.get("key"), "app_id": app_id, "reason": reason})
            continue
        seen.add(app_id)
        slug, name = by_id[app_id]
        apps.append({
            "slug": slug, "app_id": app_id, "app_name": entry.get("app_name") or name,
            "live_version": str(entry["live_version"]), "live_build": str(entry["live_build"]),
            "via": entry.get("via", "direct"), "postures": list(entry.get("postures") or []),
            "source_key": entry.get("key"),
        })
    return apps, rejected, None


if __name__ == "__main__":
    ok, bad, err = load()
    print(json.dumps({"claimable": len(ok), "rejected": bad, "error": err,
                      "slugs": sorted(a["slug"] for a in ok)}, ensure_ascii=False, indent=1))
