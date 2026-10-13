# UsageNow：Show HN 主文＋作者首則留言＋安全性問答（claudeusagemini-03）

| 項目 | 內容 |
|---|---|
| 用途 | 在 Hacker News 發一次 Show HN，讓每天用 AI coding agent 的工程師試用，並在第一時間把「要登入四家服務安不安全」講清楚 |
| 發在哪／給誰 | news.ycombinator.com → submit，標題以「Show HN:」開頭。讀者是 HN 上的工程師 |
| 發文者 | 擁有者 Guan Feng Lai 本人的 HN 帳號（不要開新帳號、不要用別人的帳號）。首則留言已寫明是開發者本人 |
| 發文規則 | **只發一次**。依 HN 規則：不請任何人投票、不在任何地方貼「去幫我按讚」、不用多個帳號（會被當成投票部隊而降權）。送出後立刻貼「作者首則留言」，之後至少 24 小時內親自回覆，語氣平實、不行銷、不吵架。被批評就承認並說明會怎麼改。不在留言裡反覆貼 App Store 連結 |
| 發文前必做 | 1）安全性 FAQ（`usagenow-security.html`）已上線，把下方 `{{FAQ_URL}}` 換成實際網址，例如 https://open.cait518.cc/ios-app-guide/usagenow-security.html 。2）描述末尾的客服信箱已換成 UsageNow 品牌信箱（claudeusagemini-01），否則第一個問題就會是「hourstag 是誰」。3）讀過下方「只能你親自回答的問題」，先想好答案 |
| 事實依據 | `_engine/data/claudeusagemini_full.json` en-US 商店文案；50 種介面語言、App 內切換（擁有者確認，商店文案也有寫） |
| 不能寫 | 價格數字（商店文案沒有）；「best／#1」；任何 App Store 排名或下載數；其他追蹤 App 的名字；「官方」「Anthropic 認可」之類；商店文案沒有的技術細節（OAuth、用哪個 endpoint、是否開源）——除非擁有者親自確認後自己寫 |

---

## 標題（擇一，≤80 字元）

```text
Show HN: UsageNow – Claude, Codex, Copilot and Gemini limits on your iPhone
```

備選：

```text
Show HN: UsageNow – see AI coding plan limits and reset times in a widget
```

## URL 欄

```text
https://apps.apple.com/app/id6818607603?pt=118326163&ct=usagenow_showhn&mt=8
```

（Show HN 要連到「別人可以直接試用」的東西，所以連 App Store；安全性 FAQ 放在首則留言裡。）

---

## 作者首則留言（送出後立刻貼）

```text
Hi HN, I'm Guan Feng Lai, the developer of UsageNow (Lumi Studio, a one-person studio in Taiwan).

UsageNow is an iPhone, iPad and Apple Watch app that shows how much of each AI plan you have left and exactly when it resets:

- Claude: the 5-hour session limit and weekly limits, including per-model weekly caps
- ChatGPT Codex: the 5-hour and weekly windows
- GitHub Copilot: premium requests, chat and code completions
- Gemini: daily request quotas for each model

Every limit has a live countdown and the exact reset time in your local format.

Why a phone app: the numbers are already available from each service, but in different places, and the moment I want them is usually before starting a long agent run or when I'm away from the terminal. A Home Screen widget, a Lock Screen glance or a Watch complication answers "can I start this now, and which account resets first?" without opening anything. Widgets flip through all your accounts, and you can tap one to refresh it.

Multiple accounts: work and personal, Pro and Max, side by side, sorted by 5-hour reset, weekly reset, highest or lowest usage, name or service, or dragged into your own order.

Alerts: you pick the 5-hour limit, the weekly limit or all limits, and type the percentage you care about (say 90 or 98). Each alert fires once per limit per cycle, so the Lock Screen stays quiet. There's an optional alert for the moment a limit resets.

Security, since the app asks you to sign in to these services:

- You sign in on each service's own login page. There's no UsageNow login form and no UsageNow account.
- The sign-in is stored in the iOS Keychain on your device.
- There is no UsageNow server. The app talks only to the services you signed in to, plus Apple for the App Store purchase. No tracking. You can check that with a proxy.
- To revoke: remove the account in the app, and/or sign out of other sessions in the service's own security settings. iOS Keychain items can outlive an app's deletion, so the service-side sign-out is the one to rely on.

More detail (English, Japanese, Traditional Chinese): {{FAQ_URL}}

Pricing, upfront: every feature, widgets included, is free for 24 hours after you start the trial in the app. After that, a single one-time purchase unlocks UsageNow Pro. No subscription.

It's an independent app, not affiliated with Anthropic, OpenAI, GitHub, Microsoft or Google. The interface is translated into 50 languages, and you can switch languages in Settings.

I'd like feedback on two things: the security model, and which limits you actually watch day to day. I'll be around to answer questions.
```

