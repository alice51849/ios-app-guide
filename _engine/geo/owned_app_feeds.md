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

```sh
python3 geo/owned_app_feeds.py --pages-dir <Guide-feature> --refresh-catalog
python3 geo/owned_app_feeds.py --pages-dir <Guide-feature> --check \
  --reference-source <Guide-feature>/_engine/geo
OWNED_FEED_GUIDE_ROOT=<Guide-feature> python3 -m unittest -q \
  geo.tests.test_owned_app_feeds geo.tests.test_owned_feed_delivery
python3 -m unittest -q geo.tests.test_owned_feed_receipts
python3 geo/owned_feed_pair_gate.py --growth <Growth-feature> --guide <Guide-feature>
```

測試工作檔只放 checkout 內 `.owned-feed-test-work/` 並由 producer 清理。
配對 Gate 檢查最新 fetched mains 的 ancestry、乾淨 feature branches、精確 Guide gitlink、
source／tests／文件 parity，以及生成零差異。**舊候選不能作基線，也不能把 gitlink 倒退。**

交付先推 Guide feature，再推指向它的 Growth feature；不 push main、不 dispatch deployment。
日後由整合者協調 **Growth source → Guide → Growth 最終 gitlink**，以成對來源封閉整合窗口，
更新後重新 fetch、必要時 rebase、重跑本 Gate；不得 force-push 或以舊 Guide pin 蓋掉新 main。
本 feature 交付本身不授權任何 production deployment 或通知。
