# -*- coding: utf-8 -*-
"""檔期意圖頁內容（geo/gen_seasonal_peaks_2026.py 用）：每頁手寫，功能句只取 data/<key>_full.json 該語系商店文案。

欄位：key（主卡）、event（halloween／singles_day／suneung／thanksgiving／black_friday／gifts，決定追蹤碼檔期碼）、
lang、slug、terms（使用者會搜的字，第一個必須出現在標題、h1 或描述）、title、desc、h1、lead、intro、
sections（(h2, 段落, 條列)）、steps_title、steps、cards（(key, 卡片文字)，第一張是主卡）、faqs、related。
"""
from __future__ import annotations

PAGE_SPECS: list[dict] = []

# ============================================================================================
# 萬聖節（10-31）：拍照濾鏡、倒數、可愛待辦；美國英文＋日本日文
# ============================================================================================
PAGE_SPECS += [
    # H1 PhotoCream：美國「halloween photo filter app」
    {
        "key": "photocream", "event": "halloween", "lang": "en",
        "slug": "halloween-photo-filter-app-film-look-costume-photos",
        "terms": ["halloween photo filter app", "halloween filter", "halloween photo editor"],
        "title": "Halloween photo filter app: give costume and pumpkin photos a film look (live preview, on-device)",
        "desc": "Searching for a Halloween photo filter app? How to make costume, pumpkin and porch-light photos look like film instead of flat phone shots, plus how to rescue the dark, blurry party ones.",
        "h1": "Halloween photo filter app: costume photos that look like film, not flash",
        "lead": "People who search for a \"halloween photo filter app\" in late October usually have the same problem: the costumes took weeks, but the photos come out flat, too clean, or so dark you can barely see the face paint.",
        "intro": [
            "Halloween is one of the hardest nights of the year to photograph on a phone. Most of the best moments happen after sunset, under orange porch lights, candles inside carved pumpkins, string lights and the blue glow of a screen. The camera fights that mix of light by smoothing everything, so a great costume can end up looking like a plastic toy. A film look works in the opposite direction: grain, a soft glow around bright lights and a little warmth make the same scene feel like a memory instead of a security camera frame.",
            "We read through what people ask about Halloween photo filters and the same three wishes keep coming up. They want to see the look before they press the shutter, so they do not have to edit fifty photos the next morning. They want faces and costume details to stay sharp while the background gets the mood. And they would rather not upload photos of their kids in costume to some unknown server just to add a filter.",
        ],
        "sections": [
            ("What to look for in a Halloween photo filter app", [], [
                "Live preview: you should see grain, halation and light leaks on the screen before you shoot, because a party moves too fast for trial and error.",
                "Looks that suit candlelight and porch lights: retro, cinema, instant and mono styles each handle orange light differently, so it helps to have plenty to choose from.",
                "Real editing controls for the photos that matter: exposure, contrast, curves and color, so a dark group photo can be pulled back without turning gray.",
                "Skin retouching that leaves eyes, hair and face paint crisp, instead of blurring the whole face.",
                "Processing on your own device, so costume photos of your family never have to leave your phone.",
            ]),
            ("Three Halloween scenes and the look that fits each", [
                "Trick-or-treat on the porch: the light is warm and low, and everyone is moving. Pick a look with gentle grain and a soft glow, frame the costume against the door or the pumpkins, and shoot a few frames in a row. Film grain hides a little noise far better than heavy smoothing does.",
                "Costume party indoors: mixed light from lamps, screens and string lights is where flat phone photos look worst. A cinema or instant look gives the room one consistent mood. If a shot still comes out blurry or too dark, rescue it afterwards instead of deleting it, because the funniest moments are rarely the sharpest ones.",
                "Pumpkin carving and decorations: these are still subjects, so take your time. Get close, let the candle be the brightest point in the frame and add a light leak or halation for that old-camera warmth. A date stamp or a simple border turns the photo into something you would actually print.",
            ], []),
        ],
        "steps_title": "Set up your Halloween look in five minutes",
        "steps": [
            "Before the evening starts, open the camera and scroll through the looks with live preview while pointing at a lamp or a candle.",
            "Pick two looks you like: one warmer for porch and candle light, one cleaner for indoor party photos.",
            "Shoot with the look on, and take a few frames of every costume, because people move and blink.",
            "Next morning, open the keepers in the editor and adjust light, color and curves; keep the face sharp and add grain, a border or a date stamp.",
            "For a photo that came out too dark or shaky, run it through a low-light or sharpen fix on your phone before you decide to delete it.",
        ],
        "cards": [
            ("photocream", "PhotoCream turns your phone into a film camera: 100+ looks across retro, cinema, instant, mono and more, with authentic grain, halation, light leaks, bloom and vignette that you see in live preview before you shoot. The editor covers exposure, contrast, curves, HSL and split toning, skin smoothing that keeps eyes, hair and detail sharp, plus text, borders, grain, dust and a date stamp. Everything is processed on your device; nothing is uploaded and there is no account. No subscription and no ads; a single one-time unlock opens every premium pack."),
            ("unblurry", "Got a dark or shaky shot from the party? Unblurry fixes it on your iPhone: Low Light brightens and recovers dark shots, Sharpen rescues soft focus and camera shake, and a before/after slider lets you compare instantly. 100% on-device, no account."),
        ],
        "faqs": [
            ("Can I see the Halloween filter before I take the photo?", "Yes. PhotoCream shows the exact look in live preview, including grain, halation and light leaks, before you press the shutter."),
            ("Are my costume photos uploaded anywhere?", "No. PhotoCream processes everything on your device, nothing is uploaded and no account is needed. Unblurry also works 100% on-device."),
            ("My party photos are dark and blurry. Can they be saved?", "Often, yes. Unblurry has a Low Light mode that brightens dark shots and a Sharpen mode for soft focus and camera shake, with a before/after slider so you can check the result."),
            ("Is it a subscription?", "No. PhotoCream has no subscription and no ads; a single one-time unlock opens every premium pack."),
        ],
        "related": [("en-US/photocream.html", "PhotoCream: full overview"), ("en-US/unblurry.html", "Unblurry: full overview"),
                    ("en/seasonal/best-iphone-privacy-apps-end-of-year-2026.html", "Privacy-friendly iPhone apps")],
    },
    # H2 CountDaysNow：美國「halloween countdown」「days until halloween」
    {
        "key": "countdaysnow", "event": "halloween", "lang": "en",
        "slug": "halloween-countdown-widget-iphone-days-until-halloween",
        "terms": ["halloween countdown", "days until halloween", "halloween countdown widget"],
        "title": "Halloween countdown widget for iPhone: days until Halloween, and what to do on each one",
        "desc": "A Halloween countdown that does more than count: see how many days are left on your Home Screen and plan backwards, so the costume, candy and party prep land on time.",
        "h1": "Halloween countdown: see the days left and plan backwards from October 31",
        "lead": "Search for \"halloween countdown\" or \"days until halloween\" and you will find two kinds of people: kids asking every morning how many sleeps are left, and the adults who just realized the costume still has to be ordered.",
        "intro": [
            "A number on its own is fun, but it does not get the costume finished. The reason most Halloween prep goes wrong is timing: the costume that ships in ten days is ordered with five days left, the candy is bought on the 30th when the shelves are empty, and the party invitation goes out too late for anyone to plan around it. A good countdown helps with both halves, the excitement and the planning.",
            "The simplest way to fix timing is to plan backwards. Instead of a long to-do list with no dates, you attach each job to a number of days before the big night. Order the costume a couple of weeks out, buy decorations ten days out, candy a week out, and carve the pumpkins two or three days out so they still look good on the 31st. When the date is fixed, every step falls into place.",
        ],
        "sections": [
            ("What a good Halloween countdown should do", [], [
                "Show the exact number of days left, at a glance, on your Home Screen, without opening the app.",
                "Let you attach preparation steps to the date, each due a set number of days before it.",
                "Show what is late, what is due today and what is coming in the next seven days.",
                "Remind you before the day, not only on it.",
                "Keep counting after the night is over, so next year's date is ready without setting it up again.",
            ]),
            ("A simple backwards plan for October 31", [
                "Two weeks out: decide on costumes and order anything that ships. If you are hosting, pick the date and send the invitation now, because people fill up their Halloween weekend early.",
                "Ten days out: decorations, makeup and any props. One week out: candy and party food that keeps. Three days out: carve the pumpkins, since carved pumpkins only last a few days. The day before: charge the phone, lay out costumes and check the weather for trick-or-treat.",
                "After Halloween, turn the event into a repeating one. Next year it will be counting down again on its own, and your plan is already there.",
            ], []),
        ],
        "steps_title": "Set up your Halloween countdown",
        "steps": [
            "Add Halloween as an event on October 31 and choose an icon and color.",
            "Open Countdown Plan and add steps: costume, decorations, candy and pumpkins, each due a set number of days before the event.",
            "Put the event on a Home Screen widget so the days left are always visible.",
            "Check the plan view each morning to see what is late, due today or due in the next seven days.",
            "Make it a repeating event so next year's countdown starts by itself.",
        ],
        "cards": [
            ("countdaysnow", "CountDaysNow keeps future, current and past events in three clear views with precise day counts. Countdown Plan gives any event its own preparation steps, each due a set number of days before it, and shows what is late, due today, due in the next 7 days and done; change the date and every step moves with it. Put events on Home Screen widgets in every size, keep a live countdown in the Dynamic Island and on the Lock Screen, and get a nudge 7, 3 and 1 day before and on the day. No ads, no subscription, no account."),
            ("mochi", "Want the prep list itself to feel fun? Mochi is a cute, cozy checklist: add tasks, tap the little circle when you finish, pick from 101 themes and keep important tasks on your Home Screen with widgets."),
        ],
        "faqs": [
            ("Can I see the Halloween countdown on my Home Screen?", "Yes. CountDaysNow puts any event on Home Screen widgets in every size, and can also keep a live countdown on the Lock Screen and in the Dynamic Island."),
            ("Can it remind me before Halloween?", "Yes. Milestone alerts arrive 7, 3 and 1 day before and on the day itself."),
            ("What is Countdown Plan?", "Preparation steps attached to an event, each due a set number of days before it. If the date changes, every step moves with it, and you can see what is late, due today and due this week."),
            ("Do I need an account?", "No. CountDaysNow has no ads, no subscription and no account."),
        ],
        "related": [("en-US/countdaysnow.html", "CountDaysNow: full overview"), ("en-US/mochi.html", "Mochi: cute checklist"),
                    ("answers/exam-countdown-widget-app-for-iphone.html", "Exam countdown widget for iPhone")],
    },
    # H3 Mochi：美加「cute to do list」＋「halloween checklist」
    {
        "key": "mochi", "event": "halloween", "lang": "en",
        "slug": "cute-halloween-to-do-list-app-costume-party-checklist",
        "terms": ["cute to do list", "halloween checklist", "halloween party checklist"],
        "title": "Cute to do list for Halloween week: a costume and party checklist you will actually finish",
        "desc": "Looking for a cute to do list for Halloween? Split costume, candy, party and homework into small lists, check them off with a tap and keep the important ones on your Home Screen.",
        "h1": "A cute to do list for Halloween week: small lists, one tap, done",
        "lead": "Halloween week piles up fast: a costume to finish, candy to buy, a party to plan, and school or work that does not stop for any of it. People searching for a \"cute to do list\" right now want something that makes that pile feel lighter, not heavier.",
        "intro": [
            "The trouble with one giant list is that it never looks finished. Thirty unchecked lines on a plain white screen is exactly the kind of thing you stop opening by Wednesday. A short list that you can clear in a day feels completely different, especially when checking something off is satisfying to look at.",
            "That is why so many people who search for a cute to-do list are not looking for more features. They want a list that is pleasant to open, quick to update and visible without hunting for it. For a busy holiday week, those three things matter more than any planning system.",
        ],
        "sections": [
            ("Break Halloween week into four small lists", [], [
                "Costume: fabric or parts to buy, makeup, a test run, and photos of the finished look.",
                "Treats: candy for the door, a bowl or basket, and allergy-friendly options if you know kids in the neighborhood need them.",
                "Party or trick-or-treat: invitations, route and timing, a flashlight or reflective bands, and a meeting point.",
                "Everything else: homework, a work deadline, groceries and laundry, so the fun stuff does not push the normal week off the rails.",
            ]),
            ("Why a cute list keeps you going", [
                "Small wins are motivating. When each list has only a handful of things and each one gets a satisfying check, you can see progress every day instead of one huge list that never seems to shrink.",
                "Visibility matters too. Keep the list that matters most this week on your Home Screen with a widget, so you see the next costume step every time you unlock your phone, not only when you remember to open an app. A theme that matches the season makes it even easier to keep coming back.",
                "After October 31, clear the Halloween lists and start fresh for November, with the same habit.",
            ], []),
        ],
        "steps_title": "Make your Halloween checklist tonight",
        "steps": [
            "Create a list called Halloween and add the next few costume and party tasks.",
            "Keep each list short, with only the tasks you can actually finish this week.",
            "Pick a cozy theme, then add a widget so the list sits on your Home Screen.",
            "Set reminders for the tasks with a real deadline, like ordering the costume or picking up candy.",
            "Tap the little circle as each one gets done, and check your list from Apple Watch while you shop.",
        ],
        "cards": [
            ("mochi", "Mochi is the cute, cozy to-do list that makes getting organized feel good. Add tasks, tap the little circle when you finish, and plan school, work, errands, groceries, habits, routines and daily goals in one adorable place. Customize your checklist with 101 crafted themes, keep important tasks on your Home Screen with widgets, set reminders and check your list from Apple Watch."),
            ("countdaysnow", "Want to see how many days are left as well? CountDaysNow puts October 31 on a Home Screen widget with precise day counts, and Countdown Plan attaches each prep step to a number of days before the date."),
        ],
        "faqs": [
            ("Is Mochi a good cute to do list for kids and students?", "Mochi is designed to be cute and cozy: you add tasks, tap the little circle when you finish, and choose from 101 themes. It covers school, chores, errands, groceries, habits and routines."),
            ("Can I see my list without opening the app?", "Yes. Mochi has Home Screen widgets, so important tasks stay visible, and you can check your list from Apple Watch."),
            ("Can Mochi remind me about Halloween tasks?", "Yes. Mochi includes reminders that keep you on track, so tasks with a deadline, like ordering a costume, do not slip."),
        ],
        "related": [("en-US/mochi.html", "Mochi: full overview"), ("en-US/countdaysnow.html", "CountDaysNow: countdown widget"),
                    ("answers/cute-to-do-list-for-exam-season-that-you-keep-using.html", "A cute to-do list for exam season")],
    },
    # H4 PhotoCream：日本「ハロウィン 写真 加工」
    {
        "key": "photocream", "event": "halloween", "lang": "ja",
        "slug": "halloween-shashin-kakou-app-film-fuu",
        "terms": ["ハロウィン 写真 加工", "ハロウィン 加工 アプリ", "フィルム風 加工"],
        "title": "ハロウィン写真加工アプリの選び方｜仮装もかぼちゃもフィルム風に（ライブプレビュー・端末内処理）",
        "desc": "「ハロウィン 写真 加工」で探している人へ。仮装や夜の街、ジャック・オ・ランタンの写真をフィルム風に仕上げるコツと、暗い・ブレた写真を救う方法。PhotoCreamの使い方つき。",
        "h1": "ハロウィン写真加工：仮装も夜の街も、フィルム風に残すコツ",
        "lead": "10月の終わりにApp Storeで「ハロウィン 写真 加工」と検索する人の多くは、せっかくの仮装がスマホで撮るとのっぺりして見える、夜の写真が暗くてブレる、という悩みを抱えています。",
        "intro": [
            "ハロウィンはスマホ写真にとって難しい夜です。仮装パーティーの室内照明、街のイルミネーション、かぼちゃの中のろうそくなど、暗くて色の混ざった光の中で撮ることが多いからです。スマホのカメラは暗い場面を明るく見せようとして肌も背景も均一になめらかにしてしまい、手間をかけた仮装の質感が消えてしまいがちです。",
            "そこで人気なのが、フィルムカメラ風の加工です。粒子、ハレーション（光のにじみ）、光漏れを少し足すだけで、同じ写真が「記録」ではなく「思い出」に見えるようになります。ただし撮ったあとに何十枚も加工するのは大変なので、シャッターを押す前に仕上がりを確認できるかどうかが大切です。",
        ],
        "sections": [
            ("ハロウィン写真加工アプリで確認したい5つのポイント", [], [
                "シャッター前のライブプレビュー：粒子・ハレーション・光漏れを撮る前に画面で確認できるか。",
                "フィルム調ルックの数：レトロ、シネマ、インスタント、モノクロなど、暖色の照明に合う雰囲気を選べるか。",
                "本格的な補正：光・色・カーブを細かく調整して、暗い集合写真も自然に持ち上げられるか。",
                "美肌補正：目や髪、メイクのディテールを残したまま、肌だけを整えられるか。",
                "端末内処理：仮装した家族や友だちの写真を、知らないサーバーにアップロードしなくて済むか。",
            ]),
            ("シーン別：ハロウィン写真をフィルム風に撮るコツ", [
                "仮装パーティー（室内）：照明の色が混ざりやすいので、シネマ調やインスタント調で部屋全体の雰囲気をひとつにまとめると、写真に統一感が出ます。動きが多いので、一人につき数枚ずつ撮っておくのがおすすめです。",
                "夜の街やイルミネーション：明るい光のまわりにハレーションが出るルックを選ぶと、看板や街灯がやわらかくにじみ、フィルムで撮ったような空気感になります。ブレたり暗すぎたりした写真も、消す前に補正を試してみましょう。",
                "ジャック・オ・ランタンや飾りつけ：動かない被写体なので、ろうそくの光をいちばん明るい点にして近づいて撮ります。日付スタンプやフレームを付ければ、プリントしたくなる一枚になります。",
            ], []),
        ],
        "steps_title": "ハロウィン当日までの準備",
        "steps": [
            "前の晩に、部屋の照明やろうそくにカメラを向けて、ライブプレビューでルックを見比べる。",
            "暖色の光に合うルックと、室内パーティー向けのルックを1つずつ決めておく。",
            "当日はルックをかけたまま撮り、仮装ごとに数枚ずつ押さえる。",
            "翌日、残したい写真だけ光・色・カーブを調整し、粒子やフレーム、日付スタンプを足す。",
            "暗い・ブレた写真は、ローライトやシャープで補正してから残すか決める。",
        ],
        "cards": [
            ("photocream", "PhotoCreamは、スマホをフィルムカメラに変えるアプリです。シャッターを切る前から粒子・ハレーション・光漏れをライブプレビューで確認でき、100種類以上のフィルム調ルック、好きな写真の色をコピーする機能、美肌補正、光・色・カーブまで調整できる本格エディタを搭載。テキスト、フレーム、粒子効果も追加できます。すべて端末内で完結し、写真がアップロードされることはありません。サブスクも広告もありません。"),
            ("unblurry", "暗い・ブレたハロウィン写真には Unblurry。ローライトで暗い写真を明るくして細部を復元、シャープで甘いピントや手ブレを補正し、ビフォー／アフタースライダーですぐ比較できます。処理はすべて iPhone 上で完結します。"),
        ],
        "faqs": [
            ("撮る前に加工の仕上がりを確認できますか？", "はい。PhotoCreamはシャッターを切る前から、粒子・ハレーション・光漏れをライブプレビューで確認できます。"),
            ("仮装の写真がどこかにアップロードされませんか？", "されません。PhotoCreamの編集はすべて端末内で行われ、アップロードは不要です。Unblurryも処理は100%オンデバイスです。"),
            ("暗くてブレた夜の写真は直せますか？", "Unblurryのローライトモードで暗い写真を明るくし、シャープモードで手ブレや甘いピントを補正できます。ビフォー／アフターで確認しながら選べます。"),
            ("サブスクリプションですか？", "いいえ。PhotoCreamは一度の購入で、サブスクリプションも広告もありません。"),
        ],
        "related": [("ja/photocream.html", "PhotoCream の詳しい紹介"), ("ja/unblurry.html", "Unblurry の詳しい紹介")],
    },
]