> 「the moment I want them is usually before starting a long agent run or when I'm away from the terminal」是第一人稱的使用情境。如果這不是你自己的真實習慣，改成「the moment you want them is usually…」。

---

## 預先寫好的回覆（依對方實際問法改寫，不要整段照貼）

### 1. 「It has my session for four services. Why should I trust it?」

```text
Fair question, and it's the one I'd ask too. What I can say concretely: you type your credentials on each service's own login page, not into a form I made; the resulting sign-in lives in the iOS Keychain; and there is no server on my side for anything to be sent to. The app's traffic goes to the services you signed in to and to Apple for the purchase, which you can confirm with a proxy. If you'd rather not grant that access at all, the free options (each service's own usage page or CLI command) are perfectly reasonable; the app is for people who want all of it in one widget.
```

### 2. 「How do I revoke it?」

```text
Remove the account in the app, and if you want certainty, sign out of other sessions in that service's own security settings. That ends it on the service side regardless of the phone. One iOS detail worth knowing: Keychain items can survive deleting an app, so deleting the app alone isn't the guaranteed path; the service-side sign-out is.
```

### 3. 「Does it work offline / without signing in?」

```text
It needs to sign in to each service to read your usage, so no, there's no sign-in-free mode. That's why the FAQ goes into where the sign-in is kept and how to revoke it.
```

### 4. 「Android? Mac menu bar?」

```text
Not at the moment. It runs on iPhone, iPad and Apple Watch.
```

### 5. 「Why not a subscription / why paid?」

```text
It's a one-time purchase rather than a subscription. You get every feature, widgets included, for 24 hours after starting the trial, and then a single purchase unlocks it if you want to keep it.
```

（價格若被問到：只說「the price shown on the App Store page」，或貼出你當天在 App Store 看到的價格；不要從記憶寫。）

### 6. 「How fresh are the numbers in the widget?」

```text
Widgets refresh on iOS's widget schedule, and you can tap a widget to refresh it whenever you want the latest numbers.
```

### 7. 「Isn't this what /usage (or the settings page) already shows?」

```text
Yes, and for one Claude account at a terminal that's all you need. The app is for seeing several accounts and services side by side, getting an alert at the percentage you choose, and glancing at it on the Lock Screen or Watch when you're not at the terminal.
```

---

## 只能你親自回答的問題（不要讓任何人代寫，也不要猜）

下面這些一定會被問，答案必須由你根據 App 的實際實作親自寫；在不確定時就說「I'll check and update the FAQ」，不要先答：

1. **登入是怎麼實作的？**（App 內網頁、`ASWebAuthenticationSession`、OAuth device flow……）以及 App 在技術上能不能讀到密碼欄位。只有在實作上真的讀不到時，才可以說「the app can't see your password」。
2. **鑰匙圈裡存的到底是什麼**（session cookie、token），是否設為 iCloud 鑰匙圈可同步。
3. **讀用量用的是什麼介面**，是否為各服務公開的 API，是否符合各服務條款。不要宣稱「官方」「已獲許可」。
4. **是否開源／能否看原始碼**：照實回答；不開源就直接說不開源。
5. **App 內有沒有任何第三方 SDK**（當機回報、分析）。有的話，FAQ 與首則留言中「talks only to the services」那句必須先改。

---

## 發文後 24 小時檢查表

- [ ] 首則留言已貼，FAQ 連結可開
- [ ] 每個安全性問題都有回覆（不確定的就說會查，並在 FAQ 更新後回同一串）
- [ ] 沒有在任何社群或私訊請人投票
- [ ] 有人指出 FAQ 或商店文案與實際行為不符時，先修 App／文案，再回覆說明修了什麼
