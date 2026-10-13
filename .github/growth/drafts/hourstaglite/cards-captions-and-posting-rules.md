# HoursTag Lite：雙 11／黑五共用圖卡與貼文（hourstaglite-04）

| 項目 | 內容 |
|---|---|
| 用途 | HoursTag 與 HoursTag Lite 共用同一套「這東西＝幾小時工」填空圖卡（繁中、日文、英文；韓文在 `../hourstag/`），所有貼文的結尾一律導向**免費的 HoursTag Lite**，付費版不放連結 |
| 發在哪／給誰 | 店主本人的 Threads、Instagram、X。繁中＝台灣雙 11；日文＝日本ブラックフライデー；英文＝美國等英語市場的 Black Friday。讀者是正在看購物車、還沒按下結帳的人 |
| 發文者 | 店主 Guan Feng Lai 本人帳號，每則都寫明開發者身分 |
| 發文規則 | 每帳號每天最多 1 張卡；同一張卡同平台只發一次。連結只放第一則留言（或簡介），圖上與貼文本體不放連結。不引用統計（基本工資、平均時薪、消費調查都不用），只讓讀者用自己的時薪。不羞辱購物者，每張卡都以「算完還想要就買」收尾。不寫「最好用」「#1」「best」。日本貼文開頭標【PR・自社アプリ】 |
| 發文前提 | **hourstaglite-01 完成（Lite 商店頁截圖 ≥3 張）才發**。目前六個店面都只有 1 張截圖，圖卡帶來的點擊會落在無法說服人的頁面上。檢查方式：`https://itunes.apple.com/lookup?id=6794039979&country=tw` 的 `screenshotUrls` 長度 |
| 檔期 | 繁中：2026/11/4–11/10（雙 11 前一週）。日文、英文：2026/11/20–11/26（黑五 11/27 前一週） |
| 事實依據 | HoursTag Lite 商店文案（en-US／zh-Hant／ja，2026-10-13）：把價格換算成工作時間；每工作一小時的實領價值；Need／Want／Impulse；目標需要的工時與進度；Widget、Apple Watch；資料只在裝置、無帳號、不追蹤；一次付費、永久使用、無訂閱、解鎖無限。免費版具體上限商店文案沒寫，**不寫數字**。介面 50 種語言、App 內切換（店主確認） |

---

## 圖檔（1080×1350，可直接匯出 PNG）

| 檔案 | 語言 | 搭配的貼文文字 | 第一則留言連結 |
|---|---|---|---|
| `card-checkout-hours-zh-hant.svg` | 繁中（雙 11） | `../hourstag/double11-black-friday-card-copy.md` 的 zh-1 | https://apps.apple.com/app/id6794039979?pt=118326163&ct=htl_card_zh&mt=8 |
| `card-checkout-hours-ja.svg` | 日文（ブラックフライデー） | 同檔 ja-1 | https://apps.apple.com/app/id6794039979?pt=118326163&ct=htl_card_ja&mt=8 |
| `card-checkout-hours-en.svg` | 英文（Black Friday） | 本檔下方 en-1 | https://apps.apple.com/app/id6794039979?pt=118326163&ct=htl_card_en&mt=8 |
| `../hourstag/card-checkout-hours-ko.svg` | 韓文（블프） | 同檔 ko-1 | https://apps.apple.com/app/id6794039979?pt=118326163&ct=htl_card_ko&mt=8 |

匯出方法：用 Safari／Chrome 開啟 SVG，以 1080×1350 視窗截圖；或在 Mac 上 `rsvg-convert -w 1080 -h 1350 card-checkout-hours-zh-hant.svg -o card-zh.png`。字型會用系統的蘋方／Hiragino／Apple SD Gothic Neo／SF，請在 Mac 或 iPhone 上匯出，避免缺字。

---

## en-1｜Black Friday: before you check out（2026/11/20–11/26）

**Card text**（已做進 `card-checkout-hours-en.svg`）
- Label: Before Black Friday checkout
- Headline: How many hours of work is this?
- Fill-in: Price $____ ÷ Take-home per hour $____ = Hours of work ____ hours
- Note: Take-home per hour = monthly take-home ÷ hours worked per month
- Checkboxes: Need / Want / Impulse
- Closing: Still want it after the maths? Buy it.
- Footer: HoursTag Lite · Free download · Prices turned into work time · Data stays on your phone · No account · 50 interface languages, switch in-app · Card made by the app's developer

**Post text**

```text
One thing before you hit "Place order" this Black Friday:
divide the price by what you actually take home per hour.
Price ÷ take-home per hour = hours of work.
Still want it after the maths? Buy it. Not sure anymore? Leave it in the cart overnight.

I got tired of doing this on a calculator, so I built an app for it. HoursTag Lite is a free download: set your take-home hourly value once, and any price shows up as work time. You can tag each one Need, Want or Impulse. Data stays on your phone, no account. One payment unlocks unlimited use; no subscription. 50 interface languages, switchable in the app.
(I'm the developer. Link in the first comment.)
```

**Alt text**: Fill-in card: price divided by your take-home pay per hour equals hours of work, with Need, Want and Impulse checkboxes.

---

## en-2｜The "free shipping" add-on（同檔期，純文字貼文或用同版型改字）

**Card text**
- Label: When the cart says "$__ away from free shipping"
- Headline: The thing you added for free shipping: how many minutes?
- Fill-in A: Add-on $____ ÷ take-home per hour $____ × 60 = ____ min
- Fill-in B: Shipping $____ ÷ take-home per hour $____ × 60 = ____ min
- Closing: If B is shorter, paying for shipping is the cheaper choice.

**Post text**

```text
"You're $8 away from free shipping." So we add something we didn't plan to buy.
Two quick numbers, with your own take-home pay per hour:
A: the add-on ÷ take-home per hour × 60 (minutes)
B: shipping ÷ take-home per hour × 60 (minutes)
If B is shorter, paying shipping costs you less work. And if you wanted the add-on anyway, fine, buy it.

HoursTag Lite (free download) turns prices into work time and lets you tag spending Need / Want / Impulse. Data stays on your device, no account. One payment for unlimited use, no subscription. 50 interface languages, switch in-app.
(I'm the developer. Link in the first comment.)
```

> 「$8」只是畫面上常見的提示句型示意，不是統計；可以換成任何金額。

**Alt text**: Two fill-in lines comparing an add-on item and the shipping fee, each converted to minutes of work.

---

## 第一則留言（英文）

```text
HoursTag Lite (free download, iPhone): https://apps.apple.com/app/id6794039979?pt=118326163&ct=htl_card_en&mt=8
```
