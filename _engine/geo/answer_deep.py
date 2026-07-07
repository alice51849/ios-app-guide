#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep-content items for high-converting "winner" apps (2026-07-08).

Verified from app source code, App Store copy and support docs by two research
workers (winner-health-kids: Cyca / Lumi Bopomofo / Lumi Weather;
winner-productivity-photo: Mochi / LockHour / Unblurry). Each item is a
scenario- or FAQ-style deep answer with {name} placeholders filled at runtime.

Honesty preserved from source: Cyca = on-device, no network/ML, NOT a medical
device / not contraception; Unblurry = honest motion-blur vs out-of-focus
limits; LockHour = Screen Time API, Hard Mode bypass honesty; kids apps =
ad-free, no data collected. Consumed by answer_facts._deep_facts().
"""
import json
from typing import Any

DEEP_ITEMS: list[dict[str, Any]] = json.loads(r'''
[
 {
  "app_key": "cyca",
  "kind": "faq",
  "query": "How does a period tracking app calculate the fertile window?",
  "match": [
   "how does a period tracking app calculate the fertile window?",
   "how accurate is a cycle app's fertile window prediction?",
   "fertile window",
   "cycle tracking app",
   "how it estimates"
  ],
  "lead": "A cycle-tracking app estimates your fertile window using the statistical average of your own logged period-start dates to predict when ovulation is likely to occur — not population averages.",
  "detail": "{name} uses pure on-device calendar math — no network connection, no machine learning — to predict ovulation by subtracting the typical luteal length (~14 days) from your average cycle length. It then marks the 5 days before estimated ovulation plus the day of ovulation itself as the fertile window, reflecting the biological window in which sperm can survive up to 5 days to meet an egg. No app can guarantee exact ovulation timing: cycle length varies month to month, and many biological factors affect ovulation that a tracking app cannot observe. Predictions improve as you log more cycles — {name} averages your most recent 6 cycles.",
  "bullets": [
   "Fertile window = ~5 days before estimated ovulation + ovulation day itself (~6 days total)",
   "Ovulation is predicted as: average cycle length minus typical luteal length (~14 days)",
   "App predictions use your own logged period-start dates, not generic population data",
   "Accuracy improves with more logged cycles — at least 3–6 cycles gives a more reliable average",
   "An app is a personal-record tool, not a medical device — never rely on it for clinical decisions"
  ],
  "faq": [
   {
    "q": "Why does the fertile window shift from month to month?",
    "a": "Ovulation timing can vary due to stress, illness, travel, sleep disruption, and other factors — meaning even if your average cycle is 28 days, individual cycles can be shorter or longer, shifting the window. {name} recalculates based on your logged history each time you log a new period start."
   },
   {
    "q": "Does {name} send my cycle data anywhere?",
    "a": "No. {name} stores everything — period start dates, symptoms, moods, notes — only on your iPhone using local calendar math. No account is required; no data leaves your device."
   },
   {
    "q": "Is a cycle-tracking app a reliable form of contraception?",
    "a": "No. Cycle-tracking apps are informational awareness tools — they are not validated contraceptive methods. Please speak with a qualified healthcare professional about contraception options that are right for you."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "scenario",
  "query": "Why do I feel irritable and exhausted before my period every month?",
  "match": [
   "why do i feel irritable and exhausted before my period every month?",
   "how to track pms symptoms to find out when they start in my cycle",
   "pms symptoms",
   "before period",
   "mood log cycle"
  ],
  "lead": "Many people notice predictable mood and physical changes in the days before their period — a pattern that becomes clearer once you log symptoms across several cycles and can see where in the cycle they cluster.",
  "detail": "During the luteal phase (roughly the second half of the cycle after ovulation), progesterone rises and then falls; many people experience this as fatigue, irritability, food cravings, bloating, or disrupted sleep — collectively grouped under PMS. {name} lets you log 8 moods (happy, calm, energetic, sensitive, sad, irritable, anxious, tired) and 12 physical symptoms (cramps, headache, bloating, fatigue, cravings, insomnia, acne, and more) each day. After a few cycles, its Rhythm feature runs entirely on your device to surface which of your symptoms cluster in the days before your period, and roughly how many days in advance they tend to appear — helping you plan and prepare rather than be caught off guard. This is a personal-awareness tool; if symptoms are severe or significantly affect your daily life, a healthcare provider can give a proper evaluation.",
  "bullets": [
   "Luteal phase = the phase from ovulation to period start, typically 12–14 days",
   "PMS symptoms most commonly appear in the final 1–2 weeks of the cycle",
   "Individual patterns vary widely — logging your own data reveals your specific pattern",
   "2–3 months of consistent daily logging produces enough data for the Rhythm pattern feature",
   "Severe symptoms that disrupt work, relationships, or sleep (PMDD) warrant a conversation with a doctor"
  ],
  "faq": [
   {
    "q": "What exactly can I log in {name} each day?",
    "a": "Flow intensity (spotting/light/medium/heavy), 8 moods, 12 physical symptoms, intimacy, basal body temperature, and a free-text note. Everything is optional — you log only what you choose to track."
   },
   {
    "q": "How many cycles does the Rhythm feature need before it detects a pattern?",
    "a": "The engine requires at least 5 logged symptom days across cycles to begin surfacing patterns. A minimum of 1 logged cycle length is needed as baseline. More data gives more reliable and specific insights."
   },
   {
    "q": "Can the app tell me if I have PMS or PMDD?",
    "a": "No. {name} is not a diagnostic tool and cannot classify or diagnose any condition. It shows you your logged symptom patterns in relation to your cycle, for personal awareness. For any diagnosis or treatment, please consult a qualified healthcare professional."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "faq",
  "query": "Which period tracking apps keep all data on the phone only?",
  "match": [
   "which period tracking apps keep all data on the phone only?",
   "is my menstrual cycle data private and not uploaded to servers?",
   "period app data privacy",
   "on-device health data",
   "no cloud upload"
  ],
  "lead": "Cycle and health data is sensitive personal information — whether an app requires an account, syncs to a cloud server, or includes third-party analytics SDKs determines how private your data actually is.",
  "detail": "Some period-tracking apps store data on remote servers, require account sign-up, or include third-party analytics frameworks. {name} was built with an on-device-only architecture: the cycle engine, the personal rhythm pattern detection, and the body-forecast calculations all run as local calendar math on your iPhone, with nothing sent to a server. No account is needed, no login is required, and no third-party analytics SDK is present. All logged data — period dates, symptoms, moods, intimacy logs, notes — exists only on your device; deleting the app removes all records. Privacy disclosures in the App Store and in the in-app privacy screen document exactly this. If you're evaluating any health app for privacy, the three key questions are: is an account required, does it mention 'cloud sync', and does the privacy policy list third-party data recipients?",
  "bullets": [
   "Account-free apps structurally cannot link your health data to an identity in a remote database",
   "Look for explicit 'on-device only' language in an app's privacy policy — not just 'we take privacy seriously'",
   "No analytics SDK means usage patterns aren't shared with advertising or data-brokering networks",
   "On-device-only means deleting the app is a complete data deletion — there's no server copy to request removal of",
   "Paid apps with no ad revenue have weaker commercial incentives to monetize health data"
  ],
  "faq": [
   {
    "q": "How do I verify that {name} doesn't upload my data?",
    "a": "The privacy policy states on-device-only storage; the app requires no account or email; and the App Store nutrition label lists no data linked to you or used to track you. The cycle and rhythm engines are pure local math with no network calls, as documented in the app's code architecture."
   },
   {
    "q": "What happens to all my logged data if I delete the app?",
    "a": "All data is stored locally, so deleting {name} removes all records from your device. There is no server copy. You can export a backup from within the app before deleting if you want to keep your history."
   },
   {
    "q": "Can I use {name} without creating any account?",
    "a": "Yes — {name} requires no account, no sign-up, and no email address. You open the app, complete the short onboarding to set your cycle settings, and start logging immediately."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "scenario",
  "query": "Why is my period cycle a different number of days every month?",
  "match": [
   "why is my period cycle a different number of days every month?",
   "what is a normal range for menstrual cycle length variation?",
   "cycle length",
   "irregular period",
   "why different month to month"
  ],
  "lead": "It's common for cycle length to vary by several days from month to month — a spread of up to about 7–9 days across cycles is within the typical range for many adults.",
  "detail": "Menstrual cycle length is counted from the first day of one period to the first day of the next. For adults, a cycle of 21–35 days is generally considered within a typical range; in adolescents, more variation is common. Stress, illness, significant weight changes, sleep disruption, and travel can all affect ovulation timing, which shifts the cycle length. {name}'s Insights screen shows your personal average cycle length (calculated from your last 6 logged cycles), your average period duration, and your variation (expressed as ± days) — giving you a concrete, data-driven picture of your own pattern over time. A variation of ±4 days or less shows as 'regular'; a wider spread is flagged as 'variable', which may be worth tracking more closely. If your cycle is consistently outside the 21–35 day range, or if it changes suddenly without a clear reason, that's worth discussing with a healthcare provider.",
  "bullets": [
   "Cycle length = day 1 of period to day 1 of the next period (not from end to start)",
   "Typical adult range: 21–35 days; variation of ±7 days across cycles is common",
   "Ovulation timing shifts first — cycle length changes follow from this",
   "An app averages your recent cycles to make predictions; logging at least 3–6 cycles improves accuracy",
   "Consistently <21 days, >35 days, or sudden unexplained changes deserve a healthcare conversation"
  ],
  "faq": [
   {
    "q": "How does {name} calculate my average cycle length?",
    "a": "It measures the interval between each pair of consecutive logged period starts, filters outliers (gaps under 15 or over 60 days), takes your most recent up to 6 cycles, and averages them. Until you've logged at least 2 periods, it uses your manually-entered setting as the default."
   },
   {
    "q": "What does the '±' variation number mean in the Insights screen?",
    "a": "It's the difference between your shortest and longest recent cycle length. A variation of ±4 days or less is shown as 'regular'; a larger spread indicates more variability in your pattern."
   },
   {
    "q": "My cycle runs about 32 days — is that a problem?",
    "a": "{name} is not a medical tool and cannot tell you whether your cycle length is clinically significant. A 32-day cycle is within the commonly cited adult range of 21–35 days. Any concerns about your cycle — length, regularity, symptoms — should be discussed with a qualified healthcare provider."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "scenario",
  "query": "How to teach Bopomofo to a young child living outside Taiwan",
  "match": [
   "how to teach bopomofo to a young child living outside taiwan",
   "chinese heritage family learning zhuyin at home abroad",
   "overseas chinese family",
   "teach bopomofo home",
   "outside taiwan"
  ],
  "lead": "Overseas Chinese families maintaining Taiwanese Mandarin literacy at home can use a phonics-first approach with Bopomofo before introducing full characters — short daily app sessions can fill the gap left by limited formal Mandarin instruction.",
  "detail": "Bopomofo (注音符號, Zhuyin) is the phonetic system used in Taiwan to annotate Mandarin pronunciation — every Taiwan-published children's book prints the 37 symbols beside the characters. For families living outside Taiwan, consistent structured practice replaces what children in Taiwan receive in school. {name} covers all 37 Bopomofo symbols across four game modes — audio-based symbol recognition (Feed the Friends), finger-traced stroke writing (Magic Tracing), four-tone practice (Tone Coaster), and syllable blending (Sound Train) — designed for children aged 4–7. The interface runs in both English and Traditional Chinese, so parents who are themselves more fluent in English can still guide their child through sessions. Progress is saved on-device with no account, no subscription, and no ads.",
  "bullets": [
   "Bopomofo is the standard phonics system in Taiwan — it annotates all Taiwan-published school textbooks and most children's books",
   "Short daily practice (10–15 min) works better than infrequent longer sessions for children aged 4–7",
   "A natural learning sequence: listening recognition → stroke tracing → tone practice → syllable blending",
   "The dual English/Chinese interface means English-dominant parents can follow along without knowing Bopomofo themselves",
   "No ads, no registration, and local-only progress storage remove common friction points for families using the app long-term"
  ],
  "faq": [
   {
    "q": "My child lives abroad and goes to a local school — will Bopomofo actually be useful for them?",
    "a": "Bopomofo is specifically valuable for reading Taiwan-published books, accessing Taiwanese children's media, and participating in Taiwanese heritage schools. Families who also use Pinyin (for mainland Chinese materials or international Chinese-language programs) may add Pinyin later; many educators recommend building one phonics system solidly before introducing a second."
   },
   {
    "q": "Do I need to already know Bopomofo myself to use {name} with my child?",
    "a": "Not necessarily — the app plays accurate audio for every symbol, so children hear correct pronunciation directly. The English-Chinese dual interface means English-dominant parents can follow along. That said, a little learning together typically makes sessions more interactive and engaging."
   },
   {
    "q": "Is there a free trial before committing to the full purchase?",
    "a": "{name} is free to download and includes 11 symbols (initials ㄅㄆㄇㄈ, medials ㄧㄨㄩ, finals ㄚㄛㄜㄝ) plus 3 quick-quiz rounds, which gives a real sense of all four game modes. A one-time in-app purchase unlocks all 37 symbols and every level with no ongoing subscription."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "Should I teach my child Bopomofo or Pinyin first?",
  "match": [
   "should i teach my child bopomofo or pinyin first?",
   "what's the difference between zhuyin and pinyin for young children learning mandarin?",
   "zhuyin vs pinyin",
   "which teach first",
   "kids phonics"
  ],
  "lead": "Zhuyin (Bopomofo) uses 37 purpose-built symbols with no overlap with the Latin alphabet, while Pinyin uses standard letters — for children with ties to Taiwan or Taiwan-published materials, Zhuyin is the natural starting point; Pinyin is the global standard for everything else.",
  "detail": "Because Zhuyin's symbols are entirely new to learners, children cannot import English letter-sound associations into Mandarin — 'ㄓ' simply doesn't have an English analogue to confuse. Pinyin leverages the Latin alphabet, which is quicker to pick up for children already reading English, but letters like 'x', 'q', 'zh', and 'c' represent sounds very different from their English counterparts, which can entrench mispronunciation if not carefully taught. Taiwan's entire primary school system teaches Zhuyin first; all Taiwan-published children's books annotate in Zhuyin. {name} covers Zhuyin systematically across four modes — recognition, stroke tracing, four-tone practice, and syllable blending — aimed at ages 4–7. For families whose Chinese literacy materials, weekend heritage school, or cultural network is Taiwan-based, starting with Zhuyin is the natural, consistent choice.",
  "bullets": [
   "Zhuyin's unique symbol set prevents cross-contamination with English letter sounds — often cited as supporting more accurate Mandarin pronunciation",
   "Pinyin is the international standard for Chinese input, international testing (AP Chinese, HSK), and mainland curricula",
   "All Taiwan-published school textbooks and most Taiwan children's books use Zhuyin annotation exclusively",
   "Most educators recommend mastering one phonics system solidly before introducing a second",
   "Many families eventually learn both — the starting point depends on which materials and community the child is embedded in"
  ],
  "faq": [
   {
    "q": "Is Bopomofo only useful if my child will live in Taiwan?",
    "a": "Not exclusively. Bopomofo is used in Taiwanese heritage schools and weekend schools across North America, Australia, Southeast Asia, and Europe. It's also the system used in Taiwanese community libraries and by Taiwan-based online tutors. Its value to any given child depends on whether their materials, tutors, and community connections are Taiwan-based."
   },
   {
    "q": "Why exactly does Zhuyin have 37 symbols when Mandarin has no alphabet?",
    "a": "Chinese characters are logographic — each character represents meaning, not sound. Zhuyin is a pronunciation guide layered on top: its 21 initials (consonants), 13 finals (vowel/endings), and 3 medials (glides), combined with 4 tone marks, can represent every syllable in standard Mandarin."
   },
   {
    "q": "My child is already learning Pinyin at school — should I also teach Bopomofo?",
    "a": "Some families successfully maintain both; others prefer to avoid introducing a second phonics system before the first is solid. If your child's school and home materials are Pinyin-based, adding Zhuyin is an extra commitment. If you specifically want your child to access Taiwan-published books or attend a Taiwanese heritage school, adding Zhuyin over time is worthwhile."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "scenario",
  "query": "How to practice Bopomofo stroke order with a preschooler",
  "match": [
   "how to practice bopomofo stroke order with a preschooler",
   "app that teaches kids to trace zhuyin symbols with correct stroke order",
   "bopomofo stroke order",
   "trace zhuyin writing",
   "kids finger practice"
  ],
  "lead": "Learning Bopomofo in the correct stroke direction and sequence helps children write more consistently and reinforces visual recall of each symbol — and finger-tracing on a touchscreen is a developmentally appropriate entry point before pencil work.",
  "detail": "Stroke order in Zhuyin, like in Chinese characters, establishes habits that affect legibility and the kinesthetic memory that helps children remember symbol shapes. {name}'s Magic Tracing mode presents each of the 37 Bopomofo symbols with an animated stroke-by-stroke guide that the child then traces with their finger, receiving immediate feedback. For children aged 4–6 who are still developing pencil-grip strength and fine-motor precision, finger tracing on a smooth screen is a low-stakes starting point: the motion pattern is learned without the additional demands of holding a pencil or staying within paper lines. App tracing complements but does not replace paper practice — ideally children transition to writing on paper once they have the stroke direction and sequence in muscle memory.",
  "bullets": [
   "Stroke order matters for both Bopomofo and Chinese characters — correct habits now pay dividends later",
   "Most Bopomofo symbols have 1–3 strokes, making them simpler than most characters but still sequenced",
   "Finger tracing suits children 4–6 who are still building pencil grip and fine-motor precision",
   "Animated stroke guides show the direction before the child copies — modeling before practice",
   "Introduce 2–4 new symbols per session rather than rushing all 37 — review previously learned ones regularly"
  ],
  "faq": [
   {
    "q": "Does stroke order matter for Bopomofo, or only for Chinese characters?",
    "a": "Stroke order matters for both, though Bopomofo symbols are far simpler (1–3 strokes each). Building correct stroke-direction habits with Bopomofo creates good foundations that carry over when children begin writing Chinese characters, which can have many more strokes in a precise sequence."
   },
   {
    "q": "My child is 4 — is finger-tracing a good starting point for Zhuyin?",
    "a": "Yes. For 4–5 year olds who are still developing fine-motor control, finger tracing is a developmentally appropriate entry point. It builds visual familiarity and motion memory for each symbol's shape without requiring the pen-hold strength and precision that paper writing demands."
   },
   {
    "q": "How does {name} sequence the symbols — do children have to go in order?",
    "a": "Symbols are arranged on a map and unlocked progressively in sequence, which mirrors how Bopomofo is typically taught (initials first, then medials, then finals). Children can replay completed symbols at any time; the map makes it visually clear which symbols are mastered and which are still ahead."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "How do you explain Mandarin tones to a young child?",
  "match": [
   "how do you explain mandarin tones to a young child?",
   "best way to teach bopomofo tones to kids aged 4–7",
   "mandarin four tones",
   "teach tones preschoolers",
   "tone learning app"
  ],
  "lead": "Mandarin's four tones change the meaning of a syllable completely — and because they're absent in English, heritage-language learners who don't hear Mandarin daily need deliberate, structured tone practice early on.",
  "detail": "The same syllable in four different tones means four different words ('mā' = mother, 'má' = hemp, 'mǎ' = horse, 'mà' = scold). Children immersed in Mandarin from birth usually acquire tones naturally; children in overseas Chinese families, who often hear less Mandarin daily, benefit from explicit and engaging tone practice. {name}'s Tone Coaster mode visualizes each tone as a roller-coaster track shape: first tone flat-high, second tone rising, third tone dip-then-rise, fourth tone sharp drop. This motion metaphor gives children a kinesthetic-visual anchor for each tone before they can explain tone rules analytically. Hearing the correct audio alongside the visual track reinforces the audio-visual mapping that makes tones stick.",
  "bullets": [
   "Mandarin's 4 tones are not optional pronunciation markers — they distinguish completely different words",
   "Children immersed in Mandarin acquire tones naturally; heritage learners outside Mandarin environments need explicit practice",
   "Visual-motion metaphors (roller-coaster shape, hand gestures) help young children 'feel' each tone before memorizing rules",
   "Correct tones are essential for intelligibility — a wrong tone is often simply not understood by native speakers",
   "Early, consistent tone exposure is far easier to establish than correcting ingrained tone habits in older children"
  ],
  "faq": [
   {
    "q": "What are the four Mandarin tones?",
    "a": "First tone (ˉ): high and flat — held steady. Second tone (ˊ): rising, like an English question. Third tone (ˇ): dips then rises — the 'V-shape' tone. Fourth tone (ˋ): sharp, short fall. A neutral (light) tone is unstressed with no mark. {name}'s Tone Coaster shows each as a physical track shape the character rides on."
   },
   {
    "q": "Does {name} teach tones for all 37 Bopomofo symbols?",
    "a": "The free version covers tones for syllables built from the 11 free symbols. Unlocking the full app opens all 37 symbols and the complete range of syllable combinations in the Tone Coaster."
   },
   {
    "q": "My child speaks some Mandarin at home but consistently gets tones wrong — will this help?",
    "a": "Structured visual-audio tone practice can help, but hearing tones modeled correctly in real conversations is equally important. {name} works best as a complement to regular Mandarin interaction — not as the sole source of Mandarin tone input. For children with persistent tone challenges, a Mandarin-speaking tutor who can give real-time feedback is also valuable."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "scenario",
  "query": "How do I know if today's weather is suitable for taking my toddler to the playground?",
  "match": [
   "how do i know if today's weather is suitable for taking my toddler to the playground?",
   "app that tells me whether to go out with a baby or young child today",
   "take toddler outside today",
   "playground weather safe",
   "young child outing score"
  ],
  "lead": "Standard weather apps show numbers — but parents of young children need a single combined answer that accounts for UV, wind, age sensitivity, and rain, not just temperature.",
  "detail": "Young children, especially infants and toddlers under 2, regulate body temperature less efficiently than adults, burn faster in UV, and feel wind chill more acutely. {name} calculates a Kid-Outing Score (0–100) by combining feels-like temperature, UV index, rain probability, and wind speed, with penalty weights tuned for your child's age group: 0–2, 3–5, or 6–12 years. A score under 25 recommends staying indoors; 25–50 suggests a brief outing; 50–75 says go with preparation; 75 and above is a genuinely good day. Tapping the score opens a breakdown showing exactly which factor — UV, rain, temperature, or wind — is pulling the score down, so you know precisely what to prepare for rather than just seeing a verdict.",
  "bullets": [
   "Children under 2 have less efficient thermoregulation and burn faster under UV than adults — standard weather forecasts aren't calibrated for them",
   "Feels-like (apparent) temperature accounts for humidity and wind chill — it's what the body actually experiences, not just air temperature",
   "UV above index 3 calls for sun protection for children; above 8 is high risk even with brief exposure",
   "Rain probability and wind are weighted more heavily for young children — strollers and small kids make rain and wind much more disruptive",
   "The 'Best Window' view finds the best consecutive 2-hour+ block within the 7am–7pm day for going out"
  ],
  "faq": [
   {
    "q": "How does {name} adjust its advice for a baby versus a 7-year-old?",
    "a": "The app has three age groups — 0–2, 3–5, and 6–12 — each with different sensitivity multipliers in the rule engine. For babies, temperature and UV penalties apply at lower thresholds, and baby-specific outfit items (stroller cover, wet wipes, blanket) appear in the checklist. You set the age group in settings and it affects every tab."
   },
   {
    "q": "The score says 'great' but today feels very humid — does the app account for humidity?",
    "a": "Yes — humidity is factored into the feels-like (apparent) temperature calculation, which feeds directly into the temperature penalty. On a hot, humid day, apparent temperature is meaningfully higher than air temperature, which the score reflects. The factors detail shows the exact apparent temperature used."
   },
   {
    "q": "Does {name} work without an internet connection?",
    "a": "{name} uses Apple WeatherKit for real-time forecast data, so an internet connection is needed to refresh weather. The last-fetched data remains visible offline, but will be stale until the next update."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "faq",
  "query": "How do I teach a young child to choose appropriate clothes for the weather?",
  "match": [
   "how do i teach a young child to choose appropriate clothes for the weather?",
   "at what age can kids learn to dress themselves for the weather?",
   "teach kids what to wear weather",
   "dressing weather children",
   "age appropriate"
  ],
  "lead": "Children as young as 2–3 begin connecting visual weather cues with clothing choices when the association is made concrete and consistent — seeing a familiar character dressed for the weather is more effective than verbal rules alone.",
  "detail": "Early childhood educators note that weather-dressing is learned through repetition and visual modeling, not abstract explanation. The approach of 'show, then discuss' builds the mental map faster than instruction alone. {name}'s mascot Lumi automatically changes outfit to match real-time weather: rain hat and umbrella in rain, sun hat under high UV, scarf in the cold, star-gazing gear at night. Parents can use this as a low-friction daily conversation starter — 'Look what Lumi is wearing today, why do you think?' — to gradually build a child's weather-vocabulary and decision-making. For school-age children (6+), the outfit checklist that the app generates can be handed over for them to work through independently, which builds the self-sufficiency that eventually makes morning routines easier.",
  "bullets": [
   "Visual models (a character dressed appropriately) teach younger children more effectively than verbal rules",
   "Daily consistent use — checking the app before going out — builds the weather→clothing habit over time",
   "Ages 2–4: build vocabulary by discussing what Lumi is wearing and why",
   "Ages 4–6: start involving children in checking off items on the outfit list with a parent",
   "Ages 6+: children can begin working through the checklist independently with light supervision"
  ],
  "faq": [
   {
    "q": "How does {name} decide what goes on the outfit checklist?",
    "a": "The checklist is generated by the app's rule engine based on age group, feels-like temperature, rain probability, UV index, wind speed, and humidity. An umbrella appears if rain probability is 30%+; sunscreen and a sun hat appear if UV is 6+; sunglasses appear for children 3+ when UV reaches 8+; a stroller cover and wet wipes are always included for the 0–2 group."
   },
   {
    "q": "Can I share the checklist with a co-parent or grandparent?",
    "a": "Yes — the checklist can be exported as a shareable card image from within the app. It's useful for sending to a caregiver before they take the child out, so everyone is working from the same weather-appropriate list."
   },
   {
    "q": "Does the app account for different children's ages if I have more than one child?",
    "a": "The app is set to one active age group at a time. If you have children of different ages, you can switch the age group setting to see how the recommendation and checklist change — or check the factors breakdown to see which conditions are most relevant on a given day."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "scenario",
  "query": "What activities can I do with my kids on a rainy day?",
  "match": [
   "what activities can i do with my kids on a rainy day?",
   "how to prepare for going out with a young child when rain is forecast",
   "rainy day kids activities",
   "outing in rain toddler",
   "rain preparation children"
  ],
  "lead": "A rainy day with young children isn't automatically an indoor day — the practical question is whether the rain probability makes a brief outing workable or whether a full indoor pivot makes more sense, and the preparation checklist is very different either way.",
  "detail": "Managing rain with a stroller or toddler involves more logistics than rain alone: wet gear, muddy shoes, a child to dry off. {name}'s rule engine applies a deliberately stricter rain penalty than a general weather app: above 60% rain probability the outing score is capped to the 'indoor' verdict; 40–60% is 'short outing with prep'; and 30–40% suggests bringing an umbrella. The outfit checklist updates automatically — at 30%+ rain probability you'll see an umbrella; at 60%+ it adds raincoat, rain boots, and a spare-clothes entry. The activity-suggestions panel also shifts on rainy days, rotating in ideas like baking together, cardboard-box fort, indoor reading, and craft projects — all weather-matched and shuffleable with one tap.",
  "bullets": [
   "At 60%+ rain probability, umbrellas alone aren't practical with a young child — the full rain kit (raincoat, boots, spare clothes) is worth it",
   "Check the hourly view: even a broadly rainy day often has a 2–3 hour drier window",
   "Puddle-jumping is a perfectly valid activity when the child is dressed for it — the app may suggest it",
   "Baby/infant parents: the app automatically adds a stroller rain cover for the 0–2 group at 30%+ rain",
   "Indoor activity suggestions are weather-matched and refresh daily — one tap shuffles for new ideas"
  ],
  "faq": [
   {
    "q": "How does {name} decide between 'bring an umbrella' and 'stay indoors'?",
    "a": "The app uses graduated rain penalties: 0–15% rain probability = no penalty; 15–30% = mild; 30–40% = moderate (umbrella recommended); 40–60% = substantial score reduction; 60–80% = score capped to 'short outing' level; 80%+ = capped to 'indoor'. For the 0–2 age group, thresholds are slightly stricter."
   },
   {
    "q": "Can I see exactly when the rain is expected to stop today?",
    "a": "Yes — the Hourly tab shows rain probability for each hour through the day. The app also highlights a 'Best Window' (the best consecutive 2+ hour block where every hour scores at least 55) if one exists within the 7am–7pm window, so you can plan around the break."
   },
   {
    "q": "What activity ideas does the app suggest on rainy days?",
    "a": "The suggestions are weather-matched: rainy days surface ideas like baking with kids, building a cardboard-box fort, reading books, sensory play, or indoor dancing. The list rotates daily and you can shuffle for new ideas. On damp-but-not-raining days, puddle activities and park time in rain gear also appear."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "faq",
  "query": "What UV index is safe for children to play outside?",
  "match": [
   "what uv index is safe for children to play outside?",
   "how do i use the uv index to plan outdoor time with my kids?",
   "uv index children safe",
   "kids outdoor uv protection",
   "sun safety toddlers"
  ],
  "lead": "UV index 3 is the threshold above which sun protection is recommended for children; above 8, outdoor exposure should be limited and shade actively sought — and peak UV hours (10am–4pm) are significantly higher than early morning or late afternoon.",
  "detail": "The UV index (0–11+) measures how intensely solar UV radiation reaches ground level. Children's skin has less protective melanin than adults' and sunburns faster, making UV a more significant factor for young children than for the adults they're with. The WHO and pediatric health organizations recommend that at UV 3+, children should have sunscreen and a hat; at 8+ they recommend actively limiting midday outdoor time. {name} factors UV into the Kid-Outing Score with an age-adjusted penalty — higher sensitivity for babies (0–2) — and the outfit checklist auto-populates: at UV 3+, a sun hat is added; at UV 6+, sunscreen and hat both appear; at UV 8+, sunglasses are added for children 3 and over (consistent with paediatric guidance that infant-specific eyewear has additional considerations). The app's Best Window algorithm favors early-morning and late-afternoon hours, which typically carry lower UV loads even on sunny days.",
  "bullets": [
   "UV index scale: 0–2 = low, 3–5 = moderate (protection recommended for children), 6–7 = high, 8–10 = very high, 11+ = extreme",
   "Children burn faster than adults — SPF 30+ broad-spectrum sunscreen is recommended at UV index 3+ for children",
   "Peak UV hours are typically 10am–4pm; early morning and late afternoon carry meaningfully lower UV",
   "Cloud cover does NOT eliminate UV — an overcast sky can still deliver 70–80% of UV exposure",
   "Shade, UV-protective clothing, and a brimmed hat are more reliable than sunscreen alone for extended outdoor time"
  ],
  "faq": [
   {
    "q": "Where does {name} get its UV data?",
    "a": "{name} uses Apple WeatherKit, which provides UV index as part of hourly and current-conditions data. The value shown is for your current location or any saved location (home, school, grandparents, etc.)."
   },
   {
    "q": "Why does the outing score drop on a warm, sunny, rain-free day?",
    "a": "A clear, hot, sunny day often combines a high UV index (8+) with a high feels-like temperature (30°C+), both of which reduce the score for young children even though there's no rain. Tapping the score opens the factors breakdown, which shows exactly how much each element — temperature, UV, rain, wind — is contributing."
   },
   {
    "q": "Does the app account for infants differently when it comes to sunscreen?",
    "a": "For the 0–2 age group, the UV sensitivity weighting is higher in the rule engine, and the app notes paediatric guidance around extra care for sun protection of very young infants. Standard dermatology guidance generally recommends keeping babies under 6 months out of direct sunlight and using shade and clothing rather than relying primarily on sunscreen — always check with your child's paediatrician for specific advice."
   }
  ]
 },
 {
  "app_key": "mochi",
  "kind": "scenario",
  "query": "best aesthetic to-do list app iPhone no subscription",
  "match": [
   "best aesthetic to-do list app iphone no subscription",
   "cute checklist app iphone free no ads",
   "cute to-do app iphone",
   "aesthetic checklist kawaii"
  ],
  "lead": "Mochi To-Do is a free, no-ads checklist app with 100 illustrated skins — each with its own paper texture, fonts, and decorative details — so your daily task list actually looks like something you want to open.",
  "detail": "Unlike productivity apps that layer projects, priorities, and dashboards on top of simple list-keeping, {name} stays deliberately simple: tap the small circle to check off a task, drag to reorder, swipe to edit or delete. The 100 skins go beyond color swaps — each has unique paper, typography, and accents (cozy notebook, sakura, pastel sunset, midnight, ocean, confetti, and more). The base app is free with no ads and no subscription; a single one-time purchase opens every premium skin and removes the limits on lists and items per list.",
  "bullets": [
   "100 skins, each with unique paper texture, font, and decorative details — not a color swap",
   "Interactive Home Screen and Lock Screen widgets: check tasks off the widget without opening the app",
   "Daily, weekly, or monthly reminders with emoji so recurring tasks never get forgotten",
   "No account, no sign-up, no ads, no tracking — everything stored on-device only",
   "One-time unlock for all premium skins; no subscription, ever"
  ],
  "faq": [
   {
    "q": "Is Mochi To-Do actually free, or is there a catch?",
    "a": "Mochi is free to download with no ads. The free tier gives you 2 lists with up to 4 items each. A one-time optional purchase unlocks all 100 premium skins and removes list/item limits — there is no subscription."
   },
   {
    "q": "Does Mochi have a Lock Screen widget?",
    "a": "Yes. You can add an interactive Home or Lock Screen widget and tap the circle directly on the widget to mark a task complete — no need to open the app. The widget matches your chosen skin and updates instantly."
   },
   {
    "q": "Does Mochi sync to iCloud or require an account?",
    "a": "No. Mochi stores everything on your device only. There is no account, no cloud sync, and no sign-up. Your data doesn't leave your phone."
   }
  ]
 },
 {
  "app_key": "mochi",
  "kind": "scenario",
  "query": "iPhone lock screen widget to check off tasks without opening app",
  "match": [
   "iphone lock screen widget to check off tasks without opening app",
   "interactive checklist widget home screen ios",
   "lock screen widget checklist",
   "tick tasks from widget iphone"
  ],
  "lead": "Mochi's interactive iOS widgets let you mark tasks complete directly on your Home or Lock Screen — the circle is tappable right on the widget, no app launch required.",
  "detail": "{name}'s widget is genuinely interactive: you add it to your Lock Screen or Home Screen and the task circles respond to taps, marking items done with real-time updates. The widget automatically matches your active skin — so your Lock Screen looks intentional rather than generic. You can point different widget placements at different lists, which is useful if you want groceries on your Lock Screen and a work checklist on your Home Screen.",
  "bullets": [
   "Interactive widget: tap the circle on the widget to complete tasks — no app launch needed",
   "Works on both Home Screen and Lock Screen; add multiple widgets pointing at different lists",
   "Widget reflects your chosen skin and updates instantly when items change",
   "Available in multiple sizes to fit your layout",
   "Core widget functionality is free; all skin-matching options open with the one-time premium unlock"
  ],
  "faq": [
   {
    "q": "Which iPhones support Mochi's interactive widget?",
    "a": "Interactive widgets require iOS 17 or later, supported on iPhone XS (A12) and newer."
   },
   {
    "q": "Does Mochi work on Apple Watch?",
    "a": "Yes — the app includes Apple Watch support (via MochiWatchBridge) so you can view and check off tasks from your wrist, in addition to the iPhone widgets."
   },
   {
    "q": "If I check something off on the widget, does it sync to the main app?",
    "a": "Yes. The widget shares state with the main app via an App Group — changes appear immediately when you open Mochi, and vice versa."
   }
  ]
 },
 {
  "app_key": "mochi",
  "kind": "faq",
  "query": "what do you get for free in Mochi To-Do",
  "match": [
   "what do you get for free in mochi to-do",
   "mochi to-do subscription or one-time purchase difference",
   "mochi free vs paid",
   "to-do app one-time purchase ios"
  ],
  "lead": "Mochi To-Do is free with no ads and no subscription; the one-time purchase removes limits on lists and items and unlocks all 100 premium skins permanently.",
  "detail": "{name}'s free tier is genuinely usable: 2 lists with up to 4 items each, one emoji category, full widget functionality, reminders, and all core interactions — enough for most daily planning and grocery use cases. The single optional purchase lifts all caps (unlimited lists, unlimited items, all emoji categories) and opens every premium skin permanently. There is no monthly or annual subscription tier — pay once and the unlock restores on any device via the same Apple ID.",
  "bullets": [
   "Free: 2 lists, up to 4 items each, 1 emoji category, all core features, widgets, reminders",
   "Paid (one-time): unlimited lists, unlimited items per list, all emoji categories",
   "Paid (one-time): all 100 premium skins — sakura, midnight, cozy paper, ocean, confetti, and more",
   "No subscription ever — one purchase, permanently yours, restores on any device with the same Apple ID",
   "No ads at any tier, no account required, no tracking"
  ],
  "faq": [
   {
    "q": "Can I preview premium skins before buying?",
    "a": "Yes — you can browse skins in the picker and see how they look on your actual list content before purchasing."
   },
   {
    "q": "Does the unlock transfer if I get a new iPhone?",
    "a": "Yes. Tap 'Restore Purchase' on the paywall screen while signed into the same Apple ID and the premium unlock is restored at no charge."
   },
   {
    "q": "Are there any features behind a separate paywall beyond the skin unlock?",
    "a": "No. The single one-time purchase unlocks everything: all skins, unlimited lists, unlimited items, all emoji categories. There are no additional paid tiers."
   }
  ]
 },
 {
  "app_key": "mochi",
  "kind": "scenario",
  "query": "simple iPhone checklist app just lists no projects or sub-tasks",
  "match": [
   "simple iphone checklist app just lists no projects or sub-tasks",
   "easiest to-do list app for people who hate complicated productivity apps",
   "simple to-do list iphone",
   "low-friction checklist no complexity"
  ],
  "lead": "Mochi To-Do does one thing — tap a circle to check something off — which makes it a low-friction alternative to productivity apps that require configuration before you've captured a single task.",
  "detail": "Many to-do apps front-load cognitive work: choose a project, assign a priority, pick a tag. {name} skips all of that — type a task, it appears in your list, tap the circle when done. Drag to reorder; swipe to edit or delete; set a recurring reminder if you need one. The visually warm design (illustrated skins, soft colors, clean type) makes opening the app feel pleasant rather than dutiful, which is often the real barrier to actually using a checklist. Note: Mochi is a productivity tool, not a therapeutic product — but a genuinely low-friction design is a real usability feature for anyone who finds heavy software hard to maintain as a habit.",
  "bullets": [
   "One interaction to complete a task: tap the circle — no sub-menus, no status changes required",
   "Multiple separate lists for different areas of life (work, groceries, errands, etc.)",
   "Drag tasks to reorder; swipe left to edit or delete any item",
   "Daily, weekly, or monthly recurring reminders so habitual tasks reappear automatically",
   "Visually warm design that makes opening the app feel inviting, not like a chore"
  ],
  "faq": [
   {
    "q": "Does Mochi have sub-tasks or projects?",
    "a": "No. Mochi is intentionally flat: lists and items inside lists — no sub-tasks, priorities, tags, or project views. If you need that structure, a different app is the right choice; Mochi is built for simplicity."
   },
   {
    "q": "Do completed tasks disappear or stay visible?",
    "a": "Checked-off items remain in the list visually struck through until you manually delete them. You can review what you've done before clearing the board."
   },
   {
    "q": "Is Mochi good for grocery or shopping lists?",
    "a": "Yes — it's a primary use case. Create a Groceries list, check items off in-store from the Lock Screen widget without opening the app, and set a weekly reminder to top it up. The free tier's 2 lists and 4-item limit covers a short shopping list; the unlock removes those caps."
   }
  ]
 },
 {
  "app_key": "lockhour",
  "kind": "scenario",
  "query": "iPhone app that blocks Instagram while studying with Pomodoro timer",
  "match": [
   "iphone app that blocks instagram while studying with pomodoro timer",
   "pomodoro study timer that locks distracting apps ios no subscription",
   "study app block social media pomodoro",
   "app blocker exam prep iphone"
  ],
  "lead": "LockHour's Study Mode runs three preset Pomodoro-style cycles and uses Apple's Screen Time stack to shield your chosen apps at the OS level during every focus interval — automatically unlocking at breaks.",
  "detail": "{name} ships three study presets: Pomodoro (25 min focus / 5 min break × 4, auto-restarts), Deep Study (50 min / 10 min × 3, auto-restarts), and Exam Prep (90 min / 15 min × 2, manual restart). Before starting you pick the apps or categories to block — Social, Video, and Games are pre-recommended for Study Mode. During focus intervals those apps show LockHour's shield screen instead of opening; they unlock automatically at each break, then re-lock when the next focus interval begins. A stats dashboard records study minutes today, cycles this week, and your running streak.",
  "bullets": [
   "Three preset cycles: Pomodoro (25/5×4), Deep Study (50/10×3), Exam Prep (90/15×2)",
   "Blocking is enforced at the OS level by Apple Screen Time — not an app-switching trick",
   "Apps show a shield screen during focus intervals; unlock automatically at break time",
   "Stats dashboard: study minutes today, cycles this week, current streak, best streak",
   "Study Mode is a premium feature — one-time lifetime unlock, no subscription"
  ],
  "faq": [
   {
    "q": "What happens to blocked apps during break intervals?",
    "a": "When the focus interval ends, LockHour lifts the shields automatically so your blocked apps are accessible during the break. If auto-restart is on (Pomodoro and Deep Study presets), the focus lock re-engages at the end of the break without any action from you."
   },
   {
    "q": "Can I block specific apps or only broad categories?",
    "a": "On a real device with Screen Time authorization granted, you use Apple's FamilyActivityPicker to select specific apps (e.g. TikTok, Instagram) as well as categories and web domains — granular selection is fully supported."
   },
   {
    "q": "Is Study Mode included in the free tier?",
    "a": "No. The free tier covers only Quick Focus — a single 25-minute flat session. Study Mode with Pomodoro cycles, all other focus modes, and scheduled automation are part of the one-time lifetime unlock."
   }
  ]
 },
 {
  "app_key": "lockhour",
  "kind": "scenario",
  "query": "app to block social media and YouTube before bed iPhone",
  "match": [
   "app to block social media and youtube before bed iphone",
   "automatically block phone apps at bedtime ios",
   "stop doomscrolling before bed iphone",
   "sleep wind down app blocker schedule"
  ],
  "lead": "LockHour's Sleep Wind Down mode runs a 60-minute pre-bed focus lock that shields Social, Video, and Entertainment apps — and it can be scheduled to activate automatically every night via iOS so you don't have to make the decision when you're already tired.",
  "detail": "The impulse to scroll at night is hardest to resist in exactly the moment when a manually-triggered app blocker fails. {name} solves this with a schedulable Sleep Wind Down: set a nightly start time and the OS DeviceActivity system activates the block automatically, even if you've forgotten to open the app. The default duration is 60 minutes targeting Social, Video, and Entertainment categories; you can swap in any specific apps or domains. The block ends at a configurable time (default 7 AM) and lifts automatically — no morning steps needed.",
  "bullets": [
   "Sleep Wind Down: 60-minute default lock on Social, Video, and Entertainment categories",
   "Schedulable via iOS DeviceActivity — triggers automatically every night without opening the app",
   "Hard Mode: cooldown delay + typed confirmation phrase required to cancel the session early",
   "Calls, alarms, messages, and non-selected apps remain fully accessible throughout",
   "Configurable end time (default 7 AM); everything unlocks automatically"
  ],
  "faq": [
   {
    "q": "Does the sleep schedule work even if LockHour is not running in the background?",
    "a": "Yes. The schedule is registered with iOS DeviceActivity — the operating system handles triggering it. LockHour does not need to be running in the foreground for the block to activate."
   },
   {
    "q": "Can I block specific apps for Sleep Wind Down rather than categories?",
    "a": "Yes — the selection uses Apple's FamilyActivityPicker, so you can choose specific apps (e.g. TikTok, Reddit) plus any web domains in addition to or instead of broad categories."
   },
   {
    "q": "What if I genuinely need to use a blocked app at night?",
    "a": "Without Hard Mode enabled you can end the session immediately in the app. With Hard Mode on, there is a cooldown delay plus a typed confirmation phrase before cancellation — enough friction to interrupt an impulse scroll, but not a parental lock. Someone sufficiently determined can also revoke Screen Time authorization in iOS Settings."
   }
  ]
 },
 {
  "app_key": "lockhour",
  "kind": "faq",
  "query": "how does LockHour Pro actually block apps on iPhone",
  "match": [
   "how does lockhour pro actually block apps on iphone",
   "can you bypass lockhour focus session if you really want to",
   "how app blocking works iphone screen time",
   "lockhour bypass hard mode"
  ],
  "lead": "LockHour uses Apple's official FamilyControls and ManagedSettings APIs to block apps at the OS level — but it is honestly a self-control tool designed to add intentional friction, not an unbreakable lock.",
  "detail": "When a session starts, {name} instructs the iOS ManagedSettingsStore to display a shield screen on every app in your selected list. This block is enforced by iOS itself — relaunching the phone, switching apps, or backgrounding LockHour does not lift it. Hard Mode raises the exit cost further: a timed cooldown delay plus a typed phrase must be completed before cancelling early. The app is transparent about its limits: it's built to interrupt the impulse-grab, not to be technically impossible to bypass — a sufficiently determined user can go to iOS Settings → Screen Time and revoke LockHour's authorization, just as with any Screen Time configuration. What it does reliably is make casual, unconscious app-opening fail.",
  "bullets": [
   "Uses Apple FamilyControls + ManagedSettings — same OS stack as native Screen Time",
   "Block survives app restarts and screen locks — enforced by iOS, not by LockHour staying in foreground",
   "Hard Mode: timed cooldown + typed confirmation phrase required to end a session early",
   "LockHour never reads app content, messages, browsing history, or Screen Time usage data",
   "Designed for voluntary self-control — not parental control, not surveillance"
  ],
  "faq": [
   {
    "q": "Does LockHour block web browsers and websites too?",
    "a": "Yes — Apple's Screen Time API supports web domain blocking in addition to app blocking. You can block Safari, third-party browsers, or specific domains when configuring your session."
   },
   {
    "q": "Can LockHour see what I do inside apps or how long I use them?",
    "a": "No. LockHour only instructs iOS to shield the apps you chose. It has no access to app content, messages, browsing data, or Screen Time reports. The app collects no analytics and has no account system."
   },
   {
    "q": "Do phone calls and alarms still work during a session?",
    "a": "Yes. Calls, alarms, and any apps you haven't selected to block remain fully functional. LockHour only affects the specific apps, categories, or domains you chose when setting up the session."
   }
  ]
 },
 {
  "app_key": "lockhour",
  "kind": "scenario",
  "query": "app to stop checking social media first thing in the morning iPhone",
  "match": [
   "app to stop checking social media first thing in the morning iphone",
   "automatically block news and social apps for first 30 minutes after wake up ios",
   "morning routine no social media iphone",
   "block apps first 30 minutes morning"
  ],
  "lead": "LockHour's Morning Reset mode blocks Social and News apps for the first 30 minutes of your day and can be scheduled to activate automatically every morning — removing the willpower requirement from the moment you're most vulnerable.",
  "detail": "The reflexive phone-grab right after an alarm is strongest precisely when willpower is lowest. {name}'s Morning Reset mode (default: 30 minutes, targeting Social and News categories) is schedulable via iOS DeviceActivity — the OS activates it at your chosen time every day whether you've opened LockHour or not. After the 30-minute block ends, your apps unlock automatically. Every completed morning reset is logged in your session history, and the streak counter shows how many consecutive mornings you've successfully protected, which gives the habit visible momentum.",
  "bullets": [
   "Morning Reset: 30-minute default block targeting Social and News app categories",
   "Schedulable via iOS DeviceActivity — activates automatically every morning, no manual trigger",
   "Streak tracker shows consecutive mornings completed — makes the habit visible",
   "Calls, messages, alarms, and all non-selected apps remain fully accessible",
   "Morning Reset is included in the one-time lifetime unlock (not available in free Quick Focus tier)"
  ],
  "faq": [
   {
    "q": "Can I extend the morning block beyond 30 minutes?",
    "a": "The Morning Reset preset is 30 minutes. For a longer custom morning block you can use Custom Focus mode, set your preferred duration, and start it manually. The scheduled auto-start is currently tied to the preset duration."
   },
   {
    "q": "What exactly does 'Social' and 'News' category cover?",
    "a": "These are Apple's App Store category groupings, which include apps Apple classifies in those categories on the device — typically covering major social media platforms and news aggregators. You can also hand-pick specific apps to add or remove."
   },
   {
    "q": "Will LockHour impact my battery life with scheduled automation?",
    "a": "No measurably. The block is enforced by iOS DeviceActivity extensions running at the OS level. LockHour does not run a background process during a session — there is no continuous CPU or network activity."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "scenario",
  "query": "how to fix slightly blurry soft focus photo on iPhone",
  "match": [
   "how to fix slightly blurry soft focus photo on iphone",
   "best app to sharpen out-of-focus photo iphone no cloud no subscription",
   "fix soft focus blurry iphone photo",
   "sharpen photo on-device ai iphone"
  ],
  "lead": "Unblurry works best on soft-focus and mild camera-shake photos where real detail was captured but not resolved sharply — the Sharpen and AI Clarity modes produce visibly crisper results on these, entirely on your device.",
  "detail": "{name} uses two complementary approaches: a multi-scale unsharp masking Core Image pipeline (Sharpen and Auto Clear modes — fast, runs on any photo) and an on-device Real-ESRGAN x4 neural model (AI Clarity mode) that reconstructs high-frequency edge detail tile by tile. For photos that are soft rather than streaked — imperfect autofocus, slight hand-tremor in low light — these tools typically produce visible improvement. A strength slider controls intensity, and a press-and-hold before/after comparison lets you assess the actual result on your own photo before you commit to saving it.",
  "bullets": [
   "Sharpen mode: multi-scale unsharp masking + luminance sharpening — fast, color-faithful result",
   "AI Clarity: Real-ESRGAN x4 neural model runs entirely on-device — rebuilds edge detail from scratch",
   "Auto Clear: one-tap balanced fix combining sharpening, denoise, and micro-contrast for everyday soft shots",
   "Strength slider: dial from subtle to aggressive — avoid pushing too high as over-sharpening creates haloing",
   "Before/after press-and-hold comparison — verify the real improvement on your photo before saving"
  ],
  "faq": [
   {
    "q": "Does Unblurry improve every blurry photo?",
    "a": "Sharpening improves photos where detail was captured but not resolved cleanly — soft focus, light camera shake. It cannot manufacture detail that was never captured. The before/after slider shows you the real result on your specific photo before you save."
   },
   {
    "q": "What is the difference between Sharpen mode and AI Clarity?",
    "a": "Sharpen uses Core Image unsharp masking — fast and runs on any photo. AI Clarity runs a Real-ESRGAN x4 neural model on-device, which tends to produce sharper, more natural edge reconstruction, especially on small or very soft images. AI Clarity takes longer and processes photos in tiles with a size cap."
   },
   {
    "q": "Are enhanced photos saved at full resolution?",
    "a": "Free exports are watermarked and resolution-capped. The one-time Pro unlock saves at your photo's full original resolution with no watermark, enables 4× upscaling, Portrait and Restore modes, and removes the daily save limit."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "faq",
  "query": "can an app actually fix motion blur in a photo",
  "match": [
   "can an app actually fix motion blur in a photo",
   "what kind of blur can unblurry realistically fix",
   "motion blur vs out of focus blur fix",
   "can app fix motion blur photo"
  ],
  "lead": "Unblurry substantially improves soft-focus and mild camera-shake photos, but heavy directional motion blur — the streaking from a fast-moving subject — is a physically different problem that no sharpening or AI super-resolution tool can fully reverse.",
  "detail": "Out-of-focus blur makes an image soft in all directions because the lens didn't resolve the subject sharply — the underlying edge data is blurred but present, and sharpening or neural SR can recover much of it. Motion blur from a fast subject or slow shutter averages light from multiple positions across time into directional streaks: spatial information along the smear direction is destroyed, not just blurred. {name}'s Sharpen mode will increase local contrast in a motion-blurred image — it will look less soft overall — but it cannot de-streak a runner or a moving car; the data was never captured. The Real-ESRGAN model powering AI Clarity was trained for general image super-resolution (recovering detail from degraded inputs), not for inverting specific motion-blur kernels. A practical test: if the subject is clearly recognizable but soft, sharpening genuinely helps; if edges and lines are smeared in a clear direction and the subject is hard to identify, no editing app will produce a clean fix.",
  "bullets": [
   "Out-of-focus blur: Unblurry's strongest use case — sharpening and AI SR both work well",
   "Mild camera shake (hand tremor, not hard directional smear): noticeably improved with Sharpen or AI Clarity",
   "Heavy directional motion blur (streaking subject): sharpening improves local contrast but cannot de-streak",
   "Extreme blur (subject unrecognizable): no editing tool can reconstruct content that was never captured — be skeptical of apps that claim otherwise",
   "Use the built-in before/after slider to judge the real result on your own photo before saving"
  ],
  "faq": [
   {
    "q": "What neural model powers Unblurry's AI Clarity mode?",
    "a": "A Core ML conversion of Real-ESRGAN x4 (BSD-3 licensed), running entirely on-device on the Neural Engine or GPU. Real-ESRGAN is a super-resolution model trained on real-world image degradations including blur, noise, and compression artifacts — it tends to sharpen edges well, but it is not a dedicated motion-deblur network designed to invert directional blur kernels."
   },
   {
    "q": "Why do many apps claim they can fix any blur?",
    "a": "Sharpening algorithms increase edge contrast, which makes images look perceptually sharper and is a genuine improvement on soft-focus photos. Marketing often conflates 'looks less blurry' with 'fully recoverable' — they're not the same thing. Unblurry's support documentation is straightforward about what sharpening can and can't do."
   },
   {
    "q": "Can Unblurry help a dark, blurry night photo?",
    "a": "Night photos are often blurry for two separate reasons: high-ISO noise (fixable with Denoise mode) and blur from hand-shake or subject movement (partially fixable with Sharpen or AI Clarity for camera shake; not fully fixable if there is heavy directional motion blur). Try Auto Clear or Sharpen first — the before/after slider shows whether it helps on your specific shot."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "scenario",
  "query": "app to restore and upscale old scanned family photos iPhone no cloud",
  "match": [
   "app to restore and upscale old scanned family photos iphone no cloud",
   "how to improve quality of faded scanned old photo on iphone",
   "restore old scanned family photos iphone",
   "upscale low-resolution vintage photo app"
  ],
  "lead": "Unblurry's Restore mode and 4× AI Upscale work well together on scanned or phone-photographed prints — reducing speckle and reviving faded colors before scaling the image up with neural edge reconstruction rather than simple pixel stretching.",
  "detail": "When you scan or photograph an old print, the result is typically soft, grainy, color-faded, and small in pixel count. {name}'s Restore pipeline addresses each issue in sequence: a median filter suppresses scratch and speckle artifacts; noise reduction cleans up grain; a warm color-temperature shift compensates for the blue drift that printed photos develop with age; saturation and contrast boosts recover faded vibrancy. The 4× Upscale mode (Pro unlock required) then runs Real-ESRGAN on-device, producing sharper edges and finer texture than bicubic interpolation. One honest note: if a scanned area has no surviving detail — completely washed out or heavily damaged — the neural model fills in plausible texture that looks convincing at normal viewing sizes but is generated, not recovered historical data.",
  "bullets": [
   "Restore mode pipeline: median filter (scratch/speckle) → noise reduction → warmth shift → saturation and contrast revival",
   "4× Upscale (Pro unlock): Real-ESRGAN neural upscaling — sharper edges and texture than standard bicubic",
   "Works best on prints with visible content (even if faded) — not effective on fully washed-out or blank areas",
   "Document mode is a good alternative for old typed letters, newspapers, or sheet music",
   "100% on-device — your family photos never leave your iPhone"
  ],
  "faq": [
   {
    "q": "What is the maximum output size from 4× AI upscaling?",
    "a": "The AI engine caps the input long edge at 768 pixels before running the model, producing a maximum output of 3072 pixels on the long edge. For large originals, the photo is first scaled down to fit the 768px cap, then upscaled 4× — keeping processing time and memory reasonable across all supported devices."
   },
   {
    "q": "Should I use Restore mode or just Sharpen for old photos?",
    "a": "Restore is specifically tuned for faded printed photos: speckle suppression, then warmth and color revival, then sharpening — in that order. Sharpen mode alone skips the color revival and noise steps. For genuinely old or faded prints, Restore is the better starting point; try Sharpen only if the photo is soft but not color-faded."
   },
   {
    "q": "Can Unblurry colorize black-and-white photos?",
    "a": "No. Unblurry enhances clarity, contrast, sharpness, and noise. It does not colorize grayscale images — that is a separate category of AI model not included in the app."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "scenario",
  "query": "how to make blurry whiteboard photo text sharp on iPhone",
  "match": [
   "how to make blurry whiteboard photo text sharp on iphone",
   "app to fix soft document scan or jpeg-compressed screenshot iphone",
   "sharpen whiteboard photo text iphone",
   "make document scan readable app"
  ],
  "lead": "Unblurry's Document mode boosts contrast, lifts shadows, and applies tight unsharp masking specifically tuned for text strokes — making photographed whiteboards, soft document scans, and compression-softened screenshots noticeably more readable.",
  "detail": "{name}'s Document pipeline differs from the general Sharpen mode in how it prioritizes readability over photographic quality: it reduces saturation (pushing toward neutral ink-on-paper contrast), boosts overall contrast more aggressively to separate text from background, and applies tightly-radiused unsharp masking that sharpens fine strokes without the haloing that general sharpening creates on continuous-tone images. It is also effective on a specific modern problem: screenshots shared via messaging apps (WhatsApp, iMessage) are JPEG-recompressed at lower quality, which smears fine text into soft artifacts — Document mode's denoise-then-sharpen pipeline recovers much of that apparent compression blur. The strength slider lets you push contrast without burning out fine hairline strokes.",
  "bullets": [
   "Document mode: contrast boost + shadow lift + fine-radius unsharp mask — tuned for text, not photographic content",
   "Effective on photos of whiteboards, receipts, printed documents, handwritten notes",
   "Also handles JPEG-compressed screenshots: compression softness responds well to denoise + fine sharpening",
   "Strength slider: push sharpening and contrast without overexposing thin strokes",
   "100% on-device — photograph a receipt, sharpen it, share it, no server involved"
  ],
  "faq": [
   {
    "q": "Is Document mode better than just using a dedicated scan app?",
    "a": "Scan apps (including iOS built-in scanning) are better for capturing new documents — they correct perspective, normalize lighting, and output PDF. Document mode in Unblurry is for improving photos you've already taken: sharpening, contrast, and noise on an existing image. The two complement each other — scan first, then use Document mode in Unblurry if the text is still soft."
   },
   {
    "q": "Can Unblurry make a blurry license plate or street sign readable?",
    "a": "If the plate is soft due to mild focus blur or slight camera shake, sharpening usually helps. If it's blurry due to distance, fast movement, or very low resolution, the same limits apply: sharpening improves perceived contrast but cannot reconstruct characters that were never captured as distinct pixels. The before/after slider shows the real result before you save."
   },
   {
    "q": "Does Document mode change the colors in my photo?",
    "a": "Yes, intentionally — it reduces saturation by up to 25% at maximum strength to push the image toward readable ink-on-paper contrast, and it lifts shadows. For most document and whiteboard use cases this is helpful. If you want to preserve colors in a colorful flyer or printed illustration, use Auto Clear or Sharpen instead."
   }
  ]
 }
]
''')


def deep_facts(q: str, key: str, name: str) -> dict[str, Any] | None:
    """Match a deep-content item for `key`; return a content overlay or None."""
    ql = q.lower()
    for it in DEEP_ITEMS:
        if it["app_key"] != key:
            continue
        if any(m in ql for m in it["match"]):
            def sub(s: str) -> str:
                return s.replace("{name}", name)
            detail = sub(it["detail"])
            lead = sub(it["lead"])
            return {
                "meta_description": (sub(it["lead"])[:150]).rsplit(" ", 1)[0] + ".",
                "lead": lead,
                "short_answer_paragraphs": [
                    detail,
                    f"Try {name} on a real example first, and check the current App Store "
                    f"listing for exact features and pricing before you decide.",
                ],
                "what_to_look_for": [sub(b) for b in it["bullets"]],
                "where_app_fits": f"{name} is built for exactly this — use the checklist above and test it on a real example.",
                "faq": [{"q": sub(f["q"]), "a": sub(f["a"])} for f in it["faq"]],
            }
    return None


ALL_DEEP_QUERIES: dict[str, list[str]] = {}
for _it in DEEP_ITEMS:
    ALL_DEEP_QUERIES.setdefault(_it["app_key"], []).append(_it["query"])

if __name__ == "__main__":
    print(f"{len(DEEP_ITEMS)} deep items")
    for _it in DEEP_ITEMS:
        print(f"  {_it['app_key']:14} {_it['kind']:9} {_it['query']}")
