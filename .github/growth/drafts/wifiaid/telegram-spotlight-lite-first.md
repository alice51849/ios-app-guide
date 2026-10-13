# WiFi Aid／WiFi Aid Lite：Telegram 佇列文案（Lite 為入口，付費版只講 Watch／iPad）（wifiaid-04 的 Telegram 部分）

| 項目 | 內容 |
|---|---|
| 用途 | 佇列 `.github/scripts/telegram_posts.json` 裡付費版 WiFi Aid 的 en／ja 兩則把讀者直接導到 US$5.99／¥1,000 的付費 App，但付費版在 13 組母語搜尋全部缺席、0 評分；Lite 已出現在每個母語微利基。本檔把外宣入口改成 Lite，付費版改寫成「Apple Watch・小工具・iPad 版」，並在結尾把想先試的人導回 Lite |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道；zh-Hant、日文、英文讀者 |
| 發文者 | 由維護佇列的流程（店主或本機 Claude）把下面 JSON 貼進 `telegram_posts.json`，以 Lumi Studio 頻道名義發出。本檔沒有改佇列、不會自動發出 |
| 發文規則 | 每則開頭寫「50 種介面語言、App 內切換」；Lite 的免費額度一律寫「所有工具合計可免費完整檢查一次」（**不可寫「每項工具各一次」**）；付費版只寫 listing 有的 Apple Watch「執行檢查」、小工具（已連線・執行檢查）、iPad；不寫測速、不寫「讓網路變快」；不點名其他 App；連結用 `ct=telegram`（與現有條目一致）；同一 App 兩則之間至少隔 21 天 |
| 事實依據 | wifiaidlite_full.json（zh-Hant／ja／en-US）：執行檢查、深度檢查、網站檢查、DNS／TCP／TLS／TTFB／HTTP／直連 IP／IPv4／IPv6 證據、穩定度（抖動）、紀錄僅存本機、無帳號／廣告／分析／追蹤、一次性終身解鎖、無訂閱。免費額度依 10/13 審核的線上描述。wifiaid_full.json：Apple Watch — 執行檢查、Widget · iPad — 已連線 · 執行檢查、App Store 一次付費買斷。50 種介面語言、App 內切換（店主確認）|
| 發前核對 | Lite 線上描述的免費額度句仍為「合計一次」 |

## 建議換掉的舊條目（在 `telegram_posts.json` 用 text 搜尋）

| app | lang | 舊文案開頭 | 處理 |
|---|---|---|---|
| wifiaid | en | 📶 WiFi Aid — Wi-Fi says connected but nothing loads? | 換成下方「付費版 en」：改講 Watch／小工具／iPad，結尾導回 Lite |
| wifiaid | ja | 📶 WiFi Aid — 「接続済みなのに繋がらない」を切り分け。 | 換成下方「付費版 ja」 |
| wifiaidlite | en | 📶 WiFi Aid Lite — Stop guessing whether Wi-Fi, DNS or the website is failing. | 可保留；或換成下方「Lite en」（多了 50 語、免費額度說明）|
| wifiaidlite | ja | 📶 WiFi Aid Lite — Wi‑Fi・DNS・Webサイトのどこで問題が起きているかを切り分け。 | 同上，可換成「Lite ja」 |
| — | zh-Hant | （目前兩版都沒有 zh-Hant 條目）| 新增「Lite zh-Hant」與「付費版 zh-Hant」 |

## 貼入佇列用 JSON（與現有條目格式相同，一行一則）

