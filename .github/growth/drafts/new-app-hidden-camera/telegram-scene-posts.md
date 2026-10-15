# Lensafe：Telegram 場景貼文草稿（en／zh-Hant／ja／ko，上架前備稿）

| 項目 | 內容 |
|---|---|
| 用途 | spec.md 第 14 節「第 1 週 Telegram LumiApps2026：每個語言一則場景貼文」的草稿。四種語言各一則，各寫一個查房場景 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（telegram-daily 自動發文），以 Lumi Studio 頻道名義發出 |
| 目前狀態 | **staging，不發文**。本檔沒有修改 `.github/scripts/telegram_posts.json`。Lensafe 尚未上架，所以 `app` 和 `url` 裡的 App ID 都是佔位字 `LENSAFE_APP_ID`。上架後由維護佇列的流程把佔位字換成正式 App ID，再把下面的 JSON 貼進 `telegram_posts.json`（上架後第 1 週）。**佔位字還在的時候不可以貼進佇列** |
| 發文規則 | 每則只放一個連結（`url` 欄位，正文不放連結），參數 `ct=telegram`。不寫價格數字，不寫「免費」「試用」；絕不寫「安全」「保證」「100%」；不提磁力計，不宣稱抓得到竊聽器，不寫準確率數字；不點名其他 App；不放 Airbnb 等他人商標 |
| 事實依據（只用這些） | spec.md ★ 節、第 4、5 節，以及店主提供的 App 事實：<br>・付費下載，無內購、無訂閱、無免費版；iOS 26 起；全部在手機上處理，不收集資料；不做磁力計偵測<br>・打開就是相機，手電筒脈衝，自動標出可能的鏡頭反光<br>・點「確認這一點」，換兩個角度判斷<br>・掃描覆蓋率<br>・前鏡頭紅外線，含電視遙控器自我測試<br>・同一個 Wi-Fi／藍牙上像攝影機的裝置<br>・場景清單與 PDF 查房報告<br>・支援站：https://alice51849.github.io/lensafe-support/ |

## 貼入佇列用 JSON（上架後把 `LENSAFE_APP_ID` 換成正式 ID；與現有條目格式相同，一行一則）

```json
{"lang": "zh-Hant", "app": "LENSAFE_APP_ID", "text": "🔍【Lensafe 針孔偵測】出差住飯店，進房先查房：煙霧偵測器、插座、電視周圍、浴室鏡子旁。Lensafe 打開就是相機，手電筒自動脈衝，畫面上直接圈出可能是鏡頭的反光點；覺得可疑就點「確認這一點」，換兩個角度再判斷一次。暗房裡可以切到前鏡頭找紅外線光點，先用電視遙控器自我測試，確認手機看得到紅外線。手機能查的是幾種常見跡象，不是全部，可疑的地方請靠近確認。全部在手機上處理，不收集資料。付費下載、一次買斷，沒有內購、沒有訂閱。需要 iOS 26 以上。", "url": "https://apps.apple.com/app/idLENSAFE_APP_ID?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "LENSAFE_APP_ID", "text": "🔍 Lensafe：民泊や旅館に泊まる夜、寝る前に部屋をひと回り。暗視カメラの多くは目に見えない赤外線を出すので、Lensafe では前面カメラで暗い部屋の赤外線の光点を探せます。最初にテレビのリモコンでセルフテストをして、そのiPhoneで赤外線が見えることを確かめてから使えます。明るい部屋ではライトが自動で点滅し、レンズかもしれない反射に印が付き、タップすると角度を変えてもう一度判定します。スマホで確認できるのはよくある手がかりで、すべてではありません。処理はすべて端末内、データは集めません。有料ダウンロードの買い切りで、アプリ内課金・サブスクなし。iOS 26以降。", "url": "https://apps.apple.com/app/idLENSAFE_APP_ID?pt=118326163&ct=telegram&mt=8"}
{"lang": "ko", "app": "LENSAFE_APP_ID", "text": "🔍 Lensafe: 숙소에 도착하면 몰카 점검부터. 방 와이파이에 연결하면 같은 네트워크와 주변 블루투스에서 카메라처럼 보이는 기기를 목록으로 보여 줘요. 카메라를 켜면 손전등이 자동으로 깜빡이면서 렌즈일 수 있는 반사 지점에 원이 뜨고, 탭하면 각도를 바꿔 한 번 더 확인해요. 스캔 범위 표시로 아직 안 비춘 방향도 알 수 있고, 장소별 체크리스트를 마치면 PDF 점검 보고서로 남길 수 있어요. 휴대폰으로 볼 수 있는 건 흔한 단서 몇 가지일 뿐 전부는 아니에요. 모든 처리는 기기 안에서, 데이터 수집 없음. 유료 다운로드 한 번 구매, 인앱 결제·구독 없음. iOS 26 이상.", "url": "https://apps.apple.com/app/idLENSAFE_APP_ID?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "LENSAFE_APP_ID", "text": "🔍 Lensafe: checking in to a hotel room or a rental? Open Lensafe and you're already in the camera. The flashlight pulses on its own and possible lens reflections get a ring on screen; tap one to check it from two angles. In a dark room, the front camera looks for infrared points, and a TV remote lets you test that your iPhone can see infrared first. It also lists camera-like devices on the same Wi-Fi and nearby Bluetooth, shows how much of the room you've scanned, and exports a PDF room-check report. A phone can check common signs, not everything, so look closely at anything suspicious. Everything stays on your iPhone; no data collected. Paid download: one purchase, no in-app purchases, no subscription. iOS 26 or later.", "url": "https://apps.apple.com/app/idLENSAFE_APP_ID?pt=118326163&ct=telegram&mt=8"}
```

## 純文字版（人工貼到頻道時用；上架前一律用佔位字）

### zh-Hant

```text
🔍【Lensafe 針孔偵測】出差住飯店，進房先查房：煙霧偵測器、插座、電視周圍、浴室鏡子旁。Lensafe 打開就是相機，手電筒自動脈衝，畫面上直接圈出可能是鏡頭的反光點；覺得可疑就點「確認這一點」，換兩個角度再判斷一次。暗房裡可以切到前鏡頭找紅外線光點，先用電視遙控器自我測試，確認手機看得到紅外線。手機能查的是幾種常見跡象，不是全部，可疑的地方請靠近確認。全部在手機上處理，不收集資料。付費下載、一次買斷，沒有內購、沒有訂閱。需要 iOS 26 以上。
https://apps.apple.com/app/idLENSAFE_APP_ID?pt=118326163&ct=telegram&mt=8
```

（ja／ko／en 的純文字版同上方 JSON 的 text 欄位，最後一行貼 url。）

## 上架後的檢查

- [ ] `LENSAFE_APP_ID` 全部換成正式 App ID，連結打開是 Lensafe 的商品頁（四個語言的商店都要有販售）
- [ ] 文案與上架版商品頁一致（功能名稱、iOS 版本需求）；商品頁沒寫到的功能就刪掉那一句
- [ ] 每則仍只有一個連結，`ct=telegram`
- [ ] 同一語言不和其他 Lensafe 條目擠在同一週輪播
