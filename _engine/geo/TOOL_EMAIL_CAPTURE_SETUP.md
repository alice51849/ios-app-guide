# Buttondown owned-email：exact47 × Apple official50

## 授權與證據界線

本契約只產生候選內容、驗證同意、計算寄送資格及執行 GET readback。
**沒有寄送／建立 draft／建立 subscriber／自動訂閱／ASC mutation／社群
writer，也不部署或 push main。** `sender_enabled` 固定為 `false`；
`owned_email_sender.plan()` 即使找到合格讀者，也只回 `plan_only`、
`send_allowed=false`、`send_requests=0`。

2026-09-12 新要求：47 款 canonical sellable App × 50 官方 locale，
capture inventory 恰好 **2350** 格；原有五語免費工具通知不可轉作 App 行銷。
來源：Session `2fd0fa72-ea4f-49fe-94ee-f12ec0ac0d6a`，
「新的第5位 live worker／Buttondown capture consent sender readback exact47×50」。

| 證據 | 可以證明 | 不可以證明 |
|---|---|---|
| 原始碼／HTML／表單／HTTP 200 | `content_ready`，且必須綁定內容 digest | 有訂閱者、有人收到信、原生發送 |
| 完整 Buttondown subscriber GET census | 服務商當下名單總量 | `regular` 等於 double opt-in |
| 已驗 HMAC 的 confirmation＋前置 scope＋新鮮 subscriber GET | 特定 App／locale／campaign 的同意資格 | 郵件已寄送或送達 |
| 原生 email ID GET＋其公開 archive URL GET＋完整 body/scope | `buttondown_public_archive_verified` | 指定真人已收到信 |
| queue／workflow success／本機 receipt 的自填旗標 | 無原生發送證據 | 任何 subscriber/delivery 數量 |

未知名單量回 `UNKNOWN`；有證據的 double opt-in／native 數量才可累計。
產生的 content inventory 永遠保持 verified subscribers=0、subscriber total=
`UNKNOWN`、native emails=0，不可把 2350 張表單當成 2350 位訂閱者。

## 內容與同意

- `owned_email_copy.json` 是 50 locale 母語文案唯一來源，包括 email label、
  成人明確同意、Buttondown 處理資料、隱私、取消訂閱及第一方發行者揭露。
  缺語、缺欄或未知 locale 一律 fail closed；沒有英文 fallback。
- 原有 `gen_tool_email_capture.py` 保留 `new_free_tools_v1` scope；
  App 表單使用獨立的 `app_updates_v1`。舊名單不遷移、不擴權、不自動補同意。
- `<locale>/email/<app_key>.html` 一 App × 一 locale × 一 campaign，
  共 2350 張內容契約。**第2輪 production default 為 inactive：實際表單為 0**，
  不是 2350 位讀者，也不是 2350 個已啟用入口。
  另有 50 個語系目錄與 1 個語言入口，不算 capture 格。
  這些偏好頁是 `noindex,follow`，不冒充 2350 篇搜尋內容。
- 表單只收 email 與 scope metadata，使用官方 `metadata__<key>` 欄位。
  唯一的 `metadata__owned_consent=yes` 來自**未預選、required 的 checkbox**。
  沒有 `type=regular`、付費名單、import、JS 自動提交或「訂閱才能用工具」。
- 同意文字的 digest 同時綁 App、locale、campaign、consent version、
  隱私與第一方揭露；不能換文案後沿用舊 receipt。
- Buttondown metadata 是服務商方案功能；沒有實際 GET 回讀完整 metadata
  就不算可用，不能以「表單接受 POST」推論服務商有保存 scope。

## sender eligibility

1. `observe_pending()` 只 GET 真實 `unactivated`、`source=organic` 的表單申請，
   把當時 App／locale／campaign 與信箱雜湊封進私有 HMAC receipt。
2. `confirm_pending()` 只接受官方 `subscriber.confirmed` 的原始 webhook bytes
   及 `X-Buttondown-Signature` HMAC；newsletter／subscriber 必須完全相同。
   再 GET 同一 subscriber：需為 `regular`，且 scope／信箱仍相同。
   不能只看 `regular`，因為 API 可直接建立 regular 而略過 double opt-in。
