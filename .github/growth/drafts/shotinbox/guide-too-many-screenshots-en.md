# ShotInbox：英文教學「Too many screenshots on your iPhone? Find the text first, then clear them」（shotinbox-03，en）

| 項目 | 內容 |
|---|---|
| 用途 | en-US 副標寫「Photo Cleaner」去搶大廠詞，外部導流近乎零；en-US answers 頁相似度 91–95% 有模板頁風險。這篇是人工撰寫、可取代那批模板頁的一頁教學：先教 iPhone 內建（Photos 搜尋截圖文字、Screenshots 相簿批量刪、Copy and Delete），再寫內建做不到的，最後才介紹 ShotInbox |
| 發在哪／給誰 | 1) 網站 guides 頁（英文，en-US 只保留這一頁，見 shotinbox-04）；2) 店主本人 Medium 或 dev.to 帳號（全文，加 canonical 指回網站頁）；3) r/iosapps 每週自我推廣串只貼 2–3 行摘要＋連結（依該版規則，由店主依 shotinbox-07 處理）；4) Threads／X 一則摘要，連結放第一則回覆。讀者：camera roll 裡堆滿截圖的英語 iPhone 使用者 |
| 發文者 | 店主 Guan Feng Lai 本人名義。開頭「Disclosure」句不可刪（美國 FTC 對自家產品推薦要求清楚揭露） |
| 發文規則 | 不點名其他 App（包括自家 PicClear）；不寫「best」「#1」；不寫無出處數字；不寫價格數字；Reddit 只在每週自我推廣串發、只發一次，回覆要揭露身分、不拉票；每帳號每天 ≤3 則；追蹤碼用 sib_en_* |
| 事實依據 | ShotInbox en-US 商店文案（_engine/data/shotinbox_full.json）：categories（Shopping, Receipts, Travel, Tickets, Maps & Places, Chats & Social, Work, Study, Recipes & Food, Inspiration, QR & Codes, Errors & Tech, Sensitive）；search text, categories, links；detected events and reminders ordered by time；Open in Maps, Open Link, Copy Text, Open Code, Call Number, Track Package, Add Reminder, Add to Calendar；never auto-deletes, Photos asks for final confirmation；Apple Vision + Natural Language on-device, nothing uploaded；latest 50 screenshots include the complete core workflow for free；Lifetime Pro one purchase, no subscription：unlimited history, custom rules, batches & similar groups, sensitive lock, widgets, backup & export。50 種介面語言、App 內切換（店主確認） |
| 不能寫 | 「photo cleaner」「cleans your whole library」；auto-delete；AI decides what to delete；價格；batch actions 是免費功能 |
| 發前確認 | 用英文介面的 iPhone 對一次選單字樣（Media Types, Screenshots, Recently Deleted, Copy and Delete, Live Text） |
| 連結 | 網站／Medium：https://apps.apple.com/app/id6802166527?pt=118326163&ct=sib_en_guide&mt=8<br>Reddit：https://apps.apple.com/app/id6802166527?pt=118326163&ct=sib_en_reddit&mt=8 |

---

## 貼上用內文

**Title:** Too many screenshots on your iPhone? Find the text you need first, then clear them in bulk

