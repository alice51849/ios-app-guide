#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 一鍵發布 — 重建多語頁 → git commit/push(GitHub Pages)→ IndexNow 推送。

ASO 文案(data/<app>_full.json)更新後,跑這支即可讓全球 LLM 索引更新。可排程。

    python geo/publish.py            # 全量重建+部署+推送
    python geo/publish.py --no-push  # 只重建(不部署/推送)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide")
PY = sys.executable


def run(cmd, cwd=None, env=None):
    print(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip()[-1500:])
    return r.returncode, out


def main():
    env = dict(os.environ, GEO_SITE=SITE)
    # 1) 重建
    run([PY, os.path.join(HERE, "build_pages_i18n.py")], env=env)
    if "--no-push" in sys.argv:
        print("\n(--no-push:略過部署/推送)")
        return
    # 2) git commit + push(用 porcelain 偵測變更,locale 無關)
    run(["git", "add", "-A"], cwd=PAGES)
    _, status = run(["git", "status", "--porcelain"], cwd=PAGES)
    if not status.strip():
        print("內容無變更,略過部署與 IndexNow。")
        print("\n✅ GEO 發布完成(無變更)")
        return
    run(["git", "-c", "user.name=alice51849",
         "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Update multilingual GEO pages"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential",
         "push", "-q", "origin", "main"], cwd=PAGES)
    # 3) IndexNow:有變更才推
    run([PY, os.path.join(HERE, "indexnow_submit.py")], env=env)
    print("\n✅ GEO 發布完成")


if __name__ == "__main__":
    main()
