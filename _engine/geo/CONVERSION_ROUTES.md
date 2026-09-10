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

Storefront 金額是帶時間戳的歷史 readback，**不在可見文案或 schema.org Offers 硬編全球價格**；沒有法國／日本 readback 時保持 `unknown`，不套美國價。`APPROVED` 不等於 runtime 購買已驗證。

`effective_at_utc` 在首次 exact production GET 前保持 `unknown`；本機 GET、產檔及 feature branch push 不算曝光。公開 contract 的 `generated_not_deployed` 是 producer 狀態，實際發布由既有 `.well-known/deployment.json` 與獨立 exact GET receipt 證明。不要為改寫曝光日期再觸發一次部署。

來源／campaign／成交未知值不是零；14 天只做方向性診斷，不自動擴量，不變更既有 cooling／hysteresis。因果 WIN 仍須既有授權 randomized day-30、power、multiplicity Gates。

## 驗證與安全整合

以 `test_conversion_route_contract`、`test_high_intent_decision_routes`、`test_store_attribution_integrity` 同一次 unittest 執行驗證。正式 `_engine` 測試須把 `HIGH_INTENT_CURRENT_SOURCE_ROOT` 指向**另一個** GrowthEngine worktree 的 `geo/`，不得指回 mirror 本身。

使用既有 generator 產生 route HTML、coverage、feed、sitemap、conversion JSON／schema 與 expected-output manifest，不手改 HTML。部署前須通過 materialization／production closure 與來源同步 Gate。

先在兩個隔離 feature branch 提交；GrowthEngine 的 `geo/pages` gitlink 最後綁定對應 Guide commit。只有 main 穩定且環境 Gates 通過時才依序整合 source、Guide，讓一次 Pages push 觸發一次部署，再 exact GET；不得另跑社群或重複 dispatch。
