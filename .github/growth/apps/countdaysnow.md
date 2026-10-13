# CountDaysNow: Event Counter（countdaysnow）

**一句話診斷**：CountDaysNow 上架 17 天、50 個語系的名稱全是英文「Event Counter」，副標題是「每日焦點／오늘의 초점／今日のフォーカス」這類 UI 字串，在倒數日、디데이、カウントダウン這些核心詞上根本沒被索引。

## 結論
上架 17 天、0 評分很正常；不正常的是 50 個語系的名稱全是「CountDaysNow: Event Counter」，副標題是「每日焦點／오늘의 초점／今日のフォーカス」，宣傳文與描述第一行是 UI 字串。倒數日、디데이、カウントダウン 這些核心詞不在任何可索引欄位，scoreboard 已測詞全無名次。學測百日就是現在、수능剩 5 週，列表要在兩週內改完才有意義。

## 各市場真正問題
- **zh-Hant**：名稱副標題無「倒數」，描述開頭看不懂。
- **ko**：關鍵字沒有 디데이，D-day 文化市場卻缺核心詞。
- **ja**：副標題無搜尋詞，Countdown Plan 沒翻。
- **vi**：越南文列表只在 VN 店面顯示，在台越南社群看不到，建議降級。

## 行動
| claude | local | you |
|---|---|---|
| Telegram 補 ko；草擬 Dcard、Clien 貼文 | GEO 產 農曆生日倒數／수능 디데이／推し活 三頁 | 本週內在地化 zh-Hant/ko/ja 名稱與副標題 |
| 草擬 MrMad、蘋果仁 pitch | — | ko 關鍵字補 디데이；各語系第一段改 Countdown Plan |
| scoreboard 挑戰詞（倒數日、디데이、あと何日、品牌詞） | — | 15 秒 Shorts 配合學測／수능時點 |

## 二次審核修正

- 第一版的 vi 市場假設有邏輯漏洞：越南文列表只在 VN 店面顯示，台灣的越南社群看不到；建議從 best_markets 降級，把資源集中在 zh-Hant 與 ko。
- 第一版說 iTunes 不通：本次 lookup 已確認 9 個店面名稱皆未在地化、0 評分；名次因共用配額 403 未測。scoreboard 對本 App 已測詞全部無名次，和「核心詞不在可索引欄位」一致。
- 第一版正確指出 ko 缺 디데이、各語系描述未同步 Countdown Plan；本次逐語系 grep 確認 ja/ko/zh-Hant/vi/de/pt-BR 都沒有 Countdown Plan。
- 時機補充：學測 2027/1 的百日倒數就是現在、수능 2026-11-19 剩 5 週，店主若要改名稱／副標題，這兩週內做才趕得上。
- 六款 App 列表皆無語言數量句，「改 50」不適用；可新增「50 種介面語言、App 內切換」。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 名稱沒在地化、副標題「每日焦點」無搜尋詞、宣傳文與描述第一行是「每日焦點: 過往 · 今天 · 未來 — 儲存」這種介面字串；學測 100 天倒數正好是現在，但使用者打「倒數日」找不到。 | iTunes lookup TW：0 評分，名稱「CountDaysNow: Event Counter」(50 語系皆同，已實測 TW/JP/KR 店面)，2026-09-26 上架、v1.0.3。zh-Hant 描述確認含農曆、民國、動態島、免費 3 事件。「倒數日」名次本次未測得（403）；scoreboard 對本 App 所有已測詞皆無名次。 |
| ko | 韓國是全球最強的 D-day 文化，但 ko 關鍵字沒有「디데이」(只有 카운트다운、100일、수능、전역일)，名稱副標題也沒有；2026-11-19 수능只剩 5 週，窗口就在眼前。 | iTunes lookup KR：0 評分。ko 關鍵字欄原文：카운트다운,생일,날짜계산,…,수능,전역일,…（無 디데이）；ko 描述不含 Countdown Plan 段落。 |
| ja | 副標題「今日のフォーカス」、描述以 UI 字串開頭，Countdown Plan（新主打）只在 en-US 有寫；推し活、受験關鍵字倒是有。 | iTunes lookup JP：0 評分。ja 描述 grep「プラン」= 無；關鍵字含 推し活,受験,旧暦,令和。 |
| vi | 第一版想打「在台越南新住民」，但 vi 列表只會出現在越南店面（locale_storefronts：vi→vn）；在台越南人用台灣 Apple ID 看到的是 zh-Hant 或英文頁。vi 是低產出市場，應降級。 | _engine/geo/locale_storefronts.json：vi→vn、zh-Hant→tw。iTunes lookup VN：0 評分，名稱同為英文。 |
