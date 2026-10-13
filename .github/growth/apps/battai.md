# BattAI（battai）

**一句話診斷**：BattAI 在有需求的詞已站上第 10–42 名（JP「バッテリー劣化」第 10、TW「電池健康」第 15、US「battery health」第 42）卻只有 1 則評分：iOS 設定本來就顯示最大容量，而線上文案真正的差異「預估到 80% 的時間」與「二手／送修電池報告」沒有出現在 TW／JP／KR 的名稱與副標。

## 結論
BattAI 已在有需求的詞站上可見位置（JP バッテリー劣化第 10、TW 電池健康第 15、US battery health 第 42、cycle count 第 13）卻只有 1 則評分：iOS 設定本來就顯示最大容量，而線上文案真正的差異「預估到 80% 的時間」「二手／送修報告」沒進 TW／JP／KR 的名稱副標。Scoreboard 的 3 個第 1 名是「電池健康分數」直譯詞、對手 0 則，不是需求。優先度：中。

## 各市場真正問題
- **zh-Hant**：第 15 名但副標「規則、來源與限制都說清楚」沒有利益點；領先者電池壽命 18,575 則。
- **ja**：第 3 名「バッテリー劣化 充電サイクル記録 交換時期」0 則卻排我們前面＝名稱含詞權重；我們名稱無劣化／売却。
- **en-US**：US 名稱已改「Battery Health & Life」但 en-GB 未同步；線上功能表已刪「Cycles」卻仍靠該關鍵字排第 13，貼文不可宣傳循環次數。

## 行動
| claude | local | you |
|---|---|---|
| PTT MacShop／Mobile01「賣 iPhone 前整理電池資訊」、note「メルカリで売る前に」草稿；Telegram 以二手報告框架發文；回填線上文案 | 6 個 best-battery-* GEO 頁去 best | ASC：副標改「二手轉讓、送修用電池報告」「劣化・交換時期・売却用レポート」「Battery report for resale」；en-GB 名稱同步；zh-Hant 關鍵字補滿；決定 Cycles 與「AI」；加 50 種語言句；錄 PNG 報告影片 |

## 二次審核修正

- 線上 US／TW／JP／KR 描述的「健康」清單已無「Cycles／循環次數」行（repo 仍有），貼文不可宣傳循環次數顯示；US「battery cycle count」第 13 名是靠殘留的 en-US 關鍵字。
- 「Battery Health & Life」只改了 en-US，en-GB 與印尼回退仍是「Battery health score」，兩個英語店面不一致。
- Scoreboard 的 CZ／DK／SA 三個第 1 名全是「電池健康分數」的直譯詞，第 1 名對手 0 則評分，代表沒人搜，不是成長訊號。
- 線上描述已新增「預估到 80% 的時間」「為檢修、二手轉讓或個人留存建立電池報告」「分析最快每 5 分鐘一次」，repo 的 battai_full.json 落後，第一輪引用的 repo 字數問題（副標 32 字、關鍵字超長）需以線上版重新核對。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 第 15 名已可見但不被點：副標「規則、來源與限制都說清楚」是價值宣言不是利益點，報告功能沒進名稱副標；領先者有 18,575 則評分，光靠「健康分數」沒有下載理由。 | wsSearch 10/13：電池健康 170 筆 BattAI 第 15（電池壽命 Battery Life 18,575 則、系統電池分析 143）；lookup TW 1 則評分、6 張截圖、名稱「BattAI: 電池健康分數」。 |
| ja | 第 10 名，但第 3 名「バッテリー劣化 充電サイクル記録 交換時期」0 則評分仍排在我們前面＝名稱含詞權重高；JP 名稱副標沒有劣化／交換時期／売却。 | wsSearch 10/13：バッテリー 劣化 159 筆 BattAI 第 10；バッテリー・ライフ 26,834 則、節電バッテリーライフ 9,661；lookup JP 0 評分。 |
| en-US | 「battery health」第 42／160、「battery cycle count」第 13／132，但線上功能表已刪掉「Cycles」行，仍靠殘留關鍵字排名；US 名稱已改「Battery Health & Life」而 en-GB 與印尼回退仍是舊名；Scoreboard 第 1 名全是「電池健康分數」直譬詞、對手 0 則＝無需求。 | wsSearch 10/13：battery health 160 筆第 42（Battery Life 33,818）；battery cycle count 132 筆第 13；scoreboard #8：US「Battery health score」第 9（第 1 名 12,317 則）、CZ／DK／SA 第 1 但對手 0 則；lookup US 名稱「BattAI: Battery Health & Life」、GB「Battery health score」、0 評分、5 張截圖。 |
