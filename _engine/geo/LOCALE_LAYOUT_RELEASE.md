# Locale + layout release candidate

此合成只建立可審核的 paired feature，不授權 main、部署、ASC、App 或社群操作。

## 輸入與保留界線

- Content：Growth `e8142dcc6bfcd71a8f32db900252d6a5b097e380`、Guide `43b52650b475faa234b8f2d684b8729143a8b36a`。
- Layout：Growth `a976d412c4981358e7059680e4aef2a6f6d274d1`、Guide `aea899ce7330b1c05c8a2a47ba35f069386fee73`。
- 289 個 source cells／968 欄真值保持原樣；不加入 context-blocked Indic、social 或歷史 receipt 修正。
- Growth `geo/pages` gitlink 保持建立本輪時的 production 值。Guide feature SHA 只寫入私人 release manifest，不能在此階段釘入 gitlink。
- Index canary、bn market boundary、public host、owned-content、公開搜尋 monitor 等 main 前進必須保留；不啟動服務或手動 dispatch。

## 可重現候選

`locale_layout_candidate.py` 只讀取 production checkout，使用正常的 primary、MobileApplication identity、facts、attribution、decision card、QR、mobile/share CTA、hub、decision 及 layout renderer，輸出至新的候選目錄。不得重用舊輸出。

```sh
GEO_PAGES=/absolute/path/to/guide \
GEO_SITE=https://open.cait518.cc/ios-app-guide \
APP_STORE_PROVIDER_TOKEN=118326163 \
python3 geo/locale_layout_candidate.py \
  --source /absolute/path/to/guide \
  --output /absolute/path/to/new-candidate \
  --field-truth /absolute/path/to/reviewed-field-truth.json
```

候選不是已發布網站。首頁/canary與既有sitemap inventory保留，bn 560 個檔案不改；完整publisher/feed索引的最後整合仍須由index canary協調者在同一source上關閉。修正cells的decision copy明確取自新生成的app頁，不再默默沿用舊persona answer。未修正cells保留原本的intent選擇。

## Index canary前進後的整合順序

1. 先唯讀 `git fetch`，釘選最新兩個production main與目前部署generation；確認canary整合已結束。此release feature不自行更新gitlink。
2. 在新隔離worktree上，以最新main為基線整合本feature的source與生成asset差異；套用Growth差異時仍排除`geo/pages`。已推送的feature不得force-push；需重排歷史時建立有明確來源的successor feature。
3. 語意保留`build_pages_i18n`三批content hooks、文字formatter dispatcher與layout/bidi helpers；保留main的bn/public-host/canary/owned-content/search服務。不可以整檔覆蓋或舊候選HTML覆蓋最新main。
4. 重新核對289／968真值、pt-PT 47、Hebrew 47、CJK 12、production source/asset parity、exact50／identity／paid／canonical／sitemap及bn347／560／659原始hash。raw回讀只使用既有source-derived verifier，不裁掉response、不新增normalizer。
5. 以合成後的最終文案重新產生候選；舊layout驗收不能代替新文案。主矩陣至少保留原21語×47款×6尺寸×JS雙態×Reduce Motion雙態，再覆蓋原矩陣外所有修正cells；hub／decision與健康頁對照亦須有完整證據。timeout必須具名重跑同一候選，不能當作PASS或skip。
6. 跑locale22＋36＋21＋8DOM＋57、layout13、release-composer測試、62／18／206／46與canary相關Gate，全部0 skipped。fixture root必須明確指向本次Guide checkout。
7. **只有另獲明確整合／部署授權後**，才由協調者關閉最新canary與source manifest、處理Guide main → Growth exact gitlink/main → 單次精確SHA部署 → canonical/origin完整raw readback。本文件不是部署授權。

## 證據要求

release manifest須列出source SHAs、未改的production gitlink、候選與assets hash、每個Gate的原始結果、所有geometry case keys、same-candidate重跑記錄、raw generation binding及index canary依賴。不得把publication、索引、點擊或營收推論成測試結果。