# ============================================================================================
# 雙 11（11-11）：記帳、購物清單、比價；台灣繁中、中國簡中、泰國泰文、印尼印尼文
# ============================================================================================
PAGE_SPECS += [
    # S1 HoursTag：台灣「雙11 購物清單」「雙11 記帳」
    {
        "key": "hourstag", "event": "singles_day", "lang": "zh-Hant",
        "slug": "shuang11-gouwu-qingdan-jizhang-app-zhhant",
        "terms": ["雙11 購物清單", "雙11 記帳", "購物清單 app"],
        "title": "雙11 購物清單怎麼列？先把價格換成工時，再決定要不要買（附記帳與截圖整理 App）",
        "desc": "雙11 購物清單與記帳一次搞定：購物車越加越滿、湊免運、限時倒數，結帳前先把價格換算成工時，標記必要、想要、衝動；訂單和收據截圖自動分類。附 HoursTag 用法與台灣 App Store 直連。",
        "h1": "雙11 購物清單：結帳前先看「這要我工作幾小時」",
        "lead": "雙11 前在 App Store 搜「雙11 購物清單」「雙11 記帳」的人，多半是購物車已經加了一堆，心裡知道有些買了會後悔，卻說不出哪幾樣。",
        "intro": [
            "雙11 的設計本來就是讓人多買：限時倒數、湊免運、滿額折抵、搶購名額，每一個都在催你「現在就下單」。問題不是不能買，而是在這種氣氛下，很難分清楚哪些是真的需要、哪些只是被氣氛推著走。等到月底帳單出來，才發現買了一堆用不到的東西。",
            "比較有效的方法，是在結帳前換一個角度看價格。一件衣服標價一千多元，看起來不算什麼；但如果換算成「我要工作幾小時才賺得到」，很多東西就會自動從購物車裡掉出來。這不是要你什麼都不買，而是把錢留給真的值得的那幾樣。",
        ],
        "sections": [
            ("雙11 前三天：把購物清單分成三類", [], [
                "必要：本來就要買、而且會用完的東西，例如日用品、補貨的保養品、壞掉要換的家電。這一類趁雙11 買最划算。",
                "想要：喜歡、但沒有也過得下去的東西。先放進清單，看它換算成幾小時工作後，再決定留不留。",
                "衝動：因為倒數計時、限量、別人在買才想買的東西。這一類最容易後悔，建議先放一晚，隔天還想要再說。",
                "清單之外的東西一律不加：看到「再買一件就免運」，先算算那一件值不值得你額外工作的時間。",
            ]),
            ("下單之後：記帳與訂單截圖別再散落各處", [
                "雙11 之後最常見的混亂，是不記得自己到底買了什麼、花了多少。每一筆下單後，把金額記下來，並保留它是必要、想要還是衝動的標記，月底回頭看，就能知道自己的錢主要花在哪一類，下一次購物節也比較好拿捏。",
                "訂單成立畫面、付款收據、物流通知，很多人習慣截圖存起來，結果相簿裡一堆截圖找不到。把截圖自動分成購物、收據等類別，圖裡的文字也搜得到，要查某一筆訂單時打幾個字就找到，還能直接追蹤包裹或加提醒。",
            ], []),
        ],
        "steps_title": "雙11 前 10 分鐘設定好",
        "steps": [
            "在 HoursTag 設定一次收入（時薪或月薪），算出你每小時的真實價值。",
            "把購物車裡的東西一樣一樣輸入價格，看它等於幾小時工作。",
            "標記成必要、想要或衝動；衝動的先放一晚再決定。",
            "11 月 11 日只買清單上留下來的東西，下單後保留每一筆花費與標記。",
            "訂單、收據截圖交給 ShotInbox 自動分類，之後用文字搜尋或直接追蹤包裹。",
        ],
        "cards": [
            ("hourstag", "HoursTag 把任何價格換算成你需要工作的時數：設定一次收入（時薪或月薪），輸入價格就立刻看到等於多少工時。花費可標記為必要、想要、衝動，依類別查看花費洞察與月度明細，也能看每一筆消費佔你工作日的百分比；目標與願望清單用真實工時追蹤進度。無需帳號、不追蹤、沒有廣告，資料只留在你的裝置上；沒有訂閱，也沒有 App 內購買。"),
            ("hourstaglite", "想先用簡單版試試？HoursTag Lite 一樣把價格換算成工作時間，分成必要、想要、衝動，也能看到一個目標背後要工作多久；支援小工具與 Apple Watch，資料只留在裝置上、無需帳號。"),
            ("shotinbox", "訂單、收據、物流截圖越存越多？ShotInbox 自動分成購物、收據、旅遊、票券等類別，圖裡的文字、分類與連結都搜得到；可以追蹤包裹、加入提醒事項或行事曆。辨識只在裝置上進行，絕不上傳，也絕不自動刪除。"),
        ],
        "faqs": [
            ("把價格換算成工時是怎麼算的？", "在 HoursTag 設定一次收入（時薪或月薪），它會算出你每小時的真實價值；之後輸入任何價格，就會直接顯示等於多少工時。"),
            ("需要註冊帳號嗎？資料存在哪？", "不需要。HoursTag 無需帳號、不做追蹤、沒有廣告，所有資料都只留在你的裝置上，也可以隨時備份與還原。"),
            ("雙11 的訂單截圖可以自動整理嗎？", "可以。ShotInbox 會把截圖自動分成購物、收據等類別，圖中文字也能搜尋，還能直接追蹤包裹或加入提醒。辨識只在裝置上進行。"),
            ("HoursTag 是訂閱制嗎？", "不是。HoursTag 沒有訂閱，也沒有 App 內購買。"),
        ],
        "related": [("zh-Hant/hourstag.html", "HoursTag 完整介紹"), ("zh-Hant/hourstaglite.html", "HoursTag Lite：買前先算工時"),
                    ("zh-Hant/shotinbox.html", "ShotInbox 截圖整理")],
    },
    # S2 HoursTag Lite：中國「双十一 记账」「双11 购物清单」
    {
        "key": "hourstaglite", "event": "singles_day", "lang": "zh-Hans",
        "slug": "shuang11-jizhang-app-gouwu-qingdan-zhhans",
        "terms": ["双十一 记账", "双11 购物清单", "理性消费"],
        "title": "双十一记账与购物清单：下单前先算这件东西要你工作几小时（理性消费不剁手）",
        "desc": "双十一记账、列购物清单，最怕凑满减越买越多。下单前把价格换算成工时，标记必要、想要、冲动；订单和快递截图自动分类可搜索。附 HoursTag Lite 用法与 App Store 直达链接。",
        "h1": "双十一记账：下单前先看「这件东西等于我几小时的工作」",
        "lead": "双十一前搜「双十一 记账」「双11 购物清单」的人，大多已经把购物车塞满了，一边担心凑满减越凑越多，一边又怕错过。",
        "intro": [
            "双十一的玩法越来越复杂：预售、定金、尾款、跨店满减、限时秒杀，每一步都在推你多买一点。很多人不是不想省钱，而是在这么多规则里，很难冷静判断一件东西到底值不值得买。等到尾款付完、快递一个个到了，才发现有好几件其实用不上。",
            "一个简单又有效的办法，是把价格换成时间。标价几百块的东西，看起来不贵；可是一想到要上好几个小时的班才赚得回来，很多“想要”就会自己冷静下来。真正需要的，照样趁双十一买；只是因为凑单、因为别人都在买的那几件，就先放一放。",
        ],
        "sections": [
            ("把购物清单分成三类", [], [
                "必要：本来就要买、会用完的东西，比如日用品、需要补货的护肤品、坏了要换的家电，这类趁双十一囤货最划算。",
                "想要：喜欢但不急的东西。先放进清单，看它等于几小时的工作，再决定留不留。",
                "冲动：因为倒计时、限量、凑满减才想买的东西，最容易后悔，建议先放一晚，第二天还想要再说。",
                "凑单前先算一算：为了凑满减多加的那一件，值不值得你多工作的那几个小时。",
            ]),
            ("付完尾款之后：账和截图都要理清楚", [
                "每一笔下单之后记下金额，并保留它是必要、想要还是冲动的标记。月底回头看，就知道钱主要花在哪一类，下一个购物节也更好把握预算。",
                "订单页、付款记录、快递通知，很多人习惯截图保存，结果相册里截图越堆越多。把截图自动分成购物、收据等类别，图里的文字也能搜索，想查某一单时输入几个字就能找到，还可以直接追踪包裹、加提醒。",
            ], []),
        ],
        "steps_title": "双十一前 10 分钟设置好",
        "steps": [
            "在 HoursTag Lite 设置一次收入，算出你每工作一小时的实际收入价值。",
            "把购物车里的东西逐一输入价格，看它等于几小时的工作。",
            "标记为必要、想要或冲动，冲动的先放一晚再决定。",
            "双十一当天只买清单上留下的东西，下单后保留每一笔花费与标记。",
            "订单、收据截图交给 ShotInbox 自动分类，之后用文字搜索或直接追踪包裹。",
        ],
        "cards": [
            ("hourstaglite", "HoursTag Lite 把价格换算成工作时间，让你花得明白：看到每工作一小时的实际收入价值，把花费分为必要、想要、冲动，看见一个目标背后要工作多久并追踪进度；支持备份与恢复、小组件和 Apple Watch。所有数据只留在你的设备上，无需账号，不做追踪；一次付费，永久使用，绝无订阅。"),
            ("hourstag", "需要更完整的分析？HoursTag 同样把任何价格换算成工时，还能按类别查看花费洞察与月度明细，用真实工时追踪目标与愿望清单。无需账号、没有广告，数据只留在你的设备上。"),
            ("shotinbox", "订单和快递截图太多？ShotInbox 自动把截图分成购物、收据、旅行、票券等类别，图中文字、分类和链接都能搜索，还能追踪包裹、添加提醒事项或添加到日历。识别只在设备上进行，不会上传，也绝不自动删除。"),
        ],
        "faqs": [
            ("价格换算成工时是怎么算的？", "在 HoursTag Lite 设置一次收入，它会算出你每工作一小时的实际收入价值；之后输入任何价格，就能看到它等于多少小时的工作。"),
            ("需要注册账号吗？数据存在哪里？", "不需要。HoursTag Lite 无需账号、不做追踪，所有数据只留在你的设备上，并支持备份与恢复。"),
            ("双十一的订单截图能自动整理吗？", "可以。ShotInbox 会自动把截图分成购物、收据等类别，图中文字可以搜索，还能直接追踪包裹。识别只在设备上进行。"),
            ("是订阅制吗？", "不是。HoursTag Lite 一次付费、永久使用，绝无订阅。"),
        ],
        "related": [("zh-Hans/hourstaglite.html", "HoursTag Lite 完整介绍"), ("zh-Hans/hourstag.html", "HoursTag 完整介绍"),
                    ("zh-Hans/shotinbox.html", "ShotInbox 截图整理")],
    },
    # S3 HoursTag：泰國「11.11」購物季
    {
        "key": "hourstag", "event": "singles_day", "lang": "th",
        "slug": "11-11-shopping-list-app-chua-mong-tham-ngan-th",
        "terms": ["11.11", "แอปจดรายจ่าย", "ช้อปปิ้ง 11.11"],
        "title": "ช้อป 11.11 อย่างไม่เสียใจทีหลัง: ดูราคาเป็นชั่วโมงทำงานก่อนกดสั่งซื้อ",
        "desc": "เตรียมช้อป 11.11? ก่อนกดจ่าย ลองเปลี่ยนราคาเป็นชั่วโมงทำงาน แล้วแท็กว่าจำเป็น อยากได้ หรือชั่ววูบ พร้อมวิธีจดรายจ่ายหลังเทศกาลและลิงก์ดาวน์โหลด HoursTag จาก App Store",
        "h1": "ช้อป 11.11: ดูก่อนว่าของชิ้นนี้ต้องแลกกับงานกี่ชั่วโมง",
        "lead": "ช่วงก่อน 11.11 คนที่ค้นหาแอปจดรายจ่ายหรือวิธีช้อปให้คุ้ม ส่วนใหญ่มีของเต็มตะกร้าแล้ว และรู้สึกว่าบางชิ้นซื้อไปอาจไม่ได้ใช้",
        "intro": [
            "เทศกาล 11.11 ถูกออกแบบมาให้เราซื้อมากขึ้น ทั้งการนับถอยหลัง โปรค่าส่งเมื่อซื้อครบยอด โค้ดที่มีจำกัด และสินค้าที่ขึ้นว่าเหลือน้อย ทุกอย่างพยายามให้เรากดสั่งซื้อทันที ปัญหาไม่ใช่การซื้อของ แต่เป็นการแยกให้ออกว่าชิ้นไหนจำเป็นจริง และชิ้นไหนซื้อเพราะบรรยากาศพาไป",
            "วิธีที่ได้ผลคือมองราคาในอีกมุมหนึ่ง ของที่ดูไม่แพงในหน้าจอ ถ้าเปลี่ยนเป็นจำนวนชั่วโมงที่เราต้องทำงานเพื่อหาเงินจำนวนนั้น หลายชิ้นจะหลุดออกจากตะกร้าไปเอง ส่วนของที่จำเป็นจริงก็ยังซื้อในช่วงลดราคาได้ตามปกติ",
        ],
        "sections": [
            ("แบ่งรายการช้อป 11.11 เป็นสามกลุ่ม", [], [
                "จำเป็น: ของที่ต้องซื้ออยู่แล้วและใช้หมดแน่นอน เช่น ของใช้ในบ้าน สกินแคร์ที่ต้องเติม หรือของที่เสียต้องเปลี่ยน",
                "อยากได้: ของที่ชอบแต่ยังไม่มีก็อยู่ได้ ใส่ไว้ในรายการก่อน แล้วดูว่าเท่ากับงานกี่ชั่วโมงค่อยตัดสินใจ",
                "ชั่ววูบ: ของที่อยากได้เพราะนับถอยหลัง เพราะเหลือน้อย หรือเพราะเห็นคนอื่นซื้อ กลุ่มนี้มักทำให้เสียใจทีหลัง ลองรอหนึ่งคืนก่อน",
                "ก่อนเพิ่มของเพื่อให้ครบยอด ลองคิดดูว่าชิ้นที่เพิ่มเข้ามาคุ้มกับเวลาทำงานที่ต้องเสียไปหรือไม่",
            ]),
            ("หลัง 11.11: จดรายจ่ายและดูภาพรวม", [
                "ทุกครั้งที่สั่งซื้อ ให้จดราคาและแท็กไว้ว่าจำเป็น อยากได้ หรือชั่ววูบ พอถึงสิ้นเดือนจะเห็นชัดว่าเงินส่วนใหญ่ไปอยู่ที่หมวดไหน และเทศกาลถัดไปอย่าง 12.12 จะวางแผนได้ง่ายขึ้น",
                "ถ้ามีเป้าหมายการออม เช่น ทริปปลายปีหรือของชิ้นใหญ่ที่อยากได้ ให้ตั้งเป็นเป้าหมายแล้วดูว่าต้องทำงานอีกกี่ชั่วโมง วิธีนี้ช่วยให้เห็นว่าของชิ้นเล็กหลายชิ้นในวันลดราคากำลังกินเวลาของเป้าหมายใหญ่ไปเท่าไร",
            ], []),
        ],
        "steps_title": "ตั้งค่าก่อน 11.11 ภายใน 10 นาที",
        "steps": [
            "ตั้งค่ารายได้ใน HoursTag เพียงครั้งเดียว",
            "ใส่ราคาของแต่ละชิ้นในตะกร้า แล้วดูว่าเท่ากับงานกี่ชั่วโมง",
            "แท็กว่าจำเป็น อยากได้ หรือชั่ววูบ ของที่ชั่ววูบให้รอหนึ่งคืน",
            "วันที่ 11 ซื้อเฉพาะของที่ยังอยู่ในรายการ และเก็บแท็กของทุกการซื้อไว้",
            "ดูสรุปตามหมวดหมู่และรายเดือนหลังเทศกาล เพื่อวางแผนเทศกาลถัดไป",
        ],
        "cards": [
            ("hourstag", "HoursTag เปลี่ยนราคาทุกอย่างเป็นเวลาทำงานที่ต้องใช้เพื่อหาเงินจำนวนนั้น ตั้งค่ารายได้ครั้งเดียว ใส่ราคา แล้วดูชั่วโมงจริงก่อนซื้อ แท็กรายจ่ายเป็นจำเป็น อยากได้ หรือชั่ววูบ ติดตามเป้าหมายและรายการของที่อยากได้ด้วยชั่วโมงทำงานจริง และดูสรุปตามหมวดหมู่และรายเดือนได้ชัดเจน ไม่มีบัญชี ไม่มีโฆษณา ไม่มีการติดตาม ไม่มีการสมัครสมาชิกและไม่มีการซื้อในแอป"),
            ("hourstaglite", "อยากได้แบบเรียบง่ายกว่า? HoursTag Lite เปลี่ยนราคาเป็นเวลาทำงานเช่นกัน แยกประเภทเป็นจำเป็น ต้องการ หรือกระตุ้น ดูงานที่อยู่เบื้องหลังเป้าหมายและติดตามความก้าวหน้า มีวิดเจ็ตและ Apple Watch ทุกอย่างอยู่ในอุปกรณ์ของคุณ ไม่มีบัญชี"),
        ],
        "faqs": [
            ("HoursTag คำนวณชั่วโมงทำงานอย่างไร?", "ตั้งค่ารายได้ครั้งเดียว แล้วใส่ราคาของที่อยากซื้อ แอปจะแสดงว่าราคานั้นเท่ากับเวลาทำงานกี่ชั่วโมง"),
            ("ต้องสมัครบัญชีไหม?", "ไม่ต้อง HoursTag ไม่มีบัญชี ไม่มีโฆษณา และไม่มีการติดตาม"),
            ("ใช้ดูภาพรวมการใช้จ่ายหลังเทศกาลได้ไหม?", "ได้ HoursTag แสดงสรุปตามหมวดหมู่และรายเดือน และติดตามเป้าหมายด้วยชั่วโมงทำงานจริง"),
            ("เป็นแบบสมัครสมาชิกหรือเปล่า?", "ไม่ใช่ HoursTag ไม่มีการสมัครสมาชิกและไม่มีการซื้อในแอป"),
        ],
        "related": [("th/hourstag.html", "HoursTag รายละเอียดแอป"), ("th/hourstaglite.html", "HoursTag Lite รายละเอียดแอป")],
    },
    # S4 HoursTag Lite：印尼「belanja 11.11」
    {
        "key": "hourstaglite", "event": "singles_day", "lang": "id",
        "slug": "belanja-11-11-aplikasi-catat-pengeluaran-jam-kerja-id",
        "terms": ["belanja 11.11", "aplikasi catat pengeluaran", "harbolnas"],
        "title": "Belanja 11.11 tanpa menyesal: lihat harga dalam jam kerja sebelum checkout",
        "desc": "Siap belanja 11.11? Sebelum checkout, ubah harga menjadi jam kerja, tandai Perlu, Ingin atau Impulsif, lalu catat pengeluaran setelah promo selesai. Lengkap dengan cara pakai HoursTag Lite dan tautan App Store.",
        "h1": "Belanja 11.11: berapa jam kerja yang kamu tukar untuk barang ini?",
        "lead": "Menjelang 11.11, orang yang mencari aplikasi catat pengeluaran biasanya sudah punya keranjang yang penuh, dan diam-diam tahu beberapa barang di dalamnya akan disesali.",
        "intro": [
            "Promo 11.11 memang dirancang supaya kita belanja lebih banyak. Ada hitung mundur, potongan ongkir kalau belanja sampai batas tertentu, voucher terbatas, dan label stok hampir habis. Semuanya mendorong kita untuk checkout sekarang juga. Masalahnya bukan belanja itu sendiri, tetapi sulitnya membedakan barang yang benar-benar perlu dari barang yang dibeli karena suasana.",
            "Cara yang sederhana tapi ampuh adalah melihat harga dari sudut lain. Barang yang di layar terlihat murah akan terasa berbeda ketika kamu tahu harus bekerja berapa jam untuk mendapatkan uangnya. Banyak barang akan keluar dari keranjang dengan sendirinya, sementara kebutuhan yang memang penting tetap bisa kamu beli saat harganya sedang bagus.",
        ],
        "sections": [
            ("Bagi daftar belanja 11.11 menjadi tiga", [], [
                "Perlu: barang yang memang harus dibeli dan pasti habis dipakai, seperti kebutuhan rumah, skincare yang mau habis, atau barang rusak yang harus diganti.",
                "Ingin: barang yang kamu suka tapi tidak mendesak. Masukkan dulu ke daftar, lihat berapa jam kerjanya, baru putuskan.",
                "Impulsif: barang yang ingin dibeli karena hitung mundur, stok terbatas, atau karena orang lain membelinya. Ini yang paling sering disesali, jadi tunggu satu malam dulu.",
                "Sebelum menambah barang supaya lolos minimum belanja, tanyakan apakah barang tambahan itu sepadan dengan jam kerja yang dibutuhkan.",
            ]),
            ("Setelah 11.11: catat pengeluaran dan lihat polanya", [
                "Setiap kali checkout, catat harganya dan tandai Perlu, Ingin, atau Impulsif. Di akhir bulan kamu bisa melihat ke mana sebagian besar uangmu pergi, sehingga promo berikutnya seperti 12.12 dan Harbolnas lebih mudah direncanakan.",
                "Kalau kamu sedang menabung untuk sesuatu yang lebih besar, misalnya liburan akhir tahun, jadikan itu tujuan dan lihat berapa jam kerja yang dibutuhkan. Dari situ terlihat jelas berapa banyak barang kecil saat promo yang sebenarnya menggerus tujuan besarmu.",
            ], []),
        ],
        "steps_title": "Siapkan dalam 10 menit sebelum 11.11",
        "steps": [
            "Atur penghasilanmu sekali di HoursTag Lite untuk melihat nilai bersihmu per jam kerja.",
            "Masukkan harga setiap barang di keranjang dan lihat berapa jam kerjanya.",
            "Tandai Perlu, Ingin, atau Impulsif; barang impulsif ditunda satu malam.",
            "Pada tanggal 11, beli hanya barang yang masih ada di daftar.",
            "Pasang tujuan tabungan dan pantau kemajuannya setelah promo selesai.",
        ],
        "cards": [
            ("hourstaglite", "HoursTag Lite mengubah harga menjadi waktu kerja sehingga kamu berbelanja dengan jelas: lihat nilai bersihmu per jam kerja, tandai belanja sebagai Perlu, Ingin, atau Impulsif, dan lihat kerja di balik sebuah tujuan sambil melacak kemajuannya. Ada cadangan dan pemulihan, widget, dan Apple Watch. Semua tetap di perangkatmu, tanpa akun dan tanpa pelacakan; sekali bayar, akses seumur hidup, tanpa langganan."),
            ("hourstag", "Ingin wawasan yang lebih lengkap? HoursTag juga mengubah harga apa pun menjadi jam kerja, menandai belanja sebagai Perlu, Ingin, atau Impuls, memantau tujuan dan wishlist dalam jam kerja nyata, serta menampilkan wawasan kategori dan ringkasan bulanan. Tanpa akun, iklan, atau pelacakan."),
        ],
        "faqs": [
            ("Bagaimana harga diubah menjadi jam kerja?", "Atur penghasilanmu sekali, lalu masukkan harga barang. Aplikasi menampilkan berapa jam kerja yang setara dengan harga itu."),
            ("Apakah perlu membuat akun?", "Tidak. HoursTag Lite tidak memerlukan akun dan tidak melakukan pelacakan; semua data tetap di perangkatmu."),
            ("Apakah bisa dipakai untuk menabung?", "Bisa. Kamu dapat melihat berapa jam kerja di balik sebuah tujuan dan melacak kemajuannya."),
            ("Apakah ini langganan?", "Bukan. HoursTag Lite sekali bayar dengan akses seumur hidup, tanpa langganan."),
        ],
        "related": [("id/hourstaglite.html", "HoursTag Lite: ulasan lengkap"), ("id/hourstag.html", "HoursTag: ulasan lengkap")],
    },
]

