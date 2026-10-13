# WiFi Aid Lite：免費額度句的替換文字（給執行 wifiaidlite-02 的人用）

| 項目 | 內容 |
|---|---|
| 用途 | 線上 US／TW／JP／ID 描述已改成「所有工具合計可完整檢查一次」，但 repo 的 `_engine/data/wifiaidlite_full.json` 與至少 6 個語系的 `wifiaidlite.html`（含 meta／og／twitter 描述）仍寫「每項工具各含一次免費」，對使用者是不實宣稱。本檔只準備好替換文字；**本次沒有修改任何資料檔或頁面**（那些檔案不在雲端 Claude 本次可寫範圍，且 html 由 GrowthEngine 產生，需同步改模板）|
| 給誰 | 有權限改資料檔與 GrowthEngine 模板的人（店主或本機 Claude）|
| 發文者 | 不對外發布；套用後的文字以 App 官方頁面名義出現 |
| 套用規則 | ① 先以當天 App Store 線上描述再核對一次（lookup 加 `lang=` 參數），以線上為準。② 同時改 `description`、`promotionalText` 與頁面 meta／og／twitter 描述，不要只改其中一處。③ 「修正前後對照」來自 10/13 審核看到的線上新文案；若線上已不見這句就不要加。④ 改完後 GrowthEngine 的 wifiaidlite 模板也要同步，否則下次重生會寫回舊句 |

## 替換對照

| 語系 | 舊句（repo 現況） | 新句 |
|---|---|---|
| zh-Hant | 每項工具皆含一次免費的完整使用 | 所有工具合計可免費完整檢查一次 |
| zh-Hant（promotionalText 全句） | 找出真正的問題。每項工具皆含一次免費完整使用。可選的一次性終身解鎖提供無限使用——無訂閱、無廣告、無追蹤。 | 找出真正的問題。所有工具合計可免費完整檢查一次；一次性終身解鎖後不限次數，並可查看修正前後對照——無訂閱、無廣告、無追蹤。 |
| en-US | Each tool includes one free complete use. | One complete check is free, shared across all tools. |
| en-US（promotionalText 全句） | Find the real problem. Each tool includes one free complete use. Optional one-time lifetime unlock for unlimited use—no subscription, ads or tracking. | Find the real problem. One complete check is free, shared across all tools. A one-time lifetime unlock adds unlimited checks and a before/after comparison—no subscription, ads or tracking. |
| ja | 各ツールは 1 回ずつ、制限なしの完全な状態で無料利用できます。 | 全ツール合わせて 1 回、無料で完全なチェックができます。 |
| ja（promotionalText 全句） | 本当の問題を見つける。各ツールは1回無料で完全に利用可能。オプションの1回限りの永久アンロックで無制限に利用—サブスクリプション、広告、追跡なし。 | 本当の問題を見つける。全ツール合わせて1回、無料で完全なチェックが可能。1回限りの永久アンロックで無制限に使え、修正前後の比較も表示—サブスクリプション、広告、追跡なし。 |
| ko | 각 도구는 한 번씩 제한 없이 완전하게 무료로 사용할 수 있습니다. | 모든 도구를 합쳐 한 번, 완전한 검사를 무료로 할 수 있습니다. |
| ko（promotionalText 全句） | 진짜 문제 찾기. 각 도구는 1회 무료 사용을 포함합니다. 선택적 1회성 평생 잠금 해제로 무제한 사용—구독, 광고, 추적 없음. | 진짜 문제 찾기. 모든 도구를 합쳐 1회 완전한 검사가 무료입니다. 1회성 평생 잠금 해제로 무제한 사용과 수정 전후 비교—구독, 광고, 추적 없음. |
| id | Setiap alat mencakup satu penggunaan penuh gratis. | Gratis satu pemeriksaan lengkap, total untuk semua alat. |
| id（promotionalText 全句） | Temukan masalah aslinya. Tiap alat: satu penggunaan penuh gratis. Buka kunci seumur hidup opsional untuk penggunaan tanpa batas—tanpa langganan. | Temukan masalah aslinya. Gratis satu pemeriksaan lengkap, total untuk semua alat. Buka kunci seumur hidup sekali bayar untuk penggunaan tanpa batas dan perbandingan sebelum/sesudah—tanpa langganan. |
| vi | Mỗi công cụ bao gồm một lần dùng đầy đủ miễn phí. | Miễn phí một lần kiểm tra đầy đủ, tính chung cho tất cả công cụ. |

其餘語系請以同一原則改寫：「合計一次」而非「每項一次」；解鎖句可補「修正前後對照」（僅在線上仍有此句時）。
