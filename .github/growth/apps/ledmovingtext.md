# LED Moving Text（ledmovingtext）

**一句話診斷**：唯一真正的問題是名稱：各店面都叫英文「LED Moving Text」，而台日韓第 2–5 名有 2、8、63 則評分的小 App 只因名稱帶「跑馬燈／電光掲示板／전광판」就排前五；外宣貼文有效，但沒有名稱在地化排名不會動。

## LED Moving Text（6806639602）— 優先度：中

**結論**：唯一真正的問題是名稱。各店面都叫英文「LED Moving Text」，而 TW「跑馬燈」#5（8 則評分）、JP「電光掲示板」#2（63 則）、KR「전광판」#5（2 則）都只因名稱帶在地詞就排前五。我們 TW #46、JP #115、KR #151。評分不是門檻，名稱才是；貼文有效，但名稱不改排名不會動。

**各市場真正問題**
- zh-Hant：名稱無「跑馬燈」；多句輪播沒寫進 zh-Hant 描述。
- ja／ko：名稱無「電光掲示板／전광판」。
- th：泰文詞不在榜、前五全英文名，降為測試。
- de-DE：成績單的「Leuchttafel #4」只有 6 筆結果，是假機會；真實詞 Laufschrift 沒被量到。

**行動**
- claude：修 growth_scoreboard.py（排除 result_count<30、加覆寫詞）；3 支影片腳本；活動日曆與貼文排程表。
- local：threads-autopilot 接排程，每帳號每天 ≤3 則、連結放留言。
- you：名稱在地化（跑馬燈／電光掲示板／전광판／ป้ายไฟวิ่ง＋品牌）；en-US 副標改「LED Banner & Scrolling Sign」；三語描述補多句輪播；de-DE keywords 前三放 Laufschrift；市集示範不做付費業配。

## 二次審核修正

- 第一輪的「名稱沒在地化」診斷正確，補上決定性證據：TW #5 只有 8 則、JP #2 只有 63 則、KR #5 只有 2 則評分，皆因名稱命中——評分不是門檻，名稱才是。
- 成績單（issue #8）把 DE「Leuchttafel」#4 列為機會：該詞只有 6 筆結果，是量測假象；growth_scoreboard.py 已記錄 result_count 但 opportunities() 沒用它。
- 第一輪把 th 列為四大市場之一：實測泰文詞不在榜、前五全是英文名 App，th 降為測試。
- 第一輪說 Cue Flow 只在 en-US：正確，但 zh-Hant Telegram 貼文已用「一行一句、2–20 秒輪播」描述（來自 en-US listing），可繼續使用，不必等 ASC；listing 沒說這功能免費或付費，貼文不得歸類。
- 第一輪沒注意 de-DE 副標已有「Laufschrift und Leuchtschild」且德國對手第 1、2 名 0 則評分——DE 是值得量測的低競爭市場。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | TW「跑馬燈」#46；前 4 名名稱全是「跑馬燈」，#5「追星跑馬燈」只有 8 則評分。zh-Hant 名稱沒有「跑馬燈」，多句輪播（Cue Flow）也沒寫進 zh-Hant 描述。 | TW「跑馬燈」#46／169（#1 跑馬燈－LED跑馬燈 8,123、#2 2,294、#3 827、#4 LED廣告牌臨 2,842、#5 追星跑馬燈 8 則）。Lookup TW：免費、0 則、上架 2026-09-17、名稱「LED Moving Text」。 |
| ja | 「電光掲示板」#115；#2「電光掲示板(シンプル)」只有 63 則評分——名稱命中即可排第 2。ja 名稱無「電光掲示板」。 | JP「電光掲示板」#115／168（#1 LEDバナープロ 16,660、#2 電光掲示板(シンプル) 63、#3 3,224、#4 260、#5 1,063）。Lookup JP：0 則。 |
| ko | 「전광판」#151；#3「전광판」123 則、#4 23 則、#5「전광판: LED」2 則評分——同樣是名稱命中。 | KR「전광판」#151／181（#1 LED 전광판 4,380、#2 어썸 141、#3 123、#4 23、#5 2）。Lookup KR：0 則。 |
| th | 「ป้ายไฟวิ่ง」183 筆無我方；前五全是英文名「LED Banner」類（357–6,729 則），泰國使用者的搜尋習慣不明，th 應列為測試市場而非主市場。 | TH「ป้ายไฟวิ่ง」183 筆（#1 LED Banner - Big Text Maker 357、#4 LED Scroller 1,976、#5 LED Banner Pro 6,729）；th 副標「ป้ายไฟวิ่งบนหน้าจอ」已含該詞仍不在榜。 |
| de-DE | 成績單把 DE「Leuchttafel」#4 列為機會，但這個詞只有 6 筆結果，沒人搜；真實詞「Laufschrift」在副標卻不在 keywords 前三，所以沒被量測。德國對手第 1、2 名 0 則評分，值得量。 | DE「Leuchttafel」6 筆（#1、#2 皆 0 則評分；我方 #4）；de-DE keywords 前三：Leuchttafel,Anzeigetafel,Namensschild；issue #8（2026-10-13）列為「最接近第 1 名」。 |
