# TripBee：Telegram 5 則貼文改導向 TripBee Lite（tripbee-04）

| 項目 | 內容 |
|---|---|
| 用途 | `telegram_posts.json` 裡 app `6787754435`（TripBee Pro）共 5 則（索引 148–152：en、zh-Hant、ja、de、es）。依報告，系列外宣全部導向免費的 TripBee Lite（6791299610）；Pro 只在文末一句帶過 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（telegram-daily 自動發文）。本檔不發文；**本次沒有修改 `telegram_posts.json`**，由負責該檔的人照下方 JSON 逐則替換（`app` 與 `url` 都改成 Lite） |
| 發文者 | Lumi Studio 官方頻道（店主 Guan Feng Lai 經營） |
| 發文規則 | 沿用頻道規則：每則一個連結（ct=telegram），不重複、不灌版；不寫排名、不用其他 App 名稱 |
| 為什麼正文要重寫 | 原文寫的是 Pro 的功能（孩子年齡打包、Apple 地圖、離線）。連結改成 Lite 後，正文只能寫 Lite listing 有的：每日時間軸、航班／住宿／活動、備註、提醒、票券資訊；免費存一趟；一次購買解鎖無限行程、分享、完整備份還原、智慧打包清單；無帳號、無廣告／分析／追蹤。Pro 的四項（Apple 地圖、天氣備案、海報、CSV）只出現在文末那句，且明說是 Pro |
| 事實依據 | Lite：tripbeelite_full.json（en-US、zh-Hant、ja、de-DE、es-ES）。Pro：tripbee_full.json en-US（One-time purchase — no subscription, no ads；One-tap Apple Maps directions；weather-aware planning with rainy-day backup ideas；trip or day poster；CSV import）。介面 50 種語言、App 內切換（店主確認；Pro listing 仍寫 40+，貼文以 50 為準） |
| 不能寫 | Lite「離線」（Lite 描述沒寫）；Lite 有孩子年齡打包、Apple 地圖、天氣、海報、CSV；Pro「沒有內購」（Pro listing 沒寫這句，只寫一次購買、無訂閱、無廣告）；「calm／polished」這類抽象形容取代具體情境 |
| 新連結 | `https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8`，`app` 改為 `6791299610` |

---

## 1. 索引 148，取代 en（原文：`✈️ TripBee Pro turns flights, hotels, restaurants and activities into a clear day-by-day plan…`）

```json
{
  "lang": "en",
  "app": "6791299610",
  "text": "✈️ Flight times in one chat, the hotel in another, ticket numbers in screenshots? TripBee Lite puts the trip you're about to take on one day-by-day timeline: flights, stays and activities, with notes, reminders and ticket references next to them. The free app saves one journey at a time; a one-time Premium unlock adds unlimited journeys, sharing, full backup and restore and the smart packing list. No account, no ads, no tracking. 50 interface languages, switchable in the app. Prefer to pay once up front? TripBee Pro adds one-tap Apple Maps directions, rainy-day backup ideas and trip posters.",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

## 2. 索引 149，取代 zh-Hant（原文：`✈️ 【TripBee Pro】把航班、飯店、餐廳與活動排成清楚的每日行程…一次買斷。`）

```json
{
  "lang": "zh-Hant",
  "app": "6791299610",
  "text": "✈️ 訂房確認信、航班截圖、景點門票編號，出發前一晚還在三個 App 之間找？【TripBee Lite】把眼前這一趟排成每日時間軸：航班、住宿、活動一格一格放好，備註、提醒和票券編號就在旁邊。免費版可存一趟，回來再換下一趟；一次買斷 Premium 解鎖無限行程、分享、完整備份與智慧打包清單，沒有訂閱。不用帳號、沒有廣告和追蹤。介面 50 種語言，可在 App 內切換。想直接買付費版，TripBee Pro 另有 Apple 地圖一鍵導航、天氣備案與旅程海報。",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

## 3. 索引 150，取代 ja（原文：`✈️ TripBee Pro なら、フライト・ホテル・レストラン・予定を日ごとの旅程に整理…`）

```json
{
  "lang": "ja",
  "app": "6791299610",
  "text": "✈️ 旅のしおり、まだスクショとメモに散らばっていませんか。TripBee Lite は「いま準備している旅ひとつ」を日ごとのタイムラインにまとめます。フライト・宿泊・予定を並べ、メモ、リマインダー、チケット情報もその横に。無料版は旅を1件保存でき、終わったら次の旅に入れ替え。複数保存・共有・バックアップ・スマート持ち物リストは買い切りの Premium で解除、サブスクなし。アカウント不要、広告・追跡なし。表示言語は50言語、アプリ内で切り替え。最初から買い切りの有料版がよければ、Appleマップ案内や雨の日の代替案がある TripBee Pro もあります。",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

## 4. 索引 151，取代 de（原文：`✈️ TripBee Pro ordnet Flüge, Hotels, Restaurants und Aktivitäten…`）

```json
{
  "lang": "de",
  "app": "6791299610",
  "text": "✈️ Buchungsbestätigung im Postfach, Flugzeiten im Chat, Ticketnummern als Screenshot? TripBee Lite ordnet die nächste Reise in einer klaren Tageszeitleiste: Flüge, Unterkünfte und Aktivitäten, dazu Notizen, Erinnerungen und Ticketinfos griffbereit. Kostenlos lässt sich jeweils eine Reise speichern; ein einmaliger Premium-Kauf schaltet unbegrenzt viele Reisen, Teilen, vollständige Sicherung und die intelligente Packliste frei. Kein Abo, kein Konto, keine Werbung, kein Tracking. 50 Sprachen, direkt in der App umstellbar. Lieber gleich einmal bezahlen? TripBee Pro bietet zusätzlich Apple-Maps-Routen, Regenalternativen und Reiseposter.",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

## 5. 索引 152，取代 es（原文：`✈️ TripBee Pro organiza vuelos, hoteles, restaurantes y actividades…`）

```json
{
  "lang": "es",
  "app": "6791299610",
  "text": "✈️ ¿El vuelo en un correo, el hotel en otro y las entradas en capturas? TripBee Lite ordena el próximo viaje en una cronología diaria: vuelos, alojamientos y planes, con notas, recordatorios y referencias de billetes a mano. La versión gratuita guarda un viaje a la vez; una única compra Premium desbloquea viajes ilimitados, compartir, copia de seguridad completa y la lista de equipaje inteligente. Sin suscripción, sin cuenta, sin anuncios ni seguimiento. Interfaz en 50 idiomas, se cambia dentro de la app. ¿Prefieres pagar una vez desde el principio? TripBee Pro añade rutas con Apple Maps, planes para días de lluvia y pósteres del viaje.",
  "url": "https://apps.apple.com/app/id6791299610?pt=118326163&ct=telegram&mt=8"
}
```

---

## 替換後檢查

- [ ] 5 則的 `app` 都是 `6791299610`、`url` 都是 id6791299610＋ct=telegram
- [ ] 正文裡 Lite 的部分沒有「離線／offline」、孩子年齡、Apple 地圖、天氣、海報、CSV
- [ ] 每則文末都有一句 Pro，而且只寫 Pro listing 有的功能
- [ ] 沒有「40+ languages」
- [ ] 若店主在 tripbee-02 決定 Lite Premium 與 Pro 功能相同，文末那句改成「想一次付清、不在 App 內解鎖，可選 TripBee Pro」，刪掉功能比較
