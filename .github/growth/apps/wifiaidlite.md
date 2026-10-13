# WiFi Aid Lite（wifiaidlite）

**一句話診斷**：Lite 已出現在每個母語微利基（TW「無法上網」第 2／2、JP「ネット繋がらない」第 2／2、ID「wifi lemot」第 1／4、JP「ネット遅い」第 11／11），但這些詞幾乎沒人搜；真正的槓桿是名稱加搜尋詞與店外問答導流，而且我們的 GEO 頁與 repo 仍宣稱「每項工具各免費一次」，線上實際是「合計一次」。

## 結論
Lite 已出現在每個母語微利基（TW 無法上網 2／2、JP ネット繋がらない 2／2、ID wifi lemot 1／4、JP ネット遅い 11／11），但這些詞幾乎沒人搜；真正的槓桿是名稱加搜尋詞＋店外問答導流。另一個急件：線上實際是「所有工具合計免費檢查一次」，我們的 GEO 頁與 repo 仍寫「每項工具各一次」。優先度：中。

## 各市場真正問題
- **ja**：排最後一名，因為前面的 App 名稱就含「ネット不調」「Wi-Fi診断」；我們的 JP 名稱只有品牌字。
- **zh-Hant**：需求在 Dcard 租屋板、PTT 的真實提問，不在搜尋框；網路檢測 113 筆我們第 99。
- **en-US**：wifi troubleshoot 第 116（第一輪 74，下滑）；痛點詞被 ISP App 壟斷。
- **id**：wifi lemot 第 1 但只有 4 筆＝量趨近零；靠在台移工社群。

## 行動
| claude | local | you |
|---|---|---|
| 修正 _full.json 與各語系 wifiaidlite.html 的免費額度句（合計一次＋解鎖含修正前後對照）；JP X 回覆、Dcard 教學、印尼社團貼文草稿 | 產生器改掉 12 個 best-* 頁與「is a great choice」模板 FAQ | ASC：名稱加詞（zh-Hant「網路斷線檢查」、ja「ネット不調チェック」、ko「인터넷 안됨 진단」）、副標「Wi-Fi or the website?」、加「50 種介面語言」句；考慮免費額度改 2 次；本人帳號每週 ≤3 則回覆 |

## 二次審核修正

- 線上 US／TW／JP／ID 描述已證實是「所有工具合計可完整檢查一次」；repo 的 wifiaidlite_full.json 與至少 6 個語系的 GEO 頁（含 meta／og／twitter 描述）仍寫「每項工具各含一次免費」→ 我方頁面目前對使用者作出不實宣稱，需立即修正。
- 線上文案新增「一次解鎖後可查看修正前後對照」，第一輪與 repo 都沒提到，這是解鎖最具體的理由，貼文可用。
- 第一輪「Connected Node 需精確位置會讓人卻步」證據不足，刪除。
- US「wifi troubleshoot」由第一輪的第 74 名掉到今日第 116 名。
- Scoreboard 的 ES（ca）「avaria internet」第 1 名，第 1 名對手 0 則評分，代表沒人搜這個詞，不是成長訊號。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| ja | 排在最後一名，因為前面的 App 名稱就含「ネット不調」「Wi-Fi診断」，我們的 JP 名稱只有品牌字「WiFi Aid Lite」；利基極小（11 筆）但名稱加詞＋少量真實下載就能進前 3，是低成本的小勝利而非成長引擎。 | wsSearch 10/13：ネット 遅い 11 筆，Lite 第 11；前 3 名 NetDoctor 0 則、ネット不調チェッカー 12 則、Wi-Fi診断 - 遅い原因を特定 0 則；ネット 繋がらない 2 筆、Lite 第 2；lookup JP 名稱「WiFi Aid Lite」、0 評分。 |
| zh-Hant | 「無法上網」只有 2 筆結果＝沒人這樣搜；大眾搜「網路測速」而我們是診斷不是測速；需求在 Dcard 租屋板、PTT 的真實提問，不在搜尋框。 | wsSearch 10/13：無法上網 2 筆 Lite 第 2；網路檢測 113 筆 Lite 第 99，前 10 皆免費測速 App（測網速大師 12,913、測網速 10,689 則）；lookup TW 名稱只有「WiFi Aid Lite」、0 評分。 |
| en-US | 連 165–179 筆結果的痛點詞都被 ISP／路由器 App 佔滿，Lite 第 116 或缺席；只能用揭露身分的 Reddit 回答導流。 | wsSearch 10/13：wifi troubleshoot 171 筆 Lite 第 116（第一輪 74；NETGEAR 708k、eero 206k）；connected but no internet 165 筆缺席；internet not working 179 筆缺席；lookup US 0 評分。 |
| id | 「wifi lemot」我們第 1，但總共只有 4 筆＝搜尋量趨近零；印尼市場靠在台移工社群（經管理員同意）而非搜尋。 | wsSearch 10/13：wifi lemot 4 筆 Lite 第 1（其餘 0 則評分）；lookup id&lang=id_id 證實印尼文店面資料已上線（名稱「WiFi Aid Lite」、描述「total satu pemeriksaan lengkap」）；0 評分。 |
