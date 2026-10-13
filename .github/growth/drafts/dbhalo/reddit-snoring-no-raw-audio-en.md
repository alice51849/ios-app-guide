# Reddit r/snoring 說明文：睡眠日誌如何「不存原始錄音」，以及代價（dbhalo-04）

| 項目 | 內容 |
|---|---|
| 用途 | US「snoring」搜尋被大型睡眠 App 佔滿（57k／350k 則評分），dB Halo 缺席，搜尋不可行；唯一差異是「事件分類在裝置上、不保存麥克風原始音訊」。本篇以設計說明為主，**誠實寫出代價**（不能回放確認是誰在打呼）與「不是醫療器材」，不點名任何競品 |
| 發在哪／給誰 | r/snoring。讀者：自己或伴侶打呼、想記錄但不想讓臥室被錄音的人 |
| 發文者 | 店主 Guan Feng Lai 本人的 Reddit 帳號，以開發者身分發文 |
| 發文規則 | ① **先讀 r/snoring 側欄規則**。規則禁止自我推廣 → 不發主文，只在有人問「有沒有不錄音的打呼紀錄 App」時用下方「回覆版」。規則沒寫 → 發文前先用 modmail 問版主（下方附訊息），得到同意才發主文。② 標題與第一段就揭露開發者身分。③ 主文不放連結；有人問才在留言回。④ 同一篇只發一次，不跨版轉貼（不發到 r/sleep 等）。⑤ 不點名任何其他打呼／睡眠 App。⑥ 不給醫療建議，只建議「找醫師」。⑦ 結尾只問使用回饋，不要求評分或評論 |
| 事實依據 | dbhalo_full.json en-US：on-device Sleep Journal recognizes and classifies snoring, breathing, speech, coughing, alarms, animal sounds, impacts, ambient sound, and crying, then logs each event without saving raw microphone audio；Microphone audio is not saved by default; an AAC file is created only when you explicitly start a recording；no account, ads, analytics, tracking；processing stays on your devices；Spectrum, Noise Dose, and Sleep Journal each include one free use；Lifetime Pro is one non-consumable purchase, no subscription；Measurements are estimates, not a certified sound level meter, does not replace medical advice。50 種介面語言、App 內切換（店主確認）|
| 不能寫 | "detects sleep apnea"、"diagnose"、"clinically"；"more accurate than…"；任何其他 App 的名稱；沒有出處的打呼盛行率 |
| 連結（只在被問時於留言回） | https://apps.apple.com/app/id6806826699?pt=118326163&ct=dbh_en_reddit_snore&mt=8 |

---

## ① 先問版主（modmail）

```text
Hi mods, I'm the developer of an iPhone sound meter (dB Halo) that has a sleep journal for snoring. People here sometimes say they don't want their bedroom recorded, and I'd like to write one post explaining how ours logs snoring without saving any audio, including the downsides and that it isn't a medical device. No link in the post. Would that be OK under your rules? If not, no problem at all. Thanks.
```

## ② 主文（版主同意後才發）

**Title:** Developer here: how a snore log can work without saving any bedroom audio (and what you give up)

```text
Disclosure first: I'm the developer of dB Halo, an iPhone sound meter with a Sleep Journal. [只有版主真的回覆同意時才留下這句 → The mods OK'd this post.] I'm writing it because "I don't want my bedroom recorded" comes up here a lot, and I'd rather explain how we handled that, trade-offs included, than drop a link.

How it works
- While you sleep, the phone's microphone is analyzed on the device. Sounds are recognized and sorted into snoring, breathing, speech, coughing, alarms, animal sounds, impacts, ambient sound or crying.
- Each event is logged with its time and sound level. That log is what gets kept.
- The raw microphone audio is not saved. An audio file is created only if you deliberately start a recording yourself.
- No account, no ads, no analytics, no tracking. Processing stays on your devices.

What you give up
- You can't play back a clip to check whether the 3 a.m. "snoring" was you, your partner or the dog. If hearing it matters to you, this design isn't the right fit, or you'd have to start a recording on purpose.
- Classification can be wrong. A phone on the nightstand hears the whole room, including a partner's snoring.
- Levels come from a phone mic and are estimates, not a calibrated measurement.

What it isn't
- It is not a medical device and can't tell you whether you have sleep apnea. If someone has noticed you stop breathing, gasp or choke in your sleep, or you're exhausted during the day, please bring that to a doctor rather than to an app.

Cost, so nobody is surprised: the Sleep Journal includes one free session. After that it's a one-time Lifetime Pro purchase, no subscription. The app's interface comes in 50 languages you can switch inside the app.

A question for this sub, since you know the problem better than I do: for tracking snoring, is a time-and-level log without audio enough for you, or do you really need to hear the clips? Honest answers either way help me decide what to build next.
```

## ③ 回覆版（規則不允許發主文，或有人直接問時）

```text
If your main worry is audio being stored: some trackers keep recordings so you can listen back, others only keep a log. Worth checking which one you're installing.

Disclosure: I'm the developer of one of the log-only kind, dB Halo (iPhone). Its Sleep Journal classifies snoring, breathing, speech, coughing and other sounds on the device and keeps the time and level of each event, without saving the raw microphone audio (a file is only created if you start a recording yourself). The trade-off is that you can't play anything back to check who was snoring. One Sleep Journal session is free, then it's a one-time purchase. It's an estimate, not a medical device; if anyone has seen you stop breathing or gasp at night, that's one for a doctor.
```
