# 工作規則（ios-app-guide・短版）

**規則正本是 00_GrowthEngine 的 `CLAUDE.md`**（同機器上 `../00_GrowthEngine/CLAUDE.md`，或 GitHub `alice51849/00_GrowthEngine`）；細則在它的 `ops/company/rules_detail.md`、`ops/company/SHARED_RULES.md`。目標、溝通、範圍、送審、外宣、安全、省 token、交接、標題一律照正本，本檔不重抄（正本 8.4）；兩邊不同以正本為準。只在本儲存庫工作、沒掛成長引擎的工作階段，開工先讀正本再動手。讀不到正本時只做唯讀與外宣草稿，並守：不付費、不改價格、不改 App 內容、密鑰不進雲端、不強推、ASC 寫入只走成長引擎 `lib/asc_write_authorization.py`＋`tools/asc_issuer`（不改、不繞過）、Threads 每天最多 3 則，能讀到正本後再上線。

以下只列本儲存庫獨有、仍有效的做法（條號指正本）：

## 下載連結閘門（正本 6.2）
- 雲端出口一律過 `.github/scripts/download_links.py`（`ensure_download_link`／`link_problems`；`post_qa.py` 閘門與各發文出口最後一道都檢查）。核心與成長引擎 `lib/outbound_links.py`（`store_link_problems`）是同一份，兩邊要一起改。缺連結或查不到 App 連結就拒發並 `::error::` 紅燈，不可靜默發出。
- Android 上線狀態照 成長引擎 `lib/android_live.py`（`check_scan`）：空的、過舊、時間異常、已提交快照讀不到的掃描整份當「不知道」；快照有、掃描沒有的款只對該款「不知道」；掃描出現沒人認領的新套件時，名冊裡沒對上 Android 的款一律「不知道」——各閘門拒發，不是少附 Play 連結。新 Android 套件上線當天就要在成長引擎登記對照（`portfolio/revenue_os.json` 資料夾對照或 `geo/data/android_no_ios_counterpart.json`；revenue_os 的 key 不是名冊 key，不算認領）。快照由成長引擎 `geo/android_live_sync.py` 維護，確認真的下架才用 `--accept-removal KEY`。
- Instagram 說明不放網址：結尾寫在地化的「請到個人檔案（bio）的連結下載」並加該 App 品牌名 hashtag；個人檔案網站欄放 https://open.cait518.cc/ig/。
- Threads 主貼文不放連結，連結放第一則回覆（重試 3 次，仍失敗紅燈並由 ios-app-guide `.github/scripts/link_backfill.py` 補發）；已發出缺連結的貼文由 `link-backfill.yml`（mode=audit／apply）在自家貼文底下補一則，每則只補一次並讀回。

## 影片閘門（正本 6.4）
- 只擋兩條：宣稱 App 沒有的功能（對照成長引擎 `data/<key>_full.json` 商店文案）、畫面或字幕出現與商店不符的價格、Free、Pro 字樣。閘門是成長引擎 `shorts/scripts/video_compliance.py`（舊片依 `shorts/legacy_renders.json` 當時分鏡、價格對照 `shorts/store_prices.json`）。商店截圖版照樣排程；鉤子片過閘直接發（分鏡 approved 欄引用業主 10-16「我都核准了 以後不用等我 就直接發了」）。各平台每日上限照現有排程分批。

## 指南站上線與 Actions 分鐘（正本 7.6、7.7、7.8）
- `_engine/geo` 是成長引擎 `geo/` 的逐 byte 鏡像，兩邊同一次改。
- push 觸發的 Pages run 只跑 preflight；真正上傳靠配對發布（成長引擎 `geo/pages` gitlink 綁到新的 Guide main 再 dispatch）。回報「已上線」前確認 `/.well-known/deployment.json`（或 GitHub Deployments 的 github-pages 最新一筆）含該 commit。
- 不手動 dispatch guide-auto-release，推完等它自己跑（cron 7,37，抽樣後最長約 2～3 小時一次）。新增 GitHub hosted 工作流程前先估每月分鐘（private 每月 2,000 分），會超過就改 self-hosted 或降頻。

## 社群
- 平台名稱用官方名稱（Threads、Instagram、Bluesky、YouTube、YouTube Shorts、Telegram、Facebook、TikTok、Reddit、X、Pinterest、LINE、PTT、Dcard），不硬翻（正本 3.1）。
- 社群掃描回覆的護欄照 threads-autopilot `reply_scout/rs_core.py`，不可放寬（正本 6.3）。Mastodon 已依封鎖規則刪除，不再加回。
- 提交、PR、程式碼註解都不寫模型名稱（正本 7.2）。
