# Sono Note（sononote）

**一句話診斷**：名稱已補上「錄音轉文字／文字起こし／Voice to Text」，台灣該詞前 200 名仍沒有我們——0 下載的 App 在最擁擠的詞裡進不了榜；母市場描述還是機翻，而 live 隱私文案已改寫、第一輪貼文的「全程在裝置上」不再成立。

## 結論
名稱已補關鍵字（US「Voice to Text Notes」、TW「錄音轉文字」、JP「音声を文字起こし」），台灣與日本的頭部詞前 200 名仍沒有我們，正面撞內建語音備忘錄、Otter（US 84,495）與 Notta（JP 27,071）；台灣母市場描述仍是機翻；live 隱私文案已改為「Apple 語音辨識部分語言可能傳音訊給 Apple，可選僅限本機」，第一輪貼文的「全程在裝置上」不再成立。評分：TW 2，其餘 0。

## 各市場真正問題
- **zh-Hant**：機翻描述毀信任；差異（摘要＋待辦＋郵件、就醫範本）不在名稱副標。
- **ja**：「文字起こし」被 Notta（27,071）等佔住，我們不在前 200；差異只能靠情境內容講。
- **en-US**：大詞＋0 評分；免費 3 分鐘對不上 lecture／meeting 關鍵字。
- **id**：店面名稱是光的「Sono Note」，搜不到；陪診情境需先實測。

## 第一輪修正
名稱已含關鍵字（KR／ID 除外）；貼文隱私句全部改寫；語言數句「數十種」→ 50（ASC）。

## 行動
| claude | local | you |
|---|---|---|
| zh-Hant 描述自然中文改寫稿 | 重匯出 sono_full／sononote_full；確認關鍵字版本 | 貼上改寫描述；KR／ID 名稱加關鍵字；副標改「摘要、待辦與郵件」 |
| 4 則貼文入庫（id 標記需實測）；量測覆寫會議記錄 摘要／議事録 要約／voice memo summary | threads-autopilot 排程 | 「數十種語言」改 50；實測印尼文介面＋中文錄音、僅限本機模式 |
| 30 秒示範腳本 | | 本人向看護雇主社團版主徵求同意再分享；評估 3 分鐘上限 |

## 二次審核修正

- 第一輪說「名稱 Sono Note 不含任何關鍵字」：live US／TW／JP 名稱已含關鍵字，只有 KR、ID 等仍是光名稱；sono_full.json／sononote_full.json 過時。
- 但名稱含「錄音轉文字」後，台灣該詞前 200 名仍沒有我們：名稱在地化是必要非充分，排名要靠真實下載推動，外宣才是主要槓桿。
- 第一輪貼文寫「全程在 iPhone 上處理／no cloud／機內モードでも同じ」：live 文案已改為「使用 Apple 語音辨識，部分語言可能傳音訊給 Apple；僅限本機模式才全在裝置」。四則貼文已改寫。
- 描述的語言數句子是「dozens of languages／數十種語言」：依店主確認改為 50，列為 ASC 行動。
- 第一輪「免費每天 3 則、每則 3 分鐘」「就醫範本」「Pro 最長 3 小時」皆與 live 相符，保留。
- 第一輪說競品評分未查證：Otter US 84,495、JP 6,065（lookup）；日本「文字起こし」實際由 Notta（27,071）領頭，台灣「錄音轉文字」由雅婷逐字稿（5,620）領頭。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 名稱已改「Sono Note：錄音轉文字」，但「錄音轉文字」185 筆結果裡我們不在前 200——名稱加關鍵字是必要卻不夠，0 評分、0 下載的 App 進不了榜；對手雅婷逐字稿 5,620、西瓜筆記 2,819、SoundType 920。唯一有評分的店面（2 則）描述仍是機翻腔（「擁有讓你驕傲的文字」），差異（摘要＋待辦＋郵件、就醫範本）沒在名稱或副標。 | iTunes search 2026-10-13 limit 200，country=tw「錄音轉文字」：n=185，我們不在列；#1 雅婷逐字稿（5,620）、#2 SoundType AI（920）、#3 西瓜筆記（2,819）、#4 錄音轉文字: 語音備忘錄（246）、#5 AI 會議記錄（580）。iTunes lookup 2026-10-13：TW 名稱 Sono Note：錄音轉文字，評分 2（5.0），描述首句「自然地說話，擁有讓你驕傲的文字」。成績單 issue #8（2026-10-13 04:31 UTC）：最佳名次 14（DK stemmenotater）。 |
| ja | 名稱已是「Sono Note：音声を文字起こし」，但「文字起こし」187 筆結果我們不在前 200；頭部被 Notta（27,071）、無限もじおこし（5,263）、LINE WORKS AiNote（4,825）佔住，日本並不比美國鬆。差異點（要約＋ToDo＋フォローアップメール、受診メモ）只能靠情境內容講出來，搜尋進不去。 | iTunes search 2026-10-13 limit 200，country=jp「文字起こし」：n=187，我們不在列；#1 Notta（27,071）、#2 無限もじおこし（5,263）、#3 文字起こしさん（701）、#4 LINE WORKS AiNote（4,825）、#5 議事録アプリ（178）。iTunes lookup 2026-10-13：JP 名稱 Sono Note：音声を文字起こし，評分 0；Otter JP 6,065（lookup）。 |
| en-US | Otter 在美國 84,495 則評分；我們 0 評分，名稱「Voice to Text Notes」撞大詞。免費每則 3 分鐘對不上 lecture／meeting 關鍵字帶來的人。live 隱私文案已改成「Apple 語音辨識部分語言可能傳音訊給 Apple，可選僅限本機模式」，貼文不能再寫 no cloud。 | iTunes lookup 2026-10-13：US 名稱 Sono Note: Voice to Text Notes，評分 0；描述「Transcription uses Apple's speech recognition, which may send audio to Apple for some languages; choose Local Only mode…」；免費 3 則／天、3 分鐘。Otter US 84,495 則。 |
| id | 印尼店面名稱（lang=id）就是光禿禿的「Sono Note」，沒有任何關鍵字，等於搜不到；在台印尼看護陪診情境成立，但要先實測印尼文介面＋中文錄音，且貼文要說明只切介面、不翻譯。 | iTunes lookup 2026-10-13 lang=id_id：trackName「Sono Note」，評分 0；描述為印尼文。KR 同樣是光名稱「Sono Note」。 |
