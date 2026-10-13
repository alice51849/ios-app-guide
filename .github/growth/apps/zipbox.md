# Zipbox（zipbox）

**一句話診斷**：付費下載（$4.99／NT$150／¥800／₩7,700）卻只有 3 張截圖，使用者最在意的「我這個檔打不打得開」在付款前無法驗證；US「unzip」第 116、名稱含「解壓縮／解凍／압축풀기」仍排不進前 170，而 zh-Hant 關鍵字「中文亂碼」描述沒支持、GEO 頁卻據此生成 FAQ。

## 結論
付費下載（$4.99／NT$150／¥800／₩7,700）卻只有 3 張截圖；使用者最在意「我這個檔打不打得開」，付款前無法驗證。US unzip 第 116／174（前段全免費：Documents 631k、iZip 63k），TW／JP／KR 名稱含「解壓縮／解凍／압축풀기」仍不在前 170（第一輪實測，今日被 Apple 限流未重測）。另：zh-Hant 關鍵字「中文亂碼」描述沒支持，GEO 頁卻生成「中文亂碼推薦哪個 App」FAQ。優先度：中。

## 各市場真正問題
- **zh-Hant**：需求在 PTT iOS／Dcard「iPhone 打不開 RAR」提問；關鍵字只用 39／100 字；亂碼宣稱待確認。
- **ja**：知恵袋「iPhoneでRAR開く」是入口；文字化け 同樣未在描述說明。
- **en-US**：付費 App 在 unzip 無法靠搜尋，只能 Reddit 回答。

## 行動
| claude | local | you |
|---|---|---|
| PTT／Dcard／知恵袋回答草稿；Telegram spotlight；店主確認後刪 zh-Hant 亂碼 FAQ | 產生器停止把關鍵字直接變成 FAQ 宣稱；best-open-rar／best-extract-7z 頁去 best | ASC：截圖補到 6 張以上（零廣告、密碼 7z、先預覽、單檔取出、檔案 App 整合、50 種語言）；三店面關鍵字補滿；決定亂碼／文字化け 寫進描述或刪關鍵字；評估免費預覽 Lite；聯繫瘋先生更新教學；錄 30 秒影片 |

## 二次審核修正

- 新發現：zh-Hant GEO 頁把關鍵字「中文亂碼」生成 FAQ「iPhone 上 中文亂碼 推薦哪個 App?」，描述卻從未宣稱編碼修復——我方頁面有未支持的宣稱；需店主確認 App 是否處理檔名編碼後決定寫進描述或刪除。
- 今日 TW／JP／KR 搜尋因 Apple 對搜尋端點回 403 限流未完成，沿用第一輪 10/13 名次；US unzip 由第 118 → 今日第 116，兩次一致。
- 第一輪「JP iZip Pro 賣 ¥2,000 證明有人付費」今日未驗證，暫不採用。
- 六款中 Zipbox 的線上文案與 repo 一致、沒有漂移；3 張截圖的問題由 lookup 證實（US／TW／JP／KR／GB 皆 3 張）。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 需求在 PTT iOS／Dcard「iPhone 打不開 RAR」的真實提問，不在搜尋（名稱含「解壓縮」仍不在前 177）；關鍵字只用 39／100 字；關鍵字「中文亂碼」描述從未宣稱，GEO 頁卻生成「iPhone 上 中文亂碼 推薦哪個 App?」FAQ＝我方頁面有未支持的宣稱。 | lookup TW 10/13：NT$150、1 則評分、3 張截圖、v1.0.4；repo zh-Hant 關鍵字 39 字元；zh-Hant/zipbox.html 第 155 行 FAQ「iPhone 上 中文亂碼 推薦哪個 App?」；第一輪 10/13 實測：TW「解壓縮」不在前 177（第 1 名 18.4k 則），今日 TW 搜尋被 Apple 限流未重測。 |
| ja | 「解凍」不在前 174（第一輪）；ja 關鍵字含「文字化け」同樣沒在描述說明；知恵袋「iPhoneでRAR開く」是需求入口。 | lookup JP 10/13：¥800、0 評分、3 張截圖；repo ja 關鍵字 42／100；第一輪 10/13：JP「解凍」不在前 174（iZip 48.8k）。 |
| en-US | 「unzip」第 116／174，前段全是免費加廣告或內購（Documents 631k、iZip 63k、Unzip 54.9k）；付費 App 無法靠搜尋，只能在 Reddit 回答「iPhone can't open RAR」時出現。 | wsSearch 10/13：unzip 174 筆 Zipbox 第 116（第一輪 118，一致）；Unzip 54,908、iZip 63,092、Zip & RAR 28,190、Documents 631,161 則；lookup US $4.99、0 評分。 |
