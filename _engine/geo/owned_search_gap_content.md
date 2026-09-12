# 公開搜尋 gap → 既有 owned-content 增益候選

## 2026-09-12 production 配對整合

本次從 Growth `2a608f36526f` 與 Guide `2e0c4005882e` 的最新 main 隔離整合，
只帶入本功能四個 source/test；保留 public-search main、bn-BD 347 HTML／560
surfaces、官方 public-host/email 與 CLI package-pin 保護。
已逐一重新確認 1,052 頁去重 corpus 的 Git blob 與五頁 before-image，
不套用落後分支的全站產物。

完整頁面審閱另攔到日文 Aim990 原正文一句把「短診斷」直接作為開始步驟，
與目前可證實 shipping 範圍不一致；以明確、唯一的 body-only correction
改成「先試短練習，再自行回想哪裡卡住」。不動 head／meta／JSON-LD，
並新增兩項防止缺字串或錯改位置的測試。

此 renderer 仍不做網路或發布。實際 publication 由配對 integration owner
在 20+2／368／62／18／206／46 等 Gate 與 cloud-equivalent preflight PASS 後，
以 Guide `[paired-high-intent]` commit、Growth exact gitlink，以及唯一
`incremental_high_intent` workflow dispatch 完成；不手動 IndexNow 或通知，
indexed 保持 unknown。下方 feature-only 敘述保留為原候選交付的歷史範圍。

這是第 3 輪 `f020f3683a9c` 公開搜尋樣本的**有限內容研究後續**，
不是 ASC 排名修復、metadata／keywords 調整，也不表示有人搜尋、下載或購買。
只讀既有已提交產品與網頁證據；不抓網頁、不呼叫任何 API／模型、
不改 App、不發布內容、不變更 production daemon。

## 十九項分類

- **6 OWNED_CONTENT_MATCH**：產品能力相符，且既有頁缺少可用的情境檢查、
  決策步驟或限制說明；只選這 6 項，合併到 **5 個已有 answer URL**。
- **13 ASC_ONLY_NOT_ACTIONABLE**：已有 Guide／answers／persona／alternatives
  覆蓋、同義重複或沒有新的可驗證資訊；只交 brief。
  名稱不代表 ASC 有問題或授權修 ASC，只表示這筆 search absence 本身
  不足以產生本輪的 owned-content 動作。
- **0 NO_PRODUCT_FIT**：19 個來源詞本來都屬於真實產品用途，
  不為了填滿分類而虛構不相容理由。

人工逐列研究另保存 19-gap brief、1,052 頁 committed locale corpus 與
四 App 的既有 persona source 引用／SHA，沒有以未提交 WIP 充作證據。
所有產品聲稱綁定 committed high-intent conversion contracts：
原創離線 TOEIC-style 練習、Cyca 預測只是估計、注音而非漢語拼音，
以及 Mochi 基本 widget 勾選免費／Premium 外觀可選。

## 選中題目與既有頁

| App／市場 | 選中 gap | 同一既有 URL 增加的資訊 |
|---|---|---|
| Aim990／JP | `toeic リスニング`、`toeic 対策` | 聽音／理解／選項誤判的手動復盤、短練習與完整測驗的界線、離線預檢與通勤安全 |
| Aim990／US | `offline TOEIC daily practice` | 出門前驗證可用練習、離線內容與 Apple 購買／還原不同、下一次複習的一個問題 |
| Cyca／DE | `periodenkalender` | 真實記錄與估計日期、缺資料不捏造日期、無帳號不等於可從雲端找回記錄 |
| Lumi Bopomofo／TW | `ㄅㄆㄇ親子學習` | 聽辨／描寫分步、卡住時家長如何示範或停止、看得到內容不等於全部免費 |
| Mochi／US | `check off to do home screen` | 可勾選 widget 與一般入口的區別、一筆低風險的 Home Screen→App 結果核對、功能與外觀分開判斷 |

