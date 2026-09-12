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

- Outbox 同時綁定完整 Guide SHA、既有 `deployment_generation.validate_binding`、
  feed manifest、每個 topic SHA-256；通知前 GET 驗證 **全部 feeds**（含不通知的 bn-BD）
  與部署 generation，並再讀 generation 防中途切代。Partial deploy 一律零 POST。
- ACK 以 `(protocol, endpoint, topic, content hash)` 去重，不以 commit／日期去重。
  無內容更新重跑或換 source SHA 都是 **0 通知**；未 ACK 的 pending 可恢復。
  既有 54 legacy topics 也納入相同 outbox，其中 bn-BD decision feed 不通知。
- 一個 owner 持有非阻塞 `flock`；mode `0600` 的原子 state 每收到 ACK 立即保存。
  hub 交錯批次、有限退避與每 provider 90 秒軟預算，單一故障不阻塞其他 provider。
  無 ACK 的網路故障只能提供 at-least-once，不能宣稱分散式 exactly-once。
- Pages workflow 在 artifact prune 前保存執行器；`.github/owned-feed-runtime/state.json`
  由 Actions cache 恢復且失敗後仍保存，不進 git 或 Pages artifact。
  整合驗證只用 mocked GET/provider，不實際通知 WebSub、rssCloud 或 IndexNow。

## 離線驗證與配對交付

```sh
python3 geo/owned_app_feeds.py --pages-dir <Guide-feature> --refresh-catalog
python3 geo/owned_app_feeds.py --pages-dir <Guide-feature> --check \
  --reference-source <Guide-feature>/_engine/geo
OWNED_FEED_GUIDE_ROOT=<Guide-feature> python3 -m unittest -q \
  geo.tests.test_owned_app_feeds geo.tests.test_owned_feed_delivery
python3 geo/owned_feed_pair_gate.py --growth <Growth-feature> --guide <Guide-feature>
```

測試工作檔只放 checkout 內 `.owned-feed-test-work/` 並由 producer 清理。
配對 Gate 檢查最新 fetched mains 的 ancestry、乾淨 feature branches、精確 Guide gitlink、
source／tests／文件 parity，以及生成零差異。**舊候選不能作基線，也不能把 gitlink 倒退。**

交付先推 Guide feature，再推指向它的 Growth feature；不 push main、不 dispatch deployment。
日後由整合者協調 **Growth source → Guide → Growth 最終 gitlink**，以成對來源封閉整合窗口，
更新後重新 fetch、必要時 rebase、重跑本 Gate；不得 force-push 或以舊 Guide pin 蓋掉新 main。
本 feature 交付本身不授權任何 production deployment 或通知。