# ============================================================================================
# 韓國修能（2027학년도 수능：2026-11-19 목，출처：교육부 2024-08-16 발표・한국교육과정평가원 시행기본계획 2026-03-31）
# ============================================================================================
PAGE_SPECS += [
    # K1 Studydown＋LockHour：「수능 공부 앱」「공부 타이머」
    {
        "key": "studydown", "event": "suneung", "lang": "ko",
        "slug": "suneung-gongbu-app-gongbu-timer-ko",
        "terms": ["수능 공부 앱", "공부 타이머", "공부 시간 측정"],
        "title": "수능 공부 앱 고르는 법: 막판 한 달, 공부 타이머로 ‘진짜 공부한 시간’만 재기",
        "desc": "수능 공부 앱을 찾는다면: 휴대폰을 뒤집어 두면 시간이 기록되고 들면 멈추는 공부 타이머, 방해되는 앱을 잠그는 집중 앱으로 막판 공부 시간을 지키는 방법. Studydown·LockHour 사용법과 App Store 바로가기.",
        "h1": "수능 공부 앱: 막판 한 달, 진짜 공부한 시간만 남기는 법",
        "lead": "11월 19일 수능을 앞두고 App Store에서 ‘수능 공부 앱’이나 ‘공부 타이머’를 검색하는 수험생은 대부분 같은 고민을 합니다. 책상에는 오래 앉아 있었는데, 정작 집중한 시간은 얼마나 되는지 모르겠다는 것이죠.",
        "intro": [
            "막판 한 달은 새로운 공부법을 찾을 때가 아니라, 이미 하고 있는 공부의 시간을 지키는 때입니다. 그런데 휴대폰이 책상 위에 있으면 알림 하나, 짧은 영상 하나에 십 분, 이십 분이 사라집니다. 공부 시간을 적어 보면 열 시간인데, 실제로 문제를 푼 시간은 그보다 훨씬 짧은 경우가 많습니다.",
            "그래서 수험생들이 많이 찾는 것은 두 가지입니다. 하나는 진짜 공부한 시간만 정확하게 재 주는 타이머이고, 다른 하나는 공부하는 동안 손이 가는 앱을 아예 잠가 주는 집중 앱입니다. 둘을 함께 쓰면 ‘오늘 몇 시간 했는지’보다 ‘오늘 얼마나 몰입했는지’를 볼 수 있습니다.",
        ],
        "sections": [
            ("수능 공부 타이머에서 확인할 다섯 가지", [], [
                "휴대폰을 뒤집어 두면 시작되고 들면 멈추는지: 손에 들고 딴짓한 시간이 공부 시간에 섞이지 않아야 합니다.",
                "과목별로 나눠 기록할 수 있는지: 국어, 수학, 영어, 탐구를 각각 다른 활동으로 두면 어느 과목에 시간이 부족한지 바로 보입니다.",
                "오늘과 이번 주 합계, 연속 기록 일수를 보여 주는지.",
                "마감일과 목표 시간을 정하면 남은 하루 분량을 계산해 주는지.",
                "계정 없이 기기 안에서 기록되는지: 시험 기간에는 로그인 같은 사소한 단계도 귀찮습니다.",
            ]),
            ("D-30부터 수능 당일까지 이렇게 써 보세요", [
                "D-30에서 D-14까지는 과목별 시간을 고르게 맞추는 시기입니다. 매일 저녁 오늘의 과목별 시간을 보고, 한 과목에 몰린 날은 다음 날 부족한 과목을 먼저 시작하세요. 수능 날짜를 마감일로 두고 목표 시간을 정해 두면 하루에 얼마나 더 해야 하는지 숫자로 보입니다.",
                "D-14부터는 실전 감각을 위해 시험 시간표에 맞춰 공부하는 수험생이 많습니다. 국어 시간에는 국어만, 수학 시간에는 수학만 하고, 그 시간 동안 방해되는 앱은 잠가 두세요. 세션이 끝나면 자동으로 풀리기 때문에 쉬는 시간까지 참을 필요는 없습니다.",
                "마지막 일주일은 무리하게 시간을 늘리기보다 잠과 컨디션을 지키는 것이 중요합니다. 잠들기 전 모드로 늦은 밤 스크롤을 막고, 아침에는 휴대폰보다 공부를 먼저 시작해 보세요.",
            ], []),
        ],
        "steps_title": "오늘 바로 시작하는 순서",
        "steps": [
            "Studydown에서 과목별 활동(국어, 수학, 영어, 탐구)을 만들고 색을 정합니다.",
            "활동을 고르고 측정을 시작한 뒤, 화면이 아래로 가게 휴대폰을 책상에 놓습니다. 측정 중에는 앱을 열어 둡니다.",
            "공부하는 동안 손이 가는 앱은 LockHour의 공부 모드로 정해진 시간 동안 잠급니다.",
            "저녁마다 오늘·이번 주 합계와 과목별 시간 분포를 확인합니다.",
            "수능 날짜를 마감일로 두고 목표 시간을 정해, 남은 하루 분량을 확인합니다.",
        ],
        "cards": [
            ("studydown", "Studydown은 활동별로 들인 시간을 기록하는 집중 타이머입니다. 활동을 고르고 측정을 시작한 다음 화면이 아래로 향하도록 휴대폰을 책상에 놓으면 기록되고, 휴대폰을 들면 설정한 유예 시간에 따라 일시 정지합니다. 오늘과 이번 주의 합계, 연속 기록 일수, 활동별 시간 분포를 확인하고, 주간 목표와 마감일을 정해 남은 하루 분량을 볼 수 있습니다. 측정과 기록은 기기에서 처리되며 계정이나 광고가 없습니다."),
            ("lockhour", "공부할 때 자꾸 휴대폰을 집게 된다면 LockHour: 방해되는 앱을 정해진 시간 동안 잠그고, 시간이 끝나면 자동으로 풀어 줍니다. 빠른 집중, 딥 워크, 공부 모드(뽀모도로식 집중과 휴식), 잠들기 전, 아침 리셋 모드와 하드 모드, 연속 기록과 주간 차트를 제공합니다. 계정, 광고, 추적이 없습니다."),
        ],
        "faqs": [
            ("휴대폰을 뒤집지 않고 들고 있으면 어떻게 되나요?", "Studydown은 휴대폰을 들면 설정한 유예 시간에 따라 일시 정지합니다. 측정 중에는 앱을 열어 두어야 하고, 앱을 벗어난 뒤에는 시간이 더해지지 않습니다."),
            ("과목별로 공부 시간을 나눠 볼 수 있나요?", "네. 활동 이름과 색상, 순서를 직접 정할 수 있어 과목별로 기록하고 활동별 시간 분포를 확인할 수 있습니다."),
            ("공부하는 동안 SNS나 영상 앱을 막을 수 있나요?", "LockHour로 선택한 앱을 정해진 시간 동안 잠글 수 있고, 세션이 끝나면 자동으로 풀립니다."),
            ("계정이 필요한가요?", "아니요. Studydown과 LockHour 모두 계정 없이 사용하며 광고가 없습니다."),
        ],
        "related": [("ko/studydown.html", "Studydown 자세히 보기"), ("ko/lockhour.html", "LockHour 자세히 보기"),
                    ("ko/countdaysnow.html", "CountDaysNow 디데이 위젯")],
    },
    # K2 CountDaysNow：「수능 디데이」「디데이 위젯」
    {
        "key": "countdaysnow", "event": "suneung", "lang": "ko",
        "slug": "suneung-dday-widget-app-ko",
        "terms": ["수능 디데이", "디데이 위젯", "수능 D-day"],
        "title": "수능 디데이 위젯 설정법: 홈 화면과 잠금화면에서 남은 날을 매일 확인하기",
        "desc": "수능 디데이를 홈 화면 위젯과 잠금화면에 띄우고 7일·3일·1일 전 알림까지 받는 방법. 모의고사, 원서 마감, 성적 발표일까지 함께 세는 CountDaysNow 사용법과 App Store 바로가기.",
        "h1": "수능 디데이 위젯: 남은 날을 매일 보이는 곳에 두기",
        "lead": "수능이 다가오면 ‘수능 디데이’와 ‘디데이 위젯’ 검색이 늘어납니다. 남은 날을 매일 눈으로 보는 것만으로도 오늘 해야 할 공부의 무게가 달라지기 때문입니다.",
        "intro": [
            "2027학년도 수능은 2026년 11월 19일 목요일에 치러지고, 성적은 12월 11일에 통지될 예정입니다(교육부 발표, 한국교육과정평가원 시행기본계획). 수험생에게 중요한 날은 수능 하루만이 아닙니다. 마지막 모의고사, 수시 면접과 논술, 성적 발표, 정시 원서 접수까지 날짜가 줄줄이 이어집니다.",
            "날짜를 머릿속으로만 세다 보면 하루하루가 비슷하게 느껴지고, 어느새 일주일이 지나 있기 쉽습니다. 휴대폰을 켤 때마다 남은 날이 보이도록 홈 화면과 잠금화면에 디데이를 두면, 따로 마음먹지 않아도 매일 한 번씩 오늘의 계획을 떠올리게 됩니다.",
        ],
        "sections": [
            ("수능 디데이 앱에서 확인할 것", [], [
                "정확한 날짜 수: 다가올 날은 카운트다운하고, 지난날은 며칠이 지났는지 보여 주는지.",
                "홈 화면 위젯: 앱을 열지 않아도 남은 날이 보이는지, 가까운 날짜 여러 개를 한 번에 볼 수 있는지.",
                "잠금화면과 다이내믹 아일랜드: 휴대폰을 켜는 순간 남은 날이 보이는지.",
                "미리 알림: 7일·3일·1일 전과 당일에 알려 주는지.",
                "계정과 광고 없이 쓸 수 있는지: 수험 기간에는 화면에 다른 것이 끼어들지 않는 편이 좋습니다.",
            ]),
            ("수험생 디데이, 이렇게 나눠 두세요", [
                "수능 당일 하나만 두지 말고 수능 전후의 중요한 날을 함께 등록해 보세요. 수능, 수시 면접이나 논술 날짜, 성적 발표일, 원서 접수 마감일을 각각 이벤트로 만들고 카테고리로 묶어 두면, ‘다음 3개’ 위젯 하나로 가장 가까운 세 날짜를 한 번에 확인할 수 있습니다.",
                "수능이 끝난 뒤에도 디데이는 쓸모가 있습니다. 성적 발표일, 졸업식, 겨울방학 여행처럼 기다리는 날을 새로 세어 보세요. 지난 수능 날짜는 아카이브해 두면 기록을 잃지 않고 ‘그날로부터 며칠’도 확인할 수 있습니다.",
            ], []),
        ],
        "steps_title": "수능 디데이 위젯 3분 설정",
        "steps": [
            "CountDaysNow에서 2026년 11월 19일을 ‘수능’ 이벤트로 추가합니다.",
            "모의고사, 면접·논술, 성적 발표일(12월 11일)도 이벤트로 추가하고 카테고리로 묶습니다.",
            "홈 화면에 위젯을 추가하고 수능 이벤트를 선택합니다.",
            "미리 알림을 켜서 7일·3일·1일 전과 당일에 알림을 받습니다.",
            "수능이 끝나면 다음 목표 날짜를 새로 세고, 지난 이벤트는 아카이브합니다.",
        ],
        "cards": [
            ("countdaysnow", "CountDaysNow는 미래, 오늘, 과거의 이벤트를 세 가지 명확한 보기로 정리하고 정확한 날짜 수와 날짜 계산기를 제공합니다. 홈 화면 위젯은 모든 크기를 지원하고, 다이내믹 아일랜드와 잠금화면에서 남은 날이 실시간으로 이어지며, ‘다음 3개’ 위젯은 가장 가까운 세 날짜를 한 번에 보여 줍니다. 7일·3일·1일 전과 당일, 100일에 알려 주고, 카테고리와 아카이브로 정리할 수 있습니다. 광고도 구독도 계정도 없습니다."),
            ("studydown", "남은 날을 봤다면 오늘 공부 시간도 기록해 보세요. Studydown은 휴대폰을 화면이 아래로 가게 놓으면 시간을 기록하고 들면 일시 정지하며, 마감일별 목표 시간을 정하면 남은 하루 분량을 계산합니다."),
        ],
        "faqs": [
            ("2027학년도 수능은 언제인가요?", "2026년 11월 19일 목요일이며, 성적은 12월 11일 통지 예정입니다. 정확한 내용은 한국교육과정평가원 공고를 확인하세요."),
            ("잠금화면에서도 수능 디데이를 볼 수 있나요?", "네. CountDaysNow는 잠금화면과 다이내믹 아일랜드에서 남은 날을 실시간으로 보여 줍니다."),
            ("여러 날짜를 한 번에 볼 수 있나요?", "‘다음 3개’ 위젯이 가장 가까운 세 날짜를 한 번에 보여 줍니다. 수능, 면접, 성적 발표일을 함께 등록해 두면 편합니다."),
            ("알림은 언제 오나요?", "7일·3일·1일 전과 당일에 알려 드립니다. 100일과 매년 돌아오는 날에도 알림을 받을 수 있습니다."),
        ],
        "related": [("ko/countdaysnow.html", "CountDaysNow 자세히 보기"), ("ko/studydown.html", "Studydown 공부 타이머"),
                    ("answers/d-day-counter-app-korea-couple-100-days-suneung-discharge-lock-screen.html", "D-day counter app in Korea")],
    },
    # K3 Wordmate＋DailyMate：「수능 끝나고 할 일」
    {
        "key": "wordmate", "event": "suneung", "lang": "ko",
        "slug": "suneung-kkeutnago-hal-il-oegugeo-gongbu-ko",
        "terms": ["수능 끝나고 할 일", "수능 끝나고 외국어", "외국어 공부 앱"],
        "title": "수능 끝나고 할 일: 겨울방학에 외국어 하나 시작하기 (하루 한 유닛 단어·회화 앱)",
        "desc": "수능 끝나고 할 일 목록에 ‘외국어 시작하기’가 있다면: 졸업 여행과 새 학기를 앞두고 일본어, 영어, 스페인어 등 단어와 회화를 하루 조금씩 익히는 방법. Wordmate·DailyMate 사용법과 App Store 바로가기.",
        "h1": "수능 끝나고 할 일: 겨울방학에 외국어 하나 시작하기",
        "lead": "11월 19일 수능이 끝나면 ‘수능 끝나고 할 일’ 검색이 크게 늘어납니다. 운전면허, 아르바이트, 여행과 함께 거의 빠지지 않는 항목이 바로 ‘외국어 하나 시작하기’입니다.",
        "intro": [
            "수능이 끝나고 대학 입학까지는 석 달 가까운 시간이 있습니다. 처음 며칠은 실컷 쉬는 것이 당연하지만, 일주일쯤 지나면 시간이 아깝다는 생각이 들기 시작합니다. 이때 시작하기 좋은 것이 외국어입니다. 졸업 여행으로 일본이나 다른 나라에 가려는 사람도 많고, 대학에서 교양 외국어를 들을 계획이 있다면 미리 감을 잡아 둘 수 있습니다.",
            "문제는 의욕이 넘치는 첫 주에 너무 많이 하다가 금방 지치는 것입니다. 겨울방학 외국어는 하루에 조금씩, 그러나 매일 이어 가는 것이 핵심입니다. 단어는 주제별로 짧게, 회화는 실제로 쓸 문장 위주로 익히면 여행지에서 바로 써먹을 수 있습니다.",
        ],
        "sections": [
            ("수능 끝나고 외국어, 이렇게 시작하세요", [], [
                "언어 하나만 고르기: 여행 갈 나라의 언어나 대학에서 들을 교양 외국어처럼 이유가 분명한 언어 하나로 시작하세요.",
                "주제별 단어부터: 인사, 음식, 쇼핑, 이동처럼 여행에서 바로 쓰는 주제를 먼저 익히면 동기가 오래갑니다.",
                "발음은 듣고 따라 하기: 눈으로만 외운 단어는 말할 때 나오지 않습니다.",
                "완전한 문장과 대답까지: 단어를 알아도 입이 안 떨어진다면, 상대의 자연스러운 대답까지 함께 익히세요.",
                "매일 한 번 보이는 곳에 두기: 홈 화면 위젯에서 단어나 문장을 확인하면 앱을 열지 않은 날도 이어집니다.",
            ]),
            ("12주 겨울방학 계획 예시", [
                "1주부터 4주까지는 단어 위주로 하루 한 유닛씩 익힙니다. 3단계 난이도 중 초급부터 시작해, 다시 볼 단어는 즐겨찾기에 모아 둡니다. 연속 학습 기록이 쌓이는 것을 보는 것만으로도 꾸준함이 생깁니다.",
                "5주부터 8주까지는 회화 문장을 더합니다. 식사, 쇼핑, 이동, 여행처럼 졸업 여행에서 실제로 마주칠 상황의 문장을 하루 몇 개씩 듣고 따라 하세요. 9주부터는 여행 일정에 맞춰 필요한 상황을 골라 복습하고, 대학 입학 전까지 매일 이어 가는 습관을 만드는 데 집중합니다.",
            ], []),
        ],
        "steps_title": "오늘 시작하는 방법",
        "steps": [
            "Wordmate에서 앱 표시 언어는 한국어로, 학습 언어는 시작할 언어로 설정합니다.",
            "14개 주제 중 여행에서 쓸 주제부터 하루 한 유닛씩 익히고 발음을 들어 봅니다.",
            "다시 볼 단어는 즐겨찾기에 저장하고, 홈 화면 인터랙티브 위젯을 추가합니다.",
            "DailyMate로 같은 언어의 완전한 문장과 자연스러운 대답을 상황별로 익힙니다.",
            "진도와 연속 학습 기록을 보며 대학 입학 전까지 매일 이어 갑니다.",
        ],
        "cards": [
            ("wordmate", "Wordmate는 44개 언어의 단어를 14개 실용 주제와 3단계 난이도로 정리하고 발음 듣기를 함께 제공합니다. 영어 단어는 모두 예문과 함께 익힐 수 있고, 학습 언어마다 진도를 따로 관리하며, 다시 볼 단어는 즐겨찾기에 저장해 복습합니다. 홈 화면 인터랙티브 위젯과 Apple Watch에서 바로 이어서 학습할 수 있고, 계정이 필요하지 않으며 제3자 광고나 추적이 없습니다. 한 번 구매하면 구독도 앱 내 결제도 없습니다."),
            ("dailymate", "단어는 아는데 말이 안 나온다면 DailyMate: 47개 학습 언어의 실용 문장 8,400개를 14가지 생활 주제와 84가지 상황으로 정리하고, 자연스러운 대답까지 함께 알려 줍니다. 시스템 음성 듣기, 문장 저장, 위젯과 Apple Watch를 지원하며 구독은 없습니다."),
        ],
        "faqs": [
            ("수능 끝나고 외국어는 하루에 얼마나 하면 좋을까요?", "처음에는 하루 한 유닛처럼 짧게, 대신 매일 이어 가는 것을 목표로 하세요. Wordmate는 진도와 연속 학습 기록을 보여 줍니다."),
            ("일본어처럼 처음 배우는 언어도 되나요?", "Wordmate는 44개 언어, DailyMate는 47개 학습 언어를 지원하며 3단계 난이도 중 초급부터 시작할 수 있습니다."),
            ("발음도 들을 수 있나요?", "네. Wordmate는 선택한 학습 언어의 발음을 들을 수 있고, DailyMate는 선택한 언어에 맞는 시스템 음성으로 문장을 들려줍니다."),
            ("구독인가요?", "아니요. Wordmate와 DailyMate는 한 번 구매하는 앱이며 구독이 없습니다."),
        ],
        "related": [("ko/wordmate.html", "Wordmate 자세히 보기"), ("ko/dailymate.html", "DailyMate 자세히 보기"),
                    ("answers/after-suneung-start-japanese-five-words-a-day-winter-break.html", "After the Suneung: five Japanese words a day")],
    },
]

