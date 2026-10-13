# Lumi 任務星球：Telegram 貼文替換稿（3 篇改寫＋ko、vi 新增 2 篇）（供 lumimission-02 使用）

| 項目 | 內容 |
|---|---|
| 用途 | `telegram_posts.json` 裡 app `6779750237` 的 3 篇（en、zh-Hant、ja）寫了商店文案沒有的「穿衣／get dressed」，也沒寫 50 種語言。這裡是可直接貼上的替換文字，外加韓文（칭찬스티커 痛點）與越南文（在台新住民家庭）兩篇新稿 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（由 telegram-daily 自動發文）。這份檔案本身不發文；**本次沒有修改 `telegram_posts.json`**，由負責 Telegram 檔案的人照下方 JSON 替換或新增 |
| 發文者 | Lumi Studio 官方頻道（店主 Guan Feng Lai 經營） |
| 發文規則 | 沿用頻道既有規則：每則一個連結（ct=telegram），不重複、不灌版。每篇末尾都有 Pro 導流一句（lumimissionpro-04）。不用其他 App 名稱、不寫排名 |
| 事實依據 | mission_routines_full.json en-US／zh-Hant／ja／ko：吃飯、刷牙、睡覺、收玩具四個任務＋兔兔夥伴免費；一次性內購解鎖上學準備、自訂任務、六隻夥伴、完整貼紙，無訂閱；孩子點一下、兔兔歡呼、任務完成全星球慶祝；無廣告、無帳號。Pro（mission_pro_full.json）：無內購、一次購買、家人共享。50 種介面語言、App 內切換（店主確認） |
| 不能寫 | 穿衣／着替え；上學準備免費；Lite 家人共享；Montessori；「3–6 歲」舊模板用語；越南文版不可照搬 vi 舊模板（「mặc đồ」穿衣、Montessori 都是舊稿） |
| 連結 | 沿用既有格式：https://apps.apple.com/app/id6779750237?pt=118326163&ct=telegram&mt=8 |

> 給替換的人：`lang` 沿用檔案現有寫法（`en`、`zh-Hant`、`ja`）；`ko`、`vi` 都在 `social_post_common.py` 的 ASIA_LOCALES 內，會在亞洲時段發出。越南文那篇是寫給在台灣的新住民家庭，App Store 會依讀者自己的 Apple ID 開到台灣店面，所以文中附上中文名稱「Lumi 任務星球」方便搜尋。

---

## 1. 取代 en（原文：`turn daily routines (brush teeth, get dressed, tidy up)…`）

```json
{
  "lang": "en",
  "app": "6779750237",
  "text": "✅ Lumi Mission Planet — meals, tooth brushing, bedtime and tidy-up become small missions. Every tap makes the bunny buddy cheer, and a finished mission makes the whole planet celebrate. Those four missions and the bunny are free; a one-time unlock adds the rest, no subscription. No ads, no account. 50 interface languages, switchable inside the app. Families who'd rather skip in-app purchase screens can choose Pro (one purchase, Family Sharing).",
  "url": "https://apps.apple.com/app/id6779750237?pt=118326163&ct=telegram&mt=8"
}
```

## 2. 取代 zh-Hant（原文：`把刷牙、穿衣、收拾變成孩子想完成的任務`）

```json
{
  "lang": "zh-Hant",
  "app": "6779750237",
  "text": "✅ 【Lumi 任務星球】吃飯、刷牙、睡覺、收玩具變成小任務：孩子每完成一小步就點一下，兔兔夥伴立刻歡呼，任務完成全星球一起慶祝。這四個任務和兔兔免費，其餘一次買斷、不訂閱；無廣告、不用帳號。介面 50 種語言，可在 App 內切換。不想要內購畫面的家庭也有 Pro（一次購買、家人共享）。",
  "url": "https://apps.apple.com/app/id6779750237?pt=118326163&ct=telegram&mt=8"
}
```

## 3. 取代 ja（原文：`毎日の習慣をミッションにして続ける子ども向けアプリ`）

```json
{
  "lang": "ja",
  "app": "6779750237",
  "text": "🚀 Lumiミッション星 — ごはん・はみがき・ねんね・おかたづけを小さなミッションに。できたら1タップでうさぎの相棒が大よろこび、ミッション達成で星全体がお祝いします。この4つとうさぎの相棒は無料、ほかは買い切り（サブスクなし）。広告なし・アカウント不要。表示言語は50言語からアプリ内で切り替えられます。アプリ内課金の画面を出したくないご家庭には、Pro（買い切り・ファミリー共有対応）もあります。",
  "url": "https://apps.apple.com/app/id6779750237?pt=118326163&ct=telegram&mt=8"
}
```

## 4. 新增 ko（칭찬스티커 痛點）

```json
{
  "lang": "ko",
  "app": "6779750237",
  "text": "⭐ 종이 칭찬스티커판, 일주일 넘기기 어렵지 않나요? Lumi 미션 별은 식사·양치·잠자기·장난감 정리를 작은 미션으로 바꿔요. 아이가 해낼 때마다 한 번 탭하면 토끼 친구가 바로 환호하고, 미션을 끝내면 별 전체가 축하해요. 네 가지 미션과 토끼 친구는 무료, 나머지는 한 번 구매(구독 없음). 광고 없음·계정 없음. 표시 언어 50개, 앱 안에서 바꿀 수 있어요. 인앱결제 화면이 없는 Pro(한 번 구매, 가족 공유)도 있어요.",
  "url": "https://apps.apple.com/app/id6779750237?pt=118326163&ct=telegram&mt=8"
}
```

## 5. 新增 vi（在台新住民家庭：同一台 iPhone，只切介面語言）

```json
{
  "lang": "vi",
  "app": "6779750237",
  "text": "🌏 Mẹ đọc tiếng Việt, bố đọc tiếng Trung, cả nhà dùng chung một chiếc iPhone? Lumi Mission Planet (tên tiếng Trung: Lumi 任務星球) biến ăn cơm, đánh răng, đi ngủ, dọn đồ chơi thành nhiệm vụ nhỏ: bé làm xong là chạm màn hình, bạn thỏ nhảy lên cổ vũ ngay. Bốn nhiệm vụ này và bạn thỏ miễn phí; phần còn lại mua một lần, không thuê bao. Không quảng cáo, không cần tài khoản. 50 ngôn ngữ giao diện, đổi ngay trong app (chỉ đổi giao diện, chữ bạn nhập không được dịch). Gia đình không muốn màn hình mua trong app có thể chọn bản Pro (mua một lần, chia sẻ gia đình).",
  "url": "https://apps.apple.com/app/id6779750237?pt=118326163&ct=telegram&mt=8"
}
```

---

## 替換後檢查

- [ ] `6779750237` 的貼文裡已沒有 get dressed／穿衣／着替え
- [ ] 每篇都有「50 種語言、App 內切換」與 Pro 那一句
- [ ] 沒有任何一篇說上學準備（登園準備／등원 준비）免費
- [ ] 每篇只有一個 url
