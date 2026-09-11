# 真實成果圖索引閉環

`result_image_index.py` 只使用 `data/result_image_evidence_v1.json` 中已公開、
經權利與圖文覆核的圖片；不呼叫 ASC writer、不改 App、不製造圖片。
它不讀寫 conversion／owned-feed 的來源契約。

## 證據與覆蓋

- 優先盤點 photo6、Kids14、scanner/PDF2、Notes/OnePage，共 24 款。
- 每款固定輸出 Apple 官方 exact-50 coverage。缺原圖、權利、成果、
  母語或公開 GET 證據均為 `BLOCKED_EVIDENCE`，不是綠燈或零需求。
- 初始僅公開 Notes 手寫頁、OnePage 編排畫面的英文截圖；不聲稱已驗證
  iPad 完整流程、OCR 命中、音訊、可編輯 PPTX 或客戶成效。
- 人像缺肖像權文件、活動入口、封面、社群卡與生成 SVG 不計入成果圖。
- 帶文字的圖僅能使用其實際 locale，連英語區域也不冒充其他 locale。
  跨 locale 重用必須有「圖內無文字」的肯定覆核，以及逐 locale
  獨立母語 alt、caption、附近文字與摘要綁定的覆核。

## 執行與驗證

```sh
GEO_PAGES=/path/to/guide python3 geo/result_image_index.py
GEO_PAGES=/path/to/guide python3 geo/result_image_index.py --check
GEO_PAGES=/path/to/guide python3 geo/result_image_index.py --check --verify-live
python3 -m unittest discover -s geo/tests -p test_result_image_index.py
```

每次真實 GET 都有 timeout、最多三次重試、大小上限，且不接受 redirect
替代 canonical URL。HTTP 200、SHA-256、MIME／格式、尺寸、完整解碼、
圖片 `X-Robots-Tag` 與**網域根目錄** robots 均須符合。Google 將 robots
的 4xx（429 除外）視為不存在；429、5xx、不可判定回應不放行。
robots 判定共用 `crawler_policy.RobotsPolicy` 的 canonical 規則，包含
wildcard、end-anchor 與 percent-encoding 優先序，不另維護漂移的 parser。

來源層產生 `<img src>`、width／height、母語 figcaption／上下文、canonical
頁面與 `sitemap_result_images.xml`，不產生評分或 JSON-LD。圖片保留原始
Apple CDN URL，沒有宣稱已取得該 CDN 的 Search Console 驗證。

輸出 `data/result-image-coverage.json` 保存真實 coverage 與內容摘要；
lastmod 只隨頁面或圖片內容改變，不隨每日 probe 心跳更新；sitemap 本身
另以內容摘要追蹤撤圖／清空日期，與全站 lastmod generator 保持冪等。
既有圖片失效會退出 sitemap；即使移除整個 locale 與文案，舊成果頁也
會沿用原母語的退役提示降為 noindex，並納入部署後讀回，不繼續展示舊圖。
空 sitemap 不加入 sitemap index 或 robots discovery。
部署讀回共用 `deployment_generation.verify_output_bytes` 的既有規則：
只在正式網域移除單一、固定摘要的 Cloudflare beacon，再驗全部原始
HTML bytes；未知 script、其他修改、錯誤 MIME 或外部網域一律不接受。

此 generator 在 broad generation 之後執行，以受管理區塊恢復首頁入連、
robots discovery 與 sitemap index，不修改 owned-feed generator。
部署後另驗實際 HTML。`changed_pages` 只含本次有變更的 HTML，部署成功後
才可交給既有 IndexNow 工具；結果圖的 src／srcset／alt 與證據 pixel hash
納入內容摘要，純圖片修正不會被當作 head 心跳濾掉。此分支使用明確的
`data-result-image-sha256`，不重置全站舊裝飾圖的內容狀態或製造大量通知。
提交 accepted 不等於 Google／Bing indexed。

## 官方依據（2026-09-11 讀取）

- https://developers.google.com/search/docs/appearance/google-images
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec

只使用 `image:image`／`image:loc`，不新增已廢除的 image caption/title tags。
可被發現與可被索引是工程條件，不是搜尋引擎實際收錄的證明。
