# Cyca: Period & Cycle Tracker（cyca）

**一句話診斷**：Cyca 的差異點（不用帳號、資料只在手機）沒有出現在任何店面會被索引的欄位裡，所以在唯一還有空位的「隱私型經期 App」長尾搜尋也排不進前 50；而在台灣，免費版把預測鎖在 Pro 後面，反而輸給 iOS 內建健康 App。

## Cyca — 結論
不是「沒人要隱私型經期 App」，而是差異點沒寫進會被索引的欄位：US「private period tracker」前 5 名有 0–1 則評分的 App，Cyca 卻不在前 50，因為 private／offline／no account 只在描述裡。TW 唯一排得進的日常字是「月經」#16（經期 #152、生理期 #93）。免費版沒有預測，第一印象輸給免費就有預測的 iOS 健康 App。

## 各市場真正問題
- **zh-Hant**：主字被小月曆（59,045）、Flo（25,228）佔滿；名稱／副標全是通用字；關鍵字含「安全期、基礎體溫」但 App 無體溫功能、自稱不可避孕。評分 3 則。
- **id／vi**：母語字皆不在前 50；ID／VN 店面預設顯示英文版面，台灣店面沒有 id／vi 版面，母語 listing 幾乎無人看到，只能靠社群＋「App 內可切換語言」。評分 0。
- **en-US**：period tracker 是 Flo（199 萬）戰場；private 長尾空著但未被索引。評分 1 則。

## 行動
- **you**：en-US 副標「Private Period Log, No Account」＋關鍵字補 private,offline,no account；zh-Hant 副標放「月經」、刪安全期／基礎體溫，ja 刪避妊／ピル／安全日；考慮把下次經期預測改免費。
- **claude**：id／vi 社群一頁簡介＋管理員請求信；隱私評測 pitch 信稿；成績單加量「月經」「private period tracker」。
- **local**：GEO 決策頁與 visuals 刪掉 listing 沒有的 temperature、intimacy 後重新部署。

## 二次審核修正

- 第一版說「隱私／買斷利基已同質化」，但實測 US「private period tracker」前 5 名有兩款 0–1 則評分的 App，代表這條長尾幾乎沒人守；真正的問題是 Cyca 名稱、副標、關鍵字都沒有 private／offline／no account，描述不被索引。
- 第一版量了經期 #144、生理期 #90、排卵 #51，漏掉台灣最日常的「月經」：Cyca 排 #16，是唯一有機會的 TW 主字；今日複測 經期 #152、生理期 #93、排卵 #51 與第一版一致。
- 第一版把 ID #75、VN #72 視為單純曝光問題，漏掉店面語言機制：ID／VN 店面預設顯示英文版面，台灣店面沒有 id／vi 版面，所以印尼文、越南文 listing 幾乎無人會看到；對移工受眾只能靠社群＋「App 內可切換語言」的訊息。
- 第一版寫 Pro 為 $4.99，但 listing 與 Lookup 都查不到 IAP 價格，貼文不應提價格；維持只講「一次買斷、不訂閱」。
- 確認 GEO 決策頁／visuals 的 cyca.svg 寫了 temperature、intimacy，listing 沒有這兩項功能，需移除。
- Cyca 與 Sereno 的描述完全沒有語言數句子（UsageNow 已寫 50 種），所以「把語言數改成 50」對這兩款不適用，改為建議新增一句「50 種介面語言，可在 App 內切換」。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 主字都被 2 千到 5.9 萬則評分的 App 佔滿，唯一排得進的日常用語是「月經」#16；名稱／副標只重複「經期、排卵、生理期」這些通用字，使用者在搜尋結果裡看不到任何 iOS 內建「健康」App 做不到的理由，而內建功能免費就有預測，Cyca 的免費版卻沒有。zh-Hant 關鍵字還放了「安全期、基礎體溫」，App 沒有體溫功能且描述自己寫「不可作為避孕方法」。 | TW 搜尋（2026-10-13，iTunes Search API）：經期 #152（前 3：小月曆 59,045、Flo 25,228、月經日曆日記 5,653）；生理期 #93；月經 #16；排卵 #51。TW 評分 3 則（4.67）。v1.0.10 自 2026-09-07 未更新。 |
| id | 三個母語字都不在前 50，前面是 Flo（17.5 萬）等巨頭；更關鍵的是印尼店面預設顯示英文（Lookup 回傳名稱是「Cyca: Period & Cycle Tracker」），而在台灣的印尼移工若用台灣 Apple ID，店面根本沒有印尼文版面。所以印尼文 listing 幾乎無人看到，必須靠社群直接告知「App 介面有印尼文，進 App 可切換」。 | ID 搜尋：kalender menstruasi 不在前 50（前 3：Period & Cycle Tracker 25,559、Flo 175,401、My Calendar 1,749）；aplikasi haid 不在前 50；siklus haid 不在前 50。ID 店面評分 0；ID 店面 Lookup 顯示英文名稱。 |
| vi | 與印尼相同：母語字全部不在前 50，越南店面預設顯示英文版面，台灣店面沒有越南文版面；越南的領先者評分數更高（Flo 29.6 萬、MeetYou 7.9 萬）。搜尋不是可行路徑，只能靠新住民社群與服務中心口碑，且訊息要說清楚「App 內有越南文」。 | VN 搜尋：theo dõi kinh nguyệt 不在前 50（前 3：Flo 296,050、MeetYou 79,294、Period & Cycle Tracker 5,791）；lịch kinh nguyệt 不在前 50；chu kỳ 不在前 50。VN 店面評分 0。 |
| en-US | 「period tracker／period calendar」是 Flo（199 萬）等級的戰場，無解；但「private period tracker」的前 5 名裡有 0 則和 1 則評分的 App（Emberly、Private Period Tracker），這條長尾是空的，Cyca 卻排不進前 50，因為「private／no account／offline」只寫在不被索引的描述裡，名稱、副標、關鍵字一個字都沒有。 | US 搜尋：period tracker 不在前 50（前 3：Flo 1,994,330、Period Tracker Period Calendar 174,217、Period Tracker by GP Apps 78,383）；period calendar 不在前 50；private period tracker 不在前 50（前 5：Emberly Private Period Tracker 1、Clover 23,434、Period Tracker 8,292、Private Period Tracker 0、Period Tracker Period Calendar 174,240）；品牌字 cyca #1。US 評分 1 則。 |