3. `ConfirmationLedger` 使用 mode `0600` SQLite 與 transaction 防重。
   重送同 event 只回同一 receipt，不重複計數；沒有事前 pending snapshot
   或無法確認 event 身分就保留 blocked，不追溯補造證據。
4. 規劃前再次 GET subscriber；取消訂閱、complaint、bounce、封鎖、移除、
   import／API 自動加入、代購名單、地址變更、scope 改變都失去資格。
   另驗新鮮且完整、經 HMAC 封存的全域／scope suppression 與發送歷史。
5. 每 App／locale／campaign **7 天 cooldown**、每日最多 **100 recipients**、
   每位讀者每日最多 **1 封**。`reserved`／`attempted`／`unknown` 也保守占額，
   不因 timeout 或沒收到 native receipt 就重寄。
6. audience 為空立即 no-op：不讀 key、不查 provider、不寫歷史、不寄信。
   非空名單也只產 plan，不會觸發任何對外 mutation。

Webhook 接收服務、Buttondown 帳號設定與實際寄送均**沒有在本任務啟用**。
不能為了測試建立真人訂閱、要求確認信、註冊 webhook 或發送測試郵件。

## 市場、來源與時效

- `live_app_manifest.json` canonical roster 必須剛好 47 App，Apple 公開 US
  lookup 必須新鮮驗證全部 47；支援市場的公開 lookup 都要有 GET 來源、
  HTTP status、body SHA-256、ID 集合與時戳。
- 50 locale 內容永遠保留。`bn-BD` 依官方市場契約 CTA=`null`、
  conversion campaign=`N/A`；不得補 US、IN 或無國別 URL。
- 其他 49 locale 只用自己的 storefront，強制正確 `pt`／`ct`／`mt`，
  無硬編價格。**正確路由不等於該 App 在該市場可買**：個別 App lookup
  缺項仍保留 capture 內容，但 sender 回 `app_storefront_unverified`，
  不補市場、不把 HTTP 200／0 results 當可寄送。
- `conversion_cells=2303` 是路由格數，不是可寄送人數；另列
  `verified_conversion_cells`／`unverified_conversion_cells` 如實呈現。
- Growth source 與 Guide `_engine/geo` 必須逐檔 SHA-256 一致、各綁完整
  committed Git SHA；dirty source、錯誤 repo／prefix／digest、舊名單或
  超過 24 小時的 availability／inventory 都 fail closed。
  同 repo 的完整 source commit 也必須可由 Git 回讀；shallow checkout 缺物件
  時只能先唯讀 fetch 補齊，不能忽略 provenance Gate。
  subscriber／suppression／native GET 證據必須在 5 分鐘內。

## 隔離候選產生與驗證

先在兩個 feature worktree 同步 source 並 commit，再以只做 Apple 公開
GET 的 fresh availability snapshot 產生候選。不得改 live main worktree。

```bash
python3 geo/gen_owned_email_capture.py \
  --pages-dir <isolated-guide-worktree> \
  --growth-geo <isolated-growth-worktree>/geo \
  --guide-geo <isolated-guide-worktree>/_engine/geo \
  --availability <private-readonly-evidence>/apple-availability.json

python3 geo/gen_owned_email_capture.py \
  --pages-dir <isolated-guide-worktree> --check

python3 -m unittest discover -s geo/tests -p test_owned_email.py
python3 geo/owned_email_readback.py --subscriber-count
```

`--dry-run` 不寫檔；所有指令都不部署、不寄信。
公開 capture readback 指定 `--pages-dir --app --locale`；native readback 另給
`--native-reference`（僅 email ID、公開 archive URL、email body digest）。
有 credentials 才能 GET email ID；沒有就 blocked，不拿公開表單替代。

原有工具表單仍由 `publish.py`／Pages 管線在 hero 封存**之前**注入；
hero 的 `content_digest` 包含展開後的 50 語設定。禁止封存後直接改 hero HTML。
`enabled=false` 或清空 endpoint 仍會移除舊工具區塊；App capture 關閉時
產生器 fail closed，不自行部署或刪除已存在的公開素材。

