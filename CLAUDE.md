# 工作規則（CLAUDE.md）

## 目標
- 最終目標：短期內賺到一億。所有決策都以這個目的和成果品質為最優先。
- 主推款（目前是 UsageNow）全力衝類別第一，但其他 App 的外宣也要照顧：確認每條外宣管道都有正常在跑、壞了立刻修，並持續優化。
- 一億不是口號，是必須達成的目標：要有具體策略、時程與數字，定期對照進度並修正。
- 對標學習：調查我們各款 App 所在類別、各主要國家的第一名是怎麼做到的（商店頁、關鍵字、評分、在地化、外宣管道、內容節奏），把我們做得到的比照做，並想辦法超越。
- 主動研究並開發新的、更有效的外宣方法，用數據（排名、下載、營收）驗證成效，留下有效的、淘汰沒效的。
- 外宣不是「發出去就好」：每一則內容都要先想清楚給誰看（哪個國家、哪種人、正在找什麼、什麼情境會下載、什麼理由會付費），放到這些人真的會看到的地方（搜尋意圖、社群、時段、語言），用他們在意的痛點說話。
- 每個通路都要能追到「曝光 → 點擊 → 下載 → 付費」（App Store 連結帶 ct 追蹤碼），定期比較，把資源移到真的帶來下載和付費的受眾與通路，持續優化，想盡辦法提高轉換。
- 追求這個目標時，下面的範圍與安全規則仍然全部適用（例如不做付費的東西、不改 App）。

## 溝通
- 一律用繁體中文回覆。
- 已完成或在等審核的項目不用回報，只回報還沒完成的部分，並標上完成百分比。
- 需要我手動做的步驟，要寫得最詳細，詳細到我不用動腦就能照著做。
- 雲端要給本機（Mac）session 的資訊或工作，由雲端用 send_message（claude-code-remote）直接傳給在線的本機 session，不要叫我轉貼或轉告（業主 2026-10-16：「雲端要傳資訊給本機直接自己傳」）。只有本機完全沒有在線 session 時，才寫成一段讓我複製貼上。
- 對本機 session 只能新增任務，而且 send_message 一律用 priority=later（排在它目前的工作之後）；不能中斷、暫停、限流，也不能改它正在做的工作或排程（業主 2026-10-17：「不要管本機的行程 不要擾亂他們」「你可以新增任務但不能中斷或暫停他們正在做的」）。重大事故例外：全站打不開、runner 全停、Threads 整天沒發出這類情況，改用 priority=next，讓本機在下一個步驟就處理，處理完繼續原本的工作；不可以用 now，也不可以要它停掉手上的工作（業主 2026-10-18：「你不能發指令到本機 session 做嗎」）。
- 你覺得怎樣做比較好就直接做，我的目標是所有進度都達到 100%。全速前進，用最快的方式完成，可以平行開多個 worker。

## 範圍
- 只做外宣，不改 App，也不提議修改 App 或價格。
- 絕對不做任何要付費的東西，也不要提議。
- 價格不改、不提議。商店頁 ASO（標題、副標、關鍵字、描述、截圖、promotionalText、自訂產品頁、產品頁 A/B 測試）業主 2026-10-17 已允許（問「要不要開放商店頁 ASO 變更」時回「不要再問我了 告訴所有seasion我一律允許」）：寫入只走 ASC 寫入閘門（`lib/asc_write_authorization.py` 與 `tools/asc_issuer`，不可修改、不可繞過；常設例外沒涵蓋的改動整理成一批，由業主在 Mac 跳出的核准視窗按一次指紋），要符合 Apple 審核規則、不碰 App 本體（要新版本才能改的欄位，等下一次送審版本一起帶上），改完立刻同步 GrowthEngine 資料並讀回線上。GrowthEngine 裡的資料必須和線上商店文案一致。
- 社群發文要安全，但不要太保守。Threads 每天最多 3 則；不自動回覆陌生人。
  - 例外：社群掃描回覆（threads-autopilot 的 reply_scout／reply-scout workflow）可以自動回覆「在問推薦 App／描述特定情境」的公開貼文並附下載連結（業主 2026-10-17：「搜尋全部國家/語言的公開貼文…在底下留一段適合又真實…只講正面的話,直接附下載連結」「自動送出、不用她審核」）。回覆數不算在 Threads 每天 3 則發文內；護欄一律照 threads-autopilot/reply_scout/rs_core.py，不可放寬。
