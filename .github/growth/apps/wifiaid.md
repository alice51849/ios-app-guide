# WiFi Aid（wifiaid）

**一句話診斷**：付費版在 10/13 的 13 組母語搜尋全部缺席（連只有 2 筆結果的 TW「無法上網」、JP「ネット繋がらない」都只出現 Lite），它唯一不在 Lite 裡的功能是 Apple Watch、小工具與 iPad，卻沒寫進任何名稱或副標。

## 結論
付費版（US$5.99／NT$190／¥1,000）在 10/13 的 13 組母語搜尋全部缺席，連只有 2 筆結果的 TW「無法上網」、JP「ネット繋がらない」都只出現 Lite。它唯一不在 Lite 裡的功能是 Apple Watch、小工具、iPad，卻沒寫進任何名稱或副標。優先度：低；所有外宣以 Lite 為入口。

## 各市場真正問題
- **ja**：ネット 遅い 11 筆、ネット 繋がらない 2 筆，付費版都不在；對手只有 0–12 則評分。問題不是競爭，是沒有搜尋權重。
- **zh-Hant**：無法上網僅 2 筆結果＝沒人這樣搜；大眾搜「網路測速」（測網速大師 12,913 則），本 App 不是測速。
- **en-US**：connected but no internet（165 筆）被 eero 206k、Cox 133k 佔滿，付費獨立 App 無法靠搜尋。

## 行動
| claude | local | you |
|---|---|---|
| 外宣與 Telegram 一律導向 Lite，付費版只在 Watch／iPad 段落出現；撰寫 note.com、Reddit 草稿；回填 _full.json 線上文案 | GEO 產生器移除「best app… is a great choice」模板 FAQ 與 best-* 頁 | ASC：副標改成「Apple Watch, Widget & iPad」類，關鍵字留 watch／widget／ipad／買斷；把線上 TW／JP 的情境式描述移植到 en-US；評估印尼 Rp119k 價格；決定是否維持兩個 SKU；錄 20 秒 Watch 示範 |

## 二次審核修正

- 第一輪說「文案以 DNS/TCP/TLS 術語開頭」只對 en-US／en-GB 成立：線上 zh-Hant／ja／ko 描述已改成「網路又卡住了」的情境式開場，repo 的 wifiaid_full.json 仍是舊的條列版，需回填。
- 第一輪量到 US「wifi troubleshoot」Lite 第 74 名，今日為第 116 名（下滑中）；付費版在今日 13 組搜尋全部缺席，不只是被 Lite 搶走流量，而是幾乎沒有搜尋權重。
- 第一輪未點出兩版的功能差異：線上 Lite 描述沒有 Apple Watch／小工具／iPad（Lite 列的是 Connected Node），這三項是付費版唯一可宣傳的差異，應成為定位主軸。
- 六款上架文案都沒有語言數量句，不需要「改成 50」的 ASC 動作；但可新增「50 種介面語言、App 內切換」作為對免費對手的差異。
- 印尼店面 lookup 預設回英文，加 lang=id_id 證實印尼文資料已上線，第一輪的 id 相關判斷不受影響。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| ja | 付費版不在「ネット 遅い」（11 筆）與「ネット 繋がらない」（2 筆）任何結果內，Lite 在；問題不是競爭而是付費 App 幾乎沒有搜尋權重，日本使用者不會為看不到的 App 付 ¥1,000。 | iTunes wsSearch 10/13：ネット 遅い 共 11 筆、Lite 第 11、付費版缺席（對手 NetDoctor 0 則、ネット不調チェッカー 12 則）；ネット 繋がらない 共 2 筆、Lite 第 2、付費版缺席；lookup JP 評分 0、¥1,000。 |
| zh-Hant | 「無法上網」只有 2 筆結果＝沒人這樣搜，關鍵字欄雖含此詞也無效；TW 大眾的搜尋行為是「網路測速」，本 App 不是測速工具，無法在該詞取勝。 | wsSearch 10/13：無法上網 共 2 筆（Lite 第 2、付費版缺席）；網路檢測 113 筆 Lite 第 99、付費版缺席，前 10 全是免費測速 App（測網速大師 12,913 則）；lookup TW 評分 1 則、NT$190、10 張截圖。 |
| en-US | 痛點詞被電信商與路由器 App 壟斷，付費獨立診斷 App 無法靠搜尋取得曝光；唯一通路是揭露身分的 Reddit 問答，而且應把人導到 Lite。 | wsSearch 10/13：connected but no internet 165 筆（eero 206k、Cox 133k、Starlink 115k 則），兩版皆缺席；wifi troubleshoot 171 筆 Lite 第 116、付費版缺席（NETGEAR 708k）；internet not working 179 筆缺席（Xfinity 1.39M）；lookup US 評分 0、$5.99。 |