## 第2輪：production-readiness，不搶 App Store 轉換

2026-09-12 再次獨立檢查上一輪候選：2350 張中，2303 個可轉換市場的
form 全部排在 App Store CTA 之前；五尺寸 × 50 語最長標籤的 250 個
Playwright baseline 中，196 個主 CTA 離開首屏。因此不沿用「content-ready」
作為上線許可，**全 App 同步保持 inactive**，不按轉換結果挑成功 App。
來源：同 Session 第2輪使用者要求「production-readiness Gate／不傷害 App
Store 轉換／不混 shared layout」。

### 非干擾與隱私邊界

- `.oe-core[data-primary-answer]` 包含原產品名稱與主要 App Store CTA，
  永遠先於 capture；active／inactive／rollback 的 core HTML、URL、DOM 順序、
  首屏位置與 hit target 必須一致。bn-BD 不產商店 CTA，保留真實市場說明；
  純 newsletter 契約只談產品資訊，不暗示在孟加拉可下載。
- inactive 頁面不輸出 form、email input、checkbox 或 disabled 假按鈕，
  以 50 語明確說明尚未開放；完整 consent 文案仍保存在 source contract。
  `tool_email_capture.json` 的 `enabled`／`app_capture_enabled` 表示內容能力，
  **不能覆蓋 `owned_email_rollout.json` 的實際啟用策略**。
- 可啟用候選使用原生、預設收合的 `<details>`，只有讀者自選後才展開；
  無 modal、sticky、interstitial、autofocus、預勾、JS submit 或誘導文案。
  寄送確認按鈕為安靜的 secondary control，不能搶主 CTA。
- Owned HTML 不載入產品 JS、pixel、iframe 或外部資產，也不新增
  cookie／storage／beacon；這不冒充 Buttondown 尚未驗證的服務端設定。
  `pt/ct` 只保留既有 Apple 聚合 campaign 歸因，沒有個人 tracking ID。
  email、checkbox、summary、按鈕及連結的有效點擊範圍至少 44 CSS px。
- 既有頁面的 `apply_capture()` 只在最後的核心答案與 App Store CTA 之後注入；
  移除 capture 區塊後，非 capture HTML 必須逐 byte 相同。遇到 ID 衝突或
  找不到安全插入點直接 blocking，不偷偷更動 shared CSS／答案或 CTA。

### 事前固定、對所有 App 公平的 rollout

| stage | locale cohort | 每 App 入口 | 全部入口 |
|---|---|---:|---:|
| inactive（目前） | 無 | 0 | 0 |
| pilot（僅預先規劃） | en-US | 1 | 47 |
| expanded（僅預先規劃） | en-US、zh-Hant、ja、ar-SA | 4 | 188 |
| all（僅預先規劃） | 官方 50 locale | 50 | 2350 |

每個 cohort 必須全部 47 App 一起驗收；禁止挑高轉換、已成功或漂亮的 App
先上。任何一個 blocking 問題都保持整個 cohort inactive。這些表格不是啟用
授權；本輪 release Gate 只接受 active count=0，`activation_ready=false`，
sender 仍永久 no-send，不能因 geometry PASS 自行寄信、訂閱 POST 或部署。

### 可重跑的 browser／a11y／privacy Gate

鎖定 Playwright `1.63.0` 與 axe-core `4.13.0`，依 `package-lock.json`
安裝；瀏覽器與 runtime 只放在 project `.local/`，不使用系統暫存目錄。

