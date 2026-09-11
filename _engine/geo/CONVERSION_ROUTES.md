# 十一款純外宣 route contract

## 單一來源

- `data/high_intent_decision_routes_v2.json` schema 4：47 款既有 stable routes、原生決策文案與 11 個 `conversion_contract` 引用。
- `data/high_intent_conversion_contracts_v1.json`：11 款的 18 組母語首屏、free／paid 界線、排除意圖、live-version 證據與有時間戳的 storefront offer。
- `conversion_route_contract.py`：fail-closed schema、首屏及可讀取的公開 observation contract。
- `high_intent_guide_sync_contract.json` 同時封存上述來源與 renderer 的 SHA；部署副本必須逐 byte 相同。

首屏只有一個直接 App Store CTA，保留既有 `pt`／`ct`／`mt` allowlist；不建立新 campaign bucket。其可存取說明與 body 使用相同 free／paid 文句。每個有原生文案的 locale 只互連實際存在的 canonical／hreflang；不得用英文補齊未完成語言。原有 47×50 install-decision baseline 不變。

## 證據與 unknown

素材僅來自已查核的公開商店圖。CDN 原始 bytes SHA 與報告的 RGB→640px thumbnail→JPEG quality 90 SHA 分開保存，避免把轉碼差異誤判成新素材。沒有對應母語圖時不顯示英文圖替代。

`BLOCKED_EVIDENCE` 不代表功能不存在：它阻止把未驗證的診斷、搜尋命中、完整 iPad 成果或可編輯 PPTX sample 當成已完成的 proof。BattAI 的 report-export 付費範圍亦維持 blocked。Aim990 固定使用已上架 1.4.2，不操作或宣傳待審 1.4.3。

`published_claim_ids`、`free_feature_ids` 與 `paid_feature_ids` 都不得引用 blocked ID，即使另一筆 verified proof 同時列出相同 ID，仍須 fail closed。

原「已發布的任務用語」區塊只保留經 `keyword_refs` 綁定的 catalog keywords；沒有母語 catalog keywords 時不以英文補齊。Conversion queries 另以母語「正在測試的任務搜尋語句」呈現，公開 contract／schema 的 `query_evidence` 固定為 `candidate`／`unverified`，搜尋量、排名與已發布來源一律 `unknown`，不得當成 proof。UI feature labels 與每筆 evidence text 必須通過和 route 文案共用的母語字元／虛詞驗證，英文 fallback 不得發布。

Storefront 金額是帶時間戳的歷史 readback，**不在可見文案或 schema.org Offers 硬編全球價格**；沒有法國／日本 readback 時保持 `unknown`，不套美國價。`APPROVED` 不等於 runtime 購買已驗證。

`effective_at_utc` 在首次 exact production GET 前保持 `unknown`；本機 GET、產檔及 feature branch push 不算曝光。公開 contract 的 `generated_not_deployed` 是 producer 狀態，實際發布由既有 `.well-known/deployment.json` 與獨立 exact GET receipt 證明。不要為改寫曝光日期再觸發一次部署。

來源／campaign／成交未知值不是零；14 天只做方向性診斷，不自動擴量，不變更既有 cooling／hysteresis。因果 WIN 仍須既有授權 randomized day-30、power、multiplicity Gates。

## 驗證與安全整合

以 `test_conversion_route_contract`、`test_high_intent_decision_routes`、`test_store_attribution_integrity` 同一次 unittest 執行驗證。正式 `_engine` 測試須把 `HIGH_INTENT_CURRENT_SOURCE_ROOT` 指向**另一個** GrowthEngine worktree 的 `geo/`，不得指回 mirror 本身。

使用既有 generator 產生 route HTML、coverage、feed、sitemap、conversion JSON／schema 與 expected-output manifest，不手改 HTML。部署前須通過 materialization／production closure 與來源同步 Gate。

先在兩個隔離 feature branch 提交；GrowthEngine 的 `geo/pages` gitlink 最後綁定對應 Guide commit。只有 main 穩定且環境 Gates 通過時，才非 force 依序整合 Guide、Growth。配對發布的 Guide commit 使用 `[paired-high-intent]` 標記，push 只產生獨立 concurrency group 的 no-op，不取消其他有效部署。兩個 main 精確配對後，只 dispatch 一次 `pages.yml` 的 `incremental_high_intent=true`，指定完整的 `expected_guide_sha`、`expected_growth_sha`、`previous_guide_revision`。workflow 精確 checkout 兩個來源並核對 gitlink，不能把新 Guide 配舊 Growth；不得另跑社群或重複 dispatch。

## Manifest 驅動的增量發布

增量模式仍使用完整非 sparse checkout，但不呼叫 `SiteTreeIndex.scan`、
`close_sitemap_graph` 或任何整站 HTML 重建。來源推導出的完整 generation
（目前 57 routes＋5 fixed outputs＝62）先通過 cardinality、canonical、
hreflang、source/sync 與 fragment preflight，才以既有 generator materialize；
之後逐 byte 驗證完整 62 outputs、feed、sitemap 與 attribution closure。

`deployment_generation.py materialize-incremental --output-dir . --inventory
data/verified-ios-app-finder-catalog.json --previous-guide-revision <完整已審 Guide SHA>`
會根據 Git delta（含已追蹤的 working diff）只選擇受影響的 `sitemap*.xml`、
`index.html`，再加固定的 high-intent sitemap 與 sitemap index。其他頁面／
sitemap 不重建；只有明確已刪除的受影響 sitemap 才移除其 index entry。
不完整 baseline、foreign URL、缺失 target、symlink、canonical／hreflang 漂移
均在寫入 managed files 前 fail closed，不能拿 partial site inventory 跑完整
closer，也不能手改 generated HTML／JSON 讓 Gate 變綠。

乾淨且已提交的來源使用既有 `deployment_generation.py prepare`，加上
`--incremental --previous-guide-revision <同一基線>`，仍執行完整 source identity
前後夾驗、mirror/dependency/config digest、generation sealing 與雙 host exact
GET；增量 mode 與 delta digest 亦綁入 build config。Scoped route availability、
canonical／hreflang 和完整 byte closure 取代本次不相關的全站 quarantine、
discovery／hero rebuild；不重發 WebSub、rssCloud 或社群。一般完整發布模式
保留不變。

Regression：既有 controller／collector 81、Guide 110，加上
`test_high_intent_incremental` 與 `test_deployment_generation`；前者明確令
`rglob`、full-site inventory 和 full closer 一經呼叫即失敗。Remote 前進時，
重取 delta 並只重跑受影響測試與必需 Gates；未實際部署前的 `effective_at_utc`
仍為 unknown，不以本機產檔或 feature push 取代 live receipt。