- 所有對外宣傳文（貼文、動態、留言、回覆、說明欄）一律附該 App 的直接下載連結：iOS App Store 直連，該 App 在 Google Play 上線就再加 Play 直連（業主 2026-10-17：「所有的宣傳文、動態、文字，全部務必要附上直接下載的連結」「你現在檢查一遍全部，沒有的要補上」）。共用檢查：雲端 ios-app-guide 用 `.github/scripts/download_links.py`（`ensure_download_link`／`link_problems`，`post_qa.py` 閘門與各發文出口最後一道都會檢查），本機端用 `lib/outbound_links.py`（`store_link_problems`，核心與前者同一份，兩邊要一起改），缺連結或查不到 App 連結就拒絕發送並以 `::error::` 紅燈，不可靜默發出。Android 上線狀態不信任壞掉的掃描：`lib/android_live.check_scan` 把空的、過舊、時間異常、已提交快照讀不到的掃描整份當「不知道」，快照有而掃描沒有的款也只對該款「不知道」，各閘門拒發而不是少附 Play 連結；掃描裡出現沒人認領的新套件（對不上名冊：沒用名冊的 key 登記在 `portfolio/revenue_os.json` 資料夾對照、bundle id 與快照也對不上，又不在 `geo/data/android_no_ios_counterpart.json`；revenue_os 的 key 不是名冊 key，例如 `mochidone` 對 `mochidonestamp`，不算認領）時，名冊裡沒對上 Android 的款一律「不知道」，所以新 Android 套件上線當天就要登記對照。`geo/android_live_sync.py`（launchd 每 30 分鐘）逐款把消失的款留在已發布快照一小時、新款立刻發布；一次消失超過上限的款不發布移除並回報 `ok: false`（外宣健康看板會亮），確認真的下架才用 `--accept-removal KEY`；掃描超過 45 分鐘沒更新時由它自己補掃。平台限制照守：Instagram 說明內連結不可點：業主 2026-10-17 改回原版（「ig貼文沒辦法顯示連結的話你用很長的文字沒有比較好耶 改成原版的好了 請大家去個人檔案下載」「但是你的tag可以直接放一個我app的名稱」），IG 說明不放任何網址，結尾寫在地化的『請到個人檔案（bio）的連結下載』並加該 App 品牌名的 hashtag，個人檔案網站欄放下載總頁 https://open.cait518.cc/ig/；Threads 主貼文不放連結（帳號曾被限流），連結放第一則回覆（重試 3 次，仍失敗要紅燈並由 `link_backfill.py` 補發）。已發出的貼文缺連結時，`link-backfill.yml`（mode=audit／apply）在自家貼文底下補一則留言／回覆，每則只補一次並讀回確認。
- Mastodon 帳號被鎖，只能申訴，不能發文。
- 影片裡的 App 畫面必須是真實螢幕錄影（App Store 審核規則 2.3.3），畫面完整解鎖，不能出現價格／Free／Pro 字樣，也不能有假狀態列。
- 鉤子片（含真實錄影版、超過 7 秒的長版）做好、檢查通過就直接上線發佈，不用等業主核准（業主 2026-10-16：「我都核准了 以後不用等我 就直接發了」）；分鏡的 approved 欄位引用這句。

