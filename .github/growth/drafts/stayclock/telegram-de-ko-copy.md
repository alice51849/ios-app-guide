# Stay Clock：Telegram 佇列德文、韓文貼文文案（stayclock-04 的 Telegram 部分）

| 項目 | 內容 |
|---|---|
| 用途 | Telegram 佇列目前只有 en／ja／zh-Hant；補 de（第一版列為主要市場）與 ko 各一則，主打「舊 iPad／iPhone 變床頭、書桌大字鐘」 |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道，德文與韓文讀者 |
| 發文者 | 由維護 `.github/scripts/telegram_posts.json` 的流程（店主或本機 Claude）貼入佇列，以 Lumi Studio 頻道名義發出。本檔沒有改佇列，也不會自動發出 |
| 發文規則 | 每日精選規則：開頭先寫 50 種語言；只寫商店文案有的功能；不點名其他 App；連結用 `ct=telegram`。**不寫 Flip／Klapp／플립／翻頁**：商店描述沒有翻頁錶面（見 stayclock-01） |
| 事實依據 | de／ko 商店文案：iPhone 與 iPad 變成常亮桌鐘、遠處可讀的大字時間、每款錶面各自的行事曆（關／簡易／月）、充電時恆亮與電量下限、夜間排程與純黑底暗紅錶面、OLED 像素偏移、同一錶面出現在 StandBy／鎖定畫面／主畫面小工具／Apple Watch、整點報時與簡易鬧鐘；免費 1 款錶面、Lifetime 一次購買再加 100 款、無訂閱；無帳號、無廣告、無追蹤、不連網。50 種介面語言（店主確認） |
| 連結 | https://apps.apple.com/app/id6814035888?pt=118326163&ct=telegram&mt=8 |

---

## 德文：貼入佇列用 JSON

```json
{"lang": "de", "app": "6814035888", "text": "🕰️ 50 Sprachen für die Oberfläche, direkt in der App umschaltbar – die iPhone-Sprache bleibt, wie sie ist. Stay Clock macht aus einem iPhone oder iPad (auch dem alten aus der Schublade) eine dauerhaft leuchtende Tischuhr, die man quer durchs Zimmer liest: große Uhrzeit, Kalender pro Zifferblatt, wach beim Laden oder dauerhaft mit Akku-Untergrenze. Nachts ein gedämpftes rotes Zifferblatt auf echtem Schwarz, mit Pixel-Verschiebung für OLED. Dasselbe Zifferblatt in Standby, Widgets und auf der Apple Watch. Ein Zifferblatt gratis, 100 weitere per optionalem Einmalkauf, kein Abo. Kein Konto, keine Werbung, kein Netzwerk.", "url": "https://apps.apple.com/app/id6814035888?pt=118326163&ct=telegram&mt=8"}
```

## 韓文：貼入佇列用 JSON

```json
{"lang": "ko", "app": "6814035888", "text": "🕰️ 인터페이스 언어 50개, 휴대폰 언어 설정은 그대로 두고 앱 안에서 바로 바꿔요. Stay Clock은 아이폰이나 아이패드(서랍 속 예전 기기도)를 방 건너편에서도 읽히는 상시 켜짐 탁상시계로 바꿔 줘요. 큼직한 시간, 페이스마다 고르는 캘린더, 충전 중 화면 켜두기와 배터리 하한 설정. 밤에는 완전한 검정 바탕의 은은한 빨간 페이스, OLED를 위한 픽셀 이동. 같은 페이스를 StandBy·위젯·Apple Watch에서도. 페이스 1종 무료, 선택적 Lifetime 한 번 구매로 100종 추가, 구독 없음. 계정·광고·네트워크 없음.", "url": "https://apps.apple.com/app/id6814035888?pt=118326163&ct=telegram&mt=8"}
```

> 「舊的那台也可以」只在該裝置的 iOS／iPadOS 版本符合 App Store 頁面標示的最低需求時成立；佇列維護者若要更保守，可刪掉括號裡那段。
