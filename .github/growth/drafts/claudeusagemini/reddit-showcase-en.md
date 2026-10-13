# UsageNow：Reddit showcase 兩版（r/ClaudeAI、r/ChatGPTCoding）（claudeusagemini-03）

| 項目 | 內容 |
|---|---|
| 用途 | 在兩個工程師子版各發一篇「我做了這個」的作品介紹，揭露開發者身分，說清楚登入與隱私，邀請回饋 |
| 發在哪／給誰 | 版本 A：r/ClaudeAI（重度 Claude／Claude Code 使用者，重點是 5 小時與每週額度）。版本 B：r/ChatGPTCoding（同時用 Codex、Copilot、Claude、Gemini 的人，重點是多服務、多帳號並排） |
| 發文者 | 擁有者 Guan Feng Lai 本人的 Reddit 帳號；內文第一段就揭露是開發者 |
| 發文規則 | **發文前先讀兩個子版的側欄規則與置頂文**：只在允許自我推廣的地方發（有的子版要求用特定 flair、只能發在每週 showcase／self-promotion 串、或禁止貼連結）。規則禁止就不發，或只發在它指定的串。兩版各發一次、不同天發，不要同一天複製貼上到更多子版。連結依子版規則放內文或第一則留言。不要求 upvote、不拿任何東西換評分或評論、不私訊推銷。自我推廣只能是帳號活動的一小部分，平常要有正常參與 |
| 事實依據 | `_engine/data/claudeusagemini_full.json` en-US 商店文案；50 種介面語言、App 內切換（擁有者確認） |
| 不能寫 | 價格數字、排名、下載數、「best／#1」、其他追蹤 App 的名字、「官方／Anthropic 認可」；「用 Claude 寫的」之類的說法（除非屬實且你想說） |
| 連結 | A：https://apps.apple.com/app/id6818607603?pt=118326163&ct=usagenow_r_claudeai&mt=8 ；B：https://apps.apple.com/app/id6818607603?pt=118326163&ct=usagenow_r_chatgptcoding&mt=8 ；FAQ：`{{FAQ_URL}}`（安全性 FAQ 上線後替換） |

---

## 版本 A：r/ClaudeAI

**Title**

```text
I made an iPhone widget that shows Claude's 5-hour and weekly limits, with reset countdowns
```

**Body**

```text
Disclosure first: I'm the developer of this app (UsageNow, by Lumi Studio, a one-person studio). It has a free 24-hour trial and then a one-time purchase, no subscription. Not affiliated with Anthropic.

The problem it's for: the 5-hour window looks fine, you start a long Claude Code task, and the weekly limit is the one that stops you. Or you have a work Max plan and a personal Pro account and can't remember which resets first.

What it does:
- Claude's 5-hour session limit and weekly limits, including per-model weekly caps, each with a live countdown and the exact reset time in your local format
- Alerts you set yourself: choose the 5-hour limit, the weekly limit or all limits, then type a percentage like 90 or 98. Each fires once per limit per cycle. Optional alert when a limit resets.
- Several accounts side by side, sorted by 5-hour reset, weekly reset or usage, or in your own order
- Home Screen and Lock Screen widgets in every size (flip through accounts on the widget, tap to refresh), plus Apple Watch complications
- It also covers ChatGPT Codex, GitHub Copilot and Gemini if you use those too
- iPhone, iPad and Apple Watch; the interface is in 50 languages, switchable in Settings

On sign-in, since that's the obvious question: you sign in on Anthropic's own login page inside the app. The sign-in is kept in your device's Keychain. There's no UsageNow server and no UsageNow account; the app talks only to the services you sign in to (plus Apple for the purchase), and there's no tracking. You can revoke it by removing the account and signing out of other sessions in your Claude account settings. I wrote up the details here: {{FAQ_URL}}

If you only use one account at your desk, Claude Code's own usage view is all you need. This is for checking from the phone, Lock Screen or Watch, or juggling several accounts.

App Store: https://apps.apple.com/app/id6818607603?pt=118326163&ct=usagenow_r_claudeai&mt=8

Feedback welcome, especially on the sign-in and privacy side, and on which limit you actually hit most.
```

> 「Claude Code's own usage view」：發文前在最新版 Claude Code 跑一次 `/usage` 確認還在；指令改名就照實際名稱寫。

---

## 版本 B：r/ChatGPTCoding

**Title**

```text
Built an iOS widget that tracks Codex, Copilot, Claude and Gemini plan limits side by side
```

**Body**

```text
Disclosure: I'm the developer (UsageNow, Lumi Studio). It's an indie iOS app with a free 24-hour trial, then a one-time purchase, no subscription. Not affiliated with OpenAI, GitHub, Microsoft, Anthropic or Google.

If you switch between coding agents, each one counts limits differently and shows them in a different place. UsageNow puts them on one screen and in widgets:

- ChatGPT Codex: 5-hour and weekly windows
- GitHub Copilot: premium requests, chat and code completions
- Claude: 5-hour session and weekly limits, including per-model weekly caps
- Gemini: daily request quotas for each model

Every limit has a live countdown to its reset and the exact reset time in your local format. You can sort accounts by 5-hour reset, weekly reset, highest or lowest usage, name or service, so the one that frees up next is on top. Alerts are yours to set (pick a limit, type a percentage like 90), once per limit per cycle, plus an optional reset alert.

Widgets: Home Screen and Lock Screen in every size, flip through every account right on the widget, tap to refresh. Apple Watch complications too. iPhone, iPad, Watch. Interface in 50 languages, switchable in Settings.

How sign-in works: on each service's own login page, inside the app. It's stored in the device Keychain. No UsageNow server, no account, no tracking; the app talks only to the services themselves (and Apple for the purchase). Details and how to revoke access: {{FAQ_URL}}

App Store: https://apps.apple.com/app/id6818607603?pt=118326163&ct=usagenow_r_chatgptcoding&mt=8

Curious which limit bites you most, and what you'd want on the widget.
```

---

## 留言區預備回覆（依對方問法改寫）

- **「Why should I give an app my sessions?」** → 照 `show-hn-post-en.md` 預備回覆 1，最後一句保留「免費方法也完全合理」。
- **「Android／Mac?」** → `Not right now: iPhone, iPad and Apple Watch.`
- **「Price?」** → `It's a one-time purchase after the 24-hour trial; the App Store page shows the current price in your region.`（不要從記憶寫數字）
- **「Is it open source / how does sign-in work technically?」** → 只能由你根據實作親自回答，見 `show-hn-post-en.md`「只能你親自回答的問題」。
