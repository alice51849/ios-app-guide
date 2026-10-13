# Reddit r/HomeNetworking 回覆草稿（英文，4 種情境）（wifiaid-04）

| 項目 | 內容 |
|---|---|
| 用途 | US 痛點詞（connected but no internet 165 筆、wifi troubleshoot 171 筆、internet not working 179 筆）被 ISP／路由器 App 佔滿，付費獨立 App 無法靠搜尋曝光；唯一通路是揭露身分的 Reddit 問答，而且把人導到 **Lite**。付費版只在第 4 則（有人問 Apple Watch／widget）出現 |
| 發在哪／給誰 | r/HomeNetworking 裡真實的求助串（標題像 "connected but no internet"、"internet slow only at night"、"is it my wifi or the website"）；規則相近的 r/techsupport 也可用。讀者是英文使用者；App 段落只對用 iPhone 的提問者有用 |
| 發文者 | 店主 Guan Feng Lai 本人的 Reddit 帳號，以開發者身分回覆 |
| 發文規則 | ① 回覆前先讀該 subreddit 側欄規則；技術版普遍禁止或限制自我推廣 → **預設只貼 Version B（純排查步驟，不提 App）**。② 只有規則允許、提問者用 iPhone、而且 App 真的對題時，才在 B 後面加 Version A 的揭露段；揭露句一字不刪。③ 回覆中不放連結，對方問了才私訊或回覆連結。④ 每週最多 3 則；同一串只回一次；不開新帖宣傳；不回已解決的串。⑤ 依 Reddit 自我推廣原則，帳號大部分的貢獻要與自家產品無關。⑥ 不點名任何路由器、ISP 或其他 App |
| 事實依據 | wifiaidlite_full.json en-US：Run a Check（Wi-Fi、DNS、internet checks in one tap）、Deep Check（more evidence and stability samples）、Check a Website（one site or the wider internet）、Evidence（DNS · TCP · TLS · TTFB · HTTP · Direct IP · IPv4 · IPv6）、Variation（jitter）、Check History stored only on this device、no account／ads／analytics／tracking、one-time lifetime unlock、no subscription。免費額度採 10/13 審核的線上說法「one complete check, shared across all tools」。wifiaid_full.json en-US：Apple Watch Run a Check、Widget、iPad、one upfront purchase。50 種介面語言、App 內切換（店主確認）|
| 不能寫 | "speed test"、"makes your Wi-Fi faster"；"each tool has one free use"；"before/after comparison"（repo 文案尚未回填）；任何沒有出處的比例；"best" |
| 連結（只在對方問時給） | Lite：https://apps.apple.com/app/id6793414462?pt=118326163&ct=wal_en_reddit_hn&mt=8 ／付費版（只在第 4 則）：https://apps.apple.com/app/id6790467886?pt=118326163&ct=wa_en_reddit_watch&mt=8 |

---

## 1. "Wi-Fi says connected but no internet"

### Version B（純步驟，預設用這個）

```text
A quick way to narrow it down before rebooting everything again:

1. Every device, or just one? If only one device fails, forget the network on that device and rejoin, or restart it. If every device fails, keep going.

2. Can you reach the router itself? Open the router's admin page (the address is usually on the label). If that loads but websites don't, your local Wi-Fi is working and the problem is upstream (modem/ONT, ISP) or DNS.

3. DNS vs. connectivity. From a computer, ping a public IP address (for example 1.1.1.1), then ping a domain name (for example example.com). If the IP answers and the name doesn't, it's DNS. As a test, set a different DNS server on one device and see if pages load.

4. Are you behind a login page? Hotels, dorms and some apartment networks need a captive-portal sign-in. Open any plain http:// page to make the login screen appear.

5. Power-cycle in order: modem/ONT off, router off, wait a couple of minutes, modem on first, then the router once the modem is fully up. Don't press the reset button; it can wipe your ISP login settings and leave you with no connection at all.

6. If it keeps coming back, write down the times it happens. That log is the most useful thing you can hand your ISP.
```

### Version A（只有規則允許＋提問者用 iPhone 才加在 B 後面）

```text
Disclosure: I'm the developer of an iPhone app for exactly this, WiFi Aid Lite. On an iPhone it runs steps 2–4 in one tap: Wi-Fi, DNS and internet checks, with the DNS / TCP / TLS / timing evidence listed, and it tells you the most likely cause (a likely cause, not a guarantee). One complete check is free; unlimited checks are a one-time unlock, no subscription, ads or account. You don't need it for any of the steps above.
```

---

## 2. "Internet is slow only in the evening" / "drops randomly"

### Version B

```text
On-and-off problems are the hardest ones to get support to act on, so the goal is evidence rather than another reboot:

- Keep a log for a few days: date, time, and what failed (video call froze, pages timed out, everything dropped).
- When it happens, test once right next to the router and once where you usually sit. Only bad far away = Wi-Fi coverage or interference. Bad everywhere = upstream.
- If you can, test over Ethernet at the same moment. Still bad on a cable = it isn't your Wi-Fi.
- Check whether it's every site or one service. If it's one service, it's probably on their side.
- If your router has an internet/WAN status page, screenshot it during a drop.

"Drops between 8 and 11 pm on 4 of the last 5 days, also on Ethernet, cellular fine" is something support can actually work with. "My internet is slow" usually gets you "please restart your router".
```

### Version A

```text
Disclosure: I made WiFi Aid Lite for iPhone. Its Deep Check collects extra evidence and stability samples (jitter) for this kind of intermittent problem, and Check History keeps each result on the phone so you can compare evenings. One complete check is free, then a one-time unlock; no subscription or ads. The log above works fine without it.
```

---

## 3. "Is it my internet or just this site?"

### Version B

```text
Two quick checks:

1. Turn Wi-Fi off and open the same site on cellular data. Works on cellular = your home connection or DNS. Fails on cellular too = probably the site itself; check its official status page or social account.
2. On Wi-Fi, open a couple of other sites. If everything else loads, rebooting your router won't fix it; it's that destination or the route to it.
```

### Version A

```text
Disclosure: developer here. WiFi Aid Lite (iPhone) has a Check a Website tool that runs this comparison for you: it shows whether one destination or the wider internet is failing, with the evidence behind it. One complete check is free.
```

---

## 4. 只在有人問「能不能用 Apple Watch／小工具跑檢查」時

```text
Disclosure: I'm the developer. If you specifically want to run a check from Apple Watch or see connection status in a Home Screen widget, the paid version, WiFi Aid, adds Apple Watch, a widget and iPad. The checks themselves are largely the same as the free-to-start WiFi Aid Lite, so I'd try Lite first and only get the paid one if you actually want it on your wrist. One upfront purchase, no subscription.
```
