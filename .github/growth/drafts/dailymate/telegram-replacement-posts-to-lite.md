# DailyMate：Telegram 2 則貼文改導向 DailyMate Lite（dailymate-04）

| 項目 | 內容 |
|---|---|
| 用途 | `telegram_posts.json` 裡 app `6790418321`（DailyMate 付費版）的 2 則（索引 177 en、178 ja）。依報告，外宣交給免費的 DailyMate Lite（6794725568）；正文改寫成 Lite 的功能，文末一句「不想內購可選付費版 DailyMate」 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（telegram-daily 自動發文）。本檔不發文；**本次沒有修改 `telegram_posts.json`**，由負責該檔的人照下方 JSON 替換（`app` 與 `url` 改成 Lite） |
| 發文者 | Lumi Studio 官方頻道（店主 Guan Feng Lai 經營） |
| 發文規則 | 沿用頻道規則：每則一個連結（ct=telegram），不重複、不灌版；不寫排名、不用其他 App 名稱 |
| 事實依據 | Lite：dailymatelite_full.json en-US／ja——8,400 組 cue-and-reply；50 種學習語言；14 主題、84 情境；初級／中級／高級；裝置系統語音發音；各語言進度、連續天數、收藏分開；任何學習語言都能免費練「Traveler（旅行）」初級；一次購買解鎖全部主題與級別、無限收藏、互動小工具、Apple Watch、App Intents；無訂閱；無帳號、第三方廣告、分析、追蹤。付費版：dailymate_full.json——8,400 句完整短句、47 種學習語言、每主題三級各 200 句；付費下載、一次購買完整體驗、無訂閱。介面 50 種語言、App 內切換（店主確認） |
| 學習語言數 | Lite 寫 50、付費版寫 47：兩款分開寫，不混用。「50 種介面語言」與「學習語言數」也要分開 |
| 不能寫 | 付費版「50 種學習語言」；Lite 免費層含旅行以外的主題；「最好的語言 App」；其他語言 App 名稱 |
| 新連結 | `https://apps.apple.com/app/id6794725568?pt=118326163&ct=telegram&mt=8`，`app` 改為 `6794725568` |

---

## 1. 索引 177，取代 en（原文：`🗣️ DailyMate — Learn a language the way you actually use it: complete sentences, not isolated words. Pay once, no subscription.`）

```json
{
  "lang": "en",
  "app": "6794725568",
  "text": "🗣️ You know the words, but when the waiter looks at you, nothing comes out. DailyMate Lite practices the exchange, not the word list: a useful cue with a natural reply, 8,400 pairs across 14 topics and 84 situations in 50 learning languages, with on-device system voices. Pick any language and the whole Traveler topic at Beginner level is free; one purchase unlocks every topic and level, widgets and the Apple Watch app. No subscription, no account, no ads. 50 interface languages, switchable in the app. Rather buy a paid app with no in-app purchase? There's DailyMate: 8,400 complete phrases in 47 learning languages.",
  "url": "https://apps.apple.com/app/id6794725568?pt=118326163&ct=telegram&mt=8"
}
```

## 2. 索引 178，取代 ja（原文：`🗣️ DailyMate — 実際に使う形で学ぶ語学アプリ。単語ではなく完全な文で。買い切り、サブスクなし。`）

```json
{
  "lang": "ja",
  "app": "6794725568",
  "text": "🗣️ 単語は覚えたのに、いざ話そうとすると言葉が出てこない。DailyMate Lite は「問いかけ」と「自然な返答」のペアで一往復を練習します。8,400組、14テーマ・84場面、学習言語50、端末のシステム音声で発音を確認。どの言語でも「旅行」初級はすべて無料、買い切りで全テーマ・全レベル、ウィジェット、Apple Watch を解除。サブスクなし、アカウント不要、広告なし。表示言語は50言語からアプリ内で切り替え。アプリ内課金のない有料版がよければ、47言語・8,400フレーズの DailyMate もあります。",
  "url": "https://apps.apple.com/app/id6794725568?pt=118326163&ct=telegram&mt=8"
}
```

---

## 替換後檢查

- [ ] 兩則的 `app` 都是 `6794725568`，`url` 都是 id6794725568＋ct=telegram
- [ ] Lite 寫 50 種學習語言、付費版寫 47，沒有混用
- [ ] 免費範圍只寫「Traveler／旅行」初級
- [ ] 每則只有一個 url
