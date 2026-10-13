# Lumi 任務星球 Pro：Telegram 四篇替換稿（供 lumimissionpro-03 使用）

| 項目 | 內容 |
|---|---|
| 用途 | `telegram_posts.json` 裡 app `6779745474` 的 4 篇（en ×2、zh-Hant、ja）用了商店文案沒有的「visual routine chart／視覺任務」，還寫了不存在的「穿衣／着替え」，也沒有 50 種語言與 Lite 導流。這裡是逐篇可貼上的替換文字 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（telegram-daily 自動發文）。這份檔案本身不發文；**本次沒有修改 `telegram_posts.json`**，由負責 Telegram 檔案的人照下方 JSON 逐篇取代 |
| 發文者 | Lumi Studio 官方頻道（店主 Guan Feng Lai 經營） |
| 發文規則 | 每則一個連結（維持 ct=telegram）；每篇最後一句指向免費的 Lite（不另放 Lite 連結，讓讀者搜尋名稱）；不寫價格（各國不同）；不寫排名、評分數 |
| 事實依據 | mission_pro_full.json（en-US／zh-Hant／ja）：五個每日任務（吃飯、刷牙、睡覺、收玩具、上學準備）；無限自訂任務、每個可選圖示與場景；六隻夥伴（小熊、兔兔、貓貓、熊貓、小恐龍、小狐狸）；一百個成就貼紙；太空小熊 Lumi 歡呼；家長後台；無廣告、無內購、無訂閱、無帳號；一次購買、家人共享。Lite（mission_routines_full.json）：吃飯、刷牙、睡覺、收玩具四個任務免費。50 種介面語言、App 內切換（店主確認） |
| 不能寫 | visual routine chart／visual schedule／視覺任務；穿衣／get dressed／着替え；Free to try（Pro 是付費下載）；ages 3–6；Montessori；star rewards |
| 連結 | 沿用既有格式：https://apps.apple.com/app/id6779745474?pt=118326163&ct=telegram&mt=8 |

---

## 1. 取代 en（原文：`the full routine-builder for kids: visual missions, rewards…`）

```json
{
  "lang": "en",
  "app": "6779745474",
  "text": "✅ Lumi Mission Planet Pro — five daily missions (meals, tooth brushing, sleep, tidy-up and school prep), unlimited custom missions with your own icon and scene, six buddies and 100 achievement stickers. No ads, no in-app purchases, no subscription, no account. One purchase with Family Sharing. 50 interface languages, switchable inside the app. Want to try first? The free Lumi Mission Planet includes meals, brushing, sleep and tidy-up.",
  "url": "https://apps.apple.com/app/id6779745474?pt=118326163&ct=telegram&mt=8"
}
```

## 2. 取代 en（原文：`Morning meltdowns? A visual routine chart helps…`）

```json
{
  "lang": "en",
  "app": "6779745474",
  "text": "⭐ Hectic mornings before school? Lumi Mission Planet Pro includes a school-prep mission: your child taps each small win and Lumi, a space bear, cheers on the spot. Finish a mission and the whole planet celebrates. No ads, no in-app purchases, no account; one purchase covers the family with Family Sharing. 50 interface languages, switchable inside the app. Prefer to start free? Try Lumi Mission Planet.",
  "url": "https://apps.apple.com/app/id6779745474?pt=118326163&ct=telegram&mt=8"
}
```

## 3. 取代 zh-Hant（原文：`把刷牙、穿衣、收玩具與睡前流程變成…視覺任務`）

```json
{
  "lang": "zh-Hant",
  "app": "6779745474",
  "text": "⭐ 【Lumi 任務星球 Pro】吃飯、刷牙、睡覺、收玩具、上學準備五個每日任務：孩子每完成一小步就點一下，太空小熊 Lumi 立刻歡呼，任務完成全星球一起慶祝。可無限自訂任務，每個都能選圖示與場景。無廣告、無內購、無訂閱、無帳號，一次購買支援家人共享。介面 50 種語言，可在 App 內切換。想先免費試試，可以從 Lumi 任務星球開始。",
  "url": "https://apps.apple.com/app/id6779745474?pt=118326163&ct=telegram&mt=8"
}
```

## 4. 取代 ja（原文：`歯みがき・着替え・片づけ・寝る前の流れを…`）

```json
{
  "lang": "ja",
  "app": "6779745474",
  "text": "⭐ Lumiミッション星 Pro — ごはん・はみがき・ねんね・おかたづけ・登園準備の5つの毎日のミッション入り。できたら1タップで宇宙のくまLumiがその場で大よろこび。アイコンと背景を選べるカスタムミッションは無制限。広告なし・アプリ内課金なし・サブスクなし・アカウント不要、1回の購入でファミリー共有に対応。表示言語は50言語からアプリ内で切り替えられます。まず無料で試すなら「Lumiミッション星」から。",
  "url": "https://apps.apple.com/app/id6779745474?pt=118326163&ct=telegram&mt=8"
}
```

---

## 替換後檢查

- [ ] `6779745474` 的 4 篇已沒有 visual／視覺任務／穿衣／着替え
- [ ] 每篇都有「無內購」「家人共享」「50 種語言、App 內切換」
- [ ] 每篇最後一句指向免費的 Lite
- [ ] 沒有寫價格、評分數或排名