# ============================================================================================
# 感恩節（11-26）＋黑色星期五（11-27）：旅行、送禮清單、記帳；美國英文＋巴西葡文
# ============================================================================================
PAGE_SPECS += [
    # T1 TripBee：美國「thanksgiving trip planner」
    {
        "key": "tripbee", "event": "thanksgiving", "lang": "en",
        "slug": "thanksgiving-trip-planner-app-family-itinerary",
        "terms": ["thanksgiving trip planner", "thanksgiving travel", "family trip itinerary"],
        "title": "Thanksgiving trip planner app: one shared family itinerary, packing lists and a rainy-day plan",
        "desc": "Planning Thanksgiving travel? Keep flights, drives, hotel and dinner times in one shared itinerary the whole family can edit, with packing lists per person and an offline plan. How to set it up in TripBee.",
        "h1": "Thanksgiving trip planner: one itinerary the whole family can see",
        "lead": "Thanksgiving week is the busiest travel stretch of the year in the US, and people who search for a \"thanksgiving trip planner\" are usually the one person in the family group chat who ends up organizing everyone.",
        "intro": [
            "Getting the family together for one dinner involves a surprising amount of logistics. Someone is flying in on Tuesday night, someone is driving four hours on Wednesday, the kids need car seats, grandma needs a ride from the airport, and the turkey has to go in the oven at a specific time no matter who is late. Usually all of that lives in a group chat, a couple of screenshots and someone's memory.",
            "The fix is boring but it works: one itinerary that everyone looks at, organized day by day, with times and addresses in it. When the plan changes, and on Thanksgiving week it always does, you change it once and everyone sees the same version. Add a packing list per person and a backup plan for bad weather, and most of the stress goes away before you leave the house.",
        ],
        "sections": [
            ("What a Thanksgiving trip planner should handle", [], [
                "A day-by-day timeline for the whole trip: Tuesday arrivals, Wednesday drives, Thursday dinner, Friday leftovers and the Sunday trip home.",
                "Flights with time zones, because a cross-country flight on Wednesday night is where arrival times get confusing.",
                "Shared editing, so the person picking up grandma and the person cooking see the same plan.",
                "Packing lists that differ by person and by kids' ages, so nobody forgets the stroller, chargers or medication.",
                "A plan that still opens with no signal, on a rural road or a crowded airport Wi-Fi.",
            ]),
            ("A simple plan for Thanksgiving week", [
                "Start with the fixed points: flights, the drive, where everyone sleeps and the time dinner is served. Put those on the timeline first with times, time zones and addresses, then fill in the softer plans around them, such as a parade in the morning, a walk after dinner or Black Friday errands the next day.",
                "For each outdoor plan, add a rainy-day backup. Late November weather can turn a park morning into a cold, wet mess; if the backup is already written down, you switch the day in one tap instead of arguing about it in the driveway. A week before leaving, build packing lists by person and check them the night before.",
                "Finally, invite the people who need to see the plan. When a flight is delayed, update the timeline once instead of sending the same message to six people.",
            ], []),
        ],
        "steps_title": "Set up the family trip in ten minutes",
        "steps": [
            "Create the trip and add each day of Thanksgiving week to the timeline with times, time zones, addresses and notes.",
            "Turn on iCloud and invite family members so they can read and edit the shared trip.",
            "Add a rainy-day backup for any outdoor plan.",
            "Generate the smart packing list by days, season and each family member, including kids' ages.",
            "Use one-tap Apple Maps directions on the day, and share a trip poster with everyone who is not on the app.",
        ],
        "cards": [
            ("tripbee", "TripBee is a day-by-day trip planner with times, type icons, time zones, notes and reminders, a live Day X of Y progress view and a countdown before you fly. The smart packing list adapts to days, season and each family member, including kids' ages. Plan with the weather in mind and add rainy-day backup ideas, get one-tap Apple Maps directions, share a trip poster, import from CSV and back up locally. Core planning works offline; with iCloud enabled, people you invite can read and edit a shared trip. One-time purchase, no ads and no tracking."),
            ("tripbeelite", "Only one trip to plan? TripBee Lite gives one upcoming journey your full attention: a clear daily timeline with flight and hotel details, notes, reminders and ticket references, with no account required and no ads."),
        ],
        "faqs": [
            ("Can the whole family edit the Thanksgiving itinerary?", "Yes. With iCloud enabled, TripBee lets you invite others to read and edit a shared trip; Apple handles storage, sync and notifications."),
            ("Does the plan work without internet?", "Yes. TripBee's core planning works offline."),
            ("Can it make packing lists for kids?", "Yes. The smart packing list is built by days, season and each family member, including kids' ages."),
            ("Can the developer see our travel plans?", "No. Trips sync through your private iCloud account; the developer has no travel-data server and cannot access that content."),
        ],
        "related": [("en-US/tripbee.html", "TripBee: full overview"), ("en-US/tripbeelite.html", "TripBee Lite: full overview"),
                    ("en/seasonal/road-trip-games-for-kids-car-ride-missions.html", "Road trip games for kids")],
    },
    # T2 SaveTag：美國「gift list app」「gift ideas」
    {
        "key": "savetag", "event": "gifts", "lang": "en",
        "slug": "holiday-gift-list-app-save-gift-ideas-from-any-app",
        "terms": ["gift list app", "gift ideas list", "christmas gift list"],
        "title": "Gift list app for the holidays: save gift ideas from any app before Black Friday",
        "desc": "Keep a holiday gift list that actually works: save gift ideas from any app with one share, let tags sort them, find them again with a vague search, and clean up product screenshots. How to set it up with SaveTag.",
        "h1": "Holiday gift list app: save every gift idea before Black Friday",
        "lead": "People who search for a \"gift list app\" in November usually already have the ideas. They are just scattered across a dozen places: a link a sister sent in a chat, a product in a social post, a screenshot from a shop, a note from last month.",
        "intro": [
            "The hard part of holiday gifting is not thinking of ideas; it is finding them again when it is time to buy. When Black Friday and Cyber Monday arrive, you want to open one list and see the jacket your partner liked, the board game your nephew mentioned and the recipe book for your mom, not scroll through three weeks of messages trying to remember who sent what.",
            "A good gift list is mostly about capture. If saving an idea takes more than a couple of seconds, you will not do it in the moment, and the idea is gone. The best setup is the one where you share a link from whatever app you are in, and it lands in one place, already sorted.",
        ],
        "sections": [
            ("What a gift list app needs to do", [], [
                "Save from anywhere: share a product link from a shop, a social app, a browser or a chat with one tap.",
                "Sort itself: shopping, home, style, gaming, pets and other topics, so the list is not one big pile.",
                "Find an idea from a vague memory, such as \"that blue jacket\" or \"the board game\", without the exact title.",
                "Let you add your own tags, for example one per person you are buying for.",
                "Keep your list private and on your phone, with no account to create.",
            ]),
            ("A simple system for the holiday season", [
                "From now until Black Friday, save every idea the moment you see it. Do not decide anything yet. Add a custom tag for each person, such as Mom, Alex or Office Swap, so that later you can open one tag and see only their ideas.",
                "The week before Black Friday, go through each person's tag and pick one or two gifts. This is where the list pays off: you buy what you planned instead of whatever is on the front page of the sale. Product screenshots count too; if you tend to screenshot items instead of saving links, let a screenshot app sort them into a shopping category and search the text inside.",
                "After the holidays, the same list becomes next year's starting point. Ideas you did not buy this time are still there, tagged and searchable.",
            ], []),
        ],
        "steps_title": "Start your gift list today",
        "steps": [
            "When you see a gift idea in any app, tap Share and choose SaveTag; or copy a link and quick-save it from the clipboard.",
            "Let SaveTag tag it automatically, then add a custom tag with the person's name.",
            "When you remember an idea but not the name, search for what you meant; search runs across titles, notes, tags and sources.",
            "If you saved products as screenshots, let ShotInbox sort them into Shopping and search the text in them.",
            "The week before Black Friday, open each person's tag and choose what to buy.",
        ],
        "cards": [
            ("savetag", "SaveTag gives every link you save one home and does the filing for you. Share any link from any app with a share sheet or quick-save from the clipboard; title, site and preview are pulled in. Every save is tagged on your device into precise topics such as shopping, style, home, gaming and more, and you can add custom tags. Search understands what you meant across titles, notes, tags and sources, and Rediscover brings back a few unread saves each day. No account, no cloud, no ads and no tracking."),
            ("shotinbox", "Saved gift ideas as screenshots? ShotInbox sorts screenshots into Shopping, Receipts, Travel, Tickets and more, searches the text inside them, and can open links, track packages or add reminders. Apple Vision and Natural Language run on-device; nothing is uploaded and nothing is auto-deleted."),
        ],
        "faqs": [
            ("Can I save gift ideas from a social app or a shop app?", "SaveTag works from any app with a share sheet, so you can share a link from social apps, browsers, chats or shops. You can also copy a link and quick-save it from the clipboard."),
            ("Can I keep a separate list for each person?", "Yes. Add your own custom tags, such as one per person, alongside the automatic topic tags."),
            ("Do I need an account?", "No. SaveTag has no account, no cloud, no ads and no tracking; your saves never leave your device."),
            ("I mostly take screenshots of products. Does that work?", "Use ShotInbox for screenshots: it sorts them into categories like Shopping and Receipts and lets you search the text inside them, all on-device."),
        ],
        "related": [("en-US/savetag.html", "SaveTag: full overview"), ("en-US/shotinbox.html", "ShotInbox: full overview"),
                    ("en/seasonal/read-later-app-save-links-from-any-app.html", "Read-later app: save links from any app")],
    },
    # T3 G+Money：美國「black friday budget」
    {
        "key": "gmoney", "event": "black_friday", "lang": "en",
        "slug": "black-friday-budget-app-daily-spending-limit",
        "terms": ["black friday budget", "holiday spending tracker", "budget app"],
        "title": "Black Friday budget: set a spending limit, log by category and see what is left (budget app guide)",
        "desc": "A simple Black Friday budget that holds up through Cyber Monday and the holidays: set a limit, log each purchase by category, group holiday spending as its own event and export it. How to do it with G+Money.",
        "h1": "Black Friday budget: a simple limit you can see while you shop",
        "lead": "Search interest in \"black friday budget\" climbs every November, and the people searching are not trying to skip the sales. They want to buy the things they planned and still recognize their bank balance in December.",
        "intro": [
            "Black Friday spending rarely goes wrong on one big purchase. It goes wrong on twenty small ones: a gift here, a deal on something you did not need there, one more item just to reach the shipping minimum, a second order on Cyber Monday. Each one feels reasonable on its own; together they eat the whole holiday budget before December even starts.",
            "The simplest defense is a number you can see at the moment you shop. Decide how much the holiday season can cost, split it into a daily limit for the sale days, and log each purchase as it happens. When you can see what is left today, the next deal has to compete with that number instead of with a countdown timer.",
        ],
        "sections": [
            ("Build a Black Friday budget in four parts", [], [
                "Gifts: the people you are buying for and a rough amount for each. Plan this first, because it is the part you cannot skip.",
                "Planned upgrades: the one or two things you have been waiting to buy on sale, with a ceiling for each.",
                "Food and travel: Thanksgiving groceries, gas or flights, and eating out over the long weekend.",
                "A small buffer for deals you did not expect, so one surprise does not blow the whole plan.",
            ]),
            ("Keep holiday spending separate from everyday spending", [
                "Holiday shopping blurs into normal life fast. The coffee, the groceries and the gifts all come from the same card, so by mid-December nobody knows what the season actually cost. Grouping holiday purchases as their own event fixes that: everyday spending stays where it is, and the holiday total has its own subtotal.",
                "Log by category as you go, such as shopping, groceries, transport and fees, and filter by date after Cyber Monday to see where the money went. Export the list to text or CSV if you share costs with a partner or want to keep a record for next year's planning.",
            ], []),
        ],
        "steps_title": "Set it up before Black Friday",
        "steps": [
            "Create an event called Holidays with its own icon and color.",
            "Set a daily limit for the sale days so you can see how much is left today.",
            "Log each purchase right after you pay, pick a category and tag it to the Holidays event.",
            "After Cyber Monday, filter by event, category and date to see what the season cost.",
            "Export to text or CSV to share with your partner or keep for next year.",
        ],
        "cards": [
            ("gmoney", "G+Money combines an expense tracker and a currency converter. Log spending by category, set a daily limit and see how much is left today, with instant home-currency totals. Create trips or events with their own icon and color, tag any expense to them or leave it as everyday spending, and get summaries and exports grouped with subtotals. Filter by trip, category and date, and export to text or CSV. Fully offline; no account, no sign-up, no tracking and no ads; one-time purchase, no subscription."),
            ("hourstag", "Stuck on whether a deal is worth it? HoursTag turns any price into the hours you need to work to earn it, so you can tag each purchase as Need, Want or Impulse before you buy."),
        ],
        "faqs": [
            ("How do I keep Black Friday spending separate from normal spending?", "Create an event in G+Money and tag holiday purchases to it. Everyday expenses can stay unassigned, and summaries and exports are grouped with subtotals."),
            ("Can I set a daily spending limit?", "Yes. Set a daily limit and G+Money shows how much is left today."),
            ("Does it need an account or internet?", "No account and no sign-up. G+Money works fully offline; data stays on your device or in your own iCloud if you turn on iCloud Sync."),
            ("Can I export my holiday spending?", "Yes. Export to text or CSV, grouped by trip or event with subtotals."),
        ],
        "related": [("en-US/gmoney.html", "G+Money: full overview"), ("en-US/hourstag.html", "HoursTag: full overview"),
                    ("answers/black-friday-price-in-work-hours-before-you-buy.html", "Black Friday: see the price in work hours")],
    },
    # T4 HoursTag：巴西「black friday lista de compras」
    {
        "key": "hourstag", "event": "black_friday", "lang": "pt-BR",
        "slug": "black-friday-lista-de-compras-app-horas-de-trabalho",
        "terms": ["black friday lista de compras", "black friday", "controle de gastos"],
        "title": "Black Friday lista de compras: compre sem arrependimento vendo o preço em horas de trabalho",
        "desc": "Montando a lista de compras da Black Friday? Antes de pagar, transforme o preço em horas de trabalho e marque como Preciso, Quero ou Impulso. Como usar o HoursTag e link direto da App Store.",
        "h1": "Black Friday: quantas horas de trabalho custa essa compra?",
        "lead": "Quem pesquisa \"black friday lista de compras\" em novembro geralmente já tem um carrinho cheio e uma desconfiança: parte daquilo vai virar arrependimento quando a fatura chegar.",
        "intro": [
            "A Black Friday no Brasil virou uma maratona: começa semanas antes, tem contagem regressiva, cupom que acaba, frete que só compensa acima de certo valor e parcelamento que faz tudo parecer pequeno. O problema não é comprar, é que nesse clima fica difícil separar o que você realmente precisa do que entrou no carrinho só porque estava com desconto.",
            "Um jeito simples de recuperar a clareza é olhar o preço de outra forma. Um tênis que parece barato na tela muda de figura quando você vê que ele custa meio dia do seu trabalho. Não é para deixar de comprar, e sim para guardar o dinheiro para as poucas coisas que realmente valem as horas que custam.",
        ],
        "sections": [
            ("Separe a lista da Black Friday em três grupos", [], [
                "Preciso: o que você compraria de qualquer jeito e vai usar, como itens de casa, um eletrodoméstico quebrado ou reposição de produtos do dia a dia.",
                "Quero: o que você gosta mas pode esperar. Deixe na lista, veja quantas horas de trabalho custa e só então decida.",
                "Impulso: o que apareceu por causa da contagem regressiva, do estoque acabando ou porque todo mundo está comprando. Espere uma noite antes de decidir.",
                "Antes de adicionar mais um item só para atingir o valor mínimo do frete, pergunte se ele vale as horas extras de trabalho.",
            ]),
            ("Depois da Black Friday: veja o padrão e planeje o fim do ano", [
                "Registre cada compra e mantenha a marcação de Preciso, Quero ou Impulso. No fim do mês, o resumo por categoria mostra para onde o dinheiro foi e deixa o 13º salário e os presentes de Natal mais fáceis de planejar.",
                "Se você está juntando dinheiro para algo maior, como uma viagem de fim de ano, transforme isso numa meta e acompanhe em horas reais. Fica claro quantas pequenas compras de Black Friday estão adiando o que você realmente quer.",
            ], []),
        ],
        "steps_title": "Prepare em 10 minutos antes da Black Friday",
        "steps": [
            "Defina sua renda uma vez no HoursTag, por hora ou por mês.",
            "Digite o preço de cada item do carrinho e veja quantas horas de trabalho ele custa.",
            "Marque como Preciso, Quero ou Impulso; os de impulso esperam uma noite.",
            "Na Black Friday, compre só o que ficou na lista.",
            "Depois, confira o resumo por categoria e o mensal para planejar o Natal.",
        ],
        "cards": [
            ("hourstag", "O HoursTag transforma qualquer preço nas horas de trabalho que você precisa para ganhá-lo. Defina sua renda uma vez, por hora ou por mês, digite um preço e veja na hora como tempo de trabalho. Marque gastos como Preciso, Quero ou Impulso, acompanhe metas e lista de desejos em horas reais, veja análises por categoria com resumo mensal e cada compra como porcentagem do seu dia de trabalho. Sem conta, sem cadastro, sem rastreamento e sem anúncios; sem assinatura e sem compras no app."),
            ("hourstaglite", "Quer algo mais simples? O HoursTag Lite também converte preços em tempo de trabalho, separa em Necessidade, Desejo ou Impulso e mostra o trabalho por trás de uma meta, com widget e Apple Watch. Tudo fica no seu aparelho, sem conta."),
        ],
        "faqs": [
            ("Como o HoursTag calcula as horas de trabalho?", "Você define sua renda uma vez, por hora ou por mês, e o HoursTag calcula seu valor real por hora. Depois, qualquer preço aparece na hora como tempo de trabalho."),
            ("Preciso criar conta?", "Não. Sem conta, sem cadastro, sem rastreamento e sem anúncios; tudo fica no seu aparelho."),
            ("Dá para acompanhar uma meta, como uma viagem?", "Sim. O HoursTag acompanha metas e lista de desejos em horas reais, com progresso."),
            ("É assinatura?", "Não. O HoursTag não tem assinatura nem compras no app."),
        ],
        "related": [("pt-BR/hourstag.html", "HoursTag: visão completa"), ("pt-BR/hourstaglite.html", "HoursTag Lite: visão completa")],
    },
]
