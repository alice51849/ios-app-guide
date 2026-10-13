# CV Desk（cvdesk）

**一句話診斷**：美國排第 16 卻輸給兩款 0 評分、名稱以「ATS Resume Builder」開頭的 App，印尼連前 50 都沒進——瓶頸是名稱字序與在地權重，不只是評分數。

## 結論
CV Desk 不是沒人看，是**名稱字序與在地權重**輸給評分更少的對手。美國「ats resume」第 16／49，第 2、3 名是 0 評分、名稱以「ATS Resume Builder」開頭的 App；印尼「cv ats」前 50 名沒有我們，而第 1 名只有 8 則評分。評分：TW 2、US 1、其餘 0（iTunes lookup 2026-10-13）。

## 各市場真正問題
- **id**：需求最大、權重為零——沒有印尼文外宣、0 評分；副標重複名稱。
- **en-US**：名稱「CV Desk:」在前，關鍵詞在後；加上只有 1 則評分。
- **th**：頭部詞第 128／176，對手（Canva 除外）評分僅 14–658 則；0 評分、0 泰文外宣，市場薄到幾十個下載就有感。
- **zh-Hant**：104／Cake 是入口，只剩「投外商要英文 ATS 履歷」這條窄路。

## 第一輪修正
印尼不是「沒讀數」而是「不在前 50」；美國瓶頸是名稱字序不只是社會證明；資料檔與 live（一次性內購／ONE-TIME UNLOCK）不同步。

## 行動
| claude | local | you |
|---|---|---|
| id 貼文 3 則＋TikTok 腳本入 app-posts.json | threads-autopilot 排程（id／zh-Hant／en，連結放留言） | en-US 名稱改關鍵詞在前、副標去重、關鍵字去重 |
| 成績單覆寫頭部詞（cv ats、ats resume、เรซูเม่ ats、英文履歷） | 重匯出 cv_full／cvdesk_full，確認上架的關鍵字版本 | id 副標改「Skor ATS 0–100 · PDF & Word」 |
| ATS 友善格式 checklist 單頁（4 語） | | 描述加 50 語言句；本人在印尼社群發 1 則、錄 30 秒印尼文介面示範 |

## 二次審核修正

- 第一輪說印尼「沒有排名讀數」：實測「cv ats」前 50 名沒有我們，而第 1 名只有 8 則評分——問題不是競爭，是 ID 店面權重為零。
- 第一輪把美國瓶頸歸為「社會證明」：實測第 2、3 名是 0 評分 App，只因名稱以「ATS Resume Builder」開頭；名稱字序比評分更關鍵，這是 ASC 決策。
- cv_full.json 與 live 不同步：US 已改「ONE-TIME UNLOCK / Build and preview without a purchase」、TW 改「一次性內購」。貼文用詞改為「一次性解鎖」。
- API 顯示 53 種語言，描述沒有語言數句子；依店主確認可宣傳 50 種語言＋App 內切換。
- 第一輪四則貼文內容與 live 文案相符，保留但補上 50 語言一句並縮到 420 字內。
- 泰國頭部詞「เรซูเม่」第 128／176，對手（Canva 除外）評分僅 14–658 則：市場薄，泰文外宣幾十個下載就有感，優先度應高於第一輪排序。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| id | 印尼是需求最大的市場，但「cv ats」前 50 名沒有我們；第 1 名「CV ATS」只有 8 則評分，第 3 名 167 則。不是競爭太強，是我們在 ID 店面幾乎沒有權重（0 評分、0 下載、沒有任何印尼文外宣）。名稱（lang=id）確認為「CV Desk: Pembuat CV ATS」，但副標「Pembuat CV ATS · Lamaran」重複名稱，白白浪費一欄。 | iTunes search 2026-10-13 limit 50，country=id「cv ats」：我們不在前 50；#1 CV ATS（8 則）、#2 CV Maker, Resume Maker（3,614）、#3 CV Maker - Intelligent Resume（167）、#4 Canva（899,508）、#5 CV Engineer（650）。iTunes lookup 2026-10-13：ID 評分 0。limit 200 複測見 report。 |
| en-US | 「ats resume」我們第 16／49。第 2、3 名是 0 評分、名稱以「ATS Resume Builder」開頭的 App，排在 14,204 則評分的 Resume Builder 之前——Apple 搜尋把名稱開頭的完全比對看得比評分重。我們的名稱把品牌「CV Desk:」放在前面，關鍵詞在後，字序吃虧；1 則評分再加一層劣勢。 | iTunes search 2026-10-13 limit 50，country=us「ats resume」：rank 16／49；#1 Resume Builder⁺（77,978）、#2 ResumesKey: ATS Resume Builder（0）、#3 ATS Resume Builder & CV Maker（0）、#4 Resume Builder: PDF Resume App（14,204）、#5 ATS Resume Builder: CV Maker（4）。iTunes lookup 2026-10-13：US 評分 1（5.0）。 |
| th | 泰國名稱已是泰文「CV Desk: สร้างเรซูเม่ ATS」，頭部詞「เรซูเม่」176 筆我們第 128；除了 Canva（1,041,026），前 5 名評分只有 14–658 則——市場薄，我們排後段只因 0 評分、0 泰文外宣。幾十個真實下載就能進前 10；第一輪引用的「เรซูเม่ ats 第 5」只是長尾詞。 | iTunes search 2026-10-13 limit 200，country=th「เรซูเม่」：rank 128／176；#1 Canva（1,041,026）、#2 CV Maker: Resume Builder PRO（111）、#3 Top Resume（14）、#4 CV Maker - Intelligent Resume（658）、#5 CV Maker Pro with AI（19）。iTunes lookup 2026-10-13 lang=th：名稱 CV Desk: สร้างเรซูเม่ ATS，評分 0。第一輪讀數，本次未重現：เรซูเม่ ats 5／190。成績單 issue #8（2026-10-13 04:31 UTC）：最佳名次 52（GR βιογραφικό）。 |
| zh-Hant | 台灣是唯一有評分的店面（2 則，5.0），但求職者在 104／Cake 內完成履歷，App Store 不是入口。能搶的是「投外商要英文 ATS 履歷」這條窄需求；描述裡「一次性內購」和資料檔「買斷」已不同步，說明資料檔過時。 | iTunes lookup 2026-10-13：TW 評分 2（5.0），live 描述「一次性內購,沒有浮水印」vs cv_full.json「一次買斷」。第一輪讀數，本次未重現：履歷產生器 5／20。 |