```json
{"lang": "zh-Hant", "app": "6793414462", "text": "🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。\n📶【WiFi Aid Lite】Wi-Fi 顯示已連線，網頁卻打不開？到底是路由器、DNS、業者，還是網站自己的問題？一鍵檢查 Wi-Fi、DNS 與網路連線，把 DNS、TCP、TLS、回應時間等證據逐項列出，指出最可能的原因；「網站檢查」分辨是單一網站還是整條網路，「深度檢查」適合時好時壞的斷線。紀錄只存在手機上，無帳號、無廣告、無追蹤。免費下載，所有工具合計可免費完整檢查一次；之後一次買斷解鎖，沒有訂閱。", "url": "https://apps.apple.com/app/id6793414462?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "6793414462", "text": "🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。\n📶 WiFi Aid Lite：Wi-Fiはつながっているのに、ネットが遅い・開かない。ルーター？DNS？回線？それともサイト側？ワンタップで Wi-Fi・DNS・インターネット接続を確認し、DNS・TCP・TLS・応答時間などの根拠から最も可能性の高い原因を表示します。「サイトをチェック」で特定のサイトだけか回線全体かを判定、「詳細チェック」は時々切れる不調向け。履歴は端末内のみ、アカウント・広告・追跡なし。全ツール合わせて1回の完全なチェックが無料、その後は買い切りでアンロック、サブスクなし。", "url": "https://apps.apple.com/app/id6793414462?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "6793414462", "text": "🌐 50 interface languages, switchable inside the app without changing your phone's language.\n📶 WiFi Aid Lite: Wi-Fi says connected but nothing loads? Router, DNS, ISP, or the website itself? One tap checks Wi-Fi, DNS and the internet, lists the evidence (DNS, TCP, TLS, response time) and shows the most likely cause. Check a Website tells you whether one site or everything is failing; Deep Check is for on-and-off drops. History stays on your device; no account, ads or tracking. One complete check is free across all tools, then a one-time unlock. No subscription.", "url": "https://apps.apple.com/app/id6793414462?pt=118326163&ct=telegram&mt=8"}
{"lang": "zh-Hant", "app": "6790467886", "text": "🌐 介面 50 種語言，可在 App 內切換。\n⌚【WiFi Aid】想在手腕上就查網路？WiFi Aid 的 Wi-Fi、DNS 與網路檢查可以直接從 Apple Watch 執行，主畫面小工具隨時看連線狀態並一鍵檢查，也支援 iPad。App Store 一次付費買斷，無訂閱、無廣告、無追蹤，紀錄只存在裝置上。只想先試試檢查本身？從免費起步的 WiFi Aid Lite 開始就好。", "url": "https://apps.apple.com/app/id6790467886?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "6790467886", "text": "🌐 画面の言語は50言語、アプリ内で切り替え可能。\n⌚ WiFi Aid：Wi-Fi・DNS・インターネットのチェックを Apple Watch から実行。ホーム画面のウィジェットで接続状態を確認してそのままチェック、iPad にも対応。App Store で一度だけ購入、サブスク・広告・追跡なし、履歴は端末内のみ。まずチェックだけ試したい方は、無料で始められる WiFi Aid Lite からどうぞ。", "url": "https://apps.apple.com/app/id6790467886?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "6790467886", "text": "🌐 50 interface languages, switchable inside the app.\n⌚ WiFi Aid: run your Wi-Fi, DNS and internet check from Apple Watch, see connection status in a Home Screen widget and start a check from it, and use the full layout on iPad. One upfront purchase, no subscription, ads or tracking; history stays on your device. Just want to try the checks first? Start with WiFi Aid Lite, free to download.", "url": "https://apps.apple.com/app/id6790467886?pt=118326163&ct=telegram&mt=8"}
```

## 純文字版（人工貼到頻道時用）

### Lite zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。
📶【WiFi Aid Lite】Wi-Fi 顯示已連線，網頁卻打不開？到底是路由器、DNS、業者，還是網站自己的問題？一鍵檢查 Wi-Fi、DNS 與網路連線，把 DNS、TCP、TLS、回應時間等證據逐項列出，指出最可能的原因；「網站檢查」分辨是單一網站還是整條網路，「深度檢查」適合時好時壞的斷線。紀錄只存在手機上，無帳號、無廣告、無追蹤。免費下載，所有工具合計可免費完整檢查一次；之後一次買斷解鎖，沒有訂閱。
https://apps.apple.com/app/id6793414462?pt=118326163&ct=telegram&mt=8
```

### 付費版 zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換。
⌚【WiFi Aid】想在手腕上就查網路？WiFi Aid 的 Wi-Fi、DNS 與網路檢查可以直接從 Apple Watch 執行，主畫面小工具隨時看連線狀態並一鍵檢查，也支援 iPad。App Store 一次付費買斷，無訂閱、無廣告、無追蹤，紀錄只存在裝置上。只想先試試檢查本身？從免費起步的 WiFi Aid Lite 開始就好。
https://apps.apple.com/app/id6790467886?pt=118326163&ct=telegram&mt=8
```

（ja／en 純文字版同上方 JSON 的 text 欄位，換行處照 `\n` 分段，最後一行貼 url。）