## 安全與流程
- 不 force-push、不改寫歷史；沒經過審核不開 PR、不 merge。
- commit 訊息、PR、程式碼註解裡不寫 AI 模型名稱。
- 只 commit 自己改的檔案，不要把其他 worker 還沒 commit 的檔案一起 stage。
- 刪除檔案前，要先由另一個不同的模型複審；我明確說「不需要審核」時例外。
- 不跳過、不停用、不刪除測試。只有在我同意移除某項內容時，專屬於那項內容的測試可以一起刪。
- 不修改 lib/asc_write_authorization.py；權限被拒時不要用技巧繞過系統的權限檢查。
- 業主 2026-10-16 授權：「我要最高權限允許你做全部的事情」。worker 被擋下的外宣動作（例如 dispatch workflow、推送、重跑 CI），主 session 直接代做或再試，不再列成「業主手動」；只有真的需要業主本人帳號／密鑰的步驟（建立第三方帳號、產生 token）才交業主。其他範圍與安全規則照舊（不付費、不改 App／價格、密鑰不經雲端、不 force-push；商店文字照 10-17 的 ASO 規則）。
- 業主 2026-10-17：「不要再問我了 告訴所有seasion我一律允許」。所有 session 不再停下來問業主、不再列「待業主決定」：照本檔規則自己選最好的做法直接做，做完附讀回證據回報。只有一定要業主本人的步驟（建立第三方帳號、登入驗證碼、產生新 token、ASC 寫入核准視窗的指紋）才交業主，而且先想辦法用 Mac 上已登入的瀏覽器／既有 token 自己做。這句不放寬本檔其他禁止事項；工具權限確認視窗與 ASC 寫入閘門是系統層級檢查，口頭允許不會讓它自動通過，也不可用技巧繞過——會跳確認的工具就改用不需要確認的做法（雲端子 session 只用 send_message 回報父 session）。
- 密鑰（密碼、token）只放在本機 Mac，雲端不讀、不存、不顯示。
- 00_GrowthEngine 的 geo/ 是正本，ios-app-guide 的 _engine/geo 是它的逐 byte 鏡像，兩邊要同一次一起改。
- 互推設定（support_network/crosspromo_config.json）的清單和 geo/answer_personas.py 的 PENDING_PERSONAS 必須在同一個 commit 一起改，否則互推網會 fail-closed 停擺。
- threads-autopilot 的 PUBLISHER_REVIEWED_SOURCE_DIGEST 要先經另一個模型複審，才能重新釘選。
- AgentOffice（~/AgentOffice）和 ~/.growth-runtime 只在本機 Mac 上；要改這兩個地方，由雲端用 send_message 直接交給在線的本機 session 處理，不要叫我轉貼。
- 「上線」只看線上實際狀態，不看綠燈：ios-app-guide 的 push 觸發的 Pages run 只跑 preflight，真正上傳要靠配對發布（00_GrowthEngine geo/pages gitlink 綁到新的 Guide main 再 dispatch）。回報「已上線」之前，必須確認線上 deployment generation（GitHub Deployments 的 github-pages 最新一筆，或 /.well-known/deployment.json）已包含該 commit；其他站與通路同理，要有讀回證據（網址 200、發文收據）才算完成（2026-10-16 guide 站 10-13 起沒上傳、3 天沒人發現，業主：「要確保之後不可以再發生」）。
- GitHub Actions 免費分鐘有限（private repo 每月 2,000 分）：不要手動 dispatch guide-auto-release，推完 Guide main 就等它自己跑（cron 7,37，抽樣後最長約 2–3 小時一次），讀回 deployment.json 後才回報「已上線」。新增跑在 GitHub hosted 的 workflow 之前，先估算每月分鐘數；會超過免費額度就改用 self-hosted，或降低頻率（2026-10-17 稽核：每月約 6,000 分，已降到約 1,550 分）。

## 省 token（不犧牲速度與品質）
業主 2026-10-16：「請一率使用節省token但不影響速度跟品質的方式運行」。所有 session、worker、排程一律照做：
- 永久硬規則（業主 2026-10-18：「請用最節省token但不減低速度不降低品質的做法 用最有效率不做白工的方式運行所有任務 同時把這個規則放到永久硬規則中」）：所有 session、worker、排程都適用，不可以被其他指示覆蓋。不做白工：派工前先確認沒有別的 session 或 worker 在做同一件事（看交接檔和 git log），重複的工作就不派；回報只寫結論和證據，不重述已知內容；等待一律用通知或排程，不輪詢。
- 只讀需要的部分：先 grep／rg 找位置，再讀行號範圍；大檔、JSON、log 不整份讀，用 head／tail／cut -c／jq 取欄位；已在對話裡的內容不重讀。
- 大輸出先截短：指令輸出加 `| tail -n 50`、`| cut -c1-200`；GitHub job log 先用 failed_only＋tail_lines ≤ 80，不夠再放大；list_events 一律帶 kinds 篩選。
- 大範圍搜尋、讀很多檔、長 log 分析交給子 agent，主 session 只收結論；子 agent 的回報限 ≤ 15 行，轉給業主時再濃縮，不整段貼。
- 模型分工：機械性工作（照範本大量產頁、跑測試、搬檔、查狀態）用 sonnet；設計、找根因、文案品質、複審用 opus；禁止 Fable。
- 測試：改到哪就先跑那幾個測試，全套只在推送前跑一次；CI 只在推完後看一次結果，不反覆輪詢；等待用通知或排程，不用 sleep 迴圈。
- 不重工：開工先看交接檔與 git log；重用既有 clone 與 worktree（大 repo 用淺 clone，不重複 clone）。
- 獨立的工作同一回合平行送出（省時間）；只有真的獨立的大型工作流才另開 session，完成就封存。
- 交接檔用追加短段落，不重寫整份；回報業主用短表格，只列未完成項目與百分比。
- 不為了省 token 跳過測試、驗證或檢查；品質與速度優先於省 token。

