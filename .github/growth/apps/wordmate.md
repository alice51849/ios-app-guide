# Wordmate：44 種語言背單字（wordmate）

**一句話診斷**：Wordmate 的真正問題是 NT$290／¥1,500／$8.99 的付費牆配上 0–1 則評分，而它主打的小工具／手錶長尾詞幾乎沒有搜尋需求（日本該詞第 1 名只有 9 則評分），Lite 又沒有在兩邊店面頁互相指引。

## 結論
Wordmate 卡在「付費牆 × 零評分 × 賣點沒有搜尋量」。NT$290／¥1,500／$8.99 要先付，三個店面只有台灣 1 則評分；主打的小工具／手錶長尾詞在日本第 1 名也只有 9 則評分，在台灣被記事本類小工具污染。Lite 明明是免費試用入口，兩邊店面頁卻互不提及。

## 各市場真正問題
- **ja**：「単語 ウィジェット」第 62/112（第 1 名 9 則）；「単語帳」不在前 181（WordHolic 150,954、Quizlet 84,815）；¥1,500、0 評分。
- **zh-Hant**：「背單字」不在前 182；「單字 小工具」第 29（第 1 是記事本 24,855）；品牌字被 wormate.io 遊戲壓在前 3；NT$290、1 則評分。
- **en-US**：「vocabulary」是英文單字工具的地盤（219,835／329,442 則）；「apple watch vocabulary」第 1 名只有 15 則；$8.99、0 評分。降為最低優先。

## 修正第一輪
與 Lite 的差異還包括「例句」；「44」是學習語言數，介面語言 50 要另加一行而非改掉 44（binary 宣告也只有 44 個本地化碼，下一版需同步）；en-US 不該是第三市場；品牌字被遊戲占據；例句範圍矛盾確認。

## 行動
**claude**：六語系互指段落與差異表；更新 Telegram 文案（導向 Lite、加 50 種介面語言）；r/AppleWatch 貼文與 15 秒影片腳本。
**local**：app_pairs.py 生成 Lite vs Wordmate 比較頁、重生 hubs；排程 Threads。
**you**：ASC 名稱副標改成小工具＋手錶、第一段互指 Lite、加介面 50 種語言；定價實驗或明確分工；釐清例句範圍；確認 iPhone Duo；App 內評分請求；錄 15 秒影片。

## 二次審核修正

- 第一輪說 Lite 解鎖後與 Wordmate 只差小工具、Watch、84 單元；依 live 文案 Wordmate 還多了「自然例句」（Lite 描述完全沒提例句），差異應寫成：小工具、Apple Watch、例句、84 個循序單元。
- 「44 種語言」是學習語言數，不是介面語言數；owner 確認的 50 是介面語言。ASC 動作不是把 44 改 50，而是加一行「介面 50 種語言，可在 App 內切換」，44 學習語言維持。lookup 的 languageCodesISO2A 只有 44 個，表示 binary 宣告的本地化也是 44，下一版 build 需同步到 50。
- 第一輪把 en-US 列為第三市場；live 數據顯示 US 搜尋意圖錯配且 Watch/widget 詞需求極小，應只做一篇 r/AppleWatch，資源給 ja/zh-Hant。
- 例句範圍矛盾確認存在：live TW 描述第一段「學英文時每個單字都附例句」，後文「搭配自然例句」；需 owner 說明是否只限英文。
- 品牌字「wordmate」在 TW 被 wormate.io 系列遊戲占前 3，第一輪沒提；外宣要用全名或直接講功能。
- v1.0.9 只是文案更新；描述結尾同樣有「針對 iPhone Duo 最佳化」，待 owner 確認。
- 成績單：1 則評分、1 個店面、最佳搜尋名次「—」（尚未輪到量測）。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| ja | 「単語 ウィジェット」前 8 名評分只有 0–9 則，這個長尾幾乎沒人搜；真正有量的「単語帳」被 WordHolic、Quizlet 占據且我們不在前 181；¥1,500 買い切り、0 評分、沒有試用入口（Lite 在店面頁上沒被提到）。 | JP「単語 ウィジェット」Wordmate 第 62/112（第 1「1日1英単語ウィジェット」9 則）；JP「単語帳」不在前 181（WordHolic 150,954、Quizlet 84,815）；JP「単語 買い切り」不在 36 筆；lookup JP ¥1,500、n=0、v1.0.9（2026-10-09 僅更新文案）。 |
| zh-Hant | 「背單字」被免費大品牌占據、我們不在前 182；「單字 小工具」被記事本類小工具 App 污染（第 1 是記事本 24,855），我們第 29；NT$290 付費只有 1 則評分；連品牌字「wordmate」都被 wormate.io 貪食蛇遊戲壓在前 3 名。 | TW「背單字」不在前 182（單字庫 35,151、WORD UP 23,341、多益知識王 37,791、多鄰國 138,601）；TW「單字 小工具」第 29/162；TW「wordmate」第 4（前 3：wormate.io 997、蟲蟲禁區 7,217、slither.io），Lite 第 9；lookup TW NT$290、5★ n=1。 |
| en-US | 美國「vocabulary」意指英文單字工具（Vocabulary 219,835、Merriam-Webster 329,442），不是外語學習；「apple watch vocabulary」第 1 名 Watch Words 只有 15 則、LexWidget 3 則，需求極小；「learn languages」是 Duolingo 5.5M 的地盤。$8.99 付費、0 評分，US 應降為最低優先，只做一篇 r/AppleWatch。 | US「vocabulary widget」不在前 179；US「apple watch vocabulary」不在前 180；US「learn languages」不在前 194（Duolingo 5,502,278、Babbel 755,792）；lookup US $8.99、n=0。 |
