# LockHour Pro: Block Apps（lockhour）

**一句話診斷**：LockHour Pro 上架 4 個月只有 1 則評分，最大的漏洞是 50 個語系裡有 35 個（含英國、澳洲、加拿大、德、法、西、葡、義、越）用的是一段 490 字的泛用簡介，完全沒提「封鎖 App」、模式或強制模式，而且沒有任何語系寫免費能用什麼。

## 結論
上架 4 個月只有台灣 1 則 5 星。第一版沒看到的大洞：50 語系有 35 個（含 en-GB／en-AU／en-CA、de、fr、es、pt-BR、it、vi）是 490 字泛用簡介，不提封鎖 App、六種模式、強制模式；加上名稱「Pro」卻標 Free、沒有任何語系寫免費範圍，點進來的人不知道這是什麼、能不能免費用。紅海市場裡，列表先修好再談導流。

## 各市場真正問題
- **zh-Hant**：列表完整、唯一有評分；缺站外足跡與免費範圍。
- **ja**：列表完整、0 評分，純缺入口；關鍵字欄本機 145 字需核對。
- **en-US**：en-US 完整但英語另三店面是泛用文；4 個月 0 評分。

## 行動
| claude | local | you |
|---|---|---|
| 修 Telegram en 文案，移除 Opal/Forest 點名 | GEO 補「不訂閱的封鎖 App」問答頁 | 35 個語系換完整描述（英語三店面可直接貼 en-US） |
| scoreboard 挑戰詞（封鎖app、アプリ制限、app blocker） | — | 第一段寫免費範圍；核對關鍵字 ≤100 字並去重 |
| 草擬示範影片腳本、note.com 文 | — | 副標題放「一次買斷」；考季 Dcard／Threads 各一則 |

## 二次審核修正

- 第一版完全沒發現：35／50 語系的描述是泛用簡介，不提封鎖 App、模式、強制模式；英國、澳洲、加拿大三個英語店面都是這版。這比關鍵字欄超長更嚴重，而且店主一天就能修（en-GB/en-AU/en-CA 可直接貼 en-US 原文）。
- 第一版正確指出本機關鍵字 306 字超過 100 上限、名稱帶 Pro 卻無免費範圍；本次 grep en-US/ja/zh-Hant/ko 描述皆無 free／無料／免費／무료 字樣，確認。
- Telegram 佇列現有 LockHour en 文案寫「a pay-once alternative to Opal/Forest」，點名競品商標，違反規則，需修正。
- 第一版把 en-US 放進 best_markets：美國 4 個月 0 評分，而台灣有 1 則 5 星、ja/ko/zh-Hant 列表完整；短期更合理的順序是 zh-Hant → ja → 修好英語列表後再推 en。
- 六款 App 列表皆無語言數量句，「改 50」不適用；可新增「50 種介面語言、App 內切換」。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 台灣是唯一有評分的店面（1 則 5 星），zh-Hant 列表是完整版、名稱含封鎖 App 與專注計時；問題是紅海（Opal、ScreenZen 類）與零站外足跡，以及名稱「Pro」+ 免費價格卻不說免費範圍。 | iTunes lookup TW：5.0★／1 則，名稱「LockHour Pro：封鎖 App·專注計時」，Free，2026-06-14 上架、v1.0.18。zh-Hant 描述 13 個要點、含強制模式；grep 免費範圍 = 無。名次本次未測得（403）。 |
| ja | ja 列表完整（アプリ制限・集中タイマー、ハードモード），0 評分代表純粹沒有入口；朝スマホ、スマホ依存話題在 X 有量但我們沒出現。 | iTunes lookup JP：0 評分。ja 關鍵字欄本機檔 145 字（上限 100，需店主確認實際上傳）。 |
| en-US | en-US 本身是完整描述，但 en-GB／en-AU／en-CA 與其他 32 個語系是 490 字泛用文（「Fokus-Sessions zu planen… Behalte Bildschirmzeit im Blick」），沒有 block／blocker／modes／Hard Mode；英語世界一半以上的店面看到的是這版。再加上名稱「Pro」卻標 Free、沒寫免費範圍，點進來不知道能不能免費用。 | iTunes lookup US：0 評分（4 個月）。本機 lockhour_full.json：描述要點 ≥10 的語系只有 15 個（en-US, ja, ko, zh-Hant + 11 個印度語系／sl-SI／ur-PK）；de-DE、fr-FR、it、pt-BR、vi、en-GB、en-AU、en-CA 等 35 個語系描述 <600 字且不含 block 字樣。scoreboard：GR「αποκλεισμός εφαρμογών」第 15。 |
