# Stay Clock: Flip Desk Clock（stayclock）

**一句話診斷**：Stay Clock 名稱在英、日、德、台都主打「Flip／パタパタ／Klapp／翻頁」，描述卻一個字都沒提翻頁錶面，搜翻頁時鐘進來的人會失望；它真正能贏的是舊 iPad 床頭／長輩大字鐘這類沒人經營的長尾，scoreboard 已在 SA 床頭櫃一詞排第 3。

## 結論
上架 20 天、1 則評分（TW 5 星）正常。名稱在英、日、德、台都承諾「Flip／パタパタ／Klapp／翻頁」，描述卻完全沒有翻頁錶面（只有手寫紙感免費錶面＋100 款顏色字型），搜翻頁鐘進來會失望，也打不贏萬級評分的翻頁鐘 App。可贏的是沒人經營的長尾：舊 iPad 床頭鐘、長輩大字鐘、OLED 夜間紅光；scoreboard 已在 SA「床頭櫃」排第 3、CZ 第 10。內建 StandBy 是免費對手，列表沒說差異。

## 各市場真正問題
- **en-US**：flip 被佔、副標題無 nightstand／old iPad、沒講 StandBy 差異。
- **ja**：パタパタ時計是特定產品類型，名稱承諾過頭。
- **de-DE**：Klapp 同理；Apple 論壇有舊 iPad 當鐘的討論但我們不在。
- **zh-Hant**：唯一有評分；長輩大字鐘情境可打。

## 行動
| claude | local | you |
|---|---|---|
| Telegram 補 de、ko；草擬 r/ipad、r/desksetup、Apfeltalk 文案 | GEO 補「舊 iPad 當床頭鐘」四語問答頁 | 決定 Flip：有就寫進描述與首圖，沒有就改名「Big Desk Clock／置き時計／大字桌鐘」 |
| scoreboard 挑戰詞（flip clock、nightstand clock、パタパタ時計、翻頁時鐘） | — | 副標題改 nightstand／old iPad／夜間紅光；加 StandBy 差異句 |
| — | — | 15 秒舊 iPad 前後對比影片 |

## 二次審核修正

- 第一版推測上架約 2026 年 9 月：實測 2026-09-23 上架，20 天、1 則評分，0 評分在此階段正常；重點是修名稱與內容不符，不是衝評分。
- 第一版說名次無法實測：scoreboard 已有 SA 第 3、CZ 第 10（床頭櫃一詞），證明「床頭／nightstand」長尾確實有我們的位置；主要市場名次本次因共用配額未測。
- 第一版正確指出 Flip 名稱與描述不符；本次逐語系 grep 確認 en/ja/de 描述零提及，只有 zh-Hant 關鍵字欄有「翻頁時鐘」。
- 列表已寫「Switch the app language instantly／隨時切換 App 語言」但沒寫數量，可補「50 種」；六款 App 都沒有語言數量句，「改 50」不適用。
- Telegram 佇列有 en/ja/zh-Hant 但缺 de（第一版列 de-DE 為主要市場）。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| en-US | 「flip clock」被萬級評分對手佔住，而我們的列表沒有翻頁錶面（描述只說一款手寫紙感免費錶面＋100 款顏色字型）。副標題「Always-on time and calendar」沒有 nightstand、old iPad 這類真實長尾詞；內建 StandBy 免費就能做到「充電看時間」，列表沒說 iPad／直式／電量下限／夜間紅光是 StandBy 做不到的。 | iTunes lookup US：0 評分，2026-09-23 上架、v1.0.6，Utilities＋Lifestyle，Free。en-US 描述 grep flip = 無；關鍵字含 nightstand,standby,bedside,oled。scoreboard：SA「منضدة السرير」(床頭櫃) 第 3（第 1 Desk Clock - Analog Clock Face 1,251 則）、CZ「noční stolek」第 10（第 1 148 則）。美國名次本次未測得（403）。 |
| ja | 「パタパタ時計」在日本是特定的翻頁鐘產品類型，名稱這樣寫等於承諾翻頁動畫；描述卻沒有。デスクツアー族群是對的受眾，但要用「古いiPad を置き時計に」切入。 | iTunes lookup JP：0 評分，名稱「Stay Clock:パタパタ卓上時計」。ja 描述 grep パタパタ／フリップ = 僅名稱；關鍵字有 置き時計,ナイトスタンド,焼き付き防止,大きい文字。 |
| de-DE | 名稱「Klapp-Tischuhr」同樣承諾翻頁；德國 Apple 論壇對「altes iPad als Uhr」有討論但我們不在。 | iTunes lookup DE：0 評分，名稱「Stay Clock: Klapp-Tischuhr」；de 描述無 Klapp／Flip 字樣。 |
| zh-Hant | 唯一有評分的店面（1 則 5 星）；名稱「翻頁桌鐘」、關鍵字含「翻頁時鐘」，一樣有名稱與內容不符的風險；長輩大字鐘、舊 iPad 再利用是台灣可打的情境。 | iTunes lookup TW：5.0★／1 則。zh-Hant 關鍵字：數位時鐘,床頭時鐘,翻頁時鐘,…,放大時間,防烙印,護眼夜間模式,平板時鐘。 |