```bash
mkdir -p geo/browser-tests/.local/runtime
export TMPDIR="$PWD/geo/browser-tests/.local/runtime"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/geo/browser-tests/.local/browsers"
npm --prefix geo/browser-tests ci --no-audit --no-fund
node geo/browser-tests/node_modules/playwright/cli.js install chromium

python3 geo/owned_email_readiness.py --prepare-geometry <private-fixtures>
node geo/browser-tests/owned-email-geometry.mjs \
  --fixtures <private-fixtures> --output <private-evidence>/geometry.json

python3 geo/owned_email_readiness.py \
  --prepare-compatibility <private-layout-fixtures> \
  --growth-root <isolated-growth> --guide-root <isolated-guide>
node geo/browser-tests/owned-email-compatibility.mjs \
  --fixtures <private-layout-fixtures> --output <private-evidence>/layout.json

python3 geo/owned_email_readiness.py --health-only > <private-evidence>/health.json
python3 geo/owned_email_readiness.py --pages-dir <isolated-guide> \
  --geometry <private-evidence>/geometry.json --health <private-evidence>/health.json \
  --dependencies <private-evidence>/layout.json
```

完整矩陣是 **47 App × 50 locale × 5 viewport = 11750 組**：
`320×568`、`375×667`、`390×844`、`768×1024`、`1024×768`。
每組驗 inactive、active 收合／展開、no-JS 原生操作及 rollback；CLS 實測
23500 次，axe 另驗每語最長 App 名稱 × 5 尺寸 × 2 狀態，共 500 組。
axe violations **及 incomplete** 都 blocking。`--smoke` 只作預檢，
即使全綠也不符合 release Gate 的完整矩陣分母。

No-JS 使用獨立關閉 JS 的 browser context；axe／PerformanceObserver 是
另一個稽核 context 的測量工具，不是產品必要腳本。所有 browser request
一律攔截，任何新外部 request 或 POST 都 blocking，絕不以真實訂閱驗表單。
Buttondown 只 GET form endpoint（可能 302 至公開 profile）及 archive；
導向只允許同一 newsletter 的安全公開 URL。200／302 都不是訂閱或 native
delivery 證據，無法取得真實 census 時保持 `UNKNOWN/0`。

`rollout-manifest.json` 綁 committed source SHA、source／content digest、
完整 case identity、geometry／a11y／no-JS／rollback、5 分鐘內 GET health
與最新 main 的 shared-layout dependency digest。缺例、重複、stale、
錯誤 source、未審查 a11y、非預期 request 或 main 前進都 fail closed。

### Shared-layout 依賴與 rollback

本輪只讀 latest mains 的 `publish.py`、`hero_task_html.py`、
`deployment_generation.py` 與 50 個已存在 App 頁；**不合併或複製其他正在
進行的 shared-layout feature**。目前相容性抽查 250 組：inactive／active
都未改動既有 CTA 順序或 geometry，但既有 main 自身有 51 組主 CTA 不在
首屏，交由 shared-layout owner 的正式整合處理。本 feature 不偷修。
shared-layout 最終 main SHA 改變後必須重跑相容性；Buttondown metadata
保存／signed confirmation intake 尚未有真實證據，也維持 activation blocker。

**Rollback 不是 revert 回上一輪搶 CTA 的頁面。** 固定方法是把 rollout
policy 設為 inactive、commit 配對來源，再用相同 generator 的 `--rollback`
重新產生 owned outputs。只有 capture 被關閉，core／App Store CTA 完整
保留，不刪 consent ledger、不改 App、不部署、不發任何 provider mutation：

```bash
python3 geo/gen_owned_email_capture.py --rollback \
  --pages-dir <isolated-guide> --growth-geo <isolated-growth>/geo \
  --guide-geo <isolated-guide>/_engine/geo --availability <fresh-readonly-availability>
```

## 官方依據（2026-09-12 GET）

- [HTML embed metadata](https://docs.buttondown.com/building-your-subscriber-base#adding-metadata-to-your-subscribers)
- [Metadata 保存與方案](https://docs.buttondown.com/subscriber-metadata)
- [Double opt-in 與 API regular bypass](https://docs.buttondown.com/double-opt-in)
- [Subscriber GET](https://docs.buttondown.com/api-subscribers-retrieve)
- [Confirmation webhook 與 HMAC](https://docs.buttondown.com/api-webhooks-introduction)
- [Email ID／absolute_url／status／body](https://docs.buttondown.com/api-emails-introduction)
- [公開 archive](https://buttondown.com/hourstag/archive/)
- [Buttondown 隱私政策](https://buttondown.com/legal/privacy)
