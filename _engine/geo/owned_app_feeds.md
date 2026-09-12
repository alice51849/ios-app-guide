# 自有 App feeds：同代來源與零重送契約

`owned_app_feeds.py` 只讀 canonical live roster、50 語原生外宣來源與
`api/v1/ios-app-catalog`，不呼叫 ASC、不修改 App、不發社群或 IndexNow。
目前 **47 App × 50 locale = 2,350 entries、150 RSS／Atom／JSON feeds**。
這些是 Lumi Studio 的第一方產品資訊，**不是獨立排行榜**。

## 來源與公開格式

- 每個官方 locale 都有 `/<locale>/rss.xml`、`feed.xml`、`feed.json`；
  三格式共用 `urn:lumi:app-store:<id>:locale:<locale>`，canonical 指向同語 App 頁。
- JSON Feed 1.1 同時提供 `content_text`、`content_html`、`date_published`、
  `date_modified`。Atom／RSS 的 ID、全文、日期、purchase model 與 disclosure
  必須逐項等價。13 款付費下載、34 款免費起用搭配一次性解鎖；禁止假免費或硬編金額。
- `feeds/owned-apps.json` 綁定 roster、catalog 內容 digest、source hashes、
  全部 feed bytes 與 MIME。HTTP 容許對應 feed MIME 及 GitHub Pages 的
  `application/xml`／`application/json`；HTML、錯誤 charset、錯誤 bytes 一律拒絕。
- `feeds/index.html` 提供 50 語入口；locale 首頁 head 只加入具名、冪等的 discovery block。
  `sitemap_owned_feeds.xml` **只包含自己的 150 feeds 與訂閱目錄**。
  全域 sitemap stamper 不得改寫其 item-derived lastmod；其他 sitemap 日期保留原值。

## bn-BD 不是商店 fallback

依 `market_availability.py` 的 Apple 一手證據，bn-BD 保留 **47 筆孟加拉文內容**，
並攜帶精確 `MARKET_UNAVAILABLE_OR_UNVERIFIED` /
`MARKET_NOT_IN_APPLE_MEDIA_SERVICES` state、reason、evidence。
三格式都不含任何 App Store URL、price、currency、storefront facts 或可買 CTA；
不得補 `/bd/`、`/in/`、`/us/` 或無國別 URL。商品 purchase model 只描述產品契約，
不宣稱孟加拉可購買。市場狀態 `publishable=false`、`facts_allowed=false`、
`outbox_count=0`；三份 bn-BD feed 不廣告 hub、不送通知。其他 **49 語／147 feeds** 正常。

### App 層級的中國市場 N/A

2026-09-12 的公開 `lookup country=cn` 對 Lumi Letters、Lumi Math、
Lumi Math Pro、Trip Planet 四個精確 App ID 均未返回商品；同批控制商品
AI Brief 正常返回 `/cn/`，不能把 App 未返回誤稱中國沒有 App Store。
`market_availability.UNAVAILABLE_APP_MARKETS` 保存這四個有證據的例外，
不影響其他 App 或這四款的其他可驗證市場。未返回者的 catalog、
owned feeds、install records 與既有中文頁保留內容／GUID／canonical，
但 App Store CTA 為 N/A、沒有價格 facts、`outbox_count=0`；禁止
countryless／US fallback。中國可售商品仍由 `locale_storefronts.json`
與公開快照路由到 `cn`。50 個 locale、150 feeds 與 2,350 entries 不減少。

Lumi Math Pro 的完整課程 persona 另以 `answer_owner=lumimathpro` 固定
付費完整版本身分；`free_first_ownership` 不得再用泛用品類配對覆寫它。
既有 root answer 與 localized counterpart 都指向 `6776958488`；
免費 Lumi Math 仍是 `6778269699`，其他免費門規則不變。

## 同代與不 churn

- 正常 `portfolio_app_catalog_api.py` CLI 在 catalog 後生成 owned feeds。
  `--refresh-catalog` 也呼叫同一正常 catalog builder，無測試捷徑、fixture 覆蓋或網路 mutation。
- 逐語 gate 驗 native script／跨 script、母語 source 與 catalog 的 name／summary 精確一致、
  App ID、買斷邊界、attributed storefront、catalog digest 與 exact roster；
  Kannada 不能因有一個 Kannada 字而通過混入簡中的句子。
- 全部候選先在記憶體驗證，再逐檔原子替換，**manifest 最後寫入**。
  中途退出或 stale catalog 會讓 `--check`／上傳／通知全部 fail closed。
- 無內容改變時重跑與跨日的 **bytes、mtime、item dates 都不變**。
  日曆、快照觀測時間、Git SHA 與 workflow run ID 都不更新 item 日期。
  真正改變的單一 item 只更新自己的 `date_modified`，`date_published` 與 ID 永久保留。
  僅來源程式變更只更新 manifest 的來源證據，不重寫未變更的 feed。
- Daily 的兩個 commit 前及兩個 remote-first/rebase repair 路徑都重建 catalog + feeds 並檢查；
  catalog、feeds、source 與 inventory 必須在同一 commit。Pages upload 另比對外部 Growth source。