精確路徑與 before SHA 在 `data/owned_search_gap_enrichment_v1.json`。
其餘 query 不新增頁、不增添同義段落；日文 Aim990 兩個意圖合併同頁，
避免再製造另一個 doorway。

## 生成與不變性契約

`owned_search_gap_content.py` 是**明確 opt-in、target-only 的來源補充 renderer**，
不掛進或改寫全站產生／部署流程。它讀取唯一已審閱 Guide commit 與頁面 before SHA，
在既有 FAQ 前加一個母語補充 section；既有正文、FAQ、`<head>`、
canonical／hreflang／meta／JSON-LD 均不改寫。

它不是自由生成器：plan、弱訊號 snapshot、去重 corpus 與產品 source 全部需
明確 digest；只有 4–8 個 selected MATCH 可產頁。實際選 6 query／5 頁。
新段落不得含 URL、HTML、硬價、評分、排名／得分保證；
需母語 script、三個不同的實用決策、三段情境與三組 FAQ。
完整段落若已在 corpus 出現則阻擋；5-word／7-character shingle novelty
是重複文字檢查，**不是 SEO 成效評分**。內容價值仍來自逐段人工審閱。

CTA 只把已存在、正確 App ID 的 App Store 連結固定到 US／JP／DE／TW storefront，
原 `pt=118326163`、`ct=geo_ask`、`mt=8` 與其他 query 完整保留。
連結數、其他 href 均不變。原 QR 改為 deterministic inline SVG，
payload 與按鈕的完整 attributed storefront URL 一致；
**不新增 QR 檔、不改其他頁共用資產、不新增 HTTP asset URL**。

已套用後重跑，以同一 Git before-image 重算；若現在的頁是同一結果就不寫，
若含其他 WIP 就拒絕。五頁先全數驗證才寫入；寫入失敗只回復自己已寫且尚未漂移的頁。
`--apply` 只接受 `ios-app-guide` 的 feature branch，禁止 main／App repository。

```sh
"$HOME/00_GrowthEngine/.venv/bin/python" geo/owned_search_gap_content.py \
  --plan geo/data/owned_search_gap_enrichment_v1.json \
  --plan-sha256 "$EXACT_PLAN_SHA256" \
  --snapshot "$ROUND3/final-snapshot/snapshot.json" \
  --corpus "$ROUND4/dedupe-corpus.json" \
  --source-repo "$GROWTH_FEATURE" \
  --pages "$GUIDE_FEATURE" \
  --report "$ROUND4/candidate-report.json" --apply

"$HOME/00_GrowthEngine/.venv/bin/python" -m unittest discover \
  -s geo/tests -p test_owned_search_gap_content.py
```

## 配對 feature 與發布界線

Growth 的 renderer、data、test、本文同步到 Guide 的 `_engine/geo/`，
要求 byte-for-byte 一致；不得把另一個較舊引擎整包覆蓋較新的 Guide `_engine`。
Guide 以當時 `origin/main` 的 `05f08c583d06` 為基準隔離，
不採用本機 main 的落後備份分支或 `.appstore_live_state.json` WIP。

候選驗收對比完整 Git tree：只允許五個已存在 HTML 與四個精確 engine source
變更；所有其他 App／locale HTML bytes、canonical URL 數、
sitemap 檔名／內容／`loc` 數均相同。功能 tests 另外驗 native script、重複、
query 密度、App ID、CTA attribution、QR payload、no metadata mutation 與失敗回復。
兩邊只能 commit／push feature（帶 `[skip ci]`），不 merge main、不部署、
不 IndexNow、不碰社群。未來如要發布或併入既有 pipeline，另做明確的 paired
release 審查；本次不把候選當作已在線成效。

永遠不能宣稱：修好 ASC／App Store 排名、這些詞有特定搜尋量、增加下載／
付費轉換、Apple 推薦、醫療／避孕準確性、官方 TOEIC 教材或保證分數。
來源：Session `2fd0fa72-ea4f-49fe-94ee-f12ec0ac0d6a`，
2026-09-12 第 4 輪 owned-content gap 指令。
