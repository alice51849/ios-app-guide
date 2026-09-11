# 自有 App feed 契約

`owned_app_feeds.py` 從版本化 `live_app_manifest.json` 的完整 roster、
`api/v1/ios-app-catalog/locales/*.json` 的既有母語資料，以及既有
publisher/finder i18n 產生可訂閱 feed；不呼叫 ASC、不發社群、不改 App、
buyer-page 或 conversion-route 內容。

## 公開入口

- 每個 Apple 官方 locale：`/<locale>/feed.xml`（Atom）、
  `/<locale>/rss.xml`（RSS 2.0）、`/<locale>/feed.json`（JSON Feed 1.1）。
- `/feeds/index.html`：所有語系的訂閱入口。
- `/feeds/owned-apps.json`：roster、來源 generation、逐語 coverage、每份 feed
  SHA-256、格式與可接受 HTTP Content-Type。
- `/sitemap_owned_feeds.xml`：完整 feed 與訂閱目錄；加入既有
  `sitemap_index.xml`，不改寫大型平面 sitemap。
- 只在各語系目錄的 head 寫入可辨識、冪等的 autodiscovery block；
  同語系三種格式必須各自排在第一順位，避免訂閱器選到英文 root feed；
  根目錄只加訂閱目錄連結。既有全站 `feed.xml/rss.xml/feed.json` 保留原職責，
  不能代替任何 locale 的 feed。

## 不可放寬的檢查

1. 每語完整等於 canonical live roster；目前 47 App × 50 locale = **2,350**
   唯一 App/locale pairs、150 份 feed。不能因單一 storefront 暫時缺資料而移除
   已登錄的 live App，也不把 roster identity 當成永久有效的 availability 證據。
2. `urn:lumi:app-store:<id>:locale:<locale>` 在三種格式中一致且穩定；
   canonical 為同語系 App 頁。App Store URL 保留已驗證來源的 storefront、
   `pt`、`ct`、`mt`；不另猜售價或建立個人追蹤識別碼。
3. Purchase model 逐款與 registry 比對。目前 **13 paid-upfront、34 freemium**。
   付費下載不標 free；免費起用明確保留一次性解鎖邊界，不宣稱所有功能免費。
   每筆包含母語 publisher disclosure 與 App Store CTA。
4. 不允許英文 body/wrapper fallback、不正確 locale、重複 JSON key／App ID、
   偷換產品身分、寫死金額、站外 canonical 或錯誤 App Store ID。
   `regex` 的 Unicode Script 屬性逐 locale 驗證：非 Latin 語系至少 60%
   有效字母屬目標 script，且禁止其他非 Latin script；只有明確 Latin 品牌
   不計入比例，不可拿品牌例外藏異種 script。日文允許 Han／Hiragana／Katakana，
   中文允許 Han／Bopomofo（真實注音教學內容），不是把漢字放行給 Kannada。
   真 production Kannada catalog fixture 保留原混入中文的反例，
   正式 `math_pro_full.json`、HTML、catalog 與 feed 改用完整 Kannada 摘要。
5. XML 宣告 UTF-8，JSON 以 UTF-8 寫入。GitHub Pages 的 XML 目前實際回傳
   `application/xml`；JSON 回傳 `application/json; charset=utf-8`。這些是合法
   可解析的相容 MIME，不假裝伺服器回傳 `application/rss+xml`。
   Readback 拒絕 HTML、非 UTF-8 charset、錯誤 body/hash、HTTP 非 200。

## Source-bound 與通知

- App 名稱、母語摘要、canonical、CTA、purchase/disclosure 改變才更新該
  item 的 `date_modified`；ID 與 `date_published` 保留。
- Snapshot 查核時間、售價快取、source 排序與 Git commit 本身不造成 feed churn。
  無變更重跑必須是 **0 changed files**，包含 bytes、mtime 與日期。
- `geo-daily.yml` 英文與在地化兩段提交都在 commit 前生成及驗證 owned feeds；
  localized attestation 必須在 feed 生成後才封存，commit 前再做唯讀 check。
  Remote reconciliation 同樣先重建及 check，再跑原測試與 push，避免 catalog
  已提交、feed 卻只在 Pages runner 暫時生成而令下一次部署重新改日期。
- `owned_feed_delivery.py prepare` 在部署前讀取原公開 index／legacy feed，
  將真正內容改變寫入私有 durable outbox；不是看 workflow 日期或 commit 新舊。
- `notify` 先驗所有待發 topic 已上線且與當次 source SHA／inventory digest 一致。
  WebSub 與 rssCloud 成功 ACK 立即原子保存；成功項目不因重跑／換 commit 再送，
  失敗項目保留、有限退避重試，內容已被取代的 pending 不得送出。
- 單一 provider 第一個批次失敗即停止其本輪後續批次，其餘 provider 照常執行；
  hub 批次交錯執行，且每個 provider 有 90 秒軟預算，慢速成功也不能耗盡整輪。
  未完成仍回非零並保留 pending；下輪優先處理較少嘗試的 topics，
  避免某一個壞 URL 永久擋住同 provider 的其他 feed。
- Outbox 一次只有一個 owner，檔案 mode 0600；GitHub Actions cache 保存
  `.github/owned-feed-runtime/state.json`，`.github` 不進 Pages artifact。
  Cache 必須在失敗時仍保存。未收到 ACK 的網路故障只能提供 at-least-once 重試，
  不宣稱分散式 exactly-once；feed reader 仍以穩定 ID 去重。

## 驗證

```sh
python3 -m unittest -q geo.tests.test_owned_app_feeds \
  geo.tests.test_owned_feed_delivery geo.tests.test_notify_rsscloud_retry
python3 geo/owned_app_feeds.py --pages-dir <Guide-worktree>
python3 geo/owned_app_feeds.py --pages-dir <Guide-worktree> --check
python3 geo/owned_app_feeds.py --pages-dir <Guide-worktree> --check --verify-deployed
```

`--western-matrix <cells.json>` 只讀原稽核，驗證原本失敗的 `rss_owned` cells
確實可從各 locale feed 取得正確 App ID；不覆寫原 audit，也不把其他 surface
失敗算成修好了。