## Durable notification outbox

`owned_feed_delivery.py prepare` 只做 GET readback 與本機狀態保存；
`notify` CLI **必須明確帶 `--execute`**。預設不會發送。

- 第2輪 state 使用 `lumi.owned-feed-delivery/v3`；每個 provider × topic × attempt
  以不可變 `lumi.owned-feed-receipt/v1` 保存，規格為 `owned_feed_receipt.schema.json`。
  `intent_id` 綁定 protocol／endpoint／topic／feed content SHA，與每日 run／日期無關。
  每份 receipt 保存 request generation、feed generation／feed SHA、Guide source SHA、
  Growth engine SHA、deployment SHA、inventory SHA、完整表單 request body／SHA，
  以及 HTTP status、原始 ACK body／SHA、observed_at、Retry-After 與錯誤類型。
- WebSub `204`（空 body）及合法 `200/202`，或 rssCloud `200` 且 JSON/XML
  明確 `success=true`，**只代表 publisher accepted ACK**。
  `subscriber_delivery_verified=false`、`indexing_verified=false` 永遠保留；
  不可用 workflow success、HTTP 2xx 或先前 run 的成功宣稱 subscriber delivery／索引。
- Outbox 同時綁定完整 Guide SHA、既有 `deployment_generation.validate_binding`、
  feed manifest、每個 topic SHA-256；通知前 GET 驗證 **全部 feeds**（含不通知的 bn-BD）
  與部署 generation，並再讀 generation 防中途切代。Partial deploy 一律零 POST。
- ACK 以 `(protocol, endpoint, topic, content hash)` 去重，不以 commit／日期去重。
  無內容更新重跑或換 source SHA 都是 **0 通知**；未 ACK 的 pending 可恢復。
  既有 54 legacy topics 也納入相同 outbox，其中 bn-BD decision feed 不通知。
- `accepted` 只指向**目前完整 generation**仍適用的 receipt。source／deployment／feed SHA
  漂移即使舊 receipt 失效，`records` 仍保留不可變歷史；相同 feed bytes 的歷史 ACK
  只用於 **content deduplication**，絕不偽裝成目前 generation 的新 ACK。
  `new_notification_intents` 與 `retry_intents` 分開：重跑只重試缺少 ACK 的 provider/topic，
  不新建相同內容意圖。v2 未綁定的舊狀態保留於 `legacy_history`，不當成有效 receipt。
- 一個 owner 持有非阻塞 `flock`；mode `0600` 的原子 state 每收到 ACK 立即保存。
  hub 交錯批次，每批至多3次嘗試，指數退避／Retry-After 上限300秒，
  每 provider 90秒軟預算；單一故障不阻塞其他 provider。
  request 開始前保存 in-flight journal；ACK 落盤後才開始下一批。
  state 以 revision＋previous-state SHA＋state digest 封存，fsync 檔案與父目錄；
  crash 若發生在 ACK 已 fsync、尚未 rename，下一 owner 只接回唯一可驗證的直接後繼。
  若只有 in-flight、沒有持久化 ACK，只記 `indeterminate` 後有界重試，不能宣稱
  分散式 exactly-once 或憑空補出 ACK。
- Pages workflow 在 artifact prune 前保存執行器；`.github/owned-feed-runtime/`
  （state 及可恢復 staging journal）由 Actions cache 恢復且失敗後仍保存，
  不進 git 或 Pages artifact。repo 只收 schema、程式與明確 `fixture=true` 範例；
  fixtures 永遠不能作為真實 ACK authorization。
  整合驗證只用 mocked GET/provider，不實際通知 WebSub、rssCloud 或 IndexNow。

## 離線驗證與配對交付

### 第3輪：先對帳 production，缺 cache 不等於內容有變

`owned_feed_public_capture.py` 以至多每秒一次的 GET 讀取 exact 150 endpoints，
不跟隨 redirect，並在前後讀取、驗證同一份 production deployment generation。
`owned_feed_reconciliation.py` 再驗 HTTP、Content-Type、UTF-8、body hash、
47 GUID／locale、日期、canonical、完整內容與 first-party metadata；
404、redirect、錯 MIME／GUID／日期或 hash 都不能算公開 feed 覆蓋。

343 是147個可通知 topics × 兩個 WebSub providers ＋49個 RSS topics 的
**候選 provider/topic 分母**，不是觀察到的343次內容變更。對帳必須逐項分類：

- `endpoint_not_live`：未公開或 wire contract 無效；不建立 notification intent。
- `content_changed`：已公開且 valid，但與候選語意不同；只列為 release-held 意圖。
- `missing_ack`：語意相同、沒有可用 provider ACK；body hash 相同仍不算 ACK。
- `stale_generation`：有真實歷史 ACK，但 topic／provider／feed hash 或完整
  Guide／Growth／deployment／generation binding 已不相符；保留歷史，不升格 current。
- `already_acked_current`：有效 private durable receipt 的全部 binding 精確符合
  production，且已有 candidate/public semantic-equivalence proof，才可遷移 current。

