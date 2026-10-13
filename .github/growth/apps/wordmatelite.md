# Wordmate Lite 每天五個單字（wordmatelite）

**一句話診斷**：Wordmate Lite 上架兩個月零評分的核心原因是免費層只有 10 個字＋3 個收藏（兩次就撞牆，習慣型 App 養不成習慣），加上越南／印尼店面只剩英文頁、我方矩陣又把它歸成兒童類。

## 結論
Lite 零評分不是因為沒人要免費單字 App，而是免費層只有 10 個字＋3 個收藏，兩次練習就撞牆，一個靠連續天數活的 App 根本養不成習慣；越南、印尼店面又只剩英文頁，矩陣還把它歸成兒童類。先把這三件修掉，再談外宣。

## 各市場真正問題
- **zh-Hant**：「背單字」不在前 182；自己的名稱字「每天五個單字」第 5、「Wordmate Lite」第 1，代表品牌字沒有流量；0 評分；矩陣 category=kids。
- **id**：店面是英文頁（id 文案沒上線）；「belajar bahasa mandarin」不在前 183，前段是 SuperChinese 4,433、HelloChinese 1,282 這類有拼音／漢字教學的專用 App；中文內容繁簡未確認。
- **vi**：店面是英文頁；日文學習被 Mikun 15,869、Mazii 18,550 占據；「học từ vựng」兩輪 403 未量到。
- **ja**：「単語帳」= WordHolic 150,954／Quizlet 84,815，不在前 181；排最後。

## 修正第一輪
id/vi 貼文的落地頁其實是英文；量錯了品牌字（「每天五個單字」第 5，非第 34）；44 是學習語言數、介面語言 50 要另加一行；成績單那 1 則評分在六個主要店面之外；Lite 沒有 Apple Watch，是與 Wordmate 最明確的差異；免費層矛盾確認。

## 行動
**claude**：修矩陣 kids 分類並重生；統一免費層＋介面 50 語的多語文案草稿；Dcard 短文、20 秒影片腳本；id/vi 貼文存檔待前置條件。
**local**：重生 Lite GEO 頁、app_pairs.py 比較頁；排程 Threads。
**you**：ASC 把已有的 vi/id 本地化附到目前版本；統一免費層說法並考慮放寬到一個完整入門單元；zh-Hant 名稱副標；確認繁簡與 iPhone Duo；App 內連續 3 天後請求評分。

## 二次審核修正

- 第一輪 id/vi 貼文假設讀者會看到印尼文／越南文店面頁；live 的 VN/ID 店面是英文名與英文描述。owner 補回本地化前，這兩篇只能在社團裡說明「介面可切成印尼文／越南文」，且要預期落地頁是英文。
- 第一輪量的是「5個單字」第 34/36；App 真正名稱是「每天五個單字」，該字第 5/98、「Wordmate Lite」第 1。品牌字沒問題，問題是沒人搜品牌字。
- 「44 種語言」是學習語言數；介面語言 50 要另加一行，不是把 44 改掉（binary 的本地化碼也是 44 個）。
- 成績單顯示 Lite 有 1 則評分／1 個店面，但 TW/JP/VN/KR/US/ID 六個店面都是 0，那 1 則在六個以外的店面。
- 決策矩陣 wordmatelite category=kids、_engine/geo/data/result_image_evidence_v1.json family=kids14，確認第一輪的指控；zh-Hant hub 標題本身沒有兒童字眼，但 AI 讀矩陣會錯推。
- 免費層矛盾確認：US 描述「one learning language and one path at beginner level stay open for good」vs TW/JP/VN/ID「前 10 個字、收藏 3 個」。
- Lite 沒有 Apple Watch（lookup 裝置清單不含 Watch），第一輪沒點出；這是與 Wordmate 最明確的差異，外宣要講清楚。
- v1.0.6（2026-10-09）只是文案更新；iPhone Duo 句同樣待 owner 確認。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 「背單字」不在前 182，前段全是免費且有數千到十幾萬則評分的 App；自己的名稱字「每天五個單字」第 5、「Wordmate Lite」第 1，代表品牌字沒有流量；0 評分；免費層 10 字＋3 收藏，習慣型 App 第 3 天就撞牆，累積不了評分；決策矩陣把它歸為 kids，GEO/AI 會推給錯的人。 | TW「背單字」不在前 182（死神單字 3,001、單字庫 35,151、WORD UP 23,341、多鄰國 138,601）；TW「每天五個單字」第 5/98（第 1 島讀 5,584；第 2「5 English Words - 每日5個英文單字」7 則）；TW「Wordmate Lite」第 1/48；lookup TW 免費、n=0、2026-08-07 上架、無 Apple Watch。data/ios-app-decision-matrix.jsonl：category=kids。 |
| id | 印尼店面顯示英文「Wordmate Lite: Vocabulary」與英文描述，本地 id 文案「5 Kata Sehari」沒上線；「belajar bahasa mandarin」不在前 183，前段是有拼音／漢字教學的專用 App；Lite 的中文學習內容是繁體或簡體仍未確認。移工需求是真的，但落地頁是英文、內容不對口。 | lookup country=id：trackName 英文、描述英文、n=0。ID「belajar bahasa mandarin」不在前 183（SuperChinese 4,433、HelloChinese 1,282、Duolingo 110,676、Chinesia 53）；ID「kosakata」不在前 191（前 2 是 Words of Wonders 字謎遊戲 100,197）。 |
| vi | 越南店面同樣是英文頁；越南人在日韓學日文的需求被 Mikun、Mazii、HeyJapan 等日文專用 App 占據；「học từ vựng」被 Apple 兩輪 403 沒量到。通用 44 語單字 App 對這群人的吸引力低於專用 App，貼文只能走「介面可切越南文、一分鐘」的切角。 | lookup country=vn：trackName「Wordmate Lite: Vocabulary」、描述英文、n=0。VN「học tiếng Nhật」不在前 171（Mikun 15,869、Mazii 18,550、HeyJapan 2,607、MochiKanji 4,448）。 |
| ja | 「単語帳」被 WordHolic、Quizlet 占據、我們不在前 181；「1日5単語」沒量到（403）；0 評分。「不做單字卡」的切角適合 X，但預期產出低，排最後。 | JP「単語帳」不在前 181（WordHolic 150,954、Quizlet 84,815、暗記メーカー 13,381）；lookup JP 無料、n=0。 |
