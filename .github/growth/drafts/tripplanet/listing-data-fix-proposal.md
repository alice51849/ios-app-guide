# Trip Planet：tripplanet_full.json 修正內容（名稱、關鍵字、宣傳文字）（供 tripplanet-01 使用）

| 項目 | 內容 |
|---|---|
| 用途 | `_engine/data/tripplanet_full.json` 仍是舊名「Lumi Trip Planet 環球旅行／世界の旅」，關鍵字有機翻詞（雜誌、使命、ジャーナル），宣傳文字是機翻（「轉『我們到了嗎？』變成樂趣」）。GEO 頁、catalog、計分板都從這個檔繼承，所以要先修這裡。這份檔案列出可直接貼上的新值 |
| 發在哪／給誰 | 給有權限編輯 `_engine/data/tripplanet_full.json` 的人（本次**沒有修改**資料檔）。之後由本機 GrowthEngine 重產 GEO 頁（tripplanet-04） |
| 發文者 | 不對外發布；資料檔變更由店主 Guan Feng Lai 核准 |
| 使用規則 | name 必須和 App Store live 名稱一致；關鍵字每語系 ≤100 字元、前三個是計分板要量的詞；宣傳文字 ≤170 字元，只寫商店描述裡有的功能。ASC 上的關鍵字是否同步改，由店主在 tripplanet-05 決定 |
| 事實依據 | live 名稱（tripplanet.md，2026-10-13 lookup）：TW「Trip Planet 親子旅行遊戲」、JP「Trip Planet 子ども旅行ゲーム」、KR「Trip Planet 아이 여행 게임」、US「Trip Planet: Kids Quest」。功能：tripplanet_full.json en-US 描述（任務包：飛行日、飯店、美食、博物館、善良、勇敢、回憶；旅行護照章；旅行故事卡；iCloud 家庭共享；Plus） |
| 不能寫 | trip planner／旅行計劃（App 不是行程規劃工具）；雜誌、使命、ジャーナル、신문；離線（描述沒寫）；年齡範圍 |

---

## name

| 語系 | 新值 |
|---|---|
| zh-Hant | Trip Planet 親子旅行遊戲 |
| ja | Trip Planet 子ども旅行ゲーム |
| ko | Trip Planet 아이 여행 게임 |
| en-US | Trip Planet: Kids Quest |

> 其餘語系的 name 請以各店面 live lookup 為準，不要用這四個推測。

## keywords（前三個是計分板量測詞）

| 語系 | 新值 | 字元數 |
|---|---|---|
| zh-Hant | `帶小孩出國,飛機上 小孩,親子旅行,旅行任務,兒童,旅行遊戲,寒假,春節,出國,日本,護照章,機場,飯店,博物館,家庭旅行,獎勵,回憶,搭飛機,打發時間,機上,行前準備` | 84 |
| ja | `子連れ旅行,旅行 子ども,機内 子ども,子連れ 飛行機,ミッション,パスポート,スタンプ,家族旅行,春休み,年末年始,空港,ホテル,美術館,思い出,ごほうび,暇つぶし,帰省` | 86 |
| en-US | `road trip games for kids,travel bingo,kids travel missions,flight,airplane,vacation,passport,quest` | 98 |

## promotionalText

| 語系 | 新值 | 字元數 |
|---|---|---|
| zh-Hant | 帶小孩出國，等待最難熬？出發前選好任務包，孩子在機場、飛機上、飯店和博物館都有小任務可以完成。走完一趟旅程，旅行護照蓋一個章，還有自動產生的旅行故事卡。 | 76 |
| ja | 子連れ旅行の待ち時間を、小さなミッションに。空港、機内、ホテル、美術館で挑戦できるミッションパック。旅を終えたらパスポートにスタンプ、旅のストーリーカードも自動でできあがります。 | 89 |
| en-US | Turn travel waits into small real-world quests. Mission Packs for flights, hotels, food and museums; finish a trip to earn a passport stamp and a Trip Story Card. | 162 |

## 套用後檢查

- [ ] 四個語系的 name 和 live 一致，檔內沒有「Lumi Trip Planet」
- [ ] 關鍵字裡沒有 trip planner、旅行計劃、雜誌、使命、ジャーナル
- [ ] 計分板下一次量到的是上面三個詞（也見本次回傳的 challenge_terms）