語意 proof 固定使用 `lumi.owned-feed-semantic-equivalence/v1`，保留 GUID、
canonical、title、summary、全文及 publisher／purchase／market metadata；
只排除日期與衍生 item digest。proof 同時保存兩邊 body SHA 與 semantic SHA，
**不以 workflow success、歷史 HTTP 摘要或 public body hash 冒充 provider ACK**。
只接受既有 notifier 維護、mode0600且有完整 state／receipt checksum 的 durable state；
裸 receipt、未封存摘要、v2不完整狀態及 mock／fixture 均不得作為 current ACK。
這是本機已保存 wire observations 的一致性驗證，不是 provider 數位簽章。

Importer 只寫新指定的隔離 state；migration ID 綁定 production、候選 bytes、
觀察結果與歷史來源。相同輸入重跑連 bytes／mtime 都不變，不同輸入不得覆蓋舊遷移。
沿用v3原子0600、前一 state SHA與可恢復 staging journal，原始歷史保留。
**所有輸入結果都設 `release_hold=true`，locale/layout release 前不可通知。**
CLI 缺 state／缺 production migration 時直接 fail closed，不再把空 runner cache
當作343個新內容事件；import 本身不授權 release、部署或解除 hold。

```sh
python3 geo/owned_feed_public_capture.py --pages-dir <Guide-feature> --output-dir <private-capture>
python3 geo/owned_feed_reconciliation.py --pages-dir <Guide-feature> \
  --capture-dir <private-capture> --history-state <private-durable-state> \
  --report <private-report.json> --import-state <new-private-held-state.json>
```

不存在有效歷史 state 時省略 `--history-state`，不得拿測試 fixture 補位。
Capture／plan／真實 receipts／migration state 全部留在私有 evidence，不進 repo。

### 第4輪：單次公開部署，provider release 仍上鎖

`notification_policy.json` 是本次部署的單一通知政策，固定
`notification_release_hold=true`，同時涵蓋 WebSub、rssCloud、IndexNow。
`notification_release.py` 在四個 CLI 的 inventory／readback／state準備／POST之前
返回 typed hold outcome；`provider_intents=0`、`provider_requests=0`、
`accepted_ack=0`，不把 held／workflow success 算作 ACK 或 indexed。
既有測試與 workflows 保留；IndexNow後續workflow照樣測試、保存held outcome，
但不提交URL。本輪沒有解除migration hold或授權任何手動provider通知。

Pages 在hold期間只接受明確 `owned_feed_release=true`、
`incremental_high_intent=true`、`notification_release_hold=true` 及精確配對
Guide/Growth SHA的單次dispatch作upload；自動事件可跑preflight但不另行部署。
保留完整來源／preservation Gates，且第一個 deploy action 失敗時不盲目建立第二次部署。

`owned_feed_release.py seal` 在同代 catalog／feed Gate通過後產生
`.well-known/owned-feed-release.json`，綁定實際deployment generation、
Guide/Growth來源、catalog digest、150份feed hashes、2,350 entries及hold。
`verify` 在 owned host及GitHub Pages origin各自GET完整150份feed，驗200、MIME、
UTF-8、無redirect、parse／GUID／日期／canonical及exact bytes，再重讀同一release
manifest防中途換代。只有雙host均150/150才標記技術readback PASS；
下一步eligibility仍為 `dispatch_authorized=false`，需另次明確通知release授權及
新的production ACK對帳。404／partial／任何不一致都保持hold，不能靠重送provider解決。

```sh
python3 geo/owned_app_feeds.py --pages-dir <Guide-feature> --refresh-catalog
python3 geo/owned_app_feeds.py --pages-dir <Guide-feature> --check \
  --reference-source <Guide-feature>/_engine/geo
OWNED_FEED_GUIDE_ROOT=<Guide-feature> python3 -m unittest -q \
  geo.tests.test_owned_app_feeds geo.tests.test_owned_feed_delivery
python3 -m unittest -q geo.tests.test_owned_feed_receipts
python3 -m unittest -q geo.tests.test_owned_feed_reconciliation
python3 -m unittest -q geo.tests.test_notification_release geo.tests.test_owned_feed_release
python3 geo/owned_feed_pair_gate.py --growth <Growth-feature> --guide <Guide-feature>
```

測試工作檔只放 checkout 內 `.owned-feed-test-work/` 並由 producer 清理。
配對 Gate 檢查最新 fetched mains 的 ancestry、乾淨 feature branches、精確 Guide gitlink、
source／tests／文件 parity，以及生成零差異。**舊候選不能作基線，也不能把 gitlink 倒退。**
已有當次 main 整合授權時，可在 `main` 或全新 detached worktree 使用
`--integration`；仍強制 fetched-main ancestry、乾淨來源、精確 gitlink、
完整 parity 與重生零差異，不鬆動任何內容或通知 Gate。

交付先推 Guide feature，再推指向它的 Growth feature；不 push main、不 dispatch deployment。
日後由整合者協調 **Growth source → Guide → Growth 最終 gitlink**，以成對來源封閉整合窗口，
更新後重新 fetch、必要時 rebase、重跑本 Gate；不得 force-push 或以舊 Guide pin 蓋掉新 main。
本 feature 交付本身不授權任何 production deployment 或通知。
