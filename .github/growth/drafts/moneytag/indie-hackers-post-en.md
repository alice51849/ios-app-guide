# MoneyTag：Indie Hackers 英文稿「Project ledgers + cross-project tags, no subscription」（moneytag-05）

| 項目 | 內容 |
|---|---|
| 用途 | en-US 的「income and expense tracker」是紅海，搜尋撐不起來；Indie Hackers 讀者本身就是「有多個 side project 要分帳」的人。用一篇誠實的開發心得（設計取捨＋學到的教訓：文案寫成會計語、免費版示範不了核心功能），換到真實回饋與少量對口使用者 |
| 發在哪／給誰 | Indie Hackers（indiehackers.com）的 Posts／適合的 group（例如與 side projects、bootstrapping 相關的 group，以發文當時實際存在的為準）；讀者是 solo founder、freelancer、有多個副業的人 |
| 發文者 | 店主 Guan Feng Lai 本人的 Indie Hackers 帳號；文中第一段已寫明是開發者 |
| 發文規則 | Indie Hackers 社群不歡迎純廣告：本文以經驗分享為主，App 連結只在文末出現一次。不要求 upvote、不要求評分、不交換評價。不寫收入、下載數等數字，除非你願意公開真實數字（可自行補上）。不點名其他 App。發文後 48 小時內親自回覆留言。同一篇不在其他 group 重貼 |
| 發文前請確認 | 1) 「What I got wrong」三點都來自 2026-10-13 的診斷報告（關鍵字是會計語、描述以 FAQ 開頭、免費版只有 1 個專案）；如果發文前已經改了（moneytag-01／02／03），把對應段落改成過去式並寫出改了什麼。2) 若想加真實數字（評分數、下載數），只放你自己後台看得到的數字。3) 開頭「A lot of people I know…」要符合你的實際情況；不符就改成「Plenty of people have…」 |
| 事實依據 | en-US 商店文案（2026-10-13）：each project is a self-contained ledger with its own transactions, currency and net result；pick input currency on the Home screen, saved in project base currency；public rates about every 6 hours or manual rate；tags on any income or expense, Tags screen totals a tag across all projects；cross-project tag analysis is part of Lifetime Pro；Free · 1 project · 5 entries；Lifetime Pro: unlimited projects, tags and reports, one purchase；Export CSV／PDF／Photo；backup & restore；Apple Watch app；Home and Lock Screen widgets；iCloud Sync via user's own iCloud (Lifetime Pro)；on-device storage；automatic rates send the three-letter currency code to a public rate service, manual rate avoids it。介面 50 種語言、App 內切換（店主確認）。診斷事實見 .github/growth/apps/moneytag.md |
| 連結 | https://apps.apple.com/app/id6801956402?pt=118326163&ct=mt_ih_en&mt=8 |

---

## 貼上用內文

**Title:** Project ledgers + cross-project tags, no subscription: what I learned building a money app for people with several side gigs

```text
I'm Guan Feng, a solo iOS developer in Taiwan. This post is about MoneyTag, an app I built, so take it as a maker's write-up, not a neutral review.

THE PROBLEM

A lot of people I know don't have "a budget". They have a day job, plus freelance work, plus a weekend market stall, plus a room they rent out, plus they're the treasurer of a club. A single budget with categories doesn't fit that. Categories answer "how much did I spend on transport?", but they can't answer the question these people actually ask:

"Which of these things is actually making money?"

THE MODEL I ENDED UP WITH

1. Projects are separate ledgers.
Each project has its own transactions, its own currency and its own bottom line: income minus expenses. The freelance work doesn't leak into the market stall.

2. Tags cut across projects.
You can still ask the cross-cutting question. Tag anything "Transport" (or "Materials", or "Fees"), and the Tags screen totals that tag across every project: income, expenses and net.

So: projects for "is this worth it?", tags for "where is it going overall?".

A few decisions that came out of that:
• One currency per project. If a client pays in USD, you pick USD as the input currency on the Home screen and it's saved in the project's base currency. Rates refresh about every 6 hours, or you set a manual rate.
• No account. Data lives on the device. iCloud Sync (iPhone + iPad on the same ledger) goes through the user's own iCloud, not a server of mine.
• If automatic rates are on, the app sends the three-letter currency code to a public rate service. You can switch to a manual rate and nothing is sent. I put that in the App Store description in full, because people with side income tend to care.
• Exports: CSV, PDF, a photo, and backup & restore.
• Apple Watch app to add a transaction, and Home/Lock Screen widgets for the current project.
• The interface is in 50 languages and you can switch inside the app. That matters more than I expected for small businesses where two people share one iPad and read different languages.
• Pricing: free to download, Lifetime Pro is one purchase. No subscription.

WHAT I GOT WRONG (SO FAR)

1. I described it in accountant language.
My keywords were things like "P&L tracking" and "job costing". Nobody with a market stall types that. In Japan, the apps that show up for "side job income/expense" literally have those words in their names; my Japanese subtitle said "Projects · Tags · Report". I'm rewriting the store copy in the words people actually use: side hustle, landlord, market stall, club treasurer.

2. My description opened with an FAQ and a privacy disclosure.
Everything in it is true and I'll keep it, but the first three lines should describe the problem, not the data processing. That's moving to the end.

3. The free tier can't show the core idea.
Free is 1 project and 5 entries. But the whole point is several projects plus tags across them, which needs at least two projects. So a free user never sees the thing that makes the app different. I'm deciding how to fix that.

WHAT I'D LIKE TO KNOW

If you run more than one income stream:
• How do you keep them apart today? Separate spreadsheets, one sheet with a column, separate bank accounts?
• Would you rather split by project and tag across, or the other way round?
• What would the free version need to show you before you'd trust it with real numbers?

I'll reply to every comment.

App Store (iPhone, iPad, Apple Watch): https://apps.apple.com/app/id6801956402?pt=118326163&ct=mt_ih_en&mt=8
```
