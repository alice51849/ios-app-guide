# Mochi DoneStamp: Last Time（mochidonestamp）

**一句話診斷**：DoneStamp 的需求本來就小又分散，唯一拿到的第 1 名是阿拉伯文「床單」這種沒有意圖的詞；美日台三地都還沒有一個真正會被打出來的搜尋入口，副標題也不含任何搜尋詞。

## 結論
需求小而分散（last time／days since／いつやった／多久一次），2 則評分（US、DE 各 1 則 5 星）。scoreboard 唯一第 1 名是 SA「床單」，沒有意圖價值。en-US 副標題沒有任何搜尋詞、主類別在 Lifestyle，連店主主場台灣也 0 評分。先修入口，再用 Reddit／note 情境文導流。

## 各市場真正問題
- **en-US**：副標題無搜尋詞、類別不對、需求靠 Reddit 情境文。
- **ja**：列表用語自然，純粹缺外部入口。
- **zh-Hant**：名稱「上次何時」不是口語搜尋詞，自家市場沒啟動。

## 行動
| claude | local | you |
|---|---|---|
| 草擬 r/iosapps、r/CleaningTips 回覆、note.com 文 | GEO 補「days since／多久一次」問答頁 | en-US 副標題「Days since & last-time log」；zh-Hant「多久一次・上次是哪天・家事保養」 |
| Telegram 補 zh-Hant，三語加 50 語言句 | — | 評估主類別改 Productivity |
| scoreboard 挑戰詞，de 物品名詞不計成績 | — | 考慮免費 1 件→3 件；錄 20 秒 Shorts |

## 二次審核修正

- 第一版把 Reddit 列為已知有效通路但沒有人去發：正確，但更先決的是 en-US 副標題完全沒有搜尋詞，先改副標題再導流，否則導流進來也接不住品牌搜尋。
- 第一版沒注意主類別是 Lifestyle：同類 App 多在 Productivity／Utilities，類別影響瀏覽與榜單歸屬，是店主可考慮的一次性決定。
- scoreboard 顯示的「第 1 名」(SA「床單」) 不代表需求：de-DE 關鍵字欄是 bettwäsche,pflanzen,familie 這類物品名詞，量出來的名次沒有意義，不應拿來當成績。
- 六款 App 的列表都沒有語言數量句，「改成 50」不適用；可新增「50 種介面語言、App 內切換」一句。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| en-US | 副標題「Remember when you did it」沒有搜尋詞；主類別是 Lifestyle 而非 Productivity，和同類 App 不在同一區。需求小且用詞分散（last time、days since），曝光只能靠 Reddit 情境文。 | iTunes lookup US：5.0★／1 則，主類別 Lifestyle、副 Productivity，v1.0.18，2026-07-21 上架。scoreboard：唯一第 1 名是 SA「ملاءات」(床單)；美國母語詞名次本次未測得（iTunes search 共用配額 403）。 |
| ja | 名稱「いつやった？」和關鍵字（経過日数、家事管理、シーツ）貼近口語，列表本身沒問題；0 評分代表完全沒有外部入口（note／X）。 | iTunes lookup JP：0 評分。ja 關鍵字 100 字滿載且用語自然。名次本次未測得。 |
| zh-Hant | 台灣是店主自己的主場（Mochi 在 TW 有 4 則 5 星），DoneStamp 卻 0 評分：名稱「上次何時」不是台灣人會打的詞，連自家市場都沒啟動。 | iTunes lookup TW：0 評分；zh-Hant 名稱「Mochi DoneStamp：上次何時」，副標題「生活事件、週期與完成紀錄」。 |
