# QR Code Halo（qrcodehalo）

**一句話診斷**：線上 v1.0.3 在 US／TW／JP／KR 四個店面都寫「掃到就直接執行」、JP／KR 名稱是「すぐ開く／바로 실행」，但 TW 名稱「安全掃描」、en-GB 副標「Inspect before you open」、repo 資料檔、53 個語系 GEO 頁與 3 則 Telegram 文仍宣稱「絕不自動開啟」；身分統一前，它同時輸給免費的 iOS 相機（3 次掃描上限）與自己的承諾。

## 結論
線上 v1.0.3（US／TW／JP／KR）都寫「掃到就直接執行」、JP／KR 名稱「すぐ開く／바로 실행」，但 TW 名稱「安全掃描」、en-GB 副標「Inspect before you open」、repo 資料檔、53 個語系 GEO 頁、decide 頁與 3 則 Telegram 文仍宣稱「絕不自動開啟」。身分未統一前，它同時輸給免費的 iOS 相機（3 次掃描上限）與自己的承諾。上架 2 週、0 評分。優先度：低，但不實宣稱必須立刻修。

## 各市場真正問題
- **en-US**：qr code scanner 第 1 名 1.44M 則；qr code safe 利基開放（對手 0–44 則）但我們缺席，名稱無 safe。
- **ko**：큐싱 只有 11 筆、對手 0–183 則，利基開放；名稱「바로 실행」與訴求相反。
- **en-GB**：缺席；scoreboard CZ／ca「安全連結」詞第 5–6＝安全命名可排名。
- **zh-Hant**：缺席；免費榜第 3／16／24 全是掃碼 App，但相機免費無限；名稱與描述第一句同頁矛盾。

## 行動
| claude | local | you |
|---|---|---|
| 立即改 _full.json、53 個 qrcodehalo.html、decide 頁、3 則 Telegram：改為「預設自動執行；到設定關閉即可先檢查」；統一後寫 Naver 큐싱、r/scams、LinkedIn 草稿 | 產生器模板同步；best-qr-* 頁去 best | 二選一：A 預設不自動開啟（改 App）＋JP／KR 名改回「開く前に確認／열기 전 확인」、ko 加「큐싱 방지」；B 維持自動執行則 TW 名改「掃描與建立」、en-GB 副標改掉。建議 A；免費改「掃描與安全檢查不限次，批次／匯出付費」；加 50 種語言句 |

## 二次審核修正

- 第一輪的定位矛盾已由 4 個店面的線上描述證實；新增：en-GB 副標「Inspect before you open」、decide 頁「qr-scanner-that-shows-the-full-link-before-opening」、best-* 頁「best qr scanner that does not open links automatically」與 3 則 Telegram 文（en／ja／zh-Hant）也都宣稱不自動開啟，53 個語系 GEO 頁全部由過時的 _full.json 生成。
- 我方 GEO／Telegram 的不實宣稱是公開 repo 內容，claude 可立即修正，不需等 ASC；第一輪把它列為外部行動之一，優先度應提到最高。
- 第一輪未納入需求證據：JP Utilities 免費榜 #34「安心スキャン」掃碼 App、scoreboard CZ／ca「安全連結」詞第 5–6 名＝安全命名有需求且可排名。
- 第一輪 en／ko 貼文引用美國城市警告與 KISA 警告；貼文不得附來源連結，故改寫成不引述第三方事件的說法。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| en-US | 「qr code scanner」第 1 名 1.44M 則、我們缺席；「qr code safe」利基其實開放（對手 0–44 則）但我們同樣缺席，因為名稱沒有 safe 且 2 週新 App 權重為零；3 次免費掃描對抗免費無限的相機沒有勝算。 | wsSearch 10/13：qr code scanner 188 筆缺席（QR Reader 1,439,636）；qr code safe 186 筆缺席（DetectQR 0、Safe QR 2／44 則）；lookup US 0 評分、4 張截圖、v1.0.3（10/9 僅更新文案）、上架 2026-09-27。 |
| ko | 「큐싱」只有 11 筆結果、對手 0–183 則，利基開放但我們缺席；線上名稱「QR코드 바로 실행」與큐싱防護訴求相反。 | wsSearch 10/13：큐싱 11 筆缺席（알약M 183、스미싱쉴드+ 2、Clean Links 0、큐링크 1 則）；큐알코드 175 筆缺席（QR코드 리더 51,995）；lookup KR 名稱「QR코드 바로 실행」、0 評分。 |
| en-GB | 「qr code scanner」缺席（第 1 名 184,773）；en-GB 副標「Inspect before you open」與線上預設行為矛盾；但 scoreboard 顯示「安全連結」命名在小店面可排名。 | wsSearch 10/13：gb qr code scanner 190 筆缺席（QR Code Reader 184,773）；scoreboard #8：CZ「bezpečný odkaz」第 5、ES(ca)「enllaç segur」第 6，第 1 名皆 0 則評分；lookup GB 0 評分。 |
| zh-Hant | 「qr code」缺席（第 1 名 245,612）；TW 免費榜第 3／16／24 都是掃碼 App，品類大但 iOS 相機免費無限；TW 名稱「安全掃描與建立」與描述第一句「掃到就直接執行」同頁矛盾；台灣停車單假 QR 已被闢謠，不能拿來行銷。 | wsSearch 10/13：tw qr code 183 筆缺席（QRCode 掃描器 245,612、QR碼掃描儀 24,048）；TW Utilities 免費榜 RSS 10/13 第 3／16／24 為掃碼 App；lookup TW 名稱「QR Code Halo：安全掃描與建立」、線上描述開頭「QR Code Halo 掃到就直接執行」、0 評分。 |
