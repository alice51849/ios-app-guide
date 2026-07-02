#!/usr/bin/env python3
"""一鍵:用「我」親自撰寫的內容(零 OpenAI)重生全部 21 個 app 的 AI 指南頁。
  python3 aeo_guide_free_all.py            # 只 render
  python3 aeo_guide_free_all.py --publish  # render + git push + IndexNow
"""
import runpy, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
for m in ("aeo_guide_free_batch1.py", "aeo_guide_free_batch2.py"):
    sys.argv = [m] + (["--publish"] if "--publish" in sys.argv else [])
    runpy.run_path(m, run_name="__main__")
