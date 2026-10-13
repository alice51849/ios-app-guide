# Snapport：Reddit 只回覆提問的英文模板（snapport-05）

| 項目 | 內容 |
|---|---|
| 用途 | 有人在 Reddit 問「能不能在家拍護照照片」「照片被退件怎麼辦」「2×2 怎麼印」時，店主用來回覆的模板。重點是把規定講清楚、解決對方的問題；App 只在揭露那一行出現，**不帶連結** |
| 發在哪／給誰 | 只回覆**已存在的提問串**，不開新帖。適合的地方：討論護照、旅行、移民文件的子版裡有人直接問到照片時。每個子版先讀側欄規則：禁止自我推廣的子版，連 App 名稱都不提，只回答規定（模板 1–4 的「揭露行」改用版本 B） |
| 發文者 | 店主 Guan Feng Lai 本人的 Reddit 帳號。每則回覆都要有揭露行 |
| 發文規則 | 一串只回一次；不私訊推銷；不放 App Store 連結（對方主動要才在留言回覆名稱，仍不放連結，除非該子版規則允許）；不要求 upvote、不以任何東西交換評分；不複製貼上同一段到多串，依對方問題改寫。自我提及要遠少於一般參與 |
| 事實依據（規定） | 美國國務院照片頁 https://travel.state.gov/en/passports/apply/help/photos.html ：2×2 in；頭部從下巴到頭頂 1–1 3/8 in；白色或米白素色背景、臉與背景無陰影。眼鏡：國務院自 2016-11-01 起規定照片不得戴眼鏡（醫療原因除外，需附說明）——回覆前請到同一頁確認現行說法。德國：2025-05-01 起德國護照與身分證只接受數位傳送的照片（市政 FAQ：stadt-muenster.de、wiesbaden.de），在家拍的照片不適用 |
| 事實依據（App） | snapportlite_full.json en-US（同 shorts-script-2x2-to-4x6-en.md）。介面 50 種語言、App 內切換（店主確認） |
| 不能寫 | 保證受理；第三方價格或「比藥妝店便宜」；其他 App 的名稱或批評；「best」；替任何國家的規定下結論卻沒附官方頁 |

---

## 揭露行（每則回覆最後一行，二選一）

**版本 A（子版允許提及自己的作品時）**
```text
Disclosure: I make a photo-cropping app (Snapport Lite), so I'm biased. Not linking it; any tool or a photo counter works, the rules above are what matter.
```

**版本 B（子版禁止自我推廣時）**
```text
(For transparency: I develop a photo-cropping app, which is why I've read these rules a lot. Not mentioning it here.)
```

---

## 模板 1：「Can I take my own passport photo at home?」

```text
Yes, people do it all the time, but the photo has to meet the same rules as one from a store. For a U.S. passport the State Department page (travel.state.gov, "Passport Photos") is the source; the parts people usually miss:

- 2x2 inches printed, head 1 to 1 3/8 inches from the bottom of the chin to the top of the head
- Plain white or off-white background, no shadows on your face or on the wall behind you. Stand a few feet away from the wall so your shadow doesn't land on it
- Light from the front (face a window in daytime), no flash
- No glasses (check the current wording on that page if you need them for medical reasons)
- Recent photo, no filters, no beauty mode

What helped me most: have someone else take it with the back camera at eye level, from a few feet away, instead of a selfie. Then crop to 2x2 with the head size above and print at actual size.

If you're renewing online, follow the digital photo instructions in the online renewal flow instead of printing.

[揭露行]
```

## 模板 2：「My passport photo got rejected. Why?」

```text
Sorry, that's annoying. The letter or email usually names the reason, so start there. Things the official photo page calls out that are easy to miss:

- Shadows on the face or behind the head (one overhead light does this)
- Head too small or too large: the U.S. rule is 1 to 1 3/8 inches chin-to-crown on a 2x2 print
- Background not plain white/off-white, or the edge of the hair blending into it
- Glasses on
- Photo printed at the wrong scale ("fit to page" on the printer shrinks a 2x2)
- Heavy editing or a filter

Retake it facing a window, a few feet from a white wall, with someone else holding the phone, and check the head size before printing. travel.state.gov has example photos of what's accepted and what isn't.

[揭露行]
```

## 模板 3：「What size photo do I need for [country] visa?」

```text
This one really depends on the country and even the type of application, so go by the embassy or consulate page for that exact visa. Common sizes you'll see are 2x2 in (US), 35x45 mm (many countries), 33x48 mm and 50x70 mm, but some also specify background color and head size, and some only accept digital uploads or photos from certified providers.

If you tell us which visa it is, someone here can probably point to the official page.

[揭露行]
```

## 模板 4：「How do I print a 2x2 photo myself?」

```text
Cheapest way I know: put several 2x2 copies on one 4x6 inch print and cut them out.

1. Crop the photo to exactly 2x2 inches at a decent resolution (300 DPI or more).
2. Lay out copies on a 4x6 canvas with thin cut lines between them.
3. Order a regular 4x6 photo print. If you print at home, turn off "fit to page" / "scale to fit" so it prints at 100%.
4. Measure one copy with a ruler before you cut: it should be 2 inches each way, with the head 1 to 1 3/8 inches.

[揭露行]
```

## 模板 5：只有在對方**直接問有沒有 App 推薦**時

```text
I'm the developer of one, so take this with that bias: Snapport Lite (iPhone). It has a 2x2 preset and 34 others, head-top / eye / chin guides, and a 4x6 print-sheet layout with cut guides. Every preset and edit is free and the first export is free; unlimited exports are a one-time purchase, no subscription. Everything runs on the phone, nothing is uploaded. It can't guarantee acceptance, nothing can, so still check the rules on travel.state.gov.

Not linking it here per the sub rules; it's in the App Store under that name.
```

## 模板 6：有人問德國護照／身分證照片（在家拍不適用）

```text
Heads-up for Germany: since May 2025, photos for the German passport (Reisepass) and ID card (Personalausweis) have to be transmitted digitally by a certified photographer/booth, or taken at the citizens' office where that's offered; a printed photo you took at home won't be accepted for those. Your local Bürgeramt page explains the options. Home photos can still be fine for things like visa applications to other countries, so check the rules for whatever you're applying for.

[揭露行，版本 B]
```

---

## 回覆前自查

- [ ] 對方真的在問照片，而不是我們在找機會插話
- [ ] 讀過該子版規則，選對揭露行版本
- [ ] 沒有連結；沒有價格比較；沒有「保證」
- [ ] 美國規定的數字與 travel.state.gov 當天內容一致
