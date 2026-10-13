# ScanTo Pro（scanto）

**一句話診斷**：iOS 內建「備忘錄／檔案」免費就有掃描＋裝置端文字辨識，而我們量測的 3 組首要關鍵字（掃描器／scanner 等通用詞）完全沒有名次；真正獨特的「身分證正反面一頁、加密 PDF」被埋在說明後段，關鍵字還含競品名稱「掃描王／白描」。

## 結論
**優先度：中。** 內建備忘錄／檔案免費就有掃描＋裝置端 OCR，「離線私密掃描」說服不了人。成績單上 ScanTo 沒有任何名次，因為量的是「掃描器／scanner」這類通用大詞——量測詞本身選錯。真正獨特的「身分證正反面一頁、密碼加密 PDF」埋在說明後段；關鍵字含競品名「掃描王／白描」（審核風險）、印尼文黏字「sekalibeli」、不相關的「fax」。說明寫 33 語，App 實為 50 語（Lookup 已回報 53 個語言碼）。Telegram 英文貼文含「alternative to CamScanner」須刪。

## 各市場真正問題
- **台灣**：「身分證正反面影本」是高頻真實需求，但名稱／副標沒有「身分證」；1 則 5★ 沒人搜得到。
- **日本**：副標講技術不講情境；需要「身分証 スキャン／暗号化 PDF」長尾。
- **德國**：副標合口味，但 0 評分、無媒體提及、缺需求驅動。
- **印尼**：店面預設英文；印尼文說明 684 字，沒提證件正反面、加密 PDF、Face ID。
- **美國**：2 則平均 3.0、無文字；名稱副標重複 PDF／OCR。

## 行動
| claude | local | you |
|---|---|---|
| 刪 Telegram 競品名；量測詞改身分證 影本／身分証 スキャン／Ausweis scannen／scan ktp | GEO 頁首段改證件情境、移除 33 語句 | 刪「掃描王／扫描王／白描」、修 sekali beli、刪 fax |
| 台灣教學頁「身分證正反面影本 A4 一頁」（內建先） | — | 副標改「身分證正反面一頁・加密PDF・買斷」；說明前三行放證件與加密；33→50 |
| 德文媒體提案信草稿；印尼文說明全文草稿 | — | 補完印尼文說明；首次匯出後加 Apple 標準評分提示；寄德文提案信 |

## 二次審核修正

- 「33 languages」→ 店主確認 50 語＋App 內切換；而且 Lookup 的 languageCodesISO2A 已回報 53 個語言碼（其他四款 44），說明文比 App 本身還落後。
- 成績單：ScanTo 在已量測組合裡沒有任何名次，原因是檔案前 3 個關鍵字是「掃描器／掃描app／文件掃描」「scanner／scan／doc scanner」通用大詞；第一輪沒指出「量測詞本身選錯」。
- 印尼店面預設語言為英文，印尼文說明只有 684 字且沒提證件正反面、加密 PDF、Face ID；第一輪沒看印尼文說明內容，也把「印尼文介面不確定」當保留條件（店主已確認 50 語，撤回）。
- 美區 2 則平均 3.0：RSS 評論 feed 為空，無法回覆；第一輪建議「在 ASC 回覆美區評論」無法執行。
- 第一輪引用尼泊爾禁令、Android 版惡意程式等與目標市場無關的資料，刪除。
- Telegram 名冊英文貼文寫「a pay-once alternative to CamScanner」，違反競品商標規則，第一輪沒檢查。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 「身分證正反面影本」是台灣辦事的真實高頻需求，但繁中名稱／副標是「離線PDF掃描／私密離線・OCR・一次買斷」，沒有「身分證」「證件」；關鍵字「掃描王」是競品名（審核 2.3.7 風險）。1 則 5★ 是好開頭，但沒人搜得到。 | Lookup TW：免費、1 則 5★、v1.2.8。資料檔 zh-Hant keywords 含「掃描王」；成績單：ScanTo 在已量測組合中無任何名次（量的是「掃描器／掃描app／文件掃描」）。「身分證 掃描」查詢未測（限流）。 |
| ja | 日文副標「完全オフラインのPDF・OCR」訴求的是技術，不是情境；0 評分。日本用戶會搜「スキャナー／書類スキャン」這類被大廠佔住的詞，我們需要的是「身分証 スキャン」「暗号化 PDF」這類長尾。 | Lookup JP：無料、0 評分、名稱「ScanTo Pro: オフラインPDF」。資料檔 ja keywords 前 3 個是「スキャナー,スキャン,スキャンアプリ」。 |
| de-DE | 副標「Privat, offline, einmal zahlen」很合德國口味，但 0 評分、沒有任何德文媒體或部落格提及，缺外部需求驅動；德文關鍵字只有 10 個通用名詞。 | Lookup DE：Gratis、0 評分、名稱「ScanTo Pro: PDF Scanner & OCR」。資料檔 de-DE keywords：texterkennung,einscannen,digitalisieren,dokumente,beleg,quittung,rechnung,ausweis,vertrag,unterlagen。 |
| id | 印尼店面預設語言是英文（Lookup 回傳英文名），印尼文只給裝置設為印尼文的用戶看；且印尼文說明只有 684 字，沒提證件正反面、加密 PDF、Face ID——印尼貼文想講的賣點在印尼文商店頁上看不到。關鍵字「sekalibeli」黏在一起、有不相關的「fax」。 | Lookup ID：Free、0 評分、回傳名稱「ScanTo Pro: Offline PDF OCR」。資料檔 id description 684 字；keywords 含 sekalibeli、fax。 |
| en-US | 2 則評分平均 3.0、無文字可回覆；名稱「Offline PDF & OCR」與副標「Private PDF & OCR. Pay once.」重複 PDF／OCR；關鍵字有不相關的「fax」。 | Lookup US：Free、2 則、平均 3.0；RSS 評論 feed 無文字。資料檔 en-US keywords 含 fax。 |
