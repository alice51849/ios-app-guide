# 八頁 depth-1 canary 與 E0 唯讀 Gate

此整合只移植 `aece3cb6`／`81bc9eab` 的 canary renderer、manifest、測試與
三檔 sync contract，另從 `cfa33b69` 精確擷取 `e0_index_gate.py` 及
`E0FailClosedTest`／`CanarySelectionTest`；**不帶入**舊 llms/root patch、
`canonical_closure.py` 或會讀 ASC 的 `portfolio_availability.py`。
基準是 Growth `f2f6b68d35c5`／Guide `4c4d145181ed`，保留 bn-BD、
public-host/email、五頁 owned-content 與 public-search monitor 的所有 main 進展。

## 可觀測改動

首頁是 en／x-default hub，只加 8 個已存在、具實質內容的英文 answer 連結。
標籤直接來自其 `<title>`，轉為安全、描述性的文字；
section 為 `<nav aria-label="App picks">`、可見 `<h2>` 與一般 `<ul><li><a>`。
標題使用 **Explore practical app guides**，不暗示有量測過的熱門度、流量或排名。
沒有按鈕、inline style、hidden link、新 URL、doorway，亦不改 canary target 內容。
8 個 target 的 4–26 語變體及 en／x-default hreflang 已重查；
英文 hub 不直接塞母語鏈結，既有 50 個語系 hub 保持原樣。

## 本次增量重算

同一個最新 `build_root_index()`、同一份既有首頁與 50 locale，
只把 `INDEX_ENTRY_CANARY_ANSWERS` 從空清單換成 8 個：

- controlled A：**16,891 bytes**
- controlled B：**18,451 bytes**
- 單一 insert：**1,560 bytes**，不是舊 1,564，也不是錯誤的 692
- 完整既有首頁：**17,769 → 19,329 bytes**

本地不能用局部 renderer 的整頁結果覆蓋雲端完整首頁，否則會洗掉既有 CSS、
feed links 與其他 generator 注入。整合工具只把同-renderer A/B 的唯一 insert
插入既有 Sections nav 前；其餘 bytes 完全保留，下一次正常 root renderer
也原生包含同一 section。

`index_entry_canary_sync_contract.json` 重新釘選 renderer、manifest、canary test
三個 SHA。兩側使用實際完整 checkout，`GEO_MIRROR_ENGINE` 指向對側：
`MirrorSideTest` 的存在性、hash、byte parity 都必須執行，不接受 skip。

## E0 不等於 canary 已有效

Gate 只有在下列條件**同時成立**才 PASS：

1. 至少一個真正深層 URL 的 URL Inspection `verdict=PASS`，
   `coverageState` 含正向 `indexed`，且沒有 `not indexed`、unknown、
   excluded、redirect、duplicate 等否定訊號。
2. 精確指定的 `sitemap_index.xml` 回 `isPending is False`，
   且 `lastDownloaded` 為非空字串；不選列表中另一個已處理 sitemap 代替。
3. 必要欄位已取得；HTTP 200 卻沒有 inspection result、欄位不見或 API 失敗
   一律 UNKNOWN。首頁 indexed、crawled-but-not-indexed、數字 0 都不能開 Gate。

`lastCrawlTime=null` 會照實保留。未知時 `indexed_deep_pages=null`，
另以 `confirmed_indexed_deep_pages` 記錄真正已確認的數量，不把未知補 0。
即使 E0 PASS，也只能表示入口條件已滿足，不證明此 canary 造成索引、
下載或購買增加。

## GSC 操作界線

僅允許 `sitemaps.list` 與 `urlInspection.inspect`。
前者 transport=GET，後者 Google API transport=POST，但語意仍是**唯讀**；
既有 OAuth refresh 也是驗證流程，不修改 property 或 sitemap。
其他 operation（含 sitemap submit/delete、sites.add、requestIndexing、
searchanalytics.query）一律拋出 `MutationAttempted`。
每個實際狀態／inspection response 有 UTC observed_at 與 SHA-256，
憑證或 token 不列印、不寫入 repo；HTTP timeout 30 秒、沒有 mutation retry。

```sh
"$HOME/00_GrowthEngine/.venv/bin/python" geo/e0_index_gate.py \
  --property https://open.cait518.cc/ios-app-guide/ \
  --credentials "$HOME/.growth-private/gsc_oauth.json" \
  --sitemap https://open.cait518.cc/ios-app-guide/sitemap_index.xml \
  --out "$SESSION_FILES/e0.json" --evidence-dir "$SESSION_FILES/gsc"
```

預設 deep paths 就是 manifest 中的 8 頁。Exit 0=E0 PASS；exit 2=BLOCKED／UNKNOWN，
**不是**因為部署成功而自動改成 PASS。
原 canary 28＋link13、sync10、E0 原15＋新增11，以及既有 full-content／62／18／206／46
與 bn/owned/email/raw Gate 皆由配對發布 owner 執行。
只有一次有效 Pages 部署，不手動提交 sitemap、IndexNow 或通知。

來源：Session `2fd0fa72-ea4f-49fe-94ee-f12ec0ac0d6a`，2026-09-12 depth-1 canary
production 指令；「5」是同時 live worker 上限，不是輪次上限，沒有啟動 subagent。
