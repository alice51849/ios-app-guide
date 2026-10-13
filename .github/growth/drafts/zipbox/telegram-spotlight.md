# Zipbox：Telegram 佇列文案「iPhone 打不開 RAR／7z」情境（zh-Hant／ja／en）（zipbox-04 的 Telegram 部分）

| 項目 | 內容 |
|---|---|
| 用途 | 佇列 `.github/scripts/telegram_posts.json` 裡 Zipbox 的三則是功能條列（格式、密碼、預覽），沒有使用情境、也沒寫 50 種介面語言。本檔是三則情境式 spotlight，主打「收到打不開的 RAR／7z」與「先看再取一個檔」，並明寫付費下載 |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道；zh-Hant、日文、英文讀者 |
| 發文者 | 由維護佇列的流程（店主或本機 Claude）把下面 JSON 貼進 `telegram_posts.json`，以 Lumi Studio 頻道名義發出。本檔沒有改佇列、不會自動發出 |
| 發文規則 | 每則開頭寫「50 種介面語言、App 內切換」；必寫「付費下載、一次購買全部功能、無內購／訂閱／廣告」；**不寫中文亂碼／文字化け**（zipbox-02 未定案）；不寫「免費」「試用」；不點名其他 App；連結用 `ct=telegram`；新條目上線後，舊的三則可移除，避免同語言兩則輪播過密 |
| 事實依據 | zipbox_full.json（zh-Hant／ja／en-US）：App Store 付費下載、一次購買包含全部功能、沒有 App 內購買／訂閱／廣告；13 種格式（含 ZIP、RAR/RAR5、7z、ISO）在裝置本機處理；ZIP、RAR、7z 的分卷與密碼保護；不解壓先看清單、預覽照片／影片／PDF／文字／程式碼；取出單一檔案、勾選多個或整包；從檔案 App、Safari 下載、郵件與分享選單開啟；不連網、無帳號、無分析或追蹤。50 種介面語言、App 內切換（店主確認）|

## 建議換掉的舊條目（在 `telegram_posts.json` 用 text 搜尋）

| lang | 舊文案開頭 | 處理 |
|---|---|---|
| zh-Hant | 🗜️ Zipbox 可直接在 iPhone 開啟 ZIP、RAR/RAR5、7z 等 13 種壓縮格式 | 換成下方 zh-Hant |
| ja | 🗜️ Zipbox は iPhone 上で ZIP・RAR/RAR5・7z など13形式を展開し | 換成下方 ja |
| en | 🗜️ Zipbox opens ZIP, RAR/RAR5, 7z and 10 more archive formats directly on iPhone | 換成下方 en |

## 貼入佇列用 JSON（與現有條目格式相同，一行一則）

```json
{"lang": "zh-Hant", "app": "6806776579", "text": "🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。\n🗜️【Zipbox 解壓縮】用 Safari 下載的 RAR 躺在檔案 App 裡，手機上卻沒有一個 App 打得開？朋友傳來設了密碼的 7z 旅遊照片，只想看一眼？Zipbox 在手機本機處理 ZIP、RAR/RAR5、7z 等 13 種格式，含密碼與分卷；先瀏覽清單、預覽照片、影片、PDF，只取出需要的那一個。從檔案 App、Safari 下載、郵件或分享選單直接開。不連網、無帳號、永遠零廣告。App Store 付費下載，一次購買包含全部功能，沒有內購、沒有訂閱。", "url": "https://apps.apple.com/app/id6806776579?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "6806776579", "text": "🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。\n🗜️ Zipbox：Safariでダウンロードした圧縮ファイルがファイルAppに残っているのに、開けるアプリがない。友人からパスワード付きの7zで旅行の写真が届いて、とりあえず中身を見たい。Zipboxは ZIP・RAR/RAR5・7z など13形式を端末内だけで処理し、パスワード付きや分割ファイルにも対応。展開する前に一覧を見て、写真・動画・PDFをプレビューし、必要な1つだけ取り出せます。ファイルApp・Safariのダウンロード・メール・共有シートからそのまま起動。通信なし、アカウント不要、広告なし。App Storeの有料アプリで、1回の購入ですべての機能、アプリ内課金・サブスクなし。", "url": "https://apps.apple.com/app/id6806776579?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "6806776579", "text": "🌐 50 interface languages, switchable inside the app without changing your phone's language.\n🗜️ Zipbox: a RAR you downloaded in Safari is sitting in Files and nothing on your phone will open it? A friend sent a password-protected 7z of holiday photos and you just want to see them? Zipbox handles ZIP, RAR/RAR5, 7z and 10 more formats on your device, including password-protected and multi-part archives. Browse the list, preview photos, video and PDF, then pull out only the file you need. Open straight from Files, Safari downloads, Mail or the share sheet. No network, no account, no ads, ever. Paid App Store download: one purchase, every feature, no in-app purchases or subscription.", "url": "https://apps.apple.com/app/id6806776579?pt=118326163&ct=telegram&mt=8"}
```

## 純文字版（人工貼到頻道時用）

### zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。
🗜️【Zipbox 解壓縮】用 Safari 下載的 RAR 躺在檔案 App 裡，手機上卻沒有一個 App 打得開？朋友傳來設了密碼的 7z 旅遊照片，只想看一眼？Zipbox 在手機本機處理 ZIP、RAR/RAR5、7z 等 13 種格式，含密碼與分卷；先瀏覽清單、預覽照片、影片、PDF，只取出需要的那一個。從檔案 App、Safari 下載、郵件或分享選單直接開。不連網、無帳號、永遠零廣告。App Store 付費下載，一次購買包含全部功能，沒有內購、沒有訂閱。
https://apps.apple.com/app/id6806776579?pt=118326163&ct=telegram&mt=8
```

（ja／en 純文字版同上方 JSON 的 text 欄位，換行處照 `\n` 分段，最後一行貼 url。）