```text
Disclosure: I'm the developer of ShotInbox, an iPhone app for screenshots (indie, based in Taiwan). Everything before the last section uses only built-in iPhone features. If those are enough for you, you don't need any app.

A booking confirmation. A bank transfer reference. Something you wanted to buy. An address a friend sent. Every screenshot was a small "I'll deal with this later." Then a few hundred of them piled up in the camera roll.

You want the storage back, but you're afraid of deleting the one screenshot you still need. The trick is the order: find what you need first, then delete in bulk.

1) FIND THE TEXT INSIDE A SCREENSHOT: SEARCH IN PHOTOS

Recent iPhones recognize text inside images (Live Text), so you can search for words that appear in a screenshot.
1. Open Photos and tap Search.
2. Type a word you remember: a booking code, a store name, "invoice", "address".
3. Photos and screenshots containing that text show up in the results.
4. Open the screenshot and touch and hold the text to copy it. Tap a phone number to call it or a link to open it.

Spotlight (swipe down on the Home Screen) can find text in photos too. Which languages and models are supported depends on your iOS version.

2) SEE ONLY YOUR SCREENSHOTS

Photos → scroll down to Media Types → Screenshots. Regular photos don't show up here.

3) DELETE IN BULK

1. In the Screenshots album, tap Select.
2. Put a finger on the first screenshot and drag across and down to select a whole block.
3. Tap the trash icon.
4. Deleted screenshots go to Recently Deleted first, where you can recover them for a while. Once you're sure, delete them from Recently Deleted as well; that's when the storage is actually freed.

Heads-up: if iCloud Photos is on, deleting here also deletes the same screenshots from iCloud and your other devices.

4) STOP THE PILE FROM GROWING

- After taking a screenshot, tap the thumbnail in the corner → Done → Copy and Delete. Screenshots you only needed to paste into a chat won't stay in your camera roll.
- The same menu has Save to Files. Receipts and documents you want to keep can go into a folder in the Files app instead of your camera roll.

5) WHAT THE BUILT-IN TOOLS DON'T DO

- Sort screenshots into groups like shopping, receipts, tickets, places or chats. The Screenshots album is only sorted by date.
- Suggest "open this address in Maps" or "add this date to your calendar".
- Keep track of which screenshots you've already dealt with, so you end up scrolling through the same ones again.

6) FINALLY: THE APP I BUILT, SHOTINBOX

I built ShotInbox for those three gaps. It is designed specifically for screenshots.

- Sorting: Shopping, Receipts, Travel, Tickets, Maps & Places, Chats & Social, Work, Study, Recipes & Food, Inspiration, QR & Codes, Errors & Tech, Sensitive.
- Search the text inside screenshots, plus categories and links.
- A timeline of detected events and reminders, ordered by time.
- Act right away: Open in Maps, Open Link, Copy Text, Open Code, Call Number, Track Package, Add Reminder, Add to Calendar.
- It never deletes anything on its own. When you do delete, the Photos app asks you to confirm.
- Text recognition and sorting use Apple Vision and Natural Language on your device. Nothing is uploaded.
- The interface is available in 50 languages, and you can switch inside the app.

Pricing, plainly: your latest 50 screenshots get the complete core workflow (sorting, search, actions) for free. Lifetime Pro is a one-time purchase, not a subscription, and adds unlimited screenshot history, custom rules, batches and similar groups, a sensitive lock, widgets, and backup and export.

Honest note: if you only take a dozen screenshots a month, the Photos search in step 1 plus the Screenshots album is enough. If you have hundreds and keep digging through them for addresses, bookings and receipts, ShotInbox may save you time.

App Store: https://apps.apple.com/app/id6802166527?pt=118326163&ct=sib_en_guide&mt=8

FAQ

Q: Photos search can't find the text in my screenshot.
A: Check that your iPhone supports Live Text and try just one or two keywords. Very recent screenshots may not be indexed yet; try again a bit later.

Q: I deleted screenshots but my storage didn't change.
A: Empty the ones you're sure about from Recently Deleted.

Q: Some of my screenshots contain passwords or IDs. Is an organizer app safe?
A: Check the App Privacy section on the App Store page and the app's description first. ShotInbox processes everything on the device and uploads nothing. Still, the safest habit is not to keep passwords or ID documents as screenshots at all.
```

---

## r/iosapps 每週自我推廣串用（2–3 行，只發一次）

```text
Dev here (solo, Taiwan). ShotInbox sorts iPhone screenshots on-device into receipts, tickets, places, chats and more, lets you search the text inside them, and adds actions like Open in Maps or Add to Calendar. It never auto-deletes. Latest 50 screenshots get the full workflow free; Pro is a one-time purchase. I also wrote up the built-in way (Photos search + Screenshots album) if you'd rather not install anything: <網站 guides 頁網址>
https://apps.apple.com/app/id6802166527?pt=118326163&ct=sib_en_reddit&mt=8
```

## Threads／X 摘要（本體不放連結，連結放第一則回覆）

```text
Hundreds of screenshots, scared to delete the one you still need?
Search first: Photos search finds text inside screenshots (booking codes, store names). Keep what matters, then go to Media Types → Screenshots and drag to select in bulk.
Full steps in the link below. The last section is about an app I built (I'm the developer).
```

第一則回覆：`Full guide: <網站 guides 頁網址>`
