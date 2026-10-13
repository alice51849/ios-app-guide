# QR Code Halo：Telegram 佇列替換文案（店家自查情境＋先關閉自動執行）（qrcodehalo-05；供執行 qrcodehalo-01 的人一併使用）

| 項目 | 內容 |
|---|---|
| 用途 | 佇列 `.github/scripts/telegram_posts.json` 裡 QR Code Halo 的 en／ja／zh-Hant 三則都宣稱「scanning never auto-opens／読み取った瞬間に何かを開くアプリではありません／不會把讀取結果直接變成一次點擊」，與線上 v1.0.3「掃到就直接執行」矛盾，是不實宣稱。本檔是三則替換文案：只講店家自查情境，**每則都寫「先到設定關閉自動執行」**。本檔沒有改佇列，替換由有權限的人執行 |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道；zh-Hant、日文、英文讀者（開店、辦活動的人）|
| 發文者 | 由維護佇列的流程（店主或本機 Claude）替換 `telegram_posts.json` 的三則舊文，以 Lumi Studio 頻道名義發出 |
| 發文規則 | 每則開頭寫「50 種介面語言、App 內切換」；每則都有「目前預設掃到就執行，請先到設定關閉」；寫明「不查網路信譽、不會抓出所有詐騙」；不引用任何新聞事件或第三方警告；不點名其他 App；連結用 `ct=telegram`；qrcodehalo-03 若定案為 A（預設不自動開啟），把關閉開關那句換成「掃描後會先停在檢查畫面」 |
| 事實依據 | 自動執行：10/13 審核確認線上 v1.0.3 描述「掃到就直接執行」，設定可關閉「掃描後自動執行」，歷史紀錄可按安全檢查。功能：qrcodehalo_full.json（QR Verification 的 SHA-256 指紋比對、Batch Risk & Difference Audit 的重複／同 host 分組與有限範圍相似 host 比對、完整稽核閱讀免費、免費 3 次成功掃描、9 種 QR 建立、Lifetime Pro 一次買斷、無訂閱）。50 種介面語言、App 內切換（店主確認）|
| 發前核對 | **ja 與 en 的設定開關名稱**：zh-Hant「掃描後自動執行」來自 app-improvements.json；en「Run action after scanning」沿用 app-posts.json；ja「スキャン後に自動実行」是暫定譯名，貼進佇列前必須在 App 日文介面確認實際字樣並替換 |

## 要替換的舊條目（在 `telegram_posts.json` 用 text 搜尋）

| lang | 舊文案開頭 | 問題 |
|---|---|---|
| en | 🔍 QR Code Halo shows what a code contains before anything happens: scanning never auto-opens a destination. | 「never auto-opens」與線上預設行為相反 |
| ja | 🔍 QR Code Halo は、読み取った瞬間に何かを開くアプリではありません。 | 同上 |
| zh-Hant | 🔍 QR Code Halo 不會把讀取結果直接變成一次點擊 | 同上 |

## 替換用 JSON（一行一則）

```json
{"lang": "zh-Hant", "app": "6806779853", "text": "🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。\n🔍【QR Code Halo】開店的朋友：櫃台上的點餐、收款 QR Code，你多久確認一次它還是你的？QR Code Halo 可以把確認過的正確碼存成本機參照，下次再掃一次，依完整 SHA-256 指紋、網域、內容類型逐項比對；批次稽核會把一整批碼依相同內容與網域分組，並在明確範圍內比對容易混淆的相似網域。目前版本預設掃到就執行，請先到設定關閉「掃描後自動執行」，再到歷史紀錄按「安全檢查」。全部在手機上完成，不查網路信譽，所以不會抓出所有詐騙。免費 3 次掃描、9 種 QR Code 建立都能用；Lifetime Pro 一次買斷，沒有訂閱。", "url": "https://apps.apple.com/app/id6806779853?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "6806779853", "text": "🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。\n🔍 QR Code Halo：お店のレジやテーブルの注文・決済用QRコード、いまも本当に自分のものか、最後に確かめたのはいつですか？確認済みのコードを端末内の参照として保存し、次に読み取ったときに SHA-256 フィンガープリント、ドメイン、内容の種類を項目ごとに比較できます。まとめて読み取ったコードは、同じ内容・同じドメインごとにグループ化し、範囲を決めて紛らわしい似たドメインも比べます。現在のバージョンは読み取るとすぐ実行する設定が初期値なので、先に設定で「スキャン後に自動実行」をオフにしてから、履歴でチェックしてください。処理は端末内のみで、ネット上の評判は調べないため、すべての詐欺を見抜けるわけではありません。無料で3回スキャン、9種類のQR作成はすべて利用可能。Lifetime Pro は買い切り、サブスクなし。", "url": "https://apps.apple.com/app/id6806779853?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "6806779853", "text": "🌐 50 interface languages, switchable inside the app without changing your phone's language.\n🔍 QR Code Halo: run a shop or a market stall? When did you last check that the ordering or payment QR code on your counter is still yours? Save a verified code as a local reference, then compare a later scan by its full SHA-256 fingerprint, domain and content type. Batch audit groups a set of codes by identical content and shared domain, and checks a bounded set of lookalike domains. The current version runs the code's action right after scanning by default, so first turn off \"Run action after scanning\" in Settings, then use Security Check from History. Everything stays on your phone; there is no online reputation lookup, so it won't catch every scam. 3 free scans, all 9 QR creators free; Lifetime Pro is a one-time purchase, no subscription.", "url": "https://apps.apple.com/app/id6806779853?pt=118326163&ct=telegram&mt=8"}
```

## 純文字版（人工貼到頻道時用）

### zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。
🔍【QR Code Halo】開店的朋友：櫃台上的點餐、收款 QR Code，你多久確認一次它還是你的？QR Code Halo 可以把確認過的正確碼存成本機參照，下次再掃一次，依完整 SHA-256 指紋、網域、內容類型逐項比對；批次稽核會把一整批碼依相同內容與網域分組，並在明確範圍內比對容易混淆的相似網域。目前版本預設掃到就執行，請先到設定關閉「掃描後自動執行」，再到歷史紀錄按「安全檢查」。全部在手機上完成，不查網路信譽，所以不會抓出所有詐騙。免費 3 次掃描、9 種 QR Code 建立都能用；Lifetime Pro 一次買斷，沒有訂閱。
https://apps.apple.com/app/id6806779853?pt=118326163&ct=telegram&mt=8
```

（ja／en 純文字版同上方 JSON 的 text 欄位，換行處照 `\n` 分段，最後一行貼 url。）
