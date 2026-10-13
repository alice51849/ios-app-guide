# BattAI：Telegram 佇列文案「二手轉讓／送修」框架（zh-Hant／ja／ko／en）（battai-03 的 Telegram 部分）

| 項目 | 內容 |
|---|---|
| 用途 | 佇列 `.github/scripts/telegram_posts.json` 裡 BattAI 的 8 則都是「看懂電池趨勢、不被神祕分數唬弄」的價值宣言，沒有使用情境；報告點出真正的下載理由是「賣二手／送修前要給對方看電池」。本檔是 4 則以二手／送修為情境的替換文案，並老實說「只要最大容量數字，iOS 設定就有」 |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道；zh-Hant、日文、韓文、英文讀者 |
| 發文者 | 由維護佇列的流程（店主或本機 Claude）把下面 JSON 貼進 `telegram_posts.json`，以 Lumi Studio 頻道名義發出。本檔沒有改佇列、不會自動發出 |
| 發文規則 | 每則開頭寫「50 種介面語言、App 內切換」；只寫 repo 文案有的功能；**不寫循環次數、不寫「預估到 80% 的時間」與 PNG 報告**（前者線上已刪；後兩者線上有但 battai_full.json 尚未回填，回填後可再加一句）；不寫 AI；不承諾延長電池壽命；連結 `ct=tg_battai_resale`，好和舊條目的 `social_battai` 分開量測；de／fr／es／pt-BR 四則不動 |
| 事實依據 | battai_full.json（zh-Hant／ja／ko／en-US）：公開 iOS API 五項讀值、每項顯示來源與限制；電池健康分數與評分依據；最大容量趨勢；充電保養／區間／速率；匯出資料在本機產生、不上傳；無廣告、分析、追蹤、第三方 SDK 或網路請求；解鎖更深入的記錄、規劃與報告，只付一次、無訂閱。50 種介面語言、App 內切換（店主確認）|

## 建議換掉的舊條目（在 `telegram_posts.json` 用 text 搜尋）

| lang | 舊文案開頭 | 處理 |
|---|---|---|
| zh-Hant | 🔋 想看懂電池趨勢，又不想被神祕分數唬弄？ | 換成下方 zh-Hant |
| ja | 🔋 根拠の見えるバッテリー推移を残したい人へ。 | 換成下方 ja |
| ko | 🔋 근거를 확인할 수 있는 배터리 추세가 필요하다면 | 換成下方 ko |
| en | 🔋 Want a battery trend you can actually audit? | 換成下方 en |

## 貼入佇列用 JSON（與現有條目格式相同，一行一則）

```json
{"lang": "zh-Hant", "app": "6802423998", "text": "🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。\n🔋【BattAI】要賣舊 iPhone 或送修前，對方常會問電池狀況。最大容量 iOS 設定裡就看得到；BattAI 多做的是把電池健康分數與評分依據、最大容量隨時間的趨勢、充電保養與充電區間整理在一起，每一項都標明來源與限制：哪些來自 iOS、哪些是推算、哪些是你自己補的。資料可以在手機上產生匯出檔，不會上傳。不連網、沒有廣告、分析或追蹤。更深入的記錄、規劃與報告一次付費解鎖，沒有訂閱。", "url": "https://apps.apple.com/app/id6802423998?pt=118326163&ct=tg_battai_resale&mt=8"}
{"lang": "ja", "app": "6802423998", "text": "🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。\n🔋 BattAI：iPhoneを売る前や修理に出す前、よく聞かれるのがバッテリーの状態。最大容量はiOSの設定でも見られます。BattAIは、バッテリー状態スコアとその要因、最大容量の推移、充電ケアと充電範囲をまとめて表示し、各項目に情報源と限界を明記します（iOSの値か、計算か、あなたの入力か）。データは端末内でファイルに書き出せて、アップロードなし。通信・広告・解析・追跡なし。より深い履歴、計画、レポートは一度の支払いで、サブスクなし。", "url": "https://apps.apple.com/app/id6802423998?pt=118326163&ct=tg_battai_resale&mt=8"}
{"lang": "ko", "app": "6802423998", "text": "🌐 화면 언어 50개, 휴대폰 언어 설정은 그대로 두고 앱 안에서 바꿀 수 있어요.\n🔋 BattAI: 아이폰을 중고로 팔거나 수리 맡기기 전에 자주 받는 질문이 배터리 상태죠. 최대 용량은 iOS 설정에서도 볼 수 있어요. BattAI는 배터리 상태 점수와 그 근거, 시간에 따른 최대 용량 추세, 충전 관리와 충전 범위를 한곳에 정리하고, 항목마다 출처와 한계를 표시해요(iOS 값인지, 계산값인지, 직접 입력한 값인지). 데이터는 기기 안에서 파일로 내보내며 업로드하지 않아요. 네트워크 요청·광고·분석·추적 없음. 더 깊은 기록, 계획, 리포트는 한 번 결제로, 구독 없음.", "url": "https://apps.apple.com/app/id6802423998?pt=118326163&ct=tg_battai_resale&mt=8"}
{"lang": "en", "app": "6802423998", "text": "🌐 50 interface languages, switchable inside the app without changing your phone's language.\n🔋 BattAI: selling your old iPhone or sending it in for service? You'll be asked about the battery. Maximum capacity is already in iOS Settings; BattAI adds a battery health score with the rules behind it, maximum capacity over time, and charge care and charge range, each labeled with its source and limits (from iOS, calculated, or added by you). Export a file built on your device; nothing is uploaded. No network requests, ads, analytics or tracking. Deeper history, planning and reports are one payment, no subscription.", "url": "https://apps.apple.com/app/id6802423998?pt=118326163&ct=tg_battai_resale&mt=8"}
```

## 純文字版（人工貼到頻道時用）

### zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。
🔋【BattAI】要賣舊 iPhone 或送修前，對方常會問電池狀況。最大容量 iOS 設定裡就看得到；BattAI 多做的是把電池健康分數與評分依據、最大容量隨時間的趨勢、充電保養與充電區間整理在一起，每一項都標明來源與限制：哪些來自 iOS、哪些是推算、哪些是你自己補的。資料可以在手機上產生匯出檔，不會上傳。不連網、沒有廣告、分析或追蹤。更深入的記錄、規劃與報告一次付費解鎖，沒有訂閱。
https://apps.apple.com/app/id6802423998?pt=118326163&ct=tg_battai_resale&mt=8
```

（ja／ko／en 純文字版同上方 JSON 的 text 欄位，換行處照 `\n` 分段，最後一行貼 url。）

## battai_full.json 回填之後可加的一句（現在不要用）

- zh-Hant：「也能為檢修或二手轉讓建立一份電池報告。」
- ja：「修理や売却のためのバッテリーレポートも作れます。」
- en："You can also build a battery report for service or resale."