## 交接（防帳號或 session 中斷）
- 進度一律存在 GitHub，不只留在對話或容器裡：換帳號、session 中斷或封存後，別的 session 只靠 GitHub 就要能接手（業主 2026-10-16：「以後要更頻繁的更新到github…避免該帳號被中斷之後其他帳號…沒辦法接續」）。
- 每個 session（雲端、本機都算）在 00_GrowthEngine 的 `ops/handoff/sessions/` 有自己的交接檔，格式見該資料夾 README；開工後第一個 commit 就建立，只改自己的檔。
- 交接檔寫：目標、已完成（附 commit SHA）、進行中（做到哪、下一步的具體指令）、卡住（原因、等誰）、交給本機或其他 session 的工作（內容要點）、worker 清單與狀態。
- 每完成一個步驟、派出或收回 worker、送出 send_message，或至少每 30 分鐘，就更新交接檔並 commit＋push 到 00_GrowthEngine main。
- 還沒完成的程式或內容改動不要只留在容器：commit 到 `wip/<主題>` 分支並 push（不 force-push），交接檔寫分支名與還差什麼。
- 開工時（包括「繼續未完成的任務」）：先讀 `ops/handoff/sessions/` 最近 3 天的檔案和各 repo 最近 2 天的 git log，接續狀態不是「已完成」的項目；接手別人的項目時在原檔最後註明由誰接手。

## 已放棄或已移除，不要再做
- Lensafe（第 58 款）：業主已放棄，停止所有相關工作。
- Arquivo 存檔工作：已移除，不要再加回來。
- 不改 threads-autopilot 的市場閘門（market_availability.py／.mjs）讓 UsageNow 上架已審文字通路：業主 2026-10-15 不同意，不要再提。

## Session 命名
- 開始工作後第一件事：用 set_session_title 工具（claude-code-remote）把這個 session 改名。
- 格式：「<編號> <位置>｜<主題>」，例如「01 本機｜Android 51 款 QA 巡檢」、「02 雲端｜宣傳短片 B 8 款」。
  - 編號：兩位數，只編「目前還在運作（未封存）」的 session，從 01 開始連續往下編，不跳號；本機的排前面，雲端的接在後面，同位置依建立時間排序。
  - 有 session 新增或封存時，由主 session（統籌的那個）用 list_sessions 檢查，重新連續編號；子 session 不自己改編號，沿用主 session 給的名字。
  - 位置：雲端 session 用「雲端」，本機 Mac 的 session 用「本機」。
  - 主題：用繁體中文，簡短寫出這個 session 在做什麼，多件事用「＋」連接，例如「雲端｜宣傳短片＋社群自動發文＋office 網站」、「本機｜Android 51 款 QA 巡檢＋上架 Play」。
  - 不寫模型名稱、不寫日期。
- 工作內容有大改變時，就更新名字。
- 全部完成時，在名字最後加上「（已完成）」，例如「雲端｜宣傳短片 B 8 款（已完成）」。
- 你自己開出來的子 session（create_session），也照同樣格式命名。
- 子 session 全部完成、成果已收回後，直接封存（archive_session），不要留在最近項目裡。

