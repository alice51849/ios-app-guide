#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""發布前新鮮度閘門：只准用「跟主線一致」的程式與資料推指南站。

2026-10-19 11:50Z 指南站提交 4bce9c82 用過期的產生器輸出，把 21 款×50 語頁面
退回改版前文案、sitemap 2701→1101、加回已退役的 Zodira 頁。geo/publish.py 與
new_app_catchup.py 都會推指南站，所以兩支的入口都先過這一關：

1. 先 git fetch 兩個 checkout（00_GrowthEngine 與 geo/pages 指南站）。
2. 00_GrowthEngine 的 HEAD 必須等於 origin/main；只落後、而且落後的提交完全
   不碰會影響輸出的路徑（交接檔、報表、說明文件、geo/pages 子模組指標）才放行。
   有本機獨有提交（超前或分歧）一律擋。
3. 00_GrowthEngine 不可有會影響輸出的未提交修改或未追蹤檔。
4. data/*_full.json 必須逐檔與 origin/main 相同（雜湊比對，多一檔少一檔都擋）。
5. 指南站 HEAD 必須等於 origin/main；未提交修改只允許 _engine/ 鏡像檔（內容
   必須與 00_GrowthEngine origin/main 的同名檔逐 byte 相同）與兩個每輪重產的
   App Store 狀態快照。publish.py 用 git add -A，所以其他未追蹤檔也擋。

不一致就停止：不修復、不推送，寫紅燈警報檔（預設
~/AgentOffice/deep_qa/state/GUIDE_PUBLISH_GUARD/ALERT.txt，可用
GUIDE_PUBLISH_GUARD_ALERT_DIR 改），並在 GitHub Actions 印 ::error::。
警報檔不會自動清除，查明原因後由處理的人移走。

單獨執行（只檢查、不寫警報）：python geo/publish_freshness_guard.py [--pages DIR]
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

BLOCKED_RETURNCODE = 3

# 落後的提交只動到這些路徑時，輸出不會變，可以放行。
NON_OUTPUT_PREFIXES = (
    "ops/",
    "reports/",
    "docs/",
    "agent/reports/",
    "geo/pages",  # 子模組指標：指南站本身另外直接比對 origin/main
)
NON_OUTPUT_SUFFIXES = (".md",)

# 指南站 checkout 裡每輪由 publish 自己向 Apple 重查後覆寫的快照。
GUIDE_REGENERATED_SNAPSHOTS = (
    ".appstore_live_state.json",
    ".appstore_storefront_state.json",
)
GUIDE_MIRROR_PREFIX = "_engine/"

DEFAULT_ALERT_DIR = "~/AgentOffice/deep_qa/state/GUIDE_PUBLISH_GUARD"

# 指南站 repo 內的 _engine 鏡像：由同一個 checkout 的指南站主線提供，天然最新，
# 而且本身不是 git checkout。只有完全確定是這種情況才跳過；判斷不了照舊擋。
GUIDE_REPO_SLUG = "alice51849/ios-app-guide"
GUIDE_MIRROR_DIRNAME = "_engine"


class PublishFreshnessBlocked(RuntimeError):
    returncode = BLOCKED_RETURNCODE

    def __init__(self, problems, alert_path=None):
        self.problems = list(problems)
        self.alert_path = alert_path
        lines = "\n".join(f"  - {problem}" for problem in self.problems)
        where = f"\n紅燈警報檔：{alert_path}" if alert_path else ""
        super().__init__(
            "發布前新鮮度閘門擋下（不推送、不修復）：\n" + lines + where
        )


def _git(repo, *args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=str(repo), text=True,
        capture_output=True, check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args[:3])} 失敗（exit {result.returncode}）"
        )
    return result


def _out(repo, *args):
    return _git(repo, *args).stdout.strip()


def default_fetch(repo):
    """Authenticated bounded fetch when available, plain git fetch otherwise."""
    engine_agent = Path(__file__).resolve().parents[1] / "agent"
    if str(engine_agent) not in sys.path and engine_agent.is_dir():
        sys.path.insert(0, str(engine_agent))
    try:
        from growth_git_fetch import fetch_main
    except ImportError:
        fetch_main = None
    if fetch_main is not None:
        fetch_main(cwd=str(repo))
        return
    _git(repo, "-c", "fetch.recurseSubmodules=no", "fetch", "--quiet", "origin", "main")


def affects_output(path):
    if any(path == p or path.startswith(p.rstrip("/") + "/") or path == p.rstrip("/")
           for p in NON_OUTPUT_PREFIXES):
        return False
    return not path.endswith(NON_OUTPUT_SUFFIXES)


def _is_toplevel(repo):
    result = _git(repo, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        return False
    return Path(result.stdout.strip()).resolve() == Path(repo).resolve()


def _origin_is_guide_repo(repo):
    result = _git(repo, "remote", "get-url", "origin", check=False)
    if result.returncode != 0:
        return False
    url = result.stdout.strip().lower()
    if url.endswith(".git"):
        url = url[:-4]
    url = url.rstrip("/")
    return url.endswith("/" + GUIDE_REPO_SLUG) or url.endswith(":" + GUIDE_REPO_SLUG)


def guide_mirror_reason(engine):
    """Return why `engine` is certainly the _engine mirror inside an
    ios-app-guide checkout, or None when that cannot be established."""
    engine = Path(engine).resolve()
    if engine.name != GUIDE_MIRROR_DIRNAME or _is_toplevel(engine):
        return None
    guide = engine.parent
    if not (engine / "geo" / "publish_freshness_guard.py").is_file():
        return None
    if not _is_toplevel(guide) or not _origin_is_guide_repo(guide):
        return None
    tracked = _git(
        guide, "ls-files", "--error-unmatch", "--",
        f"{GUIDE_MIRROR_DIRNAME}/geo/publish_freshness_guard.py", check=False,
    )
    if tracked.returncode != 0:
        return None
    return (
        f"{engine} 是指南站 repo（{GUIDE_REPO_SLUG}）內追蹤的 _engine 鏡像，"
        "由同一個 checkout 的指南站主線提供，不是本機 00_GrowthEngine checkout"
    )


def _fetch(repo, label, fetch, problems):
    try:
        fetch(repo)
    except Exception as error:  # noqa: BLE001 - any fetch failure is fail-closed
        problems.append(
            f"{label} 無法 git fetch origin main，不能確認是否為最新"
            f"（{type(error).__name__}）"
        )
        return False
    if _git(repo, "rev-parse", "--verify", "-q", "origin/main", check=False).returncode != 0:
        problems.append(f"{label} 沒有 origin/main 可比對")
        return False
    return True


def _alignment(repo, label, problems, *, allow_harmless_behind):
    head = _out(repo, "rev-parse", "HEAD")
    remote = _out(repo, "rev-parse", "origin/main")
    if head == remote:
        return head, remote
    counts = _out(repo, "rev-list", "--left-right", "--count", f"{head}...{remote}").split()
    local_only, behind = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
    if local_only:
        state = "分歧" if behind else "超前"
        problems.append(
            f"{label} 與 origin/main {state}：本機獨有 {local_only} 個提交、"
            f"落後 {behind} 個（HEAD {head[:12]}，origin/main {remote[:12]}）"
        )
        return head, remote
    changed = [
        line for line in _out(repo, "diff", "--name-only", head, remote).splitlines() if line
    ]
    output_paths = [path for path in changed if affects_output(path)]
    if not allow_harmless_behind or output_paths:
        sample = "、".join(output_paths[:8]) or "（任何落後都不允許）"
        problems.append(
            f"{label} 落後 origin/main {behind} 個提交，影響輸出的路徑："
            f"{sample}（HEAD {head[:12]}，origin/main {remote[:12]}）"
        )
    return head, remote


def _engine_worktree(engine, problems):
    dirty = []
    # 不可 strip：porcelain 第一欄可能是空白（" M path"）。
    for line in _git(
        engine, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=all",
    ).stdout.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if affects_output(path) and "/__pycache__/" not in f"/{path}":
            dirty.append(f"{line[:2].strip() or '?'} {path}")
    if dirty:
        problems.append(
            "00_GrowthEngine 有會影響輸出的未提交修改或未追蹤檔："
            + "、".join(dirty[:8]) + (f" 等 {len(dirty)} 個" if len(dirty) > 8 else "")
        )


def _blob(repo, path):
    return _out(repo, "hash-object", "--", str(path))


def _blobs(repo, paths):
    paths = [str(path) for path in paths]
    if not paths:
        return []
    result = subprocess.run(
        ["git", "hash-object", "--stdin-paths"], cwd=str(repo), text=True,
        input="\n".join(paths) + "\n", capture_output=True, check=False,
    )
    hashes = result.stdout.split()
    if result.returncode != 0 or len(hashes) != len(paths):
        raise RuntimeError("git hash-object --stdin-paths 失敗")
    return hashes


def _data_matches_main(engine, problems):
    main = {}
    for line in _out(engine, "ls-tree", "origin/main", "data/").splitlines():
        meta, _, path = line.partition("\t")
        name = path.rsplit("/", 1)[-1]
        if name.endswith("_full.json"):
            main[name] = meta.split()[2]
    data_dir = Path(engine) / "data"
    items = sorted(data_dir.glob("*_full.json")) if data_dir.is_dir() else []
    local = dict(zip((item.name for item in items), _blobs(engine, items)))
    mismatched = sorted(
        name for name in set(main) | set(local) if main.get(name) != local.get(name)
    )
    if mismatched:
        detail = []
        for name in mismatched[:8]:
            if name not in local:
                detail.append(f"{name}（本機缺）")
            elif name not in main:
                detail.append(f"{name}（主線沒有）")
            else:
                detail.append(f"{name}（內容不同）")
        problems.append(
            f"data/*_full.json 與 origin/main 不一致 {len(mismatched)} 檔："
            + "、".join(detail)
        )


def _guide_worktree(pages, engine, problems):
    blocked = []
    # 不可 strip：porcelain 第一欄可能是空白（" M path"）。
    for line in _git(
        pages, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=all",
    ).stdout.splitlines():
        if not line:
            continue
        code, path = line[:2], line[3:]
        if " -> " in path:
            blocked.append(f"{code.strip()} {path}")
            continue
        path = path.strip('"')
        if path in GUIDE_REGENERATED_SNAPSHOTS:
            continue
        if path.startswith(GUIDE_MIRROR_PREFIX) and "D" not in code:
            relative = path[len(GUIDE_MIRROR_PREFIX):]
            expected = _git(engine, "rev-parse", "-q", "--verify", f"origin/main:{relative}", check=False)
            if expected.returncode == 0 and expected.stdout.strip() == _blob(pages, Path(pages) / path):
                continue
            blocked.append(f"{code.strip()} {path}（與 00_GrowthEngine 主線不同）")
            continue
        blocked.append(f"{code.strip() or '?'} {path}")
    if blocked:
        problems.append(
            "指南站 checkout 有不該帶進發布的未提交修改或未追蹤檔："
            + "、".join(blocked[:8]) + (f" 等 {len(blocked)} 個" if len(blocked) > 8 else "")
        )


def check(engine_root, pages_root, *, fetch=default_fetch):
    """Return (problems, facts). Empty problems means the publish may proceed."""
    engine = Path(engine_root).resolve()
    pages = Path(pages_root).resolve()
    problems, facts = [], {"engine": str(engine), "pages": str(pages)}
    try:
        _check(engine, pages, fetch, problems, facts)
    except Exception as error:  # noqa: BLE001 - an unverifiable tree is fail-closed
        problems.append(f"新鮮度檢查本身失敗，無法確認（{type(error).__name__}: {error}）")
    return problems, facts


def _check(engine, pages, fetch, problems, facts):
    if not _is_toplevel(engine):
        reason = guide_mirror_reason(engine)
        if reason:
            facts["guide_mirror"] = reason
            return
        problems.append(f"00_GrowthEngine 不是獨立 git checkout：{engine}")
        return
    if not _is_toplevel(pages):
        problems.append(f"指南站不是獨立 git checkout：{pages}")
        return
    if _fetch(engine, "00_GrowthEngine", fetch, problems):
        facts["engine_head"], facts["engine_origin"] = _alignment(
            engine, "00_GrowthEngine", problems, allow_harmless_behind=True,
        )
        _engine_worktree(engine, problems)
        _data_matches_main(engine, problems)
        engine_ok = True
    else:
        engine_ok = False
    if _fetch(pages, "指南站", fetch, problems):
        facts["pages_head"], facts["pages_origin"] = _alignment(
            pages, "指南站", problems, allow_harmless_behind=False,
        )
        if engine_ok:
            _guide_worktree(pages, engine, problems)


def write_alert(problems, facts, caller, alert_dir=None):
    directory = Path(
        alert_dir or os.environ.get("GUIDE_PUBLISH_GUARD_ALERT_DIR") or DEFAULT_ALERT_DIR
    ).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {"at": now, "caller": caller, "problems": problems, **facts}
    alert = directory / "ALERT.txt"
    text = (
        f"🔴 指南站發布前新鮮度閘門擋下（{now}，{caller}）\n"
        f"engine={facts.get('engine')} HEAD={str(facts.get('engine_head', '?'))[:12]} "
        f"origin/main={str(facts.get('engine_origin', '?'))[:12]}\n"
        f"pages={facts.get('pages')} HEAD={str(facts.get('pages_head', '?'))[:12]} "
        f"origin/main={str(facts.get('pages_origin', '?'))[:12]}\n"
        + "".join(f"- {problem}\n" for problem in problems)
        + "沒有推送任何東西。查明原因、讓工作目錄對齊主線後，把這個檔案移走再重跑。\n"
    )
    temporary = alert.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(alert)
    with open(directory / "blocks.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return alert


def require_fresh(engine_root, pages_root, *, caller, fetch=default_fetch, alert_dir=None):
    problems, facts = check(engine_root, pages_root, fetch=fetch)
    if not problems and facts.get("guide_mirror"):
        print(
            f"ℹ️ 新鮮度閘門跳過（{caller}）：{facts['guide_mirror']}；"
            "本機 00_GrowthEngine checkout 照常檢查"
        )
        return facts
    if not problems:
        print(
            f"✅ 新鮮度閘門通過（{caller}）：00_GrowthEngine {str(facts.get('engine_head'))[:12]}、"
            f"指南站 {str(facts.get('pages_head'))[:12]} 與 origin/main 一致"
        )
        return facts
    try:
        alert = write_alert(problems, facts, caller, alert_dir=alert_dir)
    except OSError as error:
        alert = None
        print(f"⚠️ 紅燈警報檔寫不進去（{type(error).__name__}），仍然擋下", file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::error::指南站發布前新鮮度閘門擋下（{caller}），未推送；見 {alert}")
    raise PublishFreshnessBlocked(problems, alert)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    here = Path(__file__).resolve().parent
    pages = Path(os.environ.get("GEO_PAGES", here / "pages"))
    if "--pages" in args:
        pages = Path(args[args.index("--pages") + 1])
    problems, facts = check(here.parent, pages)
    for problem in problems:
        print(f"- {problem}")
    if facts.get("guide_mirror"):
        print(f"跳過：{facts['guide_mirror']}")
    print("OK" if not problems else f"BLOCKED（{len(problems)} 項）")
    return 0 if not problems else BLOCKED_RETURNCODE


if __name__ == "__main__":
    raise SystemExit(main())
