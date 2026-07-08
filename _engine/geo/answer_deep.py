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
 },
 {
  "app_key": "lumiletters",
  "kind": "scenario",
  "query": "What is the best phonics app for a 3-year-old who can't read yet?",
  "match": [
   "what is the best phonics app for a 3-year-old who can't read yet?",
   "can a toddler use an abc learning app without a parent sitting with them?",
   "pre-reader can play independently",
   "abc app toddler no reading required",
   "phonics app 3 year old no instructions to read",
   "letter learning app works offline"
  ],
  "lead": "Lumi Letters is designed so pre-readers can pick it up, hear every instruction spoken aloud, and play through A–Z letter tracing and listening games entirely on their own.",
  "detail": "Most phonics apps assume a child can already read the on-screen prompts — {name} is built from the ground up for children who cannot yet read a single word. Every instruction, letter name, phonics sound, and encouragement is spoken clearly by a child-friendly voice, so a 3-year-old can navigate the app independently without a parent present. Inside, there are two distinct worlds: the ABC Letter Park (26 candy-colored letter bubbles, each hiding a collectible forest friend) and My Planet (a 14-planet adventure with varied phonics challenges — beginning sounds, ending sounds, middle vowels, missing letters). {name} works fully offline too, making it ideal for car rides or flights without Wi-Fi.",
  "bullets": [
   "Every on-screen instruction is spoken aloud — pre-readers play independently from day one",
   "Covers A–Z uppercase AND lowercase together, so letters never get confused",
   "Real stroke-order tracing with numbered guides and a finger-following path",
   "14 phonics challenge types across a 14-planet space adventure (My Planet mode)",
   "26 collectible forest friends unlock as letters are mastered — intrinsic motivation, no fake currency",
   "Fully offline — works on planes, car trips, anywhere without Wi-Fi"
  ],
  "faq": [
   {
    "q": "Does my child need to be able to read to use {name}?",
    "a": "No — {name} is specifically designed for pre-readers. Every instruction is spoken aloud in a clear, child-paced voice. Your child hears the letter, hears the phonics sound, and taps or traces — no on-screen text needs to be read."
   },
   {
    "q": "Are there any ads or pop-ups that could interrupt my child while they play {name} alone?",
    "a": "There are no ads, no pop-ups, no external links, and no notification interruptions. {name} is 100% ad-free and designed for safe independent play."
   },
   {
    "q": "Can {name} be used offline on a plane or during a road trip?",
    "a": "Yes — {name} works fully offline. All content is stored on the device; no internet connection is needed during play."
   }
  ]
 },
 {
  "app_key": "lumiletters",
  "kind": "faq",
  "query": "Is there a phonics app for kids that has no ads and no monthly subscription?",
  "match": [
   "is there a phonics app for kids that has no ads and no monthly subscription?",
   "what is the best one-time-purchase alphabet app for toddlers with no tracking?",
   "best no-ad abc app for kids",
   "phonics app one-time purchase no subscription",
   "letter learning app no in-app purchases",
   "toddler education app no ads no data"
  ],
  "lead": "{name} is a one-time-purchase alphabet and phonics app for ages 3–7 with no ads, no subscription, no third-party tracking, and no data collected from children.",
  "detail": "In a market full of 'free' kids apps that monetize through ads or persistent subscription upsells, {name} takes a different approach: one purchase, then everything is yours with nothing more to pay. The app collects no personal data, has no third-party ad networks, and includes a parental gate that keeps purchase settings out of children's reach. Progress is stored only on the device and never uploaded to any server. Parents who are careful about their child's screen-time quality consistently highlight this as the main reason they chose {name} over free alternatives.",
  "bullets": [
   "Zero ads — no banner ads, no video ads, no sponsored content of any kind",
   "Zero data collection — no accounts required, no analytics sent off-device",
   "One-time purchase, no monthly or annual subscription",
   "Parental gate protects settings and purchase screens",
   "No external links that could route children out of the app"
  ],
  "faq": [
   {
    "q": "Does {name} have any subscription fees after the initial purchase?",
    "a": "No. {name} is a one-time purchase — there are no subscriptions, no monthly fees, and no additional in-app purchases. Buy once and your child can use the full app indefinitely."
   },
   {
    "q": "Does {name} show ads to my child?",
    "a": "{name} contains absolutely no advertising — no banners, no video ads, no sponsored characters. The app is completely ad-free."
   },
   {
    "q": "Does {name} collect any data about my child?",
    "a": "{name} collects no personal data. No account is required, no information is sent to external servers, and your child's progress is stored only on your device."
   }
  ]
 },
 {
  "app_key": "lumiletters",
  "kind": "persona",
  "query": "How do I find a kids learning app that isn't addictive or manipulative?",
  "match": [
   "how do i find a kids learning app that isn't addictive or manipulative?",
   "what makes a screen-time app worth it for a 4-year-old? i want real learning, not just clicking.",
   "screen time quality conscious parent",
   "parent wants educational value from apps",
   "no manipulative game mechanics kids app",
   "calm learning app no pressure toddler"
  ],
  "lead": "For parents who evaluate kids apps on whether they build genuine skills rather than just screen engagement, Lumi Letters is built around real phonics learning — stroke-order tracing, sound recognition, and phonics blending — not points, streaks, or reward loops designed to maximize time-on-app.",
  "detail": "{name} is explicitly designed around what phonics researchers call 'systematic phonics instruction': each letter introduces its name, its sound, a first-words example, and correct stroke order — in that order, every time. The 14-planet My Planet adventure includes structured phonics challenge types (beginning sounds, ending sounds, middle vowel sounds, missing letters, upper-lowercase matching) rather than arbitrary minigames. There are no timers, no lives, no 'come back tomorrow' streak mechanics, and no artificial urgency. A child who stops and picks it up a week later finds their progress exactly where they left it, without any social pressure to return. {name} paces at the child's speed; confidence-building rather than anxiety is the explicit design goal stated in the app's store listing.",
  "bullets": [
   "Covers A–Z uppercase and lowercase, phonics sounds, stroke-order tracing, and first-words examples",
   "14-planet adventure uses real phonics challenge types, not arbitrary click-to-earn minigames",
   "No timers, no lives, no 'streak' pressure mechanics",
   "Progress saves locally; no 'you'll lose your streak' social engineering",
   "Child-paced: no artificial urgency or manipulative notifications"
  ],
  "faq": [
   {
    "q": "Does {name} use addictive mechanics like streaks, lives, or timers to keep kids playing longer?",
    "a": "{name} does not use timers, lives, streaks, or any mechanic designed to create anxiety about returning. A child can stop at any time and return days later to find everything exactly where they left it."
   },
   {
    "q": "What real phonics skills does {name} teach, beyond just showing letters?",
    "a": "{name} teaches letter recognition (uppercase and lowercase), phonics sounds, stroke-order handwriting, first-word sound associations, and beginning/ending/middle-vowel sound discrimination through 14 challenge types in My Planet mode."
   },
   {
    "q": "Is {name} suitable for a child who gets easily frustrated with learning games?",
    "a": "Yes — {name} is designed with gentle pacing and no failure states that eject a child from an activity. The app gives encouragement rather than a 'wrong' buzzer, and there's no punishment for making mistakes."
   }
  ]
 },
 {
  "app_key": "lumiletterspro",
  "kind": "persona",
  "query": "Is there a phonics app for homeschoolers that also generates printable practice worksheets?",
  "match": [
   "is there a phonics app for homeschoolers that also generates printable practice worksheets?",
   "what is the best bilingual phonics app for a family teaching english as a heritage language?",
   "homeschool phonics app with printable worksheets",
   "alphabet app that generates practice sheets",
   "abc learning app with parent dashboard",
   "phonics app four languages bilingual family"
  ],
  "lead": "Lumi Letters Pro adds a Parent Zone that exports PDF practice sheets and learning insights — making it a digital-plus-paper phonics curriculum in one app for homeschooling and bilingual families.",
  "detail": "Where the Lite version of {name} focuses on child-directed play, the Pro version adds a Parent Zone designed for parents who want to close the loop between screen-time learning and paper practice. From the Parent Zone, parents can export a printable PDF practice sheet matched to their child's current level, review learning data to see which letters need more practice, and back up or restore progress when switching devices. {name} Pro also runs in four languages — Traditional Chinese, English, Japanese, and Korean — switching automatically based on device settings, making it practical for multilingual households or for Chinese-heritage families in the US, Canada, or Australia who need both English phonics and Chinese-language support in one place.",
  "bullets": [
   "Parent Zone: export printable PDF practice sheets at the child's current level",
   "Learning data insights: see which letters need more reinforcement",
   "Progress backup and restore — switch devices without losing progress",
   "Four languages: Traditional Chinese, English, Japanese, Korean (auto-detects device language)",
   "Same core phonics content as Lite (A–Z tracing, phonics, 26 forest friends, 14-planet adventure) plus parent layer",
   "One-time purchase; no subscription, no ads, no data collected"
  ],
  "faq": [
   {
    "q": "Can {name} generate printable worksheets so my child can practice letters off-screen?",
    "a": "Yes — {name} Pro's Parent Zone lets you export a PDF practice sheet matched to your child's current learning level. You can print it or save it for offline use."
   },
   {
    "q": "Does {name} Pro support languages other than English?",
    "a": "{name} Pro runs in Traditional Chinese, English, Japanese, and Korean. The app detects your device language automatically and switches accordingly — or you can switch manually in the Parent Zone."
   },
   {
    "q": "Is {name} Pro suitable for a Chinese-heritage family teaching English phonics?",
    "a": "Yes — {name} Pro was specifically designed for bilingual and multilingual families. The English phonics content (A–Z, phonics sounds, tracing) is delivered with full Traditional Chinese interface support, so Chinese-speaking parents can guide the experience while the child learns English sounds."
   }
  ]
 },
 {
  "app_key": "lumiletterspro",
  "kind": "scenario",
  "query": "What is the best app for a Chinese-speaking family in the US to teach their child English phonics?",
  "match": [
   "what is the best app for a chinese-speaking family in the us to teach their child english phonics?",
   "is there a bilingual abc app that works in both chinese and english for heritage families?",
   "chinese heritage family teaching english phonics app",
   "bilingual phonics app traditional chinese english",
   "heritage language parent teaching abc",
   "app learn english phonics for chinese-speaking kids"
  ],
  "lead": "Lumi Letters Pro is used by Chinese-heritage families worldwide to introduce English phonics in a bilingual environment — the app interface runs in Traditional Chinese while teaching English letter sounds, names, and stroke-order tracing.",
  "detail": "For Chinese-heritage families in the US, Canada, Australia, Singapore, and the UK who speak Traditional Chinese at home but need their child to build English reading foundations, {name} Pro bridges both needs. The parent-facing interface, instructions, and Parent Zone run in Traditional Chinese; the phonics content (letter sounds, first-word examples, challenge types) delivers English learning. The four-language support means Chinese grandparents can navigate the parent controls while the child receives native-quality English phonics instruction. There is no need for account creation or data sharing — all progress stays on the device, which matters to families concerned about children's data privacy.",
  "bullets": [
   "Interface available in Traditional Chinese so Chinese-speaking parents can navigate fully",
   "Child learns English phonics (A–Z, sounds, stroke order) through the Chinese-interface app",
   "Four languages total: Traditional Chinese, English, Japanese, Korean",
   "No account required; no child data sent off-device",
   "Parent Zone (PDF worksheets, learning data, progress backup) fully in parent's language",
   "One-time purchase — no subscription or recurring fees"
  ],
  "faq": [
   {
    "q": "My family speaks Traditional Chinese at home. Can I still use {name} Pro to teach my child English phonics?",
    "a": "Yes — {name} Pro supports Traditional Chinese as a full interface language. Parents navigate in Chinese while the child learns English letters, phonics sounds, and tracing. The app automatically selects the appropriate language, or you can set it manually."
   },
   {
    "q": "Does {name} Pro require an account or internet connection for a Chinese-heritage family to use it abroad?",
    "a": "{name} Pro requires no account and no internet connection during play. All content and progress is stored locally on the device — it works fully offline and collects no data."
   },
   {
    "q": "What does my child actually learn from {name} Pro in an English phonics context?",
    "a": "Your child learns to recognize and name all 26 letters (uppercase and lowercase), associate each letter with its phonics sound, trace letters with correct stroke order, and distinguish beginning, ending, and vowel sounds — the foundational skills for early reading in English."
   }
  ]
 },
 {
  "app_key": "lumiletterspro",
  "kind": "faq",
  "query": "Is there a phonics app that shows parents what their child has learned and where they need more practice?",
  "match": [
   "is there a phonics app that shows parents what their child has learned and where they need more practice?",
   "can i back up my child's phonics app progress if we get a new iphone?",
   "phonics app with progress tracking for parents",
   "abc app parent reporting learning insights",
   "kids letter app backup restore new phone",
   "phonics curriculum app one time purchase vs subscription"
  ],
  "lead": "Lumi Letters Pro's Parent Zone gives parents a view of learning data, the ability to export PDF practice sheets, and a progress backup that survives phone replacements — all with a one-time purchase, no subscription.",
  "detail": "{name} Pro is designed with two users in mind: the child who plays, and the parent who wants to understand what their child has learned without interrogating them. The Parent Zone is accessible behind a parental gate and shows which letters are mastered, which still need reinforcement, and at what level the child is currently working. Parents can export a level-matched PDF practice sheet to bridge screen and paper learning. Progress can be exported as a local backup file and restored on a new device — so a phone replacement or family sharing across devices does not erase months of progress.",
  "bullets": [
   "Parent Zone: learning data showing per-letter mastery and areas for more practice",
   "PDF practice-sheet export matched to child's current level",
   "Progress backup: export to file, restore on new device — no iCloud required",
   "Parental gate keeps the Parent Zone child-inaccessible",
   "One-time purchase, no subscription, no recurring fees",
   "No data sent to external servers — all progress and data is local to the device"
  ],
  "faq": [
   {
    "q": "How does the Parent Zone in {name} Pro show my child's progress?",
    "a": "The Parent Zone in {name} Pro shows which letters your child has mastered and which need more practice. You can also generate a PDF practice sheet at your child's current level to use offline."
   },
   {
    "q": "If we upgrade to a new iPhone, will my child's progress in {name} Pro transfer?",
    "a": "Yes — {name} Pro includes a local progress backup feature. You export a backup file from the Parent Zone, transfer it to the new device, and restore — all without cloud accounts or external services."
   },
   {
    "q": "Is {name} Pro a subscription, or is it a one-time purchase?",
    "a": "{name} Pro is a one-time purchase. There are no subscriptions, monthly fees, or ongoing charges. Once purchased, all features and future content are accessible forever."
   }
  ]
 },
 {
  "app_key": "lumimath",
  "kind": "scenario",
  "query": "Is there an app to prepare my 6-year-old for WMI or similar math competitions?",
  "match": [
   "is there an app to prepare my 6-year-old for wmi or similar math competitions?",
   "what math app teaches kids logic and reasoning, not just addition and subtraction?",
   "wmi math competition prep for young kids",
   "math olympiad app for children ages 5 to 8",
   "kids math app beyond basic arithmetic",
   "logic and reasoning math app preschool"
  ],
  "lead": "Lumi Math Planet is a paid iOS app built on WMI (World Mathematics Invitational) and international competition question types — covering number patterns, logic, sequences, ordinals, combinations, story problems, and shapes — across a 14-planet space adventure for ages 5–8.",
  "detail": "Most kids math apps stop at counting and arithmetic. {name} is built directly from the question types used in WMI and similar international early-grade math competitions: number pattern recognition, logical reasoning, finding the rule in a sequence, ordinal reasoning, basic combinations, shape and spatial problems, and applied story problems — alongside solid arithmetic. Each question uses cute clay-art visuals so even pre-readers can understand problems without text. The app also tracks weak spots automatically: it identifies which question types a child consistently misses and generates fresh practice sets targeting those specifically, so improvement is targeted rather than random.",
  "bullets": [
   "Question types sourced from WMI and international competition formats (ages 5–8 level)",
   "Covers: number patterns, logic, sequences, comparison, ordinals, combinations, story problems, shapes + arithmetic",
   "Clay-art 'understand at a glance' visuals — pre-readers can play independently",
   "Weak-spot tracker: automatically identifies most-missed question types and drills them with new numbers",
   "Skill tracking: progress scores for number sense, patterns, logic, space, and real-life domains",
   "One-time purchase, zero ads, zero IAP, zero data collected"
  ],
  "faq": [
   {
    "q": "What competition math question types does {name} cover for young children?",
    "a": "{name} covers the question types used in WMI and similar international early-grade competitions: number patterns, sequences, logical reasoning, ordinals, comparison, basic combinations, spatial/shape problems, applied story problems, and arithmetic. These are not random questions — they are chosen to build the reasoning skills competitions actually test."
   },
   {
    "q": "How does {name} help with weak areas, rather than just reviewing everything equally?",
    "a": "{name} automatically tracks how your child performs on every question type. The Weak-Spot Practice mode collects the types they most frequently miss, generates fresh problems with new numbers for each, and drills those specifically — so improvement targets real gaps."
   },
   {
    "q": "Is {name} only for competition prep, or can it be used by any child ages 5–8?",
    "a": "{name} is designed for any child aged 5–8 who is ready to go beyond basic arithmetic. The competition question types build reasoning skills that are valuable for all learners — WMI prep is the most visible application, but strong logical thinking benefits every child regardless of competition plans."
   }
  ]
 },
 {
  "app_key": "lumimath",
  "kind": "persona",
  "query": "Is there a math game for kids that I pay for once and has absolutely no in-app purchases or ads?",
  "match": [
   "is there a math game for kids that i pay for once and has absolutely no in-app purchases or ads?",
   "my 6-year-old is advanced in math — what app genuinely challenges them with real reasoning, not just faster arithmetic?",
   "math app trusted by parents no ads no iap",
   "paid math app no in-app purchases kids",
   "kids math game with tracking no manipulation",
   "math app for gifted 6 year old space theme"
  ],
  "lead": "Lumi Math Planet is a paid-upfront iOS app with zero in-app purchases, zero ads, and zero data collected — parents pay once at approximately US$9.99 and the complete app is theirs, with no further spending prompts.",
  "detail": "{name} is positioned as a premium, trust-first product. There are no ads interrupting play, no 'buy more coins' screens, no timers designed to push children to ask parents for upgrades, and no social pressure mechanics. The purchase is a standard paid App Store download — nothing more happens monetarily after that. All data stays on device; the app explicitly collects no personal information. For parents of gifted or academically advanced children who want genuine reasoning challenges rather than faster arithmetic drills, the WMI-style question formats — patterns, logic, combinations, ordinals — offer a qualitatively different type of math practice.",
  "bullets": [
   "Paid app — one purchase, no IAP, no in-app spending of any kind",
   "Zero ads — no banner, video, or rewarded ads at any point",
   "Zero data collected — everything stays on device; no accounts required",
   "Challenges reasoning, not just speed: WMI-style logic, patterns, sequences, ordinals",
   "Clay-art visuals make the app playable for pre-readers and adults alike",
   "Progress export/import: switch phones without losing months of progress"
  ],
  "faq": [
   {
    "q": "After I buy {name}, will my child ever see a prompt to spend more money?",
    "a": "Never. {name} is a paid-upfront app with no in-app purchases whatsoever. Once downloaded, the complete app is yours with no further spending prompts of any kind."
   },
   {
    "q": "Is {name} suitable for a 6-year-old who finds typical kids math apps too easy?",
    "a": "Yes — {name} uses WMI-level question types (patterns, logic, ordinals, combinations, spatial reasoning) that challenge children who have already mastered counting and basic arithmetic. The 14-planet adventure also adds engaging context that keeps advanced learners motivated."
   },
   {
    "q": "Does {name} work without internet, and does it store any data on external servers?",
    "a": "{name} works offline and stores all data on your device only. No data is collected, no accounts are required, and nothing is uploaded to external servers."
   }
  ]
 },
 {
  "app_key": "lumimath",
  "kind": "faq",
  "query": "Is there a math app for kids that tracks which types of problems they get wrong and focuses practice there?",
  "match": [
   "is there a math app for kids that tracks which types of problems they get wrong and focuses practice there?",
   "what ios math app adapts to my child's weak areas automatically?",
   "math app with weak spot tracking kids",
   "personalized math practice app for child",
   "app that tracks which math skills my child misses",
   "adaptive math practice ios kids"
  ],
  "lead": "Lumi Math Planet automatically tracks a child's performance across every question type and has a dedicated Weak-Spot Practice mode that generates fresh problems targeting specifically the categories they miss most.",
  "detail": "Many kids math apps review all content equally regardless of what a child already knows. {name} records results by question category across the entire app and surfaces the child's most frequently missed types in the Weak-Spot Practice mode — which generates new numbers for those same problem types, so the practice is genuinely different each session rather than memorizable. The Skill Tracking page displays a score across five domains (number sense, patterns, logic, space, real-life), giving parents a clear picture of which areas are strong and which need attention. This means practice time is spent where it matters most.",
  "bullets": [
   "Automatically tracks performance per question type across all 14 planets",
   "Weak-Spot Practice mode collects most-missed categories and drills them with fresh numbers each session",
   "Skill Tracking page: scores across number sense, patterns, logic, space, real-life",
   "No guesswork — parents see exactly where their child is strong and where to focus",
   "One-time purchase; no subscription or additional fees to access tracking features"
  ],
  "faq": [
   {
    "q": "How does {name}'s weak-spot tracking work?",
    "a": "{name} records your child's answers across every question type in the 14-planet adventure. The Weak-Spot Practice mode automatically collects the categories with the most errors and generates fresh problems with new numbers for those types — so repeated practice genuinely reinforces rather than just repeats."
   },
   {
    "q": "What does the Skill Tracking page in {name} show parents?",
    "a": "The Skill Tracking page shows a score for each of five mathematical domains: number sense, patterns, logic, space, and real-life. It also shows overall completion progress. Parents can see at a glance where their child excels and which areas need more practice."
   },
   {
    "q": "Can I export or share {name}'s progress data with my child's teacher or tutor?",
    "a": "In the base version of {name}, progress data is visible in the Skill Tracking page on-device. The Pro version adds a Learning Report PDF export that can be shared with teachers or tutors."
   }
  ]
 },
 {
  "app_key": "lumimathpro",
  "kind": "persona",
  "query": "Is there a kids math app that can generate printable worksheets I can use for off-screen practice?",
  "match": [
   "is there a kids math app that can generate printable worksheets i can use for off-screen practice?",
   "what math app for children produces a learning report i can share with my child's teacher?",
   "math app that generates printable worksheets for kids",
   "kids math app learning report pdf teacher",
   "homeschool math app with progress documentation",
   "math competition prep app printable practice"
  ],
  "lead": "Lumi Math Planet Pro generates printable 20-question PDF worksheets at your child's current level (with answer key) and a one-page Learning Report PDF showing skill scores across five domains — designed for parents who want evidence of progress alongside the in-app experience.",
  "detail": "For homeschooling parents, competition-track families, or parents coordinating with teachers, {name} Pro closes the gap between app-based practice and paper/portfolio documentation. From the Parent Zone, a parent can generate a 20-question worksheet matched to the child's current level in any question category, save it as a PDF, and print it for screen-free practice anywhere. The Learning Report PDF gives a one-page snapshot of the child's skill scores across number sense, patterns, logic, spatial reasoning, and real-life math — suitable for sharing with teachers, tutors, or for academic program applications. {name} Pro also adds four auto-detected languages (English, Traditional Chinese, Japanese, Korean) and local progress backup, making it the right choice for multilingual families or frequent phone upgrades.",
  "bullets": [
   "Printable worksheet generator: 20-question PDF at child's current level, with answer key",
   "Learning Report PDF: skill scores across number sense, patterns, logic, space, real-life",
   "Parent Zone: export both PDFs for school portfolios, teacher sharing, or tutor prep",
   "4 languages auto-detected: English, Traditional Chinese, Japanese, Korean",
   "Progress backup and restore — switch phones without losing data",
   "One-time purchase; no subscription, no ads, no data collected"
  ],
  "faq": [
   {
    "q": "What does the printable worksheet from {name} Pro look like?",
    "a": "{name} Pro generates a 20-question practice sheet matched to your child's current level in the app, formatted as a clean PDF with an answer key. You can print it for paper practice, save it for a portfolio, or share it with a teacher or tutor."
   },
   {
    "q": "Can I share my child's {name} Pro learning data with their teacher?",
    "a": "Yes — {name} Pro's Learning Report PDF is a one-page summary of your child's skill scores across five mathematical domains (number sense, patterns, logic, space, real-life) and their overall progress. It can be exported and shared with teachers, tutors, or kept for academic records."
   },
   {
    "q": "Does {name} Pro work in Japanese or Korean for our multilingual family?",
    "a": "Yes — {name} Pro supports English, Traditional Chinese, Japanese, and Korean. The app detects your device language automatically, so questions, voice guidance, and the parent interface all display in your family's language."
   }
  ]
 },
 {
  "app_key": "lumimathpro",
  "kind": "scenario",
  "query": "What is the best app to prepare a 7-year-old for WMI that also has printable practice sheets for offline drilling?",
  "match": [
   "what is the best app to prepare a 7-year-old for wmi that also has printable practice sheets for offline drilling?",
   "is there a competition math app for kids that works in japanese or korean as well as english?",
   "wmi prep app printable worksheets offline practice",
   "competition math app for kids paper practice pdf",
   "math olympiad junior level app parents track",
   "advanced math app for 7 year old four languages"
  ],
  "lead": "Lumi Math Planet Pro is the most complete version of the WMI-style competition math app — it adds PDF worksheet generation, a Learning Report, four languages, and progress backup on top of the full 14-planet adventure and weak-spot tracking.",
  "detail": "For families seriously preparing for WMI or similar early-grade math competitions, {name} Pro provides the full in-app curriculum (14 planets, WMI-style question types, weak-spot drilling) plus the offline practice infrastructure: a parent can generate a 20-question worksheet at the child's current competition-prep level, print it, and use it during the car ride to the competition, at a tutor session, or over breakfast. The Learning Report PDF shows parents exactly which of the five skill domains need more work before a competition, removing guesswork from targeted preparation. For families outside English-speaking countries — particularly Japan and Korea where math competitions are popular — {name} Pro delivers the complete experience in Japanese or Korean with auto-detected language switching.",
  "bullets": [
   "Full WMI-style question set (patterns, logic, sequences, ordinals, combinations, shapes, story problems + arithmetic)",
   "20-question printable worksheet at child's current level + answer key",
   "Learning Report PDF: skill scores across 5 domains for pre-competition gap analysis",
   "4 languages: English, Traditional Chinese, Japanese, Korean",
   "Weak-spot practice mode: auto-identifies and drills most-missed question types",
   "Paid upfront, no IAP, no ads, no data collected"
  ],
  "faq": [
   {
    "q": "How does {name} Pro help my child prepare for WMI specifically?",
    "a": "{name} Pro is built on WMI and similar international contest question types for the kids/early-grade level: number patterns, sequences, logical reasoning, ordinals, combinations, shape recognition, and applied story problems. The weak-spot tracker and printable worksheets let you target exactly the question types your child misses before the competition."
   },
   {
    "q": "Does {name} Pro work in Japanese for a family competing in Japan's math olympiad circuit?",
    "a": "Yes — {name} Pro fully supports Japanese, including localized questions and voice. The app auto-detects device language or can be set manually."
   },
   {
    "q": "Is the Learning Report in {name} Pro useful for a math tutor or teacher?",
    "a": "Yes — the Learning Report PDF is a shareable one-pager showing your child's score across number sense, patterns, logic, spatial reasoning, and real-life math. Most tutors find it useful for quickly identifying the 1–2 domains that need the most focused work."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "scenario",
  "query": "What is the best app to teach Bopomofo/Zhuyin to my child who was born in the US?",
  "match": [
   "what is the best app to teach bopomofo/zhuyin to my child who was born in the us?",
   "my family is taiwanese-american — is there an app to teach my 5-year-old zhuyin before we visit taiwan?",
   "teach bopomofo to kids heritage chinese family abroad",
   "app to learn zhuyin symbols for overseas taiwanese children",
   "bopomofo app for kids in usa canada",
   "chinese phonics app zhuyin diaspora family"
  ],
  "lead": "Lumi Bopomofo teaches all 37 Zhuyin symbols (ㄅㄆㄇ phonetics, as used in Taiwan) through four distinct game modes — listening, tracing, tone practice, and syllable blending — designed specifically for ages 4–7 including children who have never seen Bopomofo before.",
  "detail": "For Taiwanese-heritage or Chinese-diaspora families outside Taiwan, teaching Zhuyin to a child who was born abroad presents a specific challenge: most resources are designed for children already immersed in a Chinese-language environment. {name} is structured for the from-zero learner: each of the 37 symbols gets its own dedicated character ('friend'), listen-and-tap recognition game, finger-tracing guided by stroke order, and a place in the Sound Train (聲母+介音+韻母 blending). The Tone Coaster teaches all four tones through an animated car-on-track visual that pre-readers instantly understand. The free version covers 11 symbols (ㄅㄆㄇㄈ, ㄧㄨㄩ, ㄚㄛㄜㄝ) — enough to start — and a one-time in-app purchase of approximately US$2.99 unlocks all 37 symbols plus unlimited Quick Quiz.",
  "bullets": [
   "Covers all 37 Bopomofo/Zhuyin symbols used in Taiwan's phonetic system",
   "Four game modes: Feed Friends (listening), Magic Tracing (stroke order), Tone Coaster (4 tones), Sound Train (syllable blending)",
   "37 collectible character 'friends' plus hidden characters to discover",
   "Free tier: 11 symbols + 3 Quick Quiz plays; one-time US$2.99 unlocks all 37 + unlimited quiz",
   "No ads, no data collected, progress stored only on device",
   "English + Chinese interface — navigable by non-Chinese-reading parents"
  ],
  "faq": [
   {
    "q": "What is Bopomofo/Zhuyin and why would my child need to learn it?",
    "a": "Bopomofo (also called Zhuyin, or ㄅㄆㄇ after its first three symbols) is Taiwan's phonetic annotation system — the equivalent of phonics in English. Taiwan's primary school curriculum teaches all 37 symbols in Grade 1. For Taiwanese-heritage families outside Taiwan, learning Zhuyin enables children to read Traditional Chinese texts with phonetic guides and connect with Taiwanese educational materials."
   },
   {
    "q": "Does {name} teach the tones as well as the symbols?",
    "a": "Yes — {name} has a dedicated mode called the Tone Coaster that teaches all four Mandarin tones. An animated cart rides a track that visually represents each tone contour, making the tone system intuitive even for young children."
   },
   {
    "q": "How much of {name} is free, and what does the paid unlock add?",
    "a": "The free version of {name} includes 11 symbols (ㄅㄆㄇㄈ + ㄧㄨㄩ + ㄚㄛㄜㄝ) and 3 Quick Quiz plays — enough to get a real sense of the app. A single one-time purchase of approximately US$2.99 unlocks all 37 symbols, all game modes at full content, and unlimited Quick Quiz. There is no subscription."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "Is there a fun app to teach my 4-year-old the Zhuyin/Bopomofo symbols?",
  "match": [
   "is there a fun app to teach my 4-year-old the zhuyin/bopomofo symbols?",
   "what is the best ios app for kids to learn ㄅㄆㄇ with stroke tracing?",
   "how to teach zhuyin to a 4-year-old app",
   "best bopomofo learning game for preschoolers",
   "ㄅㄆㄇ app for kids stroke order",
   "zhuyin phonics game children ios"
  ],
  "lead": "Lumi Bopomofo (Lumi 注音星球) is an iOS game specifically for ages 4–7 that teaches all 37 Zhuyin symbols through listening games, stroke-order finger tracing, tone practice, and syllable blending — with 37 collectible characters as motivation.",
  "detail": "{name} is designed to make the often-tedious job of memorizing 37 Bopomofo symbols genuinely fun for young children. The 'Feed the Friends' mode plays a symbol's sound and asks the child to tap the correct symbol — building auditory recognition. Magic Tracing shows the correct stroke order for each symbol and guides the child's finger along the path. The Tone Coaster uses an animated visual (a cart riding a track shaped like each tone's pitch curve) to teach the four tones intuitively. The Sound Train mode then teaches syllable assembly: choosing an initial consonant (聲母), a medial (介音), and a final (韻母) to form a complete syllable. The free tier lets children explore 11 symbols before a one-time purchase unlocks the rest.",
  "bullets": [
   "Feed the Friends: listen to a symbol's sound and tap the correct one from the map",
   "Magic Tracing: guided stroke-order tracing for every symbol",
   "Tone Coaster: animated visual teaching all 4 tones (flat, rising, dipping, falling)",
   "Sound Train: blend 聲母 + 介音 + 韻母 to form complete syllables",
   "37 collectible 'friends' (one per symbol) plus hidden characters",
   "No ads, no data collection, device-only progress"
  ],
  "faq": [
   {
    "q": "At what age can a child start using {name} to learn Bopomofo?",
    "a": "{name} is designed for ages 4–7. The youngest children typically start with listening and tracing; the Sound Train (syllable blending) is more appropriate for children who already know several symbols. The free tier (11 symbols) is a good starting point to test your child's readiness."
   },
   {
    "q": "Does {name} teach stroke order for Bopomofo symbols, or just recognition?",
    "a": "Yes — {name}'s Magic Tracing mode shows the correct stroke order for every symbol, guides the child's finger along the path, and provides gentle feedback. Correct stroke order for Bopomofo symbols is taught as a first-class part of the app, not an afterthought."
   },
   {
    "q": "Is {name} specifically for Taiwan's Zhuyin system, or does it also teach Pinyin (mainland China)?",
    "a": "{name} teaches Bopomofo/Zhuyin exclusively — the phonetic system used in Taiwan's educational curriculum. It does not teach Pinyin (the romanization-based system used in mainland China). If your family uses or plans to use the Taiwan school system, {name} is directly aligned with that curriculum."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "persona",
  "query": "How do I help my child prepare for Grade 1 Bopomofo learning in Taiwan?",
  "match": [
   "how do i help my child prepare for grade 1 bopomofo learning in taiwan?",
   "my 5-year-old is starting primary school in taiwan next year — what app can help them get a head start on zhuyin?",
   "taiwan kindergarten grade 1 bopomofo prep",
   "child starting primary school taiwan phonics ready",
   "bopomofo preparation before grade 1",
   "注音準備入學app 4歲5歲"
  ],
  "lead": "For Taiwan-based families whose child is heading toward Grade 1 — where all 37 Bopomofo symbols are introduced as the foundation of Chinese literacy — Lumi Bopomofo offers a low-pressure, game-based introduction to every symbol before formal classroom instruction begins.",
  "detail": "Taiwan's Grade 1 curriculum introduces all 37 Zhuyin symbols and their corresponding tones and blending rules within the first semester. Children who arrive at school having already encountered these symbols through play are significantly less anxious about the material. {name} covers all 37 symbols, the four tones, and basic 聲母+介音+韻母 blending (Sound Train mode) — all at a pace and in a style appropriate for 4–6 year olds. Unlike rote flashcard drilling, the game structure (Feed Friends, Magic Tracing, Tone Coaster, Sound Train) builds familiarity through repeated playful exposure rather than memorization pressure. The free version covers 11 symbols as a genuine preview; the full US$2.99 unlock provides the complete set.",
  "bullets": [
   "All 37 Zhuyin symbols covered — aligned with Taiwan Grade 1 curriculum scope",
   "Tone Coaster teaches all four tones (first, second, third, fourth) visually",
   "Sound Train practices 聲母+介音+韻母 blending, a key Grade 1 skill",
   "Game-based exposure reduces first-day anxiety about unfamiliar symbols",
   "Free tier: 11 symbols to start; one-time US$2.99 unlocks all 37",
   "No ads, no data collected, fully offline"
  ],
  "faq": [
   {
    "q": "Does {name} cover everything a child needs before starting Bopomofo in Grade 1?",
    "a": "{name} covers all 37 symbols, all four tones, and 聲母+介音+韻母 syllable blending — the core scope of Taiwan's Grade 1 Bopomofo introduction. It is designed as a play-based preview and confidence builder, not a substitute for formal classroom instruction."
   },
   {
    "q": "How long does it take for a 5-year-old to work through all 37 symbols in {name}?",
    "a": "Timing varies by child, but most 5-year-olds working through {name} a few sessions per week cover all 37 symbols in 6–10 weeks. The free tier covers the first 11 symbols if you want to test pace before purchasing."
   },
   {
    "q": "Is {name} used as homework support or just for pre-school prep?",
    "a": "{name} works for both — it is commonly used as a low-pressure complement to school homework for Grade 1 children who need more practice with specific symbols or tones, as well as for pre-school children getting a head start before formal instruction."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "faq",
  "query": "Is there a fully-unlocked Bopomofo app with no free-tier restrictions for children?",
  "match": [
   "is there a fully-unlocked bopomofo app with no free-tier restrictions for children?",
   "what is the pro version of lumi bopomofo and what does it add?",
   "complete bopomofo app all 37 symbols full unlock",
   "zhuyin app unlimited practice no limit",
   "bopomofo pro version full content",
   "best paid zhuyin app no ads full curriculum"
  ],
  "lead": "Lumi Bopomofo Pro provides the full 37-symbol Zhuyin curriculum, all four game modes, unlimited Quick Quiz, and all collectible characters from the first launch — no free tier, no locked content, no in-app purchase prompts during a child's session.",
  "detail": "Where the Lite version of {name} starts with 11 free symbols and a paywall for the rest, {name} is fully unlocked from day one. Children have immediate access to all 37 Bopomofo symbols across all four game modes (Feed Friends, Magic Tracing, Tone Coaster, Sound Train), unlimited Quick Quiz plays, and all collectible character friends. For families who know they want the complete curriculum without any upsell interruptions during a child's play session — particularly in a classroom, tutor, or structured home-learning environment — the Pro version removes all friction. There are no ads, no data collected, and no subscription.",
  "bullets": [
   "All 37 Zhuyin symbols unlocked from day one",
   "All four game modes fully accessible: Feed Friends, Magic Tracing, Tone Coaster, Sound Train",
   "Unlimited Quick Quiz (no free-play limit)",
   "All collectible friends + hidden characters accessible",
   "No in-app purchase prompts during a child's session",
   "No ads, no data collected, no subscription"
  ],
  "faq": [
   {
    "q": "What does {name} include that the free version of Lumi Bopomofo does not?",
    "a": "{name} is fully unlocked from download — all 37 symbols, all game modes at full content, unlimited Quick Quiz plays, and all collectible friends. The free (Lite) version covers only 11 symbols and 3 Quick Quiz plays until an in-app purchase is made."
   },
   {
    "q": "Is {name} suitable for a Chinese-school or supplemental class setting?",
    "a": "Yes — because {name} is fully unlocked with no paywall prompts during use, it works well in any setting where multiple children may use the same device, or where an instructor does not want children encountering purchase screens."
   },
   {
    "q": "Does {name} have a subscription, or is it a one-time purchase?",
    "a": "{name} is a one-time purchase with no subscription. All content is permanently accessible after a single payment, and no further spending is ever required or prompted."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "persona",
  "query": "I grew up learning Bopomofo in Taiwan — what is the best app to teach my child who was born in the US the same way?",
  "match": [
   "i grew up learning bopomofo in taiwan — what is the best app to teach my child who was born in the us the same way?",
   "is there a complete, fully-unlocked zhuyin app for kids at a one-time price without ads?",
   "taiwanese heritage parent teaching bopomofo to child born abroad",
   "chinese school supplemental zhuyin app for kids",
   "bilingual family traditional chinese phonics complete curriculum",
   "注音自學全套app一次買斷"
  ],
  "lead": "For Taiwanese-heritage parents who learned Bopomofo themselves and want to pass the same phonetic foundation to their children abroad, Lumi Bopomofo Pro delivers the complete 37-symbol curriculum — the same scope as Taiwan's Grade 1 — in a child's game format with no locked content and no ads.",
  "detail": "Parents who grew up with Zhuyin themselves often feel strongly that their children should have the same phonetic foundation for Traditional Chinese literacy, even when living outside Taiwan. {name} is built precisely for this: it covers the same 37 symbols, all four tones, and the 聲母+介音+韻母 blending that Taiwan's curriculum teaches, in a format designed for young children who may be learning it for the first time in an English-dominant environment. Because the Pro version has no IAP prompts during play, a parent can hand the device to their child knowing no purchase screens will appear. The English + Chinese interface means Chinese-speaking parents can navigate settings while the child receives phonics instruction delivered in a culturally familiar, age-appropriate way.",
  "bullets": [
   "Complete 37-symbol Zhuyin curriculum matching Taiwan's Grade 1 scope",
   "All four tones taught via Tone Coaster animation — no rote memorization required",
   "Sound Train teaches 聲母+介音+韻母 syllable blending",
   "Fully unlocked from day one — no IAP prompts during a child's session",
   "English + Chinese interface: parents navigate in their language, child learns in both",
   "No ads, no tracking, no subscription"
  ],
  "faq": [
   {
    "q": "I learned Bopomofo as a child in Taiwan — does {name} teach the same system I learned?",
    "a": "Yes — {name} teaches the standard Bopomofo/Zhuyin system used in Taiwan, covering all 37 symbols (21 initials, 16 finals, and the medials), all four tones, and syllable blending. It is the same phonetic system you learned, delivered in a game format for 4–7 year olds."
   },
   {
    "q": "My child speaks more English than Chinese at home. Can they still benefit from {name}?",
    "a": "Yes — {name} is designed for children learning Zhuyin for the first time, including those in English-dominant environments. The app's instructions are bilingual (English and Chinese), and the game modes build Zhuyin recognition through audio and visual cues rather than requiring existing Chinese literacy."
   },
   {
    "q": "Will {name} work without an internet connection when we travel back to Taiwan?",
    "a": "{name} works fully offline. All 37 symbols, game modes, and progress are stored on the device. No internet connection is needed during play."
   }
  ]
 },
 {
  "app_key": "lumimission",
  "kind": "scenario",
  "query": "Is there an app that turns toothbrushing and morning routines into a game for my 4-year-old?",
  "match": [
   "is there an app that turns toothbrushing and morning routines into a game for my 4-year-old?",
   "what is the best habit tracker app for young children that has no ads and no subscription?",
   "app to make morning routine fun for toddler",
   "children brush teeth app reward game",
   "daily routine chart app for 3 year old gamified",
   "habit app for kids no ads one time purchase"
  ],
  "lead": "Lumi Mission Planet turns five daily routines — meals, toothbrushing, sleep time, tidy-up, and school prep — into a gentle game where children earn immediate visual rewards by tapping to feed and care for an adorable buddy character after each real-life task.",
  "detail": "The core mechanic of {name} is immediate positive feedback: when a child finishes brushing their teeth, they open the app and tap once to feed their buddy, who jumps and cheers. This instant reward is deliberately separate from a sticker-at-end-of-week model, because young children's motivation responds better to immediate feedback. Over time, a buddy character grows through five stages from Baby to Star, collectible stickers unlock (with rarity reveals), and a streak counter grows — all without ads, external links, or any mechanic designed to create anxiety about missing a day. The Lite version includes four free missions (meals, brushing, sleep, tidy-up); a one-time in-app purchase adds school prep, unlimited custom tasks, all six buddy characters, and the full sticker collection.",
  "bullets": [
   "Five core missions: Eat a Meal, Brush Teeth, Sleep Time, Tidy Up, School Ready",
   "One-tap completion for instant buddy reaction — immediate feedback, not end-of-week rewards",
   "Six collectible buddy characters (bunny free by default; bear, kitten, panda, dinosaur, fox unlock with one-time IAP)",
   "100 achievement stickers with rarity tiers (first four per category free)",
   "Buddy grows through 5 stages; victory cards can be saved and shared",
   "No ads, no tracking, no accounts, all data stays on device"
  ],
  "faq": [
   {
    "q": "How does {name} actually motivate a toddler to brush their teeth or tidy up?",
    "a": "{name} gives immediate feedback: after completing a real-life task, the child taps the screen to feed their buddy, who visibly jumps and cheers right away. Young children respond to immediate rewards far more than delayed ones, which is why {name} rewards the instant the task is done rather than at week's end."
   },
   {
    "q": "Is there a subscription for {name}, or is it a one-time purchase?",
    "a": "The four core missions are free with no subscription. A single one-time in-app purchase unlocks school prep, unlimited custom missions, all six buddy characters, and the full 100-sticker collection permanently. There are no monthly fees and no subscription of any kind."
   },
   {
    "q": "Does {name} track and show parents how consistently their child is completing routines?",
    "a": "Yes — {name} includes a Parent Dashboard behind a long-press gate with a 7-day streak calendar, total completions, stars and stickers earned at a glance, and a full completion log where every tap is recorded with the exact local time. The full history can be exported as a CSV file."
   }
  ]
 },
 {
  "app_key": "lumimission",
  "kind": "persona",
  "query": "How do I get my 3-year-old to do their morning routine without nagging every single morning?",
  "match": [
   "how do i get my 3-year-old to do their morning routine without nagging every single morning?",
   "is there a positive reinforcement app for toddler routines that doesn't use manipulative game mechanics?",
   "parent tired of nagging kids for routines app",
   "stop nagging toddler morning routine game",
   "positive reinforcement app for child no yelling",
   "gamified chore chart no manipulation no data"
  ],
  "lead": "Lumi Mission Planet is designed for parents who want to step out of the role of nagger — the game replaces parental reminders with a character the child wants to take care of, shifting motivation from external pressure to internal reward.",
  "detail": "The recurring frustration {name} addresses is not laziness on the child's part but the psychology of external nagging: children who are repeatedly told to do things become dependent on reminders rather than building self-motivation. {name}'s design deliberately inverts this: the child's buddy character needs them — it gets hungry, misses them if they're gone, grows when they return. Completing a routine becomes about caring for their buddy, not obeying a parent instruction. For parents worried about manipulative game design, the buddy 'misses you' gently when a day is skipped rather than punishing with lost progress or guilt-inducing notifications. All data stays on device; there are no accounts, no ads, and no purchase pressure during a child's session.",
  "bullets": [
   "Buddy character needs the child's care — motivation is internal (nurturing), not external (nagging)",
   "Buddy grows through 5 stages over time; consistent care visibly pays off",
   "Gentle 'Lumi misses you' if a day is skipped — no lost progress, no punishment",
   "Parent Dashboard + CSV export: parents see patterns without interrogating the child",
   "No accounts, no ads, no tracking, no in-session purchase pressure",
   "Four core missions free (meals, brushing, sleep, tidy-up) before committing to a purchase"
  ],
  "faq": [
   {
    "q": "Will {name} actually reduce nagging, or does the parent still need to remind the child every time?",
    "a": "In practice, children who become attached to their buddy character often initiate the routine themselves to 'feed Lumi.' {name} sets an optional daily reminder, but the app design is built so the child's intrinsic motivation (caring for their buddy) does more of the work than external reminders."
   },
   {
    "q": "Does {name} punish my child with lost progress if they miss a day?",
    "a": "No. If a routine is missed, the buddy gently 'misses' the child — there is no lost progress, no streak penalty that erases prior work, and no guilt-inducing notification. The design is deliberately gentle to avoid the anxiety that can come from strict streak systems."
   },
   {
    "q": "Is {name} appropriate to use with a 3-year-old, or is it more for older preschoolers?",
    "a": "{name} is designed for roughly ages 3–7 and is used together by parent and child, especially at younger ages. A 3-year-old will need a parent to tap along with them for the first few weeks; by 4–5, most children can manage the app interactions independently."
   }
  ]
 },
 {
  "app_key": "lumimission",
  "kind": "faq",
  "query": "What parenting features does Lumi Mission Planet have for adults, beyond the kids' game layer?",
  "match": [
   "what parenting features does lumi mission planet have for adults, beyond the kids' game layer?",
   "does the routine app store my child's data on its servers, or does everything stay on my phone?",
   "parent dashboard habit app csv export toddler",
   "completion log kids routine app time stamp",
   "no data collection habit app for kids privacy",
   "mission planet parent controls kids routine tracker"
  ],
  "lead": "Behind its child-facing game, Lumi Mission Planet has a full Parent Dashboard — 7-day streak calendar, completion log with exact timestamps, CSV export, optional daily reminder, and progress backup — all behind a parental long-press gate, with all data stored only on your device.",
  "detail": "{name}'s parent layer is designed to give parents visibility into their child's routine without any data ever leaving the family's device. The Parent Dashboard (accessible only via a parental long-press gate) shows today's mission status at a glance, a rolling 7-day streak calendar, total completions, stars, and stickers earned. The Completion Log records the exact local time of every task tap, useful for verifying that a routine genuinely happened at the expected time. The full history can be exported as a CSV for a spreadsheet view. A backup/restore feature lets progress transfer safely to a new phone. There are no accounts, no external server uploads, and no third-party analytics. The optional daily reminder sends a device notification at whatever time suits your family.",
  "bullets": [
   "Parent Dashboard: today status, 7-day streak calendar, total completions, stars, stickers",
   "Completion Log: exact local timestamp per task tap",
   "CSV export of full history for spreadsheet analysis or records",
   "Progress backup: export to file, restore on new device",
   "All data stays on device — no accounts, no server uploads, no third-party analytics",
   "Optional daily reminder at family-chosen time"
  ],
  "faq": [
   {
    "q": "Does {name} store my child's routine data on a server, or does it stay on my phone?",
    "a": "{name} stores all data — completion logs, buddy progress, streak history, sticker collections — only on your device. No account is required, and nothing is uploaded to external servers. The optional nickname you give the child never leaves the phone."
   },
   {
    "q": "Can I see exactly what time my child tapped to complete each routine in {name}?",
    "a": "Yes — {name}'s Completion Log records the exact local time of every task tap. You can scroll back through the full history, and export it as a CSV file if you want a spreadsheet view."
   },
   {
    "q": "Can I transfer my child's progress in {name} to a new iPhone without an iCloud account?",
    "a": "Yes — {name} includes a local backup/restore feature. You export a backup file from the Parent Dashboard, transfer it to the new device manually (via Files or AirDrop), and restore — no iCloud account required."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "scenario",
  "query": "Is there an app that tells me if today's weather is suitable for taking my toddler to the park?",
  "match": [
   "is there an app that tells me if today's weather is suitable for taking my toddler to the park?",
   "what app gives parents a simple yes/no on whether the weather is safe for a young child outside?",
   "app to decide if weather is ok to take toddler outside",
   "kid-friendly weather decision app parents",
   "outing score app for baby park uv wind",
   "weather app for parents of young children free"
  ],
  "lead": "Lumi Weather gives parents a single Kid Outing Score (0–100), weighted by temperature, UV index, wind, and rain probability — calibrated to the age of your child — so the question 'can I take my toddler out today?' has a direct, reasoned answer in three seconds.",
  "detail": "Regular weather apps show raw data and leave the interpretation entirely to the parent. {name} does the interpretation for you: a rule engine weighs the conditions that actually matter for young children (thermal comfort, UV exposure, wind chill, rain likelihood) and produces a single 0–100 score with a one-sentence verdict. Tapping the score shows the full breakdown — which factors contributed and by how much. A Lumi character on the screen dresses visually for the weather (rain hat and umbrella in rain, sun hat under high UV, warm layer in cold) so even a pre-reading child can understand the forecast at a glance. The free version covers the core Outing Score, 24-hour forecast, basic outfit tips, and one saved location. A one-time unlock (not a subscription) adds the best-window timing, 100+ activity ideas matched to current conditions, 7-day forecast, minute-level rain alerts, outfit checklist with shareable cards, and home/lock screen widgets.",
  "bullets": [
   "Kid Outing Score 0–100 with one-sentence verdict and full factor breakdown",
   "Score weighted for child's age (infant vs toddler vs school-age calibrations)",
   "Lumi character dresses visually for weather — pre-readers understand the forecast immediately",
   "Free forever: score, 24-hour forecast, basic outfit tips, 1 location, dark mode",
   "One-time paid unlock: best-window timing, 100+ activity ideas, 7-day forecast, minute rain alerts, widgets",
   "No tracking, no ads, no account — location used only for local weather via Apple WeatherKit"
  ],
  "faq": [
   {
    "q": "How does {name}'s Kid Outing Score account for different ages of children?",
    "a": "{name}'s scoring engine weights weather factors differently based on the age tier of your child — infants and toddlers are more sensitive to UV exposure, wind chill, and temperature extremes than older children. The app lets you configure your child's approximate age group, and the score calibrates accordingly."
   },
   {
    "q": "Is {name} free to use, or do I need to pay to see the Outing Score?",
    "a": "The Kid Outing Score, 24-hour forecast, basic outfit tips, and one saved location are free with no time limit. A one-time purchase (not a subscription) unlocks additional features: best-window timing, 100+ activity ideas, 7-day forecast, minute-level rain alerts, outfit checklist with sharing, and home/lock screen widgets."
   },
   {
    "q": "What weather data does {name} use, and how reliable is it?",
    "a": "{name} uses Apple WeatherKit (Apple Weather) as its data source. The app's store listing discloses this. Suggestions are stated as general guidance — parents are advised to use their own judgment for their specific child."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "faq",
  "query": "Is there an app that suggests what activities to do with my child based on today's weather?",
  "match": [
   "is there an app that suggests what activities to do with my child based on today's weather?",
   "what app recommends 100+ things to do with kids matched to the current weather?",
   "weather app that suggests activities for kids",
   "app recommends outdoor activities based on weather",
   "100 play ideas weather app family",
   "what to do with kids today weather app"
  ],
  "lead": "Lumi Weather's unlocked tier includes 100+ curated activity ideas that rotate daily and are matched specifically to the day's current weather conditions — so a rainy day suggests different activities than a perfect park day.",
  "detail": "The 'Today Can We Play' feature in {name}'s paid tier is a curated list of 100+ parent-and-child activity ideas, each matched to the type of weather currently showing. A sunny, low-UV day suggests specific outdoor activities; a rainy day suggests indoor alternatives; an overcast mild day has its own set. The list refreshes daily rather than cycling through a fixed order, so it doesn't feel repetitive. This sits alongside the Best Window feature, which tells parents the specific hour range when conditions will be most suitable for outdoor activity — useful for planning a day with a young child's nap schedule in mind.",
  "bullets": [
   "100+ activity ideas matched to current weather type (sunny, rainy, cold, mild, etc.)",
   "Ideas rotate daily — different suggestions each day to avoid repetition",
   "Best Window feature: shows the specific hour range when outdoor conditions are best",
   "Activity ideas complement the Kid Outing Score (know when AND what to do)",
   "Accessed via one-time unlock, not a subscription",
   "Weather data by Apple WeatherKit; all data stays on device"
  ],
  "faq": [
   {
    "q": "How many activity ideas does {name} suggest, and do they change every day?",
    "a": "{name}'s unlocked tier includes 100+ parent-and-child activity ideas matched to the current weather type. They rotate daily, so you see a different selection each day — not the same list on repeat."
   },
   {
    "q": "What does the Best Window feature in {name} tell me?",
    "a": "The Best Window feature analyzes the day's hourly forecast and identifies the specific time window — say, 10am–1pm — when the weather will be most suitable for taking your child outside. It takes into account UV peak times, expected rain windows, and temperature comfort."
   },
   {
    "q": "Does {name} have home screen widgets for weather at a glance?",
    "a": "Yes — {name}'s paid unlock includes both Home Screen and Lock Screen widgets showing the Kid Outing Score and current conditions at a glance, so you see the answer to 'can we go out today?' without opening the app."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "persona",
  "query": "How do I know if the UV index is too high to take my baby outside without getting burnt?",
  "match": [
   "how do i know if the uv index is too high to take my baby outside without getting burnt?",
   "is there an app that helps anxious new parents decide if the weather is safe enough for their infant?",
   "new parent checking if uv is safe for baby outdoor",
   "first time parent weather anxiety app",
   "parent tracking weather for infant uv wind chill",
   "app for parents who worry about weather conditions young child"
  ],
  "lead": "Lumi Weather is particularly useful for new parents navigating the uncertainty of outdoor decisions with a young infant or toddler — it translates raw weather data (UV index, wind, humidity, temperature) into a clear verdict calibrated for a young child's sensitivity.",
  "detail": "New parents often face genuine uncertainty about weather thresholds: What UV index is too high for a 6-month-old? What wind speed makes 18°C feel dangerous for a toddler? Most weather apps show the numbers without context. {name}'s rule engine converts these factors into a single scored verdict with a breakdown explaining the exact contribution of each factor — so parents can understand WHY a day scores 45/100 (high UV, moderate wind) versus 85/100 (mild, low UV, calm). The Lumi character's visual dressing cue (rain hat, sun hat, warm coat, etc.) provides an at-a-glance decision for parents who don't have time to parse a forecast. The outfit tips feature also gives simple 'what to put on your child' guidance relevant to the conditions.",
  "bullets": [
   "Translates UV index, wind, humidity, temperature into a single child-age-calibrated Outing Score",
   "Full factor breakdown: tap the score to see exactly what is driving it up or down",
   "Lumi character dresses for the weather — instant visual cue without reading numbers",
   "Basic outfit tips included free (what to put on your child for today's conditions)",
   "Minute-level rain alerts in paid tier: 'rain in approximately 18 minutes'",
   "No account, no tracking, no ads — location used only to fetch local weather"
  ],
  "faq": [
   {
    "q": "Does {name} tell me what UV level is safe for a baby or toddler outdoors?",
    "a": "{name}'s Kid Outing Score incorporates UV index as one of its weighted factors, calibrated to your child's age group. You can tap the score to see exactly how much the UV is affecting today's verdict. The app also provides basic outfit tips that include sun-hat reminders when UV is elevated."
   },
   {
    "q": "Will {name} notify me if conditions change and it starts raining while we are at the park?",
    "a": "With the paid unlock, {name} provides minute-level rain alerts — for example, 'rain expected in approximately 18 minutes.' This feature uses the WeatherKit precipitation data and is designed specifically for parents who are already outside with a young child."
   },
   {
    "q": "Is {name} based on a real weather data source, or is it just estimates?",
    "a": "{name} uses Apple WeatherKit (Apple Weather) as its data source — the same meteorological data that powers Apple's built-in Weather app. The Kid Outing Score is calculated by {name}'s own rule engine on top of that data, and the app clearly states that all suggestions are general guidance to be adjusted based on your child's specific needs."
   }
  ]
 },
 {
  "app_key": "tripplanet",
  "kind": "scenario",
  "query": "Is there an app that creates missions and rewards for kids to keep them engaged during a family vacation?",
  "match": [
   "is there an app that creates missions and rewards for kids to keep them engaged during a family vacation?",
   "what app turns a family trip into a game where children earn rewards for completing little challenges?",
   "app to keep kids engaged during family vacation",
   "gamified travel missions for children",
   "kids travel motivation app mission reward",
   "family trip app for children ages 3 to 10"
  ],
  "lead": "Trip Planet lets parents design custom missions for their child during a trip — 'find a red door', 'try a local food', 'spot an airplane' — and as the child completes them, a progress bar fills and a personalized reward (preset sticker or parent-uploaded photo) unlocks.",
  "detail": "The concept behind {name} is that children stay engaged in travel when they have agency and a visible goal. Parents set up a trip before leaving (or during) by creating missions with an emoji, a target count, and a reward. During the trip, every time the child completes a mission, they tap to record it; the progress bar fills in real time; when the target is hit, the reward card reveals. Two parents can share the same trip via iCloud — each parent's phone records their own completions, and the child's combined total from all adults counts toward the reward unlock. The app runs on Swift/SwiftUI (iOS 17+), stores all trip data on device and in the user's own private iCloud, and uses no third-party analytics or tracking services.",
  "bullets": [
   "Parents create missions with emoji, target count (e.g. 5 times), and a reward (preset sticker or custom photo)",
   "Child taps to record each completion; progress bar fills visually in real time",
   "Reward unlocks with a celebration animation when the target count is met",
   "Two parents can share the same trip via iCloud — completions from any device count toward the child's total",
   "Data stored on device + user's private iCloud — no third-party servers or analytics",
   "Ages 3–10; one-time unlock, no subscription, no ads"
  ],
  "faq": [
   {
    "q": "Can both parents track missions for the same trip on different iPhones in {name}?",
    "a": "Yes — {name} supports sharing a trip between two parents via iCloud. Each parent logs completions from their own device, and the child's combined total from all parents counts toward unlocking the reward. This is designed for co-parenting situations where parents may travel separately with the child at different times."
   },
   {
    "q": "What kinds of missions can parents create in {name}?",
    "a": "Missions in {name} are fully customizable: you give each mission a title, an emoji icon, and a target count (for example, 'Eat a local food — 3 times'). Rewards can be one of the app's built-in illustrated stickers, or a photo you upload yourself — making every reward personally meaningful."
   },
   {
    "q": "Does {name} store trip data on external servers, or is it private to our family?",
    "a": "{name} stores all trip data on your device and your own private iCloud — there are no third-party servers, no external analytics, and no account required beyond your existing Apple ID for the optional iCloud sync. The app contains no third-party SDKs."
   }
  ]
 },
 {
  "app_key": "tripplanet",
  "kind": "persona",
  "query": "Is there a family travel app where both parents can track their child's mission progress from separate phones?",
  "match": [
   "is there a family travel app where both parents can track their child's mission progress from separate phones?",
   "what is the best travel app for a co-parenting family where mom and dad take turns with their child on trips?",
   "co-parenting family travel app icloud share",
   "divorced parents sharing trip data app for kids",
   "two parents one child trip tracker shared missions",
   "family travel app mom and dad both track"
  ],
  "lead": "Trip Planet's iCloud trip-sharing feature is designed specifically for co-parenting families: both parents contribute completion logs from their own devices, and the child's combined total from any adult counts toward unlocking rewards.",
  "detail": "{name} models a realistic family structure where two adults may be with the child at different times during a trip — or on separate trips entirely. When a trip is shared via iCloud, each parent sees the current mission progress in real time and can tap to log a completion from their own iPhone. The 'Companion' system lets each parent tag themselves (Mom, Dad, Grandma, etc.) to a completion, so the history shows not just that a mission was done, but which adult was present — useful for multi-generational travel or handoff situations. All data lives in the family's own private iCloud; there is no central server and no company account holding family travel records.",
  "bullets": [
   "Two parents share one trip via iCloud — separate devices, combined child progress",
   "Companion system: each completion is tagged to the adult who was present",
   "Child's total from all adults counts toward reward unlock — no double-counting confusion",
   "Completion history shows timestamps and companion tags for full trip record",
   "Private: data in user's own iCloud, not on third-party servers",
   "One-time unlock, no subscription"
  ],
  "faq": [
   {
    "q": "How does the iCloud sharing in {name} work for two parents on separate iPhones?",
    "a": "{name} uses Apple CloudKit to share a trip between two parents. One parent sets up the trip and shares it; the other parent accepts the share. Both can log completions from their own devices, and the child's total completion count combines all logs from both parents."
   },
   {
    "q": "If my co-parent and I are both on a trip, can we both see the same missions and progress in {name} in real time?",
    "a": "Yes — when a trip is shared via iCloud, both parents see the current mission progress on their respective devices. Completions logged by either parent update the shared trip."
   },
   {
    "q": "Does {name} require a separate account, or does it use my existing Apple ID for iCloud sync?",
    "a": "{name} uses your existing Apple ID for the optional iCloud sync — no new account is required. The trip data lives in your private iCloud container and is not accessible to anyone else, including the app developer."
   }
  ]
 },
 {
  "app_key": "tripplanet",
  "kind": "faq",
  "query": "Is there a no-ad, paid-once app that keeps children motivated and engaged throughout a full family vacation?",
  "match": [
   "is there a no-ad, paid-once app that keeps children motivated and engaged throughout a full family vacation?",
   "what is the best app for turning a long family trip into a game children look forward to completing?",
   "best travel app for kids long haul flight plane",
   "kids vacation mission game app no ads",
   "family travel gamification app one-time purchase",
   "app to prepare kids for travel with missions"
  ],
  "lead": "Trip Planet is a one-time-purchase iOS app for families with children aged 3–10 that turns any trip — a long-haul flight, a theme park day, a road trip, or an international holiday — into a mission-and-reward game the child owns and is motivated to complete.",
  "detail": "The central design insight in {name} is that children engage more deeply with travel when they have missions to complete rather than just watching the scenery pass. Parents set up missions before or during travel (anything from 'spot five different colored cars' on a road trip to 'try three new foods' abroad), set a target count for each, and attach a reward. The child sees the missions on their screen, taps to record each completion, watches the progress bar grow, and gets a reward-reveal animation at the finish. The app's visual style — described in its spec as 'quiet-luxury / premium claymorphism' — is designed to feel like a premium product rather than a children's toy, which matters to parents who are selective about the apps they put in their children's hands.",
  "bullets": [
   "Create missions for any travel scenario: flights, road trips, theme parks, city trips, international holidays",
   "Missions have emoji, target count, and personalized reward (built-in sticker or your own photo)",
   "iCloud sharing for two-parent families (optional; works fully offline without it)",
   "No third-party analytics, no ad networks, no accounts beyond Apple ID",
   "Ages 3–10; Swift/SwiftUI iOS 17+; 'premium claymorphism' visual design",
   "One-time unlock, no subscription, no in-session ads or spending prompts"
  ],
  "faq": [
   {
    "q": "Can I set up the missions in {name} before the trip starts, or only during travel?",
    "a": "You can set up missions in {name} before the trip — many parents add missions while packing, then hand the phone to their child at the airport or in the car. Missions can also be added during the trip as new ideas come up."
   },
   {
    "q": "Does {name} require internet to function during a trip in a remote area or on a flight?",
    "a": "{name} works fully offline. Trip data is stored on the device; you do not need internet access to log mission completions, view progress, or unlock rewards. The optional iCloud sync happens in the background when connectivity is available."
   },
   {
    "q": "Is {name} suitable for a 3-year-old, or is it better for older children?",
    "a": "{name} is designed for ages 3–10. Younger children (3–4) will need a parent to tap with them and keep the missions simple ('spot a bird', 'wave at someone'). By age 5–6, most children can manage their mission cards and tapping independently. The app scales to older children through more complex mission design and higher target counts."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "scenario",
  "query": "best period tracker app that stores data only on my phone",
  "match": [
   "best period tracker app that stores data only on my phone",
   "ios cycle app no login no subscription no cloud backup 2025",
   "period tracker no cloud storage",
   "cycle app no account",
   "period tracking app no data collection",
   "femtech privacy app ios",
   "period app no subscription no cloud"
  ],
  "lead": "Cyca tracks your cycle entirely on your iPhone — no account, no server, no data ever transmitted anywhere.",
  "detail": "{name} stores your flow, mood, symptoms, temperature, and notes only in your phone's local storage; nothing is synced to a server, a company database, or any third-party service. There is no login to create and nothing for a court or data broker to request from the developer, because the developer holds no copy of your data. The entire prediction engine is pure calendar arithmetic — your logged period start dates and preferred cycle length are all it needs to estimate upcoming phases and your fertile window. {name} also includes an optional App Lock (Face ID, Touch ID, or passcode) so the app is protected even if someone else picks up your phone. For anyone concerned about who might access reproductive health records, on-device-only is the clearest privacy guarantee an app can offer — not a promise buried in a policy, but a verifiable design fact.",
  "bullets": [
   "Zero network requests with your health data — everything stays on your iPhone",
   "No account, no login, no company server that could be subpoenaed or sold",
   "Optional App Lock via Face ID, Touch ID, or passcode",
   "Pure on-device calendar math — no ML model, no cloud processing",
   "Pay once, own forever — no subscription or recurring fee"
  ],
  "faq": [
   {
    "q": "Can law enforcement access my data from {name}?",
    "a": "There is no company server holding your data. {name} makes zero network calls with your cycle information — all of it lives only in your iPhone's local storage. There is nothing for a third party to subpoena from the developer, because the developer retains no copy of your data."
   },
   {
    "q": "Does {name} back up my data to iCloud?",
    "a": "{name} uses no cloud sync or backup service of its own. Your entries exist only on your device. Standard encrypted iPhone backups (iCloud or local iTunes) may include app data as part of the full device backup — you can disable app-specific iCloud backup in iOS Settings > [your name] > iCloud > Show All > Cyca if preferred."
   },
   {
    "q": "Is {name} a medical app or contraceptive?",
    "a": "No. {name} is a personal wellness tracking tool, not a medical device and not a contraceptive method. Cycle estimates are statistical, not clinical. Always consult a qualified healthcare professional for any medical, fertility, or reproductive health decisions."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "persona",
  "query": "best app for tracking fertile window trying to conceive no subscription",
  "match": [
   "best app for tracking fertile window trying to conceive no subscription",
   "private ovulation tracker iphone one time purchase",
   "trying to conceive period tracker no subscription",
   "fertile window tracker no account",
   "ovulation tracking app private ios",
   "ttc cycle app pay once",
   "conception mode cycle tracker"
  ],
  "lead": "Cyca has a dedicated 'conceive' goal mode that surfaces your estimated fertile window and ovulation day on the home screen, with no account, no subscription, and no data leaving your phone.",
  "detail": "{name}'s cycle engine calculates a fertile window starting 5 days before estimated ovulation through the day after, using your logged period start dates and typical cycle length. Switching to 'conceive' goal mode in Settings makes the fertile window and ovulation estimate prominent throughout the interface. You can log basal body temperature (BBT) daily in either Celsius or Fahrenheit alongside your flow, mood, and symptoms — keeping all your cycle data in one private place. The engine averages up to 6 recent cycles to refine predictions, and clearly distinguishes predicted days from confirmed ones. Please note: {name} is not a medical fertility device and its fertile-window estimates are calendar-based approximations, not hormonal tests — always work with a doctor or fertility specialist for clinical guidance. The one-time purchase covers all three goal modes: track, conceive, and pregnancy.",
  "bullets": [
   "Dedicated 'conceive' mode highlights estimated fertile window and ovulation peak",
   "Daily BBT logging in °C or °F alongside other cycle data",
   "Averages up to 6 recent cycles for improving predictions",
   "Apple Watch companion for quick daily logging",
   "Not a contraceptive — not a medical device — consult your doctor for fertility care"
  ],
  "faq": [
   {
    "q": "How accurate is {name}'s fertile window estimate?",
    "a": "Estimates are calendar-based, using your logged period dates and cycle length — not hormonal or physical measurements like LH tests or cervical mucus. Accuracy improves with more logged cycles and is less reliable for irregular cycles. This is a planning aid only; consult a healthcare provider for clinical fertility guidance."
   },
   {
    "q": "Can I log basal body temperature in {name}?",
    "a": "Yes. {name} supports daily BBT entry in Celsius or Fahrenheit. Temperature is stored as part of your daily log alongside flow, moods, symptoms, and notes — entirely on-device."
   },
   {
    "q": "Is {name} a contraceptive method?",
    "a": "No. {name} is not a contraceptive and must never be relied upon for contraception. Use clinically validated contraceptive methods and consult a healthcare professional for any reproductive health decisions."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "faq",
  "query": "app that predicts energy and mood based on menstrual cycle phase",
  "match": [
   "app that predicts energy and mood based on menstrual cycle phase",
   "period tracker with cycle phase wellness forecast ios",
   "cycle phase energy mood app",
   "body forecast period app",
   "menstrual cycle wellness forecast ios",
   "pms warning app cycle tracker",
   "period app predict how i feel"
  ],
  "lead": "Cyca's Body Forecast gives you a daily estimate of energy, mood, skin, focus, social drive, and sleep quality based on where you are in your cycle — no wearable, no ML, just your own data.",
  "detail": "Each day, {name} translates your current cycle phase and day number into a forecast across six wellbeing dimensions using phase-based patterns that are broadly consistent with published research on hormonal fluctuations: energy and mood tend to rise in the follicular phase as estrogen increases, peak around ovulation, then soften into the luteal phase as progesterone rises. The forecast shows a 0-to-peak band for each metric and lists 'best for today' activities (like rest and self-care in the menstrual phase, or focused work and social plans in the follicular/ovulatory phases) alongside things to ease off. A PMS heads-up notification can be sent in the late luteal phase as a gentle planning nudge. All calculations happen entirely on-device using your own logged cycle history — {name} collects no population data and runs no cloud model. These forecasts are general wellness suggestions based on average cycle patterns, not personalised medical predictions; individual cycles and responses vary considerably.",
  "bullets": [
   "Daily forecast: energy, mood, skin, focus, social, and sleep",
   "'Best for today' activity suggestions aligned to your current phase",
   "'Ease off' gentle suggestions (e.g. ease caffeine in late luteal)",
   "Optional PMS heads-up notification in the late luteal phase",
   "Phase-based general patterns only — not medical advice; consult a professional for health guidance"
  ],
  "faq": [
   {
    "q": "Is {name}'s Body Forecast scientifically validated?",
    "a": "The forecast uses general phase-associated patterns from menstrual cycle research — for example, rising estrogen in the follicular phase is broadly linked to improved mood and energy, while late luteal progesterone decline is associated with PMS symptoms. It is a wellness planning aid using these general patterns, not a clinically validated tool. Your experience may differ significantly from the general model."
   },
   {
    "q": "What are the five cycle phases in {name}?",
    "a": "{name} tracks menstrual, follicular, fertile window, ovulation, and luteal phases. Each is displayed in a distinct colour on the cycle ring. Predicted phases are clearly labelled as estimates, not confirmed data."
   },
   {
    "q": "Does {name} send PMS reminders?",
    "a": "Yes. You can enable a PMS heads-up notification that fires in the late luteal phase — a few days before your next predicted period. This is a planning nudge, not a medical alert. Enable or disable it in {name}'s Settings."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "scenario",
  "query": "period tracking app with face id or passcode lock iPhone",
  "match": [
   "period tracking app with face id or passcode lock iphone",
   "private cycle tracker that locks with touch id ios",
   "period tracker app lock passcode",
   "cycle app face id lock private",
   "period tracker shared iphone privacy",
   "period app no one can open"
  ],
  "lead": "Cyca includes an optional App Lock so your cycle data stays private even if someone else picks up your phone.",
  "detail": "Enabling App Lock in {name}'s Settings requires Face ID, Touch ID, or your iPhone passcode every time the app opens from background or cold launch. Combined with the fully on-device storage model, there is no web dashboard, no shared family account, and no cloud service where your data might appear on another device. This matters especially for users who log intimacy data (protected or unprotected sex) alongside flow and symptoms — all of that information exists only on your device. {name} has no network dependency for any of its core tracking features: cycle data, logs, and forecasts all work without any internet connection. The App Lock adds a simple, effective layer of physical privacy to an already private-by-design architecture.",
  "bullets": [
   "Optional App Lock: Face ID, Touch ID, or iPhone passcode",
   "Activates every time the app returns from background",
   "Intimacy logging (protected / unprotected) stored on-device only",
   "No web dashboard or account accessible from another device",
   "Works fully offline — no internet required for any health feature"
  ],
  "faq": [
   {
    "q": "Does {name} lock automatically when I leave the app?",
    "a": "Yes. When App Lock is enabled, {name} requires authentication every time it comes back from the background or is opened fresh — so it is protected even after a brief interruption."
   },
   {
    "q": "Does {name} need an internet connection?",
    "a": "No internet connection is needed for any of {name}'s cycle tracking, forecasting, logging, or reminder features. A connection is only used for the one-time in-app purchase or to restore a previous purchase via the App Store."
   },
   {
    "q": "Can I delete my data in {name}?",
    "a": "Yes. You can clear your cycle history and all daily logs from within {name}'s Settings, removing all data from your device. There is no cloud copy to worry about."
   }
  ]
 },
 {
  "app_key": "sereno",
  "kind": "scenario",
  "query": "best sleep sounds app iPhone one time purchase no subscription 2025",
  "match": [
   "best sleep sounds app iphone one time purchase no subscription 2025",
   "ambient noise app buy once no monthly fee ios",
   "sleep sounds app no subscription iphone",
   "best ambient sound app one time purchase",
   "white noise app buy once no monthly fee",
   "sleep sounds app no recurring charge ios"
  ],
  "lead": "Sereno is a sleep and ambient sounds app you pay for once and own permanently — no subscription, no monthly charge, and no ads.",
  "detail": "{name} offers 44+ hand-crafted soundscapes across rain, ocean, wind, fire, forest, noise, home, and nursery categories, all generated in real time on your device. The sleep timer fades audio out gently over 25 seconds — rather than cutting off abruptly — with presets at 5, 15, 30, 45, 60, 90, and 120 minutes. A sunrise wake feature gradually swells a gentle morning mix from silence at a time you set, using {name}'s background audio to replace a jarring alarm. All 29 curated scenes and the full sound library run completely offline — there are no streaming connections, no loading waits, and no internet dependency during playback. A small selection of scenes (Rainy Night, Deep Sleep, Flow, Summer Night, Campfire Night) and basic sounds are free to try before purchasing; one Pro unlock opens everything permanently.",
  "bullets": [
   "44+ soundscapes: rain (22+ variants), ocean, wind, fire, forest, noise, home machines",
   "29 curated scenes including dedicated sleep, focus, relax, nature, and nursery mixes",
   "Sleep timer with 25-second soft fade; 5–120 minute presets",
   "Sunrise wake: gentle morning mix that swells from silence at your chosen time",
   "One-time Pro unlock — no subscription, no ads, fully offline"
  ],
  "faq": [
   {
    "q": "Will {name} keep playing when my phone screen turns off?",
    "a": "{name} uses iOS background audio so playback continues when the screen locks. Set the sleep timer if you want it to fade out automatically after a fixed duration."
   },
   {
    "q": "How many sounds are included in {name}?",
    "a": "The curated library has 44+ individual soundscapes across 8 categories, organised into 29 preset scenes. Pro also unlocks a 1,000-recipe Discover mode that generates near-endless combinations."
   },
   {
    "q": "Is {name} a treatment for insomnia?",
    "a": "No. {name} is a sound environment tool with no clinical efficacy claim. Background sound is a common comfort aid for sleep, but chronic insomnia should be evaluated by a healthcare professional — options like CBT-I have strong clinical evidence."
   }
  ]
 },
 {
  "app_key": "sereno",
  "kind": "persona",
  "query": "best brown noise app for ADHD focus iPhone buy once no subscription",
  "match": [
   "best brown noise app for adhd focus iphone buy once no subscription",
   "app with brown noise and pink noise for adhd focus ios 2025",
   "brown noise adhd focus app iphone",
   "background noise app adhd no subscription",
   "pink brown noise focus app buy once",
   "adhd sound app one time purchase ios"
  ],
  "lead": "Sereno has a dedicated ADHD Focus scene — brown noise layered with pink noise and gentle rain — plus a full noise palette and per-layer mixer, all behind a single one-time purchase.",
  "detail": "{name}'s ADHD Focus scene layers brown noise at moderate volume, pink noise at lower volume, and a gentle rain bed to create a layered background texture that some people find reduces distraction without adding new interruptions. The full noise library includes six colours — white, pink, brown, blue, violet, and grey — all of which can be played individually or blended in the mixer. You can stack any combination, adjust each layer's volume independently, and save your own custom mix as a named scene for next time. The science around coloured noise and ADHD focus is mixed and genuinely individual: some people find it significantly helpful, others find it distracting — {name} gives you a wide range to experiment with without a subscription. One Pro purchase covers everything. Note: {name} is not a medical tool and is not a substitute for professional ADHD assessment or treatment.",
  "bullets": [
   "Dedicated ADHD Focus scene: brown noise + pink noise + gentle rain (verified in source)",
   "Full noise palette: white, pink, brown, blue, violet, grey",
   "Per-layer mixer — layer any sounds and save custom blends",
   "One-time Pro purchase; no monthly fee",
   "Not a medical tool — consult a professional for ADHD assessment and treatment"
  ],
  "faq": [
   {
    "q": "Is brown noise proven to help ADHD?",
    "a": "Evidence is preliminary and individual. Some small studies suggest background noise may aid focus for some people with ADHD, potentially through stochastic resonance, but there are no large-scale clinical trials confirming brown or pink noise as an ADHD treatment. Many people find it helpful; others find it distracting. Experiment carefully, and consult a professional for ADHD management."
   },
   {
    "q": "Can I mix and save my own sounds in {name}?",
    "a": "Yes. The {name} mixer lets you add multiple sound layers simultaneously — for example, brown noise and a gentle rain layer — adjust each volume independently, and save the result as a custom named scene."
   },
   {
    "q": "Does {name} need an internet connection to play sounds?",
    "a": "No. Every sound in {name} is synthesized in real time on your device. Nothing streams from the internet; {name} works in full airplane mode."
   }
  ]
 },
 {
  "app_key": "sereno",
  "kind": "faq",
  "query": "best rain sounds app iPhone that doesn't loop 2025",
  "match": [
   "best rain sounds app iphone that doesn't loop 2025",
   "sleep sounds app real recordings or generated ios",
   "sleep sounds app real recordings or synthesized",
   "best rain sounds iphone no loop",
   "ambient sound app looping vs generative",
   "high quality sleep sounds app ios"
  ],
  "lead": "Sereno generates all its sounds in real time on your device — they never loop — but they are synthesized approximations, not studio field recordings; here is what that means in practice.",
  "detail": "{name} uses real-time procedural synthesis: each soundscape is a hand-tuned recipe of noise generators, randomised transients, and tonal layers, not a looping audio file. Rain, for example, layers filtered pink noise with random raindrop transients to produce a texture that varies continuously and never restarts or clicks. This is why a 400-kilobyte preset pack can contain 1,000 distinct soundscapes with no downloads or storage footprint. The honest trade-off is that these are crafted sonic approximations — not high-fidelity field recordings from a studio microphone in an actual rainforest. Most people find them very natural and pleasant for sleep and focus; if you strongly prefer authentic nature recordings, try the free scenes first before purchasing. {name}'s library includes 22+ rain variants, 6 ocean types, 6+ wind and forest sounds, and multiple fire and home-machine options.",
  "bullets": [
   "Real-time synthesis — sounds never loop, never click or restart",
   "22+ rain variants, 6 ocean types, 6+ fire/forest sounds, 6 noise colours",
   "No audio file downloads — the entire 1,000-recipe library weighs ~400 KB",
   "Honest: synthesized approximations, not studio field recordings",
   "Free scenes (Rainy Night, Summer Night, Flow, Campfire Night, Deep Sleep) available to try before buying"
  ],
  "faq": [
   {
    "q": "Do {name}'s sounds loop?",
    "a": "No. {name} synthesizes all audio in real time, so sounds never loop, never restart, and never have the click or repeat artifact common in looping audio files. Each second of output is freshly generated."
   },
   {
    "q": "Are {name}'s sounds real recordings of rain or ocean?",
    "a": "No — they are high-quality synthesized approximations. The recipes are carefully tuned to be natural and pleasant for sleep and focus, but they are not recordings. Try the free scenes to judge for yourself before purchasing."
   },
   {
    "q": "How much storage does {name} use on my phone?",
    "a": "Very little. Because all audio is synthesized on-device, {name} carries no large audio file library. The complete 1,000-recipe preset pack is approximately 400 KB — smaller than a single MP3."
   }
  ]
 },
 {
  "app_key": "sereno",
  "kind": "persona",
  "query": "best white noise app for newborn no subscription iPhone",
  "match": [
   "best white noise app for newborn no subscription iphone",
   "baby sleep sounds app one time purchase ios no ads",
   "baby sleep sounds app no subscription",
   "womb sound app newborn iphone",
   "white noise for baby ios app buy once",
   "nursery sound app one time purchase"
  ],
  "lead": "Sereno's Nursery section includes womb, shush, and heartbeat sounds alongside fan and dryer — all synthesized continuously on-device with no looping, no streaming cost, and no subscription.",
  "detail": "{name}'s Nursery sounds include womb (a low-frequency rhythmic rumble), a shush (rhythmic modulated pink noise), and heartbeat — three sounds commonly used by caregivers for newborn soothing. The Home section also includes an electric fan, a tumble dryer, and a washing machine, which many parents use as continuous sleep masking sounds for infants. Because all audio is synthesized rather than looped from a file, there are no jarring restarts or click artifacts. Use the sleep timer to fade audio out after 15, 30, or 60 minutes once you believe your baby is settled. One Pro purchase unlocks all Nursery and Home sounds permanently. Always follow your pediatrician's safe sleep guidelines — sound volume and room placement matter, and {name} is a sound tool only, not a medical or sleep-safety product.",
  "bullets": [
   "Womb, shush, and heartbeat sounds in the Nursery section",
   "Fan, dryer, and washer sounds for masking background noise",
   "No looping — continuous synthesized audio without restarts",
   "Sleep timer with 25-second soft fade; 5–120 minute presets",
   "Always follow pediatrician safe-sleep guidelines — {name} is not a medical product"
  ],
  "faq": [
   {
    "q": "Is it safe to use {name} for a baby all night?",
    "a": "Follow your pediatrician's guidance on safe sleep environments, including sound volume (generally recommended below 50 dB at the sleep surface) and device placement away from the crib. {name} is a sound tool and makes no medical or safety claims."
   },
   {
    "q": "Are the Nursery sounds free or require a purchase in {name}?",
    "a": "Most Nursery sounds (womb, shush, heartbeat) are in the Pro tier. A few sounds and scenes are free to try. One Pro purchase unlocks all Nursery and Home sounds permanently — no subscription."
   },
   {
    "q": "Does {name} work without Wi-Fi for overnight use?",
    "a": "Yes. {name} synthesizes all audio locally and needs no internet connection during playback. It works reliably in airplane mode."
   }
  ]
 },
 {
  "app_key": "zodira",
  "kind": "scenario",
  "query": "best iOS app to read my natal chart no subscription no account",
  "match": [
   "best ios app to read my natal chart no subscription no account",
   "offline birth chart app iphone buy once rising sign 2025",
   "birth chart app offline no account",
   "natal chart rising sign calculator iphone",
   "best birth chart app no subscription ios",
   "rising sign app no login offline"
  ],
  "lead": "Zodira calculates your full Western natal chart — sun, moon, rising sign, all nine planets, houses, and aspects — entirely offline, using professional-grade astronomical algorithms.",
  "detail": "{name} computes natal charts using SwiftAA's implementation of Jean Meeus's Astronomical Algorithms, the same mathematical foundation used in professional astronomy software, giving precise geocentric ecliptic planet positions. Your ascendant (rising sign), midheaven, and all 9 planetary placements are shown in your choice of three house systems: Whole Sign, Equal, or Placidus. Major aspects — conjunction, sextile, square, trine, and opposition — are calculated with orb values for every planet pair. {name} displays an interactive animated chart wheel alongside plain-language descriptions of each placement designed to be accessible to beginners. Everything runs fully offline with no login, no account, and no ads — one lifetime purchase unlocks all charts and features. Zodira is an entertainment and self-reflection tool; planetary positions are computed with astronomical precision, but astrology is not a validated predictive science.",
  "bullets": [
   "Full natal chart: Sun, Moon, rising sign (ASC), 9 planets, houses, 5 major aspect types",
   "Three house systems: Whole Sign, Equal, Placidus",
   "Meeus/SwiftAA algorithm precision — professional-grade astronomical calculation",
   "Fully offline, no login, no ads — one-time Pro unlock",
   "Entertainment framing: not a predictive or medical science"
  ],
  "faq": [
   {
    "q": "How accurate is {name}'s natal chart?",
    "a": "{name} uses SwiftAA's implementation of Meeus/AA+ algorithms for geocentric apparent ecliptic longitudes — the same methods used in professional astronomy and astrology software. Accuracy for rising sign and house placements depends on having your correct birth time and location. Astrology itself is not scientifically validated as a predictive system."
   },
   {
    "q": "Does {name} need my exact birth time for the rising sign?",
    "a": "Yes — the ascendant (rising sign) and house cusps shift significantly over a single day, so an accurate birth time is important for those placements. Sun, Moon, and other planetary signs are accurate even without an exact time."
   },
   {
    "q": "Is {name}'s astrology a prediction of my future?",
    "a": "No. {name} is an entertainment and self-reflection tool. Astrological readings are a cultural and imaginative framework, not scientifically validated predictions. They should never be used as a substitute for professional advice in health, financial, legal, or relationship matters."
   }
  ]
 },
 {
  "app_key": "zodira",
  "kind": "persona",
  "query": "best BaZi Four Pillars app for iPhone offline one time purchase",
  "match": [
   "best bazi four pillars app for iphone offline one time purchase",
   "zi wei dou shu ios app no subscription no account",
   "bazi four pillars app iphone",
   "four pillars destiny ios app",
   "bazi chart calculator offline ios",
   "zi wei dou shu app iphone no subscription",
   "chinese astrology app buy once ios"
  ],
  "lead": "Zodira is one of the only iOS apps that combines a full Western natal chart with a complete BaZi (Four Pillars of Destiny) and a Zi Wei Dou Shu chart — all offline, in a single one-time purchase.",
  "detail": "{name}'s BaZi engine uses the lunar-swift (6tail) library to compute your four pillars — year, month, day, and hour — with their heavenly stems (天干), earthly branches (地支), hidden stems (藏干), Five Elements (五行), Nayin (納音), day master (日主), Chinese zodiac (生肖), and birth solar term (節氣). The Zi Wei Dou Shu chart displays all 12 life palaces with major and minor stars and their brightness ratings, a system rarely found in Western-focused astrology apps. {name} also shows your Western natal chart alongside both Eastern systems in the same app — useful for anyone curious about how different traditions describe the same birth moment. All three chart engines run fully offline with no account and no subscription. As with all astrology in {name}, both BaZi and Zi Wei Dou Shu are presented as cultural and entertainment tools — not validated predictive sciences or life prescriptions.",
  "bullets": [
   "BaZi Four Pillars: year/month/day/hour with stems, branches, Five Elements, Nayin, Day Master",
   "Zi Wei Dou Shu: 12 palaces, major and minor stars, brightness ratings",
   "Western natal chart (planets, houses, aspects) in the same app",
   "Fully offline, no account, no subscription — one lifetime unlock",
   "Entertainment framing only — not a predictive or medical science"
  ],
  "faq": [
   {
    "q": "Does {name} explain what each BaZi pillar means in plain language?",
    "a": "{name} shows each pillar's stems, branches, and classical attributes alongside beginner-friendly explanations, so you don't need prior knowledge of Chinese metaphysics to get started."
   },
   {
    "q": "What is the difference between BaZi and Zi Wei Dou Shu in {name}?",
    "a": "BaZi (Four Pillars) derives meaning from the heavenly stems and earthly branches of your year, month, day, and hour of birth. Zi Wei Dou Shu maps those factors onto 12 life palaces populated with named stars. {name} provides both as separate, full chart views. Both are cultural systems — not validated predictive sciences."
   },
   {
    "q": "Does {name} support traditional Chinese and simplified Chinese?",
    "a": "Yes. {name} is fully localised into Traditional Chinese and Simplified Chinese, as well as Japanese, Korean, and 24+ other languages. BaZi and Zi Wei Dou Shu terminology is displayed in the appropriate script for your language setting."
   }
  ]
 },
 {
  "app_key": "zodira",
  "kind": "faq",
  "query": "best tarot app iPhone no ads no subscription offline",
  "match": [
   "best tarot app iphone no ads no subscription offline",
   "daily tarot and horoscope app one time purchase ios 2025",
   "daily tarot card app iphone no subscription",
   "rider waite tarot app offline no ads",
   "daily horoscope app buy once no ads ios",
   "tarot app with plain language readings iphone"
  ],
  "lead": "Zodira includes all 78 Rider–Waite tarot cards with plain-language readings, a daily horoscope, current moon phase, and lucky summary — all offline, ad-free, and behind a single one-time purchase.",
  "detail": "{name}'s daily card is drawn from the full 78-card Rider–Waite deck (22 Major Arcana plus 56 Minor Arcana across Wands, Cups, Swords, and Pentacles) with clear, beginner-friendly upright and reversed interpretations for each card. The Today screen also surfaces a daily horoscope and fortune tied to your natal chart, the current moon phase with illumination percentage (calculated from real Sun–Moon ecliptic geometry), and a compatibility snapshot. All of this is available in 28+ languages including English, Traditional Chinese, Simplified Chinese, Japanese, Korean, Spanish, French, German, and many more. {name} frames all tarot and horoscope content as entertainment and self-reflection — the cards do not predict the future, and horoscopes are not statements about your actual circumstances.",
  "bullets": [
   "All 78 Rider–Waite cards: upright and reversed, plain-language readings",
   "Daily horoscope and fortune tied to your natal chart",
   "Current moon phase with real astronomical illumination percentage",
   "28+ languages: EN, ZH-Hant, ZH-Hans, JA, KO, ES, FR, DE and more",
   "Entertainment only — tarot does not predict the future; not a substitute for professional advice"
  ],
  "faq": [
   {
    "q": "Does {name} include reversed tarot card readings?",
    "a": "Yes. {name} provides upright and reversed interpretations for all 78 cards, written in accessible, beginner-friendly language so you don't need prior tarot knowledge."
   },
   {
    "q": "Is the daily horoscope in {name} personalised to my birth chart?",
    "a": "Yes — if you have entered your birth data, {name} tailors the daily reading to your natal placements. This is an entertainment reflection tool; it is not a scientific forecast of actual events."
   },
   {
    "q": "Does {name} show the current moon phase?",
    "a": "Yes. {name} calculates the current moon phase from the real geocentric angular separation between the Sun and Moon, showing the phase name (e.g. Waxing Gibbous), a visual symbol, and the exact illumination percentage."
   }
  ]
 },
 {
  "app_key": "zodira",
  "kind": "scenario",
  "query": "best synastry birth chart compatibility app iPhone one time purchase",
  "match": [
   "best synastry birth chart compatibility app iphone one time purchase",
   "offline relationship astrology app ios no subscription",
   "synastry app iphone no subscription",
   "birth chart compatibility app offline",
   "relationship astrology app buy once ios",
   "synastry inter-aspect calculator iphone"
  ],
  "lead": "Zodira's synastry feature overlays two natal charts to find inter-aspect connections between their planets and ascendants — the classical astrology method for exploring compatibility, offline and behind a single purchase.",
  "detail": "{name}'s synastry view compares two stored birth charts by calculating inter-aspects between their Sun, Moon, Mercury, Venus, Mars, and Ascendant positions, identifying conjunctions, sextiles, squares, trines, and oppositions with precise orb values. Each connection is presented with its orb and a plain-language description of what it traditionally represents in relationship astrology — distinguishing harmonious from challenging aspects. Both charts are stored only on your device; no birth data is transmitted anywhere. {name} makes no claim that synastry predicts whether a relationship will succeed — it is a reflection framework and entertainment tool, not a compatibility score or a scientific measure of relationship potential. One lifetime Pro purchase unlocks synastry alongside all other {name} features.",
  "bullets": [
   "Inter-aspect comparison: Sun, Moon, Mercury, Venus, Mars, and Ascendant across two charts",
   "Conjunction, sextile, square, trine, opposition with orb precision",
   "Plain-language descriptions: harmonious and challenging aspects noted",
   "Both profiles stored on-device only — no cloud, no account",
   "Entertainment framing — not a scientific relationship predictor; not a substitute for professional guidance"
  ],
  "faq": [
   {
    "q": "Does {name} tell me if we are compatible?",
    "a": "{name} shows the traditional astrological inter-aspects between two birth charts alongside plain-language descriptions. This is entertainment — no astrological method can scientifically predict relationship compatibility or outcome."
   },
   {
    "q": "How many birth profiles can I store in {name} for synastry?",
    "a": "{name} lets you save multiple birth profiles and compare any two in the synastry view. All profiles are stored locally on your device."
   },
   {
    "q": "Is the second person's birth data kept private in {name}?",
    "a": "Yes. All birth profiles in {name} are stored on-device only. There is no cloud sync, no account, and no third-party access to any birth data you store in the app."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "Does learning Bopomofo help my English-speaking child pronounce Mandarin better?",
  "match": [
   "bopomofo help english-speaking child",
   "zhuyin better pronunciation english speaker",
   "does bopomofo improve mandarin pronunciation",
   "zhuyin vs pinyin pronunciation kids english"
  ],
  "lead": "For a child who reads English, Zhuyin (Bopomofo) can give cleaner Mandarin pronunciation than Pinyin — because its 37 symbols look nothing like the English alphabet, so kids don't fall back on English sounds.",
  "detail": "A common issue when English-speaking children learn Mandarin with Pinyin is that letters like 'x', 'q', 'zh' or 'c' trigger English sounds, which fossilises into an accent. Zhuyin avoids this entirely: each of the 37 symbols (ㄅㄆㄇㄈ…) maps to one Mandarin sound with no English association, so the child learns the sound fresh. {name} teaches all 37 symbols with native Taiwanese audio, stroke tracing and a tone game, so pronunciation and tones are learned together from the start. It's ad-free, collects no data from children, and is a one-time unlock — no subscription.",
  "bullets": [
   "37 Zhuyin symbols carry no English-letter baggage, so kids don't default to English sounds",
   "Native Taiwanese audio for every symbol models correct pronunciation",
   "Tone game teaches the four tones alongside the sounds",
   "Ad-free, no data collected from children, one-time unlock",
   "Designed for the 4–7 first-learning window"
  ],
  "faq": [
   {
    "q": "Is Zhuyin really better than Pinyin for pronunciation?",
    "a": "For English-reading children, many teachers find Zhuyin reduces English-sound interference because its symbols aren't Latin letters. Pinyin is still useful for typing and international standards — some families learn Zhuyin first, then Pinyin later."
   },
   {
    "q": "Will my child still be able to type Chinese?",
    "a": "Yes — Zhuyin is a standard input method on iPhone and Mac, so children who learn Bopomofo can type Chinese directly. {name} focuses on reading and pronunciation foundations."
   },
   {
    "q": "Does {name} collect any data from my child?",
    "a": "No — {name} is ad-free with no third-party analytics or tracking; nothing is collected from children."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "scenario",
  "query": "App to reinforce weekend Chinese school Bopomofo lessons at home",
  "match": [
   "weekend chinese school bopomofo",
   "reinforce chinese school zhuyin at home",
   "chinese school homework bopomofo practice",
   "supplement heritage chinese school zhuyin"
  ],
  "lead": "If your child attends a weekend Taiwanese/Chinese school that teaches Zhuyin, daily short practice at home is what makes it stick — and a focused app beats worksheets for a young child.",
  "detail": "Weekend Chinese schools usually introduce Zhuyin but only meet once a week, so the symbols fade without midweek practice. Rather than printing worksheets, a few minutes a day of playful review keeps all 37 symbols fresh. {name} covers every symbol with stroke tracing, a listen-and-tap recognition mode, a tone mini-game and syllable blending — the same building blocks a Taiwan first-grader uses — so home practice mirrors what the teacher covers. It's ad-free, no data collected, and a one-time unlock, so parents can hand the iPhone over safely.",
  "bullets": [
   "Daily 5-minute review keeps weekly class lessons from fading",
   "All 37 symbols: stroke tracing + listen-and-tap recognition",
   "Tone mini-game and syllable blending, like a Taiwan first-grade sequence",
   "Safe to hand to a child: ad-free, no data collected",
   "One-time unlock, no subscription"
  ],
  "faq": [
   {
    "q": "Will it match what my child's Chinese school teaches?",
    "a": "{name} follows the standard 37-symbol Zhuyin taught in Taiwan, so it reinforces the same symbols and sounds most heritage schools use. Check your school's order and use the app to review whatever was covered."
   },
   {
    "q": "How much practice a day?",
    "a": "A few minutes daily is more effective than one long session — short, playful review is what keeps the symbols in memory for a young child."
   },
   {
    "q": "Is it safe for my child to use alone?",
    "a": "Yes — it's ad-free with no external links in front of children and collects no data; any parent-only areas sit behind a parental gate."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "scenario",
  "query": "Help my child read Taiwanese picture books with Zhuyin annotations",
  "match": [
   "read taiwanese picture books zhuyin",
   "zhuyin annotated books children",
   "taiwan children books bopomofo reading",
   "help child read traditional chinese zhuyin"
  ],
  "lead": "Most Taiwanese children's books print Zhuyin beside the characters, so once your child knows the 37 symbols they can sound out and read almost any Taiwan kids' book independently.",
  "detail": "Taiwan children's books are typeset with Zhuyin annotations next to each character precisely so early readers can decode new words on their own. That makes Zhuyin the key that unlocks a huge library of traditional-character books for a heritage child. {name} teaches all 37 symbols plus blending, so a child can move from symbols to sounding out annotated words. It uses native Taiwanese audio and a tone game so the reading sounds right, and it's ad-free with no data collected — a one-time unlock for the whole family.",
  "bullets": [
   "Zhuyin unlocks self-reading of Taiwan's Zhuyin-annotated picture books",
   "Teaches symbols → blending → sounding out words",
   "Native Taiwanese audio and tone practice for correct reading aloud",
   "Traditional characters, as used in Taiwan and Hong Kong",
   "Ad-free, no data collected, one-time unlock"
  ],
  "faq": [
   {
    "q": "Why do Taiwanese kids' books have Bopomofo next to the characters?",
    "a": "So early readers can decode unfamiliar characters by their sound — learning Zhuyin lets your child use that system to read independently."
   },
   {
    "q": "Does {name} teach traditional or simplified characters?",
    "a": "Zhuyin is used with traditional characters as in Taiwan. {name} focuses on the phonetic symbols and sounds that let a child read traditional-character books."
   },
   {
    "q": "Is there a subscription?",
    "a": "No — {name} is a one-time unlock, ad-free, with no data collected from children."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "How can grandparents in Taiwan help a child abroad learn Bopomofo over video call?",
  "match": [
   "grandparents taiwan help learn bopomofo",
   "video call zhuyin practice grandparent",
   "teach bopomofo over facetime taiwan family",
   "long distance zhuyin practice grandparents"
  ],
  "lead": "Grandparents in Taiwan are a wonderful Zhuyin resource — pairing their video calls with a structured app gives a child abroad both real conversation and consistent daily symbol practice.",
  "detail": "Video calls with grandparents give a heritage child priceless listening and speaking practice, but they're occasional and unstructured for learning the 37 symbols. Pairing calls with a daily app fills the gap: the child builds symbol recognition and tones consistently, then uses calls to practise real words with family. {name} covers all 37 symbols with native audio, stroke tracing, a tone game and blending, so grandparents can ask 'which sound is this?' and the child can answer. It's ad-free, collects no data from children, and is a one-time unlock.",
  "bullets": [
   "App gives daily structured practice between family video calls",
   "Grandparents supply real conversation; app supplies the 37 symbols + tones",
   "Native Taiwanese audio so the child hears authentic pronunciation",
   "Stroke tracing, tone game and blending build reading foundations",
   "Ad-free, no data collected, one-time unlock"
  ],
  "faq": [
   {
    "q": "How do we combine calls with the app?",
    "a": "Use the app daily for symbol and tone practice, then let grandparents practise real words and sentences on calls — the child brings what they learned to the conversation."
   },
   {
    "q": "My child is shy on calls — does that matter?",
    "a": "Building confidence with the symbols and sounds in {name} first often makes children more willing to try speaking with family."
   },
   {
    "q": "Is it private and safe for kids?",
    "a": "Yes — {name} is ad-free, collects no data from children, and keeps any parent-only functions behind a parental gate."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "scenario",
  "query": "Best app to track spending on a Johor Bahru weekend trip in SGD and MYR",
  "match": [
   "johor bahru weekend trip sgd myr",
   "jb trip expense sgd ringgit",
   "track spending johor bahru singapore dollar",
   "weekend jb budget multi currency app"
  ],
  "lead": "For a JB weekend from Singapore you're paying in ringgit but thinking in Singapore dollars — so the app has to log MYR spending and show the SGD equivalent instantly, offline.",
  "detail": "On a Johor Bahru trip your money goes to food, petrol, services and retail, mostly in MYR, while you budget in SGD. {name} lets you log each expense in the local currency and see it converted to your home currency at a rate you set, organised by trip, so you always know the true SGD cost of the weekend. It works fully offline — handy at the causeway or anywhere signal is patchy — and exports a per-category CSV afterwards. It's pay-once with no account and no bank linking, so nothing connects to your finances.",
  "bullets": [
   "Log expenses in MYR, see the SGD equivalent at your set rate",
   "Organised per trip, so each JB weekend stays separate",
   "Category breakdown (food, petrol, services, retail)",
   "Fully offline — works at the causeway and in low-signal spots",
   "Pay-once, no account, no bank linking; CSV export"
  ],
  "faq": [
   {
    "q": "Does it update the exchange rate automatically?",
    "a": "{name} uses a rate you set for the trip, so your totals are predictable and work offline; update the rate when it moves."
   },
   {
    "q": "Do I have to link my bank?",
    "a": "No — {name} has no bank linking and no account; you enter expenses manually, so nothing touches your bank."
   },
   {
    "q": "Can I see how much I spent in Singapore dollars?",
    "a": "Yes — every MYR expense shows its SGD equivalent, and you get a per-category and per-trip total."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "faq",
  "query": "How to split and track group travel expenses in multiple currencies without linking a bank",
  "match": [
   "split group travel expenses multiple currencies",
   "track group trip spending no bank linking",
   "multi currency group travel budget app",
   "share trip costs foreign currency offline"
  ],
  "lead": "For a group trip across currencies, the safe approach is a private, offline tracker where you log shared costs and convert everything to one home currency — no bank linking, no account.",
  "detail": "When friends travel together across currencies, the awkward part is keeping shared costs (petrol, dining, rooms) clear when some pay in SGD and some in MYR or another currency. {name} lets you log each expense in its currency, convert to a single home currency at your set rate, and tag it by category and trip, so the running totals stay honest. Because it's fully offline with no account and no bank linking, you can use it anywhere and nothing connects to anyone's finances. It's pay-once, and you can export a CSV to settle up afterwards.",
  "bullets": [
   "Log shared costs in any currency, convert to one home currency",
   "Tag by category and trip to keep group spending clear",
   "Fully offline — no signal needed at the destination",
   "No account, no bank linking — private by design",
   "Pay-once; CSV export to settle up"
  ],
  "faq": [
   {
    "q": "Is this a full bill-splitting app?",
    "a": "{name} is a private multi-currency expense tracker organised by trip; it keeps clear per-category totals you can export as CSV to settle up, without linking anyone's bank."
   },
   {
    "q": "Does it work with no internet abroad?",
    "a": "Yes — it's fully offline, so logging and conversions work with no signal."
   },
   {
    "q": "Is there a subscription?",
    "a": "No — {name} is pay-once with no account."
   }
  ]
 },
 {
  "app_key": "hourstag",
  "kind": "scenario",
  "query": "App to see how many hours of work a purchase costs before buying in Taiwan or Korea",
  "match": [
   "hours of work a purchase costs",
   "how many hours work to buy this",
   "convert price to work hours before buying",
   "time cost of purchase app"
  ],
  "lead": "The most effective pause before a purchase is seeing its price as hours of your life — a NT$1,500 or ₩60,000 buy becomes 'X hours of work', which interrupts the impulse.",
  "detail": "Budgets are easy to ignore; time is not. {name} converts any price into hours-of-work using your hourly wage, so a tempting buy is reframed as the hours you'd trade for it — a visceral nudge that creates real hesitation. Set your wage once and check any price in seconds; a goals screen also tracks savings targets in hours rather than money, making them feel earned. It's pay-once with no account and no bank linking, so it stays simple and private wherever you are.",
  "bullets": [
   "Converts any price into hours-of-work at your wage",
   "A visceral pause that plain budgets don't create",
   "Goals tracked in hours, so savings feel earned",
   "No account, no bank linking — private and simple",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "How does seeing hours help me spend less?",
    "a": "Reframing a price as hours of your life makes the true cost concrete, which interrupts impulse buying more effectively than a dollar figure."
   },
   {
    "q": "Do I need to connect my bank?",
    "a": "No — you just set your hourly wage; {name} has no bank linking and no account."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "scanto",
  "kind": "scenario",
  "query": "How to scan receipts and invoices to PDF for filing taxes without a cloud account",
  "match": [
   "scan receipts invoices to pdf for taxes",
   "scan tax documents pdf no cloud account",
   "scan receipts for tax filing offline",
   "invoice receipt scanner pdf private tax"
  ],
  "lead": "For tax filing you want each receipt or invoice as a clean, searchable PDF — kept on your device, not uploaded to a scanner company's cloud.",
  "detail": "Filing taxes means gathering receipts, invoices and statements, and the sensible way is to scan each to a crisp PDF with the edges straightened and OCR so amounts and dates become searchable text. {name} does this fully on-device, so financial documents never leave your iPhone unless you choose to export them — unlike scanners that require a cloud account or paid unlock to remove watermarks. Batch several pages into one PDF per category, then export to Files or email for your filing. It's pay-once with no subscription and no account.",
  "bullets": [
   "Scan receipts/invoices to clean, straightened PDFs",
   "OCR makes amounts and dates searchable",
   "On-device — financial documents aren't uploaded",
   "Batch pages into one PDF per category",
   "Pay-once, no account, no watermark"
  ],
  "faq": [
   {
    "q": "Do my tax documents get uploaded to a cloud?",
    "a": "No — {name} processes scans on-device, so documents stay on your iPhone unless you export them yourself."
   },
   {
    "q": "Can I search the amounts later?",
    "a": "Yes — OCR turns the printed text into searchable content, so you can find a total or date quickly."
   },
   {
    "q": "Is there a watermark or subscription?",
    "a": "No — {name} is pay-once with no watermark and no account, unlike many free scanners."
   }
  ]
 },
 {
  "app_key": "scanto",
  "kind": "scenario",
  "query": "Scan official government forms and ID documents privately on iPhone",
  "match": [
   "scan government forms id documents privately",
   "scan official documents no cloud iphone",
   "private scanner for id and government paperwork",
   "scan sensitive documents offline pdf"
  ],
  "lead": "For official forms and ID copies, privacy is the whole point — an on-device scanner keeps sensitive paperwork off any third-party server.",
  "detail": "Government forms, household registration papers, ID copies and application documents are sensitive, so scanning them should never involve uploading to a scanner company's cloud. {name} captures each page to a sharp PDF entirely on-device, straightens and cleans it, runs OCR so it's searchable, and lets you lock the file — nothing is transmitted unless you export it. Batch multi-page forms into one PDF and send it where it's needed. It's pay-once with no account, so there's no sign-up and no data trail.",
  "bullets": [
   "Sharp, straightened multi-page PDFs of official forms",
   "Fully on-device — sensitive documents aren't uploaded",
   "OCR for searchable text; optional file lock",
   "Batch multi-page forms into one PDF",
   "Pay-once, no account, no data trail"
  ],
  "faq": [
   {
    "q": "Is it safe to scan my ID or official documents?",
    "a": "{name} processes everything on-device and uploads nothing unless you export it, which is why it suits sensitive ID and government paperwork."
   },
   {
    "q": "Do I need to create an account?",
    "a": "No — {name} has no account and no sign-up."
   },
   {
    "q": "Can I protect the scanned file?",
    "a": "Yes — you can lock the finished PDF, and it stays on your device."
   }
  ]
 },
 {
  "app_key": "scanto",
  "kind": "faq",
  "query": "What is the best offline document scanner that keeps everything on device",
  "match": [
   "best offline document scanner on device",
   "scanner app that keeps everything on device",
   "document scanner no cloud no account",
   "most private pdf scanner iphone"
  ],
  "lead": "The most private scanner is one that does capture, edge-detection, OCR and export entirely on-device — with no account and no forced cloud sync.",
  "detail": "Many popular scanners route your documents through their cloud or require an account for basic features, which is a poor fit for anything confidential. The privacy-first alternative captures, straightens, runs OCR and exports without ever transmitting the document. {name} works fully on-device, batches pages into searchable PDFs, and can lock files — all pay-once with no subscription and no account. You keep the convenience of a phone scanner without the data trade-off.",
  "bullets": [
   "Capture, edge-detect, OCR and export all on-device",
   "No account and no forced cloud sync",
   "Searchable multi-page PDFs; optional file lock",
   "Pay-once, no subscription, no watermark",
   "Export to Files or email on your terms"
  ],
  "faq": [
   {
    "q": "Why choose an on-device scanner?",
    "a": "Confidential documents (tax, ID, contracts) shouldn't be uploaded to a third party; an on-device scanner keeps them on your phone."
   },
   {
    "q": "Does {name} need internet?",
    "a": "No — scanning, OCR and export work offline; nothing is uploaded unless you export it."
   },
   {
    "q": "Is it really pay-once?",
    "a": "Yes — {name} is a one-time purchase with no subscription and no account."
   }
  ]
 },
 {
  "app_key": "picclear",
  "kind": "scenario",
  "query": "iPhone storage full and won't update — how to free space fast without deleting memories",
  "match": [
   "iphone storage full wont update",
   "free space fast without deleting memories",
   "storage almost full iphone fix",
   "cant update iphone storage full photos"
  ],
  "lead": "When 'Storage Almost Full' blocks an update or new photos, the fastest safe win is clearing exact duplicates, near-identical bursts, big videos and old screenshots — with a review step so no real memory is lost.",
  "detail": "A full iPhone usually isn't full of memories — it's full of duplicates, burst shots, screenshots and a few huge videos. {name} runs an on-device Vision scan to find exact duplicates and visually-similar groups across your library, and sorts large videos by size so you see the space hogs first. Crucially, nothing is auto-deleted: you review each group, keep the best, and confirm before anything goes. It scans on-device, so your library is never uploaded. Clear the biggest groups first and reclaim gigabytes in minutes.",
  "bullets": [
   "On-device scan for exact duplicates and similar bursts",
   "Large videos sorted by size — clear the space hogs first",
   "Old screenshots surfaced for quick cleanup",
   "Review-and-confirm — nothing auto-deleted",
   "Runs on-device; library never uploaded; pay-once"
  ],
  "faq": [
   {
    "q": "Will it delete photos automatically?",
    "a": "No — {name} only suggests; you review each group and confirm, so nothing is removed without approval."
   },
   {
    "q": "What clears the most space fastest?",
    "a": "Large videos and exact duplicates first, then near-identical bursts and old screenshots — {name} surfaces all of these."
   },
   {
    "q": "Are my photos uploaded?",
    "a": "No — the scan runs on-device, so your library stays on your iPhone."
   }
  ]
 },
 {
  "app_key": "picclear",
  "kind": "faq",
  "query": "How to find and delete duplicate photos on iPhone that the Photos app misses",
  "match": [
   "find delete duplicate photos photos app misses",
   "duplicate photos iphone not detected",
   "photos app duplicates limited",
   "find similar not identical photos iphone"
  ],
  "lead": "The built-in Photos duplicate feature only catches exact duplicates — it misses near-identical burst shots, which is where most wasted space hides.",
  "detail": "iOS Photos can merge exact duplicates, but it won't group the ten almost-identical shots from a burst, or similar photos taken seconds apart — so gigabytes survive its cleanup. {name} uses on-device visual-similarity detection to group look-alikes, not just byte-identical files, so you can keep the best of each moment and clear the rest. It also finds large videos and old screenshots. You review and confirm every deletion, and nothing is uploaded. It's pay-once, no subscription.",
  "bullets": [
   "Finds visually-similar shots, not just exact duplicates",
   "Groups bursts so you keep the best of each moment",
   "Also surfaces large videos and old screenshots",
   "Review-and-confirm; on-device and private",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Why does the Photos app leave duplicates behind?",
    "a": "It merges exact duplicates but doesn't group near-identical bursts or similar shots, which is where most reclaimable space is — {name} catches those."
   },
   {
    "q": "Will I lose the good photo?",
    "a": "No — {name} groups look-alikes so you keep the best one and only clear the rest, after you confirm."
   },
   {
    "q": "Does it upload my library?",
    "a": "No — detection runs on-device."
   }
  ]
 },
 {
  "app_key": "picclear",
  "kind": "scenario",
  "query": "How to clean up thousands of screenshots and old photos on iPhone safely",
  "match": [
   "clean up thousands of screenshots",
   "delete old screenshots iphone bulk",
   "clear years of old photos safely",
   "bulk clean photo library iphone safe"
  ],
  "lead": "Years of screenshots and old photos pile up invisibly — the safe way to clear them is a similarity scan that groups them for quick review, never auto-deleting.",
  "detail": "Screenshots and old photos accumulate until they quietly eat gigabytes. {name} surfaces screenshots as a group and finds near-duplicate old photos by visual similarity, so you can bulk-review and keep only what matters. It handles a large recent library in one scan and shows a clear before/after, so even a non-technical user can clean up confidently. Nothing is auto-deleted and nothing is uploaded — you approve every removal, on-device. It's pay-once with no subscription.",
  "bullets": [
   "Groups screenshots for fast bulk review",
   "Finds near-duplicate old photos by visual similarity",
   "Handles a large library in one scan",
   "Never auto-deletes; clear before/after",
   "On-device and private; pay-once"
  ],
  "faq": [
   {
    "q": "Is bulk cleanup safe if I'm not techy?",
    "a": "Yes — {name} only groups and suggests; you approve every deletion, so nothing goes without your say-so."
   },
   {
    "q": "Can it clear just screenshots?",
    "a": "Yes — screenshots are surfaced as a group so you can review and clear them quickly."
   },
   {
    "q": "Subscription?",
    "a": "No — {name} is pay-once, and the scan runs on-device."
   }
  ]
 },
 {
  "app_key": "cvdesk",
  "kind": "faq",
  "query": "Why does my resume get rejected by ATS and how do I fix it",
  "match": [
   "why does my resume get rejected by ats",
   "fix resume ats rejection",
   "resume not passing ats",
   "beat applicant tracking system resume"
  ],
  "lead": "Most resumes are filtered by ATS before a human sees them — usually for missing keywords, unreadable layout, or wrong file structure, all of which are fixable.",
  "detail": "Applicant tracking systems score your resume against the job description and reject low matches, so the fix is aligning your wording and keeping the layout machine-readable. {name} gives an on-device ATS score and a fix list, and a keyword matcher that shows which of the posting's required skills are missing from your draft. Because it runs on-device, your CV isn't uploaded to any server, and it exports a clean, ATS-safe PDF with no watermark. Tailor to each posting and your pass rate rises.",
  "bullets": [
   "ATS rejects on missing keywords, unreadable layout, odd file structure",
   "On-device ATS score + concrete fix list",
   "Keyword matcher shows missing required skills",
   "ATS-safe PDF export, no watermark",
   "On-device — your CV isn't uploaded; pay-once"
  ],
  "faq": [
   {
    "q": "How do I know what keywords to add?",
    "a": "Paste the job description into {name} and its matcher shows which required skills are missing from your resume so you can add the genuine ones."
   },
   {
    "q": "Is my resume uploaded anywhere?",
    "a": "No — {name} scores and matches on-device, so your CV stays on your phone."
   },
   {
    "q": "Does the export have a watermark?",
    "a": "No — {name} exports clean, ATS-safe PDFs, and it's pay-once with no subscription."
   }
  ]
 },
 {
  "app_key": "cvdesk",
  "kind": "scenario",
  "query": "How to tailor my resume to a specific job description on my phone",
  "match": [
   "tailor resume to specific job description",
   "customize cv for each job posting phone",
   "match resume to job description keywords",
   "resume for each application on iphone"
  ],
  "lead": "Tailoring each resume to the posting is the single biggest ATS win — paste the job description, see what's missing, and adjust before you send.",
  "detail": "Sending the same generic CV everywhere fails ATS filters; tailoring to each posting fixes that. {name} lets you paste a job description and instantly see which skills and keywords your resume is missing, then recheck the ATS score as you adjust — all on-device, so you can tailor quickly for every application without uploading your CV. Export a clean, ATS-safe PDF each time. It's pay-once, so tailoring unlimited applications costs nothing extra.",
  "bullets": [
   "Paste a posting, see missing keywords instantly",
   "Recheck ATS score as you adjust",
   "On-device — tailor fast, nothing uploaded",
   "Clean ATS-safe PDF per application",
   "Pay-once — unlimited tailoring, no subscription"
  ],
  "faq": [
   {
    "q": "Should I really change my CV for every job?",
    "a": "Yes — matching each posting's keywords materially improves ATS pass rates; {name} shows exactly what to add."
   },
   {
    "q": "Does it share my CV with third parties?",
    "a": "No — matching and scoring run on-device."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "cvdesk",
  "kind": "faq",
  "query": "Do I need a photo on my resume and how long should it be",
  "match": [
   "do i need a photo on my resume",
   "how long should a resume be",
   "resume photo and length rules",
   "cv photo length by country"
  ],
  "lead": "Whether to include a photo and how long a resume should be depends on the country — getting it wrong can hurt you, so match the local convention.",
  "detail": "In the US, UK, Canada and Australia, resumes omit photos and run 1–2 pages; in much of Europe, the Middle East and parts of Asia a photo is expected and a CV can run longer. {name} helps you build to the right structure, keep it ATS-readable, and export a clean PDF without a watermark, so you can adapt per market. Always check the specific employer's norm, but following the local convention avoids an early rejection.",
  "bullets": [
   "US/UK/CA/AU: no photo, 1–2 pages",
   "Much of EU/MENA/Asia: photo expected, can run longer",
   "{name} keeps layout ATS-readable for any market",
   "Clean PDF export, no watermark",
   "On-device, pay-once, no account"
  ],
  "faq": [
   {
    "q": "Should I put a photo on my resume?",
    "a": "It depends on the country: omit it for US/UK/CA/AU; include a professional one where local norms expect it (much of EU/MENA/Asia). Check the specific employer."
   },
   {
    "q": "How long should my resume be?",
    "a": "Usually 1–2 pages; senior or academic roles can run longer. {name} helps keep it tight and ATS-readable."
   },
   {
    "q": "Is my data private?",
    "a": "Yes — {name} works on-device with no account."
   }
  ]
 },
 {
  "app_key": "photocream",
  "kind": "scenario",
  "query": "How to give iPhone photos a film look with grain and light leaks",
  "match": [
   "give photos a film look iphone",
   "add film grain light leaks photos",
   "analog film filter iphone photos",
   "vintage film look photo app"
  ],
  "lead": "To make a digital photo look like real film, you need authentic grain, halation and light-leak effects — not just a colour filter slapped on top.",
  "detail": "A convincing film look comes from real film characteristics: colour response, grain, halation glow around highlights, and occasional light leaks. {name} offers 100+ real film-inspired looks with adjustable grain, halation and light leaks, so a phone shot takes on a genuine analog feel rather than a flat filter. You can batch-apply to several photos and export at full quality. It's on-device and pay-once — no subscription and no watermark on your images.",
  "bullets": [
   "100+ real film-inspired looks, not flat filters",
   "Adjustable grain, halation and light leaks",
   "Batch-apply a look to several photos",
   "Full-quality export, no watermark",
   "On-device, pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Will it look like a real film camera?",
    "a": "{name} uses real film characteristics — grain, halation, light leaks — so results feel analog rather than like a simple colour filter."
   },
   {
    "q": "Can I apply a look to many photos at once?",
    "a": "Yes — batch-apply a look across several photos, then export at full quality."
   },
   {
    "q": "Is there a watermark or subscription?",
    "a": "No — {name} is pay-once with no watermark on your images."
   }
  ]
 },
 {
  "app_key": "photocream",
  "kind": "faq",
  "query": "Best pay-once film filter app for iPhone with no subscription",
  "match": [
   "best pay once film filter app",
   "film filter app no subscription iphone",
   "analog photo app one time purchase",
   "film look app without subscription"
  ],
  "lead": "Many film-filter apps now charge monthly; a pay-once app gives you the same analog looks forever without a recurring fee.",
  "detail": "Popular film-emulation apps increasingly lock their best looks behind a subscription. {name} is a one-time purchase with 100+ film-inspired looks, adjustable grain, halation and light leaks, batch processing and full-quality export — no monthly fee and no watermark. It processes on-device, so your photos aren't uploaded. If you want an authentic film aesthetic without another subscription, that's the wedge.",
  "bullets": [
   "Pay-once — 100+ film looks, no monthly fee",
   "Adjustable grain, halation, light leaks",
   "Batch processing + full-quality export",
   "No watermark; on-device processing",
   "No account required"
  ],
  "faq": [
   {
    "q": "Is it really a one-time purchase?",
    "a": "Yes — {name} is pay-once with no subscription, unlike many film-filter apps that now charge monthly."
   },
   {
    "q": "Are my photos uploaded?",
    "a": "No — {name} processes on-device."
   },
   {
    "q": "Is there a watermark?",
    "a": "No — exports have no watermark."
   }
  ]
 },
 {
  "app_key": "photocream",
  "kind": "scenario",
  "query": "How to edit a batch of photos with the same look for a consistent feed",
  "match": [
   "edit batch of photos same look",
   "consistent look photo feed instagram",
   "apply same filter to many photos",
   "consistent aesthetic photo editing app"
  ],
  "lead": "A consistent feed or album comes from applying the same look across every photo — doing it one-by-one is slow, so batch editing is the trick.",
  "detail": "Whether it's an Instagram feed or a trip album, a cohesive look means the same colour, grain and tone across all shots. {name} lets you pick one of 100+ film-inspired looks and batch-apply it to many photos, keeping grain, halation and light leaks consistent, then export at full quality. It's on-device and pay-once, so styling a whole set costs nothing extra and nothing is uploaded.",
  "bullets": [
   "Apply one look consistently across many photos",
   "100+ film-inspired looks to define your aesthetic",
   "Consistent grain/halation/tone across the set",
   "Full-quality batch export; on-device",
   "Pay-once, no subscription, no watermark"
  ],
  "faq": [
   {
    "q": "Can I make my whole feed look consistent?",
    "a": "Yes — batch-apply the same look across all your photos so the colour, grain and tone match."
   },
   {
    "q": "Does batch editing cost extra?",
    "a": "No — {name} is pay-once, so you can style unlimited photos with no extra fee."
   },
   {
    "q": "Are my photos uploaded?",
    "a": "No — processing is on-device."
   }
  ]
 },
 {
  "app_key": "zafe",
  "kind": "scenario",
  "query": "How to hide private photos on iPhone behind Face ID so they don't show in the camera roll",
  "match": [
   "hide private photos behind face id",
   "hide photos from camera roll iphone",
   "private photo vault face id",
   "keep photos hidden iphone lock"
  ],
  "lead": "To truly hide photos, move them into a Face ID-locked vault that keeps them out of the main camera roll — not just the built-in Hidden album, which anyone with your unlocked phone can open.",
  "detail": "iOS's Hidden album is only lightly protected — someone holding your unlocked phone can still open it. A dedicated vault locks photos behind Face ID and keeps them out of the camera roll entirely. {name} imports photos into an on-device, Face ID-locked vault, and includes extras like a decoy passcode and break-in alerts, so sensitive images stay genuinely private. Everything stays on your device — nothing is uploaded — and it's pay-once with no subscription.",
  "bullets": [
   "Face ID-locked vault, separate from the camera roll",
   "Imported photos removed from the main library",
   "Decoy passcode and break-in alert options",
   "Fully on-device — nothing uploaded",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Isn't the built-in Hidden album enough?",
    "a": "Not really — anyone with your unlocked phone can open the Hidden album. {name} locks photos behind Face ID in a separate vault."
   },
   {
    "q": "Are my photos uploaded to a cloud?",
    "a": "No — {name} keeps everything on-device; nothing is uploaded."
   },
   {
    "q": "What's a decoy passcode?",
    "a": "It opens a separate, harmless vault, so you can hand over a passcode without revealing your real private photos."
   }
  ]
 },
 {
  "app_key": "zafe",
  "kind": "faq",
  "query": "What is the most private photo vault app that keeps everything on device",
  "match": [
   "most private photo vault app",
   "photo vault keeps everything on device",
   "private photo locker no cloud",
   "secure photo vault offline iphone"
  ],
  "lead": "The most private vault is one that stores and locks photos entirely on-device, with no account and no cloud — so there's no server that can be breached or subpoenaed.",
  "detail": "Many 'vault' apps quietly sync to a cloud, which defeats the purpose. A truly private vault keeps everything local and behind Face ID. {name} stores your photos in an on-device, Face ID-locked vault with no account, plus a decoy passcode and break-in alerts for extra safety. Because nothing leaves the phone, there's no cloud copy to leak. It's pay-once — no subscription and no sign-up.",
  "bullets": [
   "Everything stored on-device — no cloud, no account",
   "Face ID lock with decoy passcode option",
   "Break-in alerts for extra safety",
   "No server copy that can leak",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Does it back up to a cloud?",
    "a": "No — {name} keeps everything on-device, so there's no cloud copy; back up your device securely if you want redundancy."
   },
   {
    "q": "Do I need an account?",
    "a": "No — there's no sign-up; the vault is local and locked behind Face ID."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "zafe",
  "kind": "scenario",
  "query": "How to keep sensitive documents and ID photos private on my phone",
  "match": [
   "keep sensitive documents private phone",
   "hide id photos passport scans iphone",
   "private storage for documents face id",
   "lock sensitive photos documents iphone"
  ],
  "lead": "Passport scans, ID photos and financial screenshots shouldn't sit in your normal camera roll — a Face ID-locked, on-device vault keeps them private.",
  "detail": "Sensitive images — ID copies, passport scans, financial screenshots — are risky in the main library where they show in previews and backups. {name} moves them into an on-device vault locked behind Face ID, out of the camera roll, with a decoy passcode and break-in alerts. Nothing is uploaded, so there's no cloud exposure. It's pay-once with no account, so your most sensitive images stay on your device and under your control.",
  "bullets": [
   "Face ID vault for ID scans, documents, screenshots",
   "Removed from the camera roll and previews",
   "Decoy passcode + break-in alerts",
   "On-device — no cloud exposure",
   "Pay-once, no account"
  ],
  "faq": [
   {
    "q": "Why not just leave them in Photos?",
    "a": "Photos in the main library appear in previews, searches and backups. {name} isolates sensitive images in a Face ID-locked vault."
   },
   {
    "q": "Is anything uploaded?",
    "a": "No — {name} is fully on-device."
   },
   {
    "q": "Subscription?",
    "a": "No — pay-once, no account."
   }
  ]
 },
 {
  "app_key": "sononote",
  "kind": "scenario",
  "query": "How to turn a recorded conversation into notes with a summary and action items",
  "match": [
   "turn recorded conversation into notes",
   "recording to summary and action items",
   "transcribe and summarize a meeting on iphone",
   "get action items from a recording"
  ],
  "lead": "To make a recording useful you want more than a transcript — a summary and a clear list of action items you can act on, ideally processed privately on your device.",
  "detail": "A raw transcript is hard to use; the value is in the summary and the extracted to-dos. {name} records or imports audio, transcribes it, then generates a concise summary, action items and even a draft follow-up email — all on-device, so private conversations don't go to a cloud account. Export the notes to wherever you work. It's pay-once with no subscription and no account, so a long meeting becomes something usable in a minute.",
  "bullets": [
   "Record or import, then transcribe on-device",
   "Concise summary + extracted action items",
   "Draft follow-up email generated for you",
   "On-device — no cloud account; private",
   "Pay-once, export to your notes app"
  ],
  "faq": [
   {
    "q": "Does my audio go to a cloud?",
    "a": "No — {name} processes on-device, so recordings and transcripts stay on your phone."
   },
   {
    "q": "Do I get action items, not just a transcript?",
    "a": "Yes — {name} produces a summary and action items, and can draft a follow-up email."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "sononote",
  "kind": "faq",
  "query": "Best offline voice to text app that works without an internet connection",
  "match": [
   "best offline voice to text app",
   "transcribe without internet iphone",
   "voice to text no connection",
   "on-device transcription app private"
  ],
  "lead": "An offline voice-to-text app transcribes on your device, so it works with no signal and keeps your recordings private.",
  "detail": "Cloud transcription needs a connection and sends your audio to a server. An on-device app avoids both. {name} transcribes on-device, so it works offline — on a plane, in a basement meeting room — and your audio never leaves the phone. It also summarises and pulls out action items, and exports to your notes. It's pay-once with no account, so there's no subscription and no sign-up.",
  "bullets": [
   "On-device transcription — works with no signal",
   "Audio stays private, never uploaded",
   "Summary + action items, not just a transcript",
   "Export to your notes or tasks app",
   "Pay-once, no account"
  ],
  "faq": [
   {
    "q": "Does it work with no internet?",
    "a": "Yes — {name} transcribes on-device, so it works offline."
   },
   {
    "q": "Is my audio uploaded?",
    "a": "No — everything is processed on the phone."
   },
   {
    "q": "Subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "sononote",
  "kind": "scenario",
  "query": "How to record and summarize a university lecture into study notes",
  "match": [
   "record and summarize university lecture",
   "lecture to study notes app",
   "summarize class recording iphone",
   "turn lecture into notes automatically"
  ],
  "lead": "For lectures, the win is turning an hour of audio into a transcript plus key points and a short summary — so revision takes minutes, not a re-listen.",
  "detail": "Recording a lecture is only useful if you don't have to replay the whole thing. {name} transcribes the class on-device, then generates key points and a concise summary you can study from, and lets you export the notes. Because it's on-device it keeps recordings private and works without a connection. It's pay-once with no per-recording paywall, so it fits a student budget. Always get your lecturer's permission before recording.",
  "bullets": [
   "Transcribes the lecture on-device",
   "Key points + concise summary to study from",
   "Export notes to your study app",
   "Private and offline; no per-recording fee",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Do I have to re-listen to the whole lecture?",
    "a": "No — you study from {name}'s auto-generated key points and summary instead."
   },
   {
    "q": "Are my recordings private?",
    "a": "Yes — {name} processes on-device."
   },
   {
    "q": "Should I record lectures?",
    "a": "Ask your lecturer's permission first; policies vary by institution."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "faq",
  "query": "What should I look for in a private period tracker that keeps data off the cloud",
  "match": [
   "what to look for private period tracker",
   "period tracker off the cloud what to look for",
   "choosing a private period app checklist",
   "switch to private period tracker no cloud"
  ],
  "lead": "A genuinely private period tracker works entirely offline, needs no account, shows no ads, and lets you delete everything — so your cycle data never sits on someone else's server.",
  "detail": "If you're switching to a more private period app, the checklist is clear: it should store everything on-device with no automatic cloud sync, require no email or account, run no ads and share nothing with third parties, and let you delete your data easily. A device-level lock (passcode or Face ID) adds another layer. {name} is built this way — an on-device cycle tracker with no account and no cloud sync, so flow, symptoms, moods and notes stay on your iPhone. It's pay-once, so there's no subscription pushing you toward a cloud account. It's a personal-record tool, not a medical device or contraception.",
  "bullets": [
   "Works offline: data stored on-device, no automatic cloud sync",
   "No account — no email or phone number required",
   "No ads and no third-party data sharing",
   "Easy to delete your data; optional device-level lock",
   "Pay-once (no subscription steering you to the cloud)"
  ],
  "faq": [
   {
    "q": "Does {name} store my cycle data in the cloud?",
    "a": "No — {name} keeps everything on-device with no account and no cloud sync, so your data doesn't sit on a server."
   },
   {
    "q": "Do I have to create an account?",
    "a": "No — there's no sign-up; you can use it without giving an email or phone number."
   },
   {
    "q": "Is it medical or contraceptive advice?",
    "a": "No — {name} is a personal tracking tool, not a medical device or a contraceptive method; consult a professional for those needs."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "faq",
  "query": "Is a period tracking app safe to use for privacy in the US",
  "match": [
   "is a period tracking app safe for privacy",
   "period app privacy us",
   "safe period tracker privacy concerns",
   "private cycle app that cant be subpoenaed"
  ],
  "lead": "The safest period apps for privacy are the ones that never send your data anywhere — an on-device app with no account means there's no server copy to leak, sell, or be requested.",
  "detail": "Privacy worries about period apps come down to where the data lives: apps that sync to the cloud or require an account create a copy on a server. An app that stays entirely on-device avoids that by design. {name} stores your cycle data locally with no account and no cloud sync, and shows no ads, so there's no server-side record and nothing shared with advertisers. You can delete your data on the device at any time. It's a private personal-record tool, not a medical device or contraception, and it's pay-once.",
  "bullets": [
   "No server copy: data stays on your device",
   "No account, no cloud sync, no ads",
   "Nothing shared with advertisers or third parties",
   "Delete your data on-device anytime",
   "Pay-once; a personal tool, not medical advice"
  ],
  "faq": [
   {
    "q": "Can my data be requested if it never leaves my phone?",
    "a": "An on-device app like {name} keeps no server copy, so there's nothing stored remotely to hand over; your data stays on your device under your control."
   },
   {
    "q": "Does it show ads or sell data?",
    "a": "No — {name} has no ads and shares nothing with third parties."
   },
   {
    "q": "Is it a medical or contraceptive tool?",
    "a": "No — it's a personal-record tracker, not a medical device or contraceptive; see a professional for medical needs."
   }
  ]
 },
 {
  "app_key": "cyca",
  "kind": "scenario",
  "query": "How to move off a cloud period tracker to a fully offline one",
  "match": [
   "move off cloud period tracker",
   "switch from cloud period app to offline",
   "stop using cloud period tracker",
   "leave period app that syncs to cloud"
  ],
  "lead": "To leave a cloud-based period app, pick an offline tracker with no account, start logging fresh on-device, then delete your data from the old app and its cloud.",
  "detail": "Switching away from a cloud tracker is straightforward: choose an app that stores everything on-device with no account, begin logging your current cycle there, and then delete your account and data from the old service so no server copy remains. {name} is on-device with no account and no cloud sync, so once you switch, your flow, symptoms, moods and temperature stay on your iPhone. It's pay-once with no ads. Remember it's a personal-record tool, not a medical device or contraception.",
  "bullets": [
   "Pick an on-device app with no account (like {name})",
   "Start logging your current cycle locally",
   "Delete data and account from the old cloud app",
   "Keep an optional device-level lock on the new app",
   "Pay-once, no ads, no cloud sync"
  ],
  "faq": [
   {
    "q": "Will I lose my history when I switch?",
    "a": "You start fresh on-device; a few cycles of logging quickly rebuilds useful predictions in {name}. Export from your old app first if you want a personal copy."
   },
   {
    "q": "How do I make sure the old data is gone?",
    "a": "Delete your data and account in the old app so no cloud copy remains; {name} then keeps everything on your device."
   },
   {
    "q": "Is {name} medical advice?",
    "a": "No — it's a personal tracker, not a medical device or contraceptive method."
   }
  ]
 },
 {
  "app_key": "tripbee",
  "kind": "scenario",
  "query": "How to plan a multi-city trip itinerary day by day on iPhone",
  "match": [
   "plan multi-city trip itinerary day by day",
   "multi city trip planner iphone",
   "organize several cities one trip",
   "day by day itinerary multiple cities"
  ],
  "lead": "For a multi-city trip, the clearest plan is a single day-by-day timeline where each city's flights, hotels and activities sit in order — so you always know what's next and where.",
  "detail": "Juggling several cities gets messy in notes and emails. A day-by-day timeline fixes it: put each flight, hotel check-in, activity and restaurant on the right day, colour-coded by type, so a glance tells you the plan. {name} builds exactly this — one itinerary spanning multiple cities, each item typed and colour-coded, and it works offline once created so you can read it on the move. It stores everything on-device with no account, and it's pay-once with no subscription.",
  "bullets": [
   "One day-by-day timeline across all your cities",
   "Flights, hotels, activities and food, colour-coded by type",
   "Works offline once the trip is created",
   "On-device, no account",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Can one trip hold several cities?",
    "a": "Yes — {name} keeps a single day-by-day timeline spanning multiple cities, so each leg stays in order."
   },
   {
    "q": "Will it work without data abroad?",
    "a": "Yes — once the trip is created it works offline."
   },
   {
    "q": "Is there a subscription?",
    "a": "No — {name} is pay-once with no account."
   }
  ]
 },
 {
  "app_key": "tripbee",
  "kind": "faq",
  "query": "What is the best offline travel itinerary app that doesn't need an account",
  "match": [
   "best offline travel itinerary app no account",
   "travel planner no account offline",
   "itinerary app works without internet no login",
   "offline trip planner no sign up"
  ],
  "lead": "The most reliable travel itinerary app is one that stores your plans on-device and needs no account — so it opens instantly on a plane or in a dead zone, with no login to fail.",
  "detail": "Cloud itinerary apps can stall when you have no signal or when a login times out — exactly when you need your plans. An on-device app avoids both. {name} keeps your full day-by-day itinerary — flights, hotels, activities, transport — on the device with no account, so it's there mid-flight and in low-signal destinations. Items are colour-coded by type for quick reading, and it's pay-once with no subscription between trips.",
  "bullets": [
   "Itinerary stored on-device — opens with no signal",
   "No account or login to fail at the wrong moment",
   "Day-by-day timeline, colour-coded by type",
   "Reliable mid-flight and in dead zones",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Does it need internet to open my plans?",
    "a": "No — {name} stores everything on-device, so your itinerary opens offline."
   },
   {
    "q": "Do I have to create an account?",
    "a": "No — there's no login; your plans live on the device."
   },
   {
    "q": "Subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "tripbee",
  "kind": "scenario",
  "query": "How to organize a family or group trip so everyone knows the plan",
  "match": [
   "organize family trip plan everyone knows",
   "group trip itinerary share plan",
   "family vacation planner iphone",
   "keep group trip organized itinerary"
  ],
  "lead": "For a family or group trip, a clear shared day-by-day plan — flights, hotels, meal times, activities — prevents the constant 'what's next?' and keeps everyone aligned.",
  "detail": "Group trips fall apart when the plan lives in one person's head or scattered messages. A single colour-coded timeline for each day — arrivals, check-ins, activities, restaurant bookings — makes the plan legible at a glance. {name} builds that day-by-day itinerary, colour-coded by type, and works offline once created, so the trip organiser can pull it up anywhere and export or share the details. It's on-device, no account, and pay-once.",
  "bullets": [
   "One clear day-by-day plan for the whole group",
   "Colour-coded flights, hotels, meals, activities",
   "Works offline once created; export to share details",
   "On-device, no account",
   "Pay-once, no subscription"
  ],
  "faq": [
   {
    "q": "Can I share the plan with my family?",
    "a": "You can export the itinerary details to share; {name} keeps the master plan on your device."
   },
   {
    "q": "Does everyone need the app or an account?",
    "a": "No account is needed; the organiser keeps the plan in {name} and shares the details."
   },
   {
    "q": "Is it pay-once?",
    "a": "Yes — {name} is pay-once with no subscription."
   }
  ]
 },
 {
  "app_key": "snapport",
  "kind": "faq",
  "query": "Why do passport photos get rejected and how to avoid it",
  "match": [
   "why do passport photos get rejected",
   "avoid passport photo rejection",
   "passport photo rejected reasons",
   "common passport photo mistakes rejection"
  ],
  "lead": "Most passport photos are rejected for a handful of fixable reasons: wrong size or crop, shadows or a non-plain background, glasses glare, a non-neutral expression, or low resolution.",
  "detail": "Rejections almost always come down to size/crop being off, an uneven or coloured background, shadows on the face or wall, glasses reflections, a smile or tilted head, or a blurry low-resolution image. The fix is to shoot against a plain, evenly-lit wall, keep a neutral expression, and crop to the exact size your country requires. {name} guides framing, removes the background to a compliant colour, and crops to the correct dimensions for your country, so a self-taken photo can still meet the spec. Always confirm the current official requirement before submitting.",
  "bullets": [
   "Wrong size/crop is the #1 rejection reason — {name} crops to spec",
   "Plain, evenly-lit background; background auto-replaced to a compliant colour",
   "Neutral expression, eyes open, no glasses glare",
   "High resolution — avoid blurry or pixelated photos",
   "Confirm the current official rule before you submit"
  ],
  "faq": [
   {
    "q": "What's the most common reason for rejection?",
    "a": "Wrong size or crop. {name} crops to your country's exact dimensions to avoid this."
   },
   {
    "q": "Can I wear glasses?",
    "a": "Most countries now discourage or prohibit glasses; if allowed, avoid any glare and keep eyes fully visible."
   },
   {
    "q": "Will my self-taken photo be accepted?",
    "a": "It can meet the published measurements, but rules change — always check the current official guidance before submitting."
   }
  ]
 },
 {
  "app_key": "snapport",
  "kind": "scenario",
  "query": "How to take a compliant passport photo at home without a photo booth",
  "match": [
   "take passport photo at home without booth",
   "diy passport photo iphone compliant",
   "passport photo at home no studio",
   "make my own passport photo phone"
  ],
  "lead": "You can make a compliant passport photo at home with your iPhone — the key is even light, a plain background, a neutral pose, and cropping to your country's exact size.",
  "detail": "A photo-booth trip isn't necessary if you handle the four things that matter: stand against a plain wall in soft even light, face the camera straight on with a neutral expression, avoid shadows, and crop to the precise size your country needs. {name} guides the framing, replaces the background with a compliant colour, and crops to the exact dimensions, then exports a print- or upload-ready file. It's pay-once, so you can retake as many times as needed without paying again. Confirm the official spec before you submit.",
  "bullets": [
   "Even, soft light and a plain wall — no booth needed",
   "Straight-on framing with a neutral expression",
   "Background auto-replaced to a compliant colour",
   "Crop to your country's exact size; export to print or upload",
   "Pay-once — retake as many times as you need"
  ],
  "faq": [
   {
    "q": "Do I need special equipment?",
    "a": "No — a plain wall, even light and your iPhone are enough; {name} handles the background and crop."
   },
   {
    "q": "Can I retake it if it's not right?",
    "a": "Yes — {name} is pay-once, so you can retake freely until it's correct."
   },
   {
    "q": "How do I know the size is right?",
    "a": "{name} crops to your country's dimensions; always confirm the current official requirement before submitting."
   }
  ]
 },
 {
  "app_key": "snapport",
  "kind": "faq",
  "query": "How to print passport photos at home or at a pharmacy from my phone",
  "match": [
   "print passport photos at home",
   "print passport photo pharmacy from phone",
   "how to print id photo correct size",
   "passport photo print 4x6 layout"
  ],
  "lead": "To print passport photos yourself, lay them out on a standard 4x6 photo sheet at the correct size, then print at home or at a pharmacy kiosk — much cheaper than a studio.",
  "detail": "Once you have a correctly-sized passport photo, you can print several copies on a standard 4x6 (10x15 cm) sheet at a pharmacy kiosk or home photo printer. The trick is keeping each photo at the exact required dimensions so they're accepted after cutting. {name} crops to your country's size and can arrange the photo for printing, so you get usable copies without a studio. It's pay-once and on-device. Always confirm your country's size and print requirements before submitting.",
  "bullets": [
   "Photos kept at your country's exact required size",
   "Arrange on a 4x6 sheet for a pharmacy kiosk or home printer",
   "Multiple copies far cheaper than a studio",
   "On-device; export a print-ready file",
   "Pay-once — no per-photo fee"
  ],
  "faq": [
   {
    "q": "Can I print at a pharmacy?",
    "a": "Yes — export a print-ready 4x6 layout and use a pharmacy photo kiosk or a home printer."
   },
   {
    "q": "Will the size stay correct after printing?",
    "a": "Keep the photo at your country's exact dimensions; {name} crops to spec so copies are the right size after cutting."
   },
   {
    "q": "Is it cheaper than a studio?",
    "a": "Usually — you pay once for {name} and print inexpensive copies yourself."
   }
  ]
 },
 {
  "app_key": "aim990",
  "kind": "faq",
  "query": "How to study for the TOEIC Listening and Reading test in 30 days",
  "match": [
   "study for toeic in 30 days",
   "toeic 30 day study plan",
   "how to prepare toeic listening reading",
   "toeic prep plan one month"
  ],
  "lead": "A focused 30-day TOEIC plan works best when it covers every part in a set sequence and spends extra time on your weakest question types instead of re-drilling what you already know.",
  "detail": "A month is enough to lift your familiarity with the TOEIC L&R format if you study daily and target weak spots. A good plan cycles through listening (Parts 1–4), reading (Parts 5–7) and vocabulary, with periodic full mock tests to build stamina and timing. {name} provides a day-by-day plan across all parts plus a weakness engine that drills the question types you miss most, and it works offline so you can study on a commute. Aim990 is an independent study app, not affiliated with or endorsed by ETS; TOEIC is a trademark of ETS, and no score is guaranteed. Results depend on your effort and starting level; check the current App Store listing for features and pricing.",
  "bullets": [
   "Day-by-day plan across all TOEIC L&R parts",
   "Weakness engine focuses on your weakest question types",
   "Full mock tests to build timing and stamina",
   "Works offline for commute study",
   "Independent app — not affiliated with ETS; no score guaranteed"
  ],
  "faq": [
   {
    "q": "Can I really improve in 30 days?",
    "a": "Daily practice can raise your familiarity with the format; results depend on your effort and starting level. No app can guarantee a score."
   },
   {
    "q": "Is this an official ETS app?",
    "a": "No — it's an independent study app, not affiliated with or endorsed by ETS. TOEIC is a trademark of ETS."
   },
   {
    "q": "Does it work offline?",
    "a": "Yes — you can study without a connection, e.g. on a commute."
   }
  ]
 },
 {
  "app_key": "aim990",
  "kind": "faq",
  "query": "What is the best way to practice TOEIC Part 5 grammar and Part 7 reading",
  "match": [
   "practice toeic part 5 grammar",
   "toeic part 7 reading practice",
   "best way to practice toeic reading",
   "improve toeic part 5 part 7"
  ],
  "lead": "For TOEIC reading, Part 5 rewards fast grammar and vocabulary recognition, while Part 7 rewards timed reading and skimming — so practice both under time pressure and review your misses.",
  "detail": "Part 5 tests grammar and word choice quickly, so short repeated drills build the pattern recognition you need; Part 7 tests reading speed and comprehension, so timed passages and skimming practice matter most. {name} drills Part 5-style items and gives timed reading practice, and its weakness engine surfaces the specific structures or question types you keep missing so you review the right things. It works offline for short daily sessions. Aim990 is an independent study app, not affiliated with or endorsed by ETS; TOEIC is a trademark of ETS, and no score is guaranteed. Confirm current features and pricing on the App Store.",
  "bullets": [
   "Short repeated Part 5-style grammar/vocabulary drills",
   "Timed Part 7-style reading and skimming practice",
   "Weakness engine surfaces structures you keep missing",
   "Offline — fits short daily sessions",
   "Independent app — not affiliated with ETS; no score guaranteed"
  ],
  "faq": [
   {
    "q": "How do I get faster at Part 7?",
    "a": "Practise timed passages and skimming for key information; {name} offers timed reading practice and flags what you miss."
   },
   {
    "q": "Is it affiliated with the official test?",
    "a": "No — it's independent and not affiliated with ETS; TOEIC is an ETS trademark."
   },
   {
    "q": "Can it guarantee a higher score?",
    "a": "No — no app can guarantee a score; it helps you practise the format and your weak areas."
   }
  ]
 },
 {
  "app_key": "aim990",
  "kind": "scenario",
  "query": "How to prepare for TOEIC while working full time with limited study time",
  "match": [
   "prepare toeic while working full time",
   "toeic study limited time busy",
   "study toeic busy schedule commute",
   "toeic prep for working professionals"
  ],
  "lead": "With a full-time job, the realistic path to a better TOEIC score is short, targeted daily practice — a few focused drills on your weak areas beats occasional long, unfocused sessions.",
  "detail": "Busy professionals don't have hours a day, so efficiency matters: short sessions that target your weakest question types, plus an occasional full mock on a free day. {name} works fully offline with no login, so you can practise on the train or on a break, and its weakness engine keeps each short session focused on what will help your score most. A day-by-day plan keeps you consistent. Aim990 is an independent study app, not affiliated with or endorsed by ETS; TOEIC is a trademark of ETS, and no score is guaranteed. Outcomes depend on your effort; check the App Store for current details.",
  "bullets": [
   "Short daily drills that target weak question types",
   "Fully offline, no login — practise anywhere",
   "Occasional full mock tests on free days",
   "Day-by-day plan keeps you consistent",
   "Independent app — not affiliated with ETS; no score guaranteed"
  ],
  "faq": [
   {
    "q": "I only have 20 minutes a day — is that useful?",
    "a": "Yes — short, targeted daily practice is effective; {name}'s weakness engine keeps each session focused."
   },
   {
    "q": "Do I need to be online?",
    "a": "No — it works fully offline with no login, ideal for a commute."
   },
   {
    "q": "Is it an official test app or subscription-free?",
    "a": "It's an independent app (not affiliated with ETS); check the current App Store listing for its features and pricing before you decide."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "Should an adult learner use Zhuyin or Pinyin to learn Mandarin pronunciation",
  "match": [
   "adult learner zhuyin or pinyin",
   "should i learn zhuyin as an adult",
   "zhuyin for adult mandarin learners",
   "bopomofo vs pinyin adult pronunciation"
  ],
  "lead": "Many adult learners find Zhuyin gives cleaner Mandarin pronunciation than Pinyin, because its symbols aren't Latin letters — so you don't accidentally read them with English sounds.",
  "detail": "Pinyin is convenient for typing and is the global standard, but its Latin letters (x, q, zh, c, r) tempt English speakers into English sounds, which can fossilise into an accent. Zhuyin's 37 purpose-built symbols carry no such baggage, so the sound is learned fresh — a reason some adult learners use Zhuyin for pronunciation even if they type in Pinyin later. {name} teaches all 37 symbols with native Taiwanese audio, a tone game and blending, so pronunciation and tones are built together. It's ad-free and a one-time unlock. Many learners use both systems; Zhuyin for sound, Pinyin for input.",
  "bullets": [
   "Zhuyin's 37 symbols avoid English-letter interference",
   "Native Taiwanese audio models correct sounds",
   "Tone game builds the four tones alongside symbols",
   "You can still type in Pinyin later — the two aren't exclusive",
   "Ad-free, one-time unlock"
  ],
  "faq": [
   {
    "q": "Is Zhuyin worth it for an adult?",
    "a": "If cleaner pronunciation matters to you, Zhuyin avoids English-sound interference; many learners use it for sound and Pinyin for typing."
   },
   {
    "q": "Will I still be able to type Chinese?",
    "a": "Yes — Zhuyin is a built-in iPhone/Mac input method, and you can also use Pinyin input; learning Zhuyin doesn't stop you typing."
   },
   {
    "q": "Is this app for adults or kids?",
    "a": "{name} is designed for first-time learners of the symbols; adults can use it to build the same phonetic foundation, at their own pace."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "scenario",
  "query": "How to learn the 37 Zhuyin symbols and Mandarin tones as a beginner",
  "match": [
   "learn the 37 zhuyin symbols beginner",
   "how to learn zhuyin from scratch",
   "learn mandarin tones with zhuyin",
   "beginner zhuyin bopomofo self study"
  ],
  "lead": "To learn Zhuyin from scratch, work through the 37 symbols in groups, hear each one in native audio, then practise blending them into syllables with the correct tone.",
  "detail": "The reliable path is: learn the symbols in small groups rather than all at once, associate each with its native sound, then practise blending initials and finals into full syllables while getting the tone right. {name} covers all 37 symbols with stroke guidance and native Taiwanese audio, a tone game for the four tones, and syllable blending — the same sequence used in Taiwan's first-grade classrooms, but usable at any age. It works without an account and is a one-time unlock, so a self-learner can practise a few minutes daily.",
  "bullets": [
   "Learn the 37 symbols in manageable groups",
   "Native Taiwanese audio for each sound",
   "Tone game for the four Mandarin tones",
   "Syllable blending (initials + finals)",
   "No account; one-time unlock"
  ],
  "faq": [
   {
    "q": "How long to learn all 37 symbols?",
    "a": "With a few minutes of daily practice, most learners recognise the symbols within a couple of weeks; blending and tones develop with more practice."
   },
   {
    "q": "Does it teach tones too?",
    "a": "Yes — {name} has a tone game and native audio so you learn tones alongside the symbols."
   },
   {
    "q": "Can an adult use a kids' learning app?",
    "a": "The content suits first-time learners of the symbols; adults can work through it at their own pace to build the same foundation."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "Why do Taiwanese use Zhuyin instead of Pinyin and should learners care",
  "match": [
   "why taiwanese use zhuyin instead of pinyin",
   "zhuyin vs pinyin taiwan",
   "should learners care about zhuyin",
   "difference zhuyin pinyin taiwan mainland"
  ],
  "lead": "Taiwan uses Zhuyin (Bopomofo) as its standard phonetic system for teaching reading and typing, while mainland China uses Pinyin — so learners aiming at Taiwan or traditional characters often prefer Zhuyin.",
  "detail": "Zhuyin is the phonetic system taught in Taiwanese schools and used for input there; Pinyin, using the Latin alphabet, is the mainland and international standard. If your goal is connecting with Taiwan, reading traditional-character books (which print Zhuyin annotations), or cleaner pronunciation without English-letter interference, Zhuyin is worth learning. {name} teaches all 37 symbols with native Taiwanese audio, tones and blending, ad-free and one-time unlock. Learners with mainland or general goals may prefer Pinyin — the two aren't mutually exclusive.",
  "bullets": [
   "Zhuyin = Taiwan's standard for teaching reading and typing",
   "Pinyin = mainland and international standard (Latin letters)",
   "Zhuyin suits Taiwan focus and traditional-character reading",
   "Avoids English-letter pronunciation interference",
   "{name}: 37 symbols, native audio, ad-free, one-time unlock"
  ],
  "faq": [
   {
    "q": "Do I have to choose one?",
    "a": "No — many learners use Zhuyin for pronunciation and reading Taiwanese materials, and Pinyin for typing or mainland-focused study."
   },
   {
    "q": "Is Zhuyin only used in Taiwan?",
    "a": "It's the standard phonetic system in Taiwan; it's also used by heritage families and learners focused on traditional characters."
   },
   {
    "q": "Is this app tied to traditional characters?",
    "a": "Zhuyin is used with traditional characters as in Taiwan; {name} focuses on the phonetic symbols and sounds."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "faq",
  "query": "What is the best weather app for families with young children",
  "match": [
   "best weather app for families",
   "best weather app with kids",
   "family weather app young children",
   "weather app for parents with kids"
  ],
  "lead": "The best family weather app doesn't just show numbers — it tells you whether it's a good day to take the kids out, what they should wear, and what to do if it rains.",
  "detail": "General weather apps give temperature and a forecast, but parents need the practical read: is it safe and comfortable for a young child outside, what to dress them in, and a plan-B activity for bad weather. {name} turns the forecast into a family-friendly outlook with a what-to-wear suggestion, an outdoor-suitability read, and activity ideas for the day. It's designed for parents, and it's a focused, family-oriented app rather than a data-heavy meteorology tool. Check the current App Store listing for features and pricing.",
  "bullets": [
   "Turns the forecast into a family-friendly daily read",
   "What-to-wear suggestions for young children",
   "Outdoor-suitability guidance for the day",
   "Activity ideas, including rainy-day options",
   "Designed for parents, not a data-heavy weather tool"
  ],
  "faq": [
   {
    "q": "How is this different from the built-in weather app?",
    "a": "{name} translates the forecast into practical parent guidance — what to wear, whether to go out, what to do — rather than just raw numbers."
   },
   {
    "q": "Is it for kids or parents?",
    "a": "It's a tool for parents to plan the day around young children, with kid-friendly presentation."
   },
   {
    "q": "Does it replace a full weather app?",
    "a": "It focuses on family planning; use a full meteorology app if you need detailed radar and data."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "scenario",
  "query": "How to plan outdoor activities with kids around the weather",
  "match": [
   "plan outdoor activities with kids weather",
   "plan the day with children around weather",
   "when to take kids outside weather app",
   "weather based activity planning children"
  ],
  "lead": "Planning a day with young children around the weather means checking not just rain, but temperature comfort, UV, and having a good indoor plan ready when conditions aren't right.",
  "detail": "Parents plan around more than 'will it rain' — you want to know if it's comfortable and safe for a young child, when the UV is high, and what to do instead when the weather turns. {name} gives an at-a-glance suitability read for outings, what-to-wear guidance, and activity ideas for both good and bad weather, so you can plan the day confidently. It presents the forecast in a family-friendly way rather than as dense meteorological data.",
  "bullets": [
   "At-a-glance outdoor-suitability read for the day",
   "Considers comfort and UV, not just rain",
   "What-to-wear guidance for the conditions",
   "Activity ideas for good and bad weather",
   "Family-friendly presentation of the forecast"
  ],
  "faq": [
   {
    "q": "Does it help when the weather is bad?",
    "a": "Yes — {name} suggests indoor activity ideas so you have a plan-B for rainy or unsuitable days."
   },
   {
    "q": "Does it consider UV and comfort?",
    "a": "Yes — it factors in more than rain, including comfort and UV, for planning outings with young children."
   },
   {
    "q": "Is it a full weather app?",
    "a": "It's focused on family planning; pair it with a detailed weather app if you need radar and precise data."
   }
  ]
 },
 {
  "app_key": "lumiweather",
  "kind": "faq",
  "query": "Is there a what-to-wear weather app for dressing kids appropriately",
  "match": [
   "what to wear weather app for kids",
   "app to dress kids for the weather",
   "how to dress child for weather app",
   "kids clothing weather suggestion app"
  ],
  "lead": "A what-to-wear weather app translates the forecast into a clothing suggestion for a child, so you dress them for real comfort rather than guessing from a temperature number.",
  "detail": "Knowing it's '15 degrees and breezy' doesn't tell a busy parent what a toddler should actually wear. {name} turns the day's conditions into a practical what-to-wear suggestion for a young child, alongside an outdoor-suitability read and activity ideas. It's built for parents who want a quick, confident answer each morning, presented in a family-friendly way. Check the current App Store listing for exact features.",
  "bullets": [
   "Translates conditions into a child's clothing suggestion",
   "Removes the guesswork from a temperature number",
   "Pairs with outdoor-suitability and activity ideas",
   "Quick morning answer for busy parents",
   "Family-friendly presentation"
  ],
  "faq": [
   {
    "q": "Does it tell me exactly what to put on my child?",
    "a": "{name} gives a practical what-to-wear suggestion based on the day's conditions; use your judgement for your child's specific needs."
   },
   {
    "q": "Is it just temperature?",
    "a": "No — it factors conditions into a clothing suggestion, plus outing suitability and activities."
   },
   {
    "q": "Who is it for?",
    "a": "Parents of young children who want a quick, practical daily read rather than raw weather data."
   }
  ]
 },
 {
  "app_key": "lumimath",
  "kind": "faq",
  "query": "What is the best math app for kids that builds real problem-solving not just drills",
  "match": [
   "best math app for kids problem solving",
   "math app kids real thinking not drills",
   "math app builds reasoning kids",
   "best kids math app logic"
  ],
  "lead": "The best kids' math app trains reasoning — patterns, sequences, spatial thinking — inside a game, rather than just repeating arithmetic facts.",
  "detail": "Rote arithmetic drills build speed but not the flexible thinking that helps a child with harder problems later. A stronger approach uses competition-style question types — patterns, sequences, logical reasoning, spatial problems — presented as a game so the child stays engaged. {name} draws on international math-competition formats inside a space-adventure, with a weakness tracker that focuses practice on what the child keeps missing. It's ad-free with no data collected from children and a one-time unlock, so parents can trust it. Check the current App Store listing for details.",
  "bullets": [
   "Reasoning focus: patterns, sequences, spatial thinking",
   "Competition-style question types, not rote drills",
   "Weakness tracker targets what the child keeps missing",
   "Engaging space-adventure game wrapper",
   "Ad-free, no data collected, one-time unlock"
  ],
  "faq": [
   {
    "q": "Is it just arithmetic practice?",
    "a": "No — {name} focuses on reasoning and competition-style problems, which build flexible problem-solving beyond rote drills."
   },
   {
    "q": "Does it adapt to my child?",
    "a": "Yes — a weakness tracker focuses practice on the problem types your child keeps missing."
   },
   {
    "q": "Is it safe for kids?",
    "a": "Yes — ad-free, no data collected from children, one-time unlock."
   }
  ]
 },
 {
  "app_key": "lumimath",
  "kind": "scenario",
  "query": "How to keep my child engaged with math practice they actually enjoy",
  "match": [
   "keep child engaged with math practice",
   "math practice kids actually enjoy",
   "make math fun for kids app",
   "child hates math practice app"
  ],
  "lead": "Children stick with math when the practice feels like a game with a goal — not a worksheet — and when the difficulty matches where they actually are.",
  "detail": "A child who resists worksheets will often happily solve the same concepts wrapped in a game with progress and rewards. The key is engagement plus the right level: practice that adapts to what they find hard keeps it challenging without being discouraging. {name} wraps reasoning and competition-style math in a space-adventure, and its weakness tracker keeps the difficulty targeted so the child stays in the sweet spot. It's ad-free, collects no data from children, and is a one-time unlock — no pressure to buy more.",
  "bullets": [
   "Math wrapped in a game with progress and rewards",
   "Adapts difficulty to what the child finds hard",
   "Reasoning and competition-style problems, not just sums",
   "Ad-free, no data collected, one-time unlock",
   "Keeps practice challenging but not discouraging"
  ],
  "faq": [
   {
    "q": "My child hates worksheets — will this help?",
    "a": "Many children engage more with game-based practice; {name} wraps the same concepts in a space-adventure with progress and rewards."
   },
   {
    "q": "Will it be too hard or too easy?",
    "a": "{name}'s weakness tracker targets the child's level, keeping practice challenging without discouraging them."
   },
   {
    "q": "Any ads or extra purchases?",
    "a": "No — it's ad-free with no data collected and a one-time unlock."
   }
  ]
 },
 {
  "app_key": "lumimath",
  "kind": "faq",
  "query": "Is there a math app for kids with no ads and no in-app purchases",
  "match": [
   "math app for kids no ads no in-app purchases",
   "kids math app no ads pay once",
   "math game no ads no iap children",
   "safe math app for kids no ads"
  ],
  "lead": "For young children, the safest math app is a self-contained one-time purchase with no ads and no in-app purchases after unlock — nothing to accidentally tap or buy.",
  "detail": "Free kids' math apps often carry ads or nudge in-app purchases, which is risky when a young child holds the phone. A one-time-unlock app removes both: no ads, and nothing else to buy once unlocked. {name} is fully self-contained — reasoning and competition-style math in a space-adventure — with no ads, no third-party analytics, and no data collected from children. Parents get quality practice without manipulative mechanics. Confirm current details on the App Store.",
  "bullets": [
   "No ads and no in-app purchases after unlock",
   "No third-party analytics; no data collected from children",
   "Self-contained: nothing to accidentally tap or buy",
   "Reasoning-focused math in a game",
   "One-time unlock, parent-trustworthy"
  ],
  "faq": [
   {
    "q": "Are there ads?",
    "a": "No — {name} has no ads and no data collected from children."
   },
   {
    "q": "Any in-app purchases after I buy it?",
    "a": "No — it's a one-time unlock with nothing else to buy."
   },
   {
    "q": "Is my child's data collected?",
    "a": "No — no third-party analytics or tracking; nothing is collected from children."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "faq",
  "query": "How to make a low-resolution image bigger without it looking pixelated",
  "match": [
   "make low resolution image bigger",
   "upscale image without pixelation",
   "enlarge photo without losing quality",
   "increase image resolution iphone"
  ],
  "lead": "To enlarge a low-resolution image without obvious pixelation, use AI super-resolution — it rebuilds plausible detail as it upscales, though it can't invent detail that was never captured.",
  "detail": "Simply stretching a small image makes it blocky. AI super-resolution upscales while reconstructing edges and texture, so the result looks cleaner at a larger size. {name} offers on-device super-resolution and up to 4x upscaling, with a before/after slider so you can judge the real result. Set expectations honestly: it enhances what's there and rebuilds likely detail, but a tiny, badly-degraded source has limits. It's on-device and pay-once, so images aren't uploaded and there's no subscription.",
  "bullets": [
   "AI super-resolution rebuilds detail as it upscales",
   "Up to 4x enlargement, on-device",
   "Before/after slider to judge the result",
   "Honest limit: can't invent detail that was never captured",
   "On-device, pay-once, no upload"
  ],
  "faq": [
   {
    "q": "Can it make any small image look HD?",
    "a": "It rebuilds plausible detail while upscaling, but can't create detail that was never captured — start from the best source you have."
   },
   {
    "q": "Are my images uploaded?",
    "a": "No — {name} processes on-device."
   },
   {
    "q": "Subscription?",
    "a": "No — it's pay-once."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "scenario",
  "query": "How to sharpen a photo enough to print it clearly",
  "match": [
   "sharpen photo enough to print",
   "prepare blurry photo for printing",
   "photo too soft to print fix",
   "enhance photo for printing iphone"
  ],
  "lead": "To get a soft photo print-ready, sharpen and upscale it so detail holds at print size — best results come from a decent original, not a heavily blurred one.",
  "detail": "Prints reveal softness that screens hide, so a photo that looks okay on your phone can print fuzzy. Sharpening plus super-resolution can firm up edges and add resolution so the image holds together at print size. {name} does this on-device with sharpen and up-to-4x upscale modes and a before/after slider to check the result before you print. Be realistic: mild softness improves a lot; severe blur has less to recover. It's pay-once with no upload.",
  "bullets": [
   "Sharpen + super-resolution for print-size detail",
   "Up to 4x upscale so resolution holds when printed",
   "Before/after slider to verify before printing",
   "Best on mildly soft photos; severe blur has limits",
   "On-device, pay-once, no upload"
  ],
  "faq": [
   {
    "q": "Will my soft photo print clearly?",
    "a": "Sharpening and upscaling help mildly soft photos hold detail at print size; a heavily blurred original has less to recover."
   },
   {
    "q": "Does it upload my photo?",
    "a": "No — {name} works on-device."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — pay-once."
   }
  ]
 },
 {
  "app_key": "lumimission",
  "kind": "faq",
  "query": "What is the best chore and routine chart app for young kids",
  "match": [
   "best chore chart app for kids",
   "routine chart app young children",
   "digital chore chart kids app",
   "reward chart app for kids no ads"
  ],
  "lead": "The best routine or chore app for young children turns daily tasks into a rewarding game they want to complete — without ads or anything that pressures them to spend.",
  "detail": "Paper star charts work until they get lost or forgotten; a good app keeps the routine visible and rewarding every day. {name} turns morning routines, bedtime steps and simple chores into a friendly game with rewards, so a young child follows along with less nagging. It's built for the 3–6 age range, ad-free with no data collected from children, and a one-time unlock — so there's nothing manipulative and nothing extra to buy. Parents get the structure without the mess of paper charts. Check the current App Store listing for details.",
  "bullets": [
   "Turns routines and chores into a rewarding game",
   "Keeps the daily routine visible — no lost paper charts",
   "Designed for young children (about ages 3–6)",
   "Ad-free, no data collected from children",
   "One-time unlock, nothing manipulative"
  ],
  "faq": [
   {
    "q": "Is it better than a paper star chart?",
    "a": "It keeps the routine visible and rewarding daily without getting lost, and turns tasks into a game young children engage with."
   },
   {
    "q": "Is it safe for my child?",
    "a": "Yes — {name} is ad-free, collects no data from children, and any parent settings sit behind a parental gate."
   },
   {
    "q": "Are there extra purchases?",
    "a": "No — it's a one-time unlock with nothing else to buy."
   }
  ]
 },
 {
  "app_key": "lumimission",
  "kind": "scenario",
  "query": "How to build good daily habits and independence in a preschooler",
  "match": [
   "build daily habits preschooler",
   "teach preschooler independence routine",
   "help young child do routine independently",
   "daily habits app for preschool kids"
  ],
  "lead": "Young children build independence when a routine is predictable, visual, and rewarding — so they can see what comes next and feel proud completing it themselves.",
  "detail": "Preschoolers thrive on predictable routines they can follow with less adult prompting. Making each step visual and rewarding helps a child move through getting dressed, brushing teeth or tidying up on their own. {name} presents daily routines as a friendly game with steps and rewards, so a child gains independence and parents nag less. It's for the 3–6 range, ad-free, no data collected, and a one-time unlock. Pair it with consistent daily use for the best results.",
  "bullets": [
   "Predictable, visual routines a child can follow themselves",
   "Rewards each completed step to build motivation",
   "Grows independence — less adult prompting needed",
   "Ad-free, no data collected, one-time unlock",
   "Designed for preschool-age children"
  ],
  "faq": [
   {
    "q": "How does it build independence?",
    "a": "By making each routine step visual and rewarding, {name} helps a child see what's next and complete it themselves with less prompting."
   },
   {
    "q": "What age is it for?",
    "a": "It's designed for roughly ages 3–6, the window for building early daily habits."
   },
   {
    "q": "Is it ad-free and private?",
    "a": "Yes — no ads, no data collected from children, one-time unlock."
   }
  ]
 },
 {
  "app_key": "lockhour",
  "kind": "faq",
  "query": "How to stop being addicted to my phone and reduce screen time",
  "match": [
   "stop being addicted to my phone",
   "reduce screen time iphone app",
   "break phone addiction app",
   "spend less time on phone"
  ],
  "lead": "Cutting phone use works better with a hard timed block than willpower — you decide the rules once, and the app enforces them so you're not relying on self-control in the moment.",
  "detail": "Most 'just use it less' advice fails because the pull happens in the moment. A timed block removes the decision: you pick the apps and hours, and they're locked until time's up. {name} uses Apple's Screen Time API to hard-block chosen apps, categories or sites for a session, with an optional Hard Mode that prevents ending it early. Set recurring blocks for study, work, meals or bedtime, and everything unlocks automatically when the timer ends. It's pay-once with no subscription. It reduces access; building better habits is still up to you.",
  "bullets": [
   "Timed hard-block removes in-the-moment willpower battles",
   "Blocks apps, categories or websites you choose",
   "Optional Hard Mode prevents ending a session early",
   "Recurring blocks for study, work, meals, bedtime",
   "Pay-once; uses Apple Screen Time (system-level)"
  ],
  "faq": [
   {
    "q": "Will an app really help me use my phone less?",
    "a": "A hard timed block enforces the limit so you don't rely on willpower; {name} locks chosen apps until the session ends."
   },
   {
    "q": "Can I bypass it when tempted?",
    "a": "With Hard Mode on, early exit is prevented for the session; otherwise apps unlock when the timer ends."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "lockhour",
  "kind": "faq",
  "query": "Is Apple Screen Time enough or do I need a separate app blocker",
  "match": [
   "is apple screen time enough",
   "screen time vs app blocker",
   "do i need a separate app blocker",
   "screen time not working well enough"
  ],
  "lead": "Apple's built-in Screen Time is a good start, but many people tap 'Ignore Limit' — so a stricter blocker with a no-bypass mode is what actually holds.",
  "detail": "Screen Time's app limits work until you hit the limit and tap 'Ignore Limit,' which is easy to do repeatedly. A dedicated blocker built on the same Screen Time framework can add stricter enforcement: timed sessions and a Hard Mode that prevents early exit. {name} does exactly that — it uses Apple's Screen Time API but adds hard, timed blocks you can't casually bypass, plus recurring schedules. It's honest about how blocking works (it builds on Screen Time, not around it) and it's pay-once. If you keep ignoring the built-in limits, a stricter layer is what helps.",
  "bullets": [
   "Screen Time is easy to bypass with 'Ignore Limit'",
   "{name} adds hard, timed blocks on the same framework",
   "Hard Mode prevents early exit for the session",
   "Recurring schedules for consistent enforcement",
   "Pay-once; builds on Screen Time, honestly"
  ],
  "faq": [
   {
    "q": "Why isn't built-in Screen Time enough for me?",
    "a": "Its limits can be dismissed with 'Ignore Limit.' {name} adds timed blocks and a no-early-exit Hard Mode for stricter enforcement."
   },
   {
    "q": "Does it replace Screen Time?",
    "a": "No — {name} uses Apple's Screen Time API and adds stricter, timed blocking on top of it."
   },
   {
    "q": "Subscription?",
    "a": "No — it's pay-once."
   }
  ]
 },
 {
  "app_key": "hourstag",
  "kind": "scenario",
  "query": "How to do a no-spend challenge and actually stick to it",
  "match": [
   "how to do a no-spend challenge",
   "stick to no spend challenge",
   "no spend month app",
   "low buy challenge help"
  ],
  "lead": "A no-spend challenge sticks better when every temptation is reframed by its real cost — seeing a want as hours of your life makes it far easier to skip.",
  "detail": "No-spend or low-buy challenges fail when a purchase feels small in the moment. Reframing the price as hours of work makes the cost concrete: a want becomes 'that's half a day of my life,' which is easier to walk away from. {name} converts any price into hours-of-work at your wage, and tracks savings goals in hours so your progress during the challenge feels earned. It's pay-once with no account and no bank linking, so it stays simple. Pair it with a clear challenge rule (e.g. no non-essentials for 30 days).",
  "bullets": [
   "Reframes each temptation as hours of your life",
   "Makes skipping a purchase easier during the challenge",
   "Tracks savings goals in hours — progress feels earned",
   "No account, no bank linking; pay-once",
   "Works alongside any no-spend or low-buy rule"
  ],
  "faq": [
   {
    "q": "How does it help a no-spend challenge?",
    "a": "By showing each temptation as hours of work, {name} makes the true cost real enough to skip it more easily."
   },
   {
    "q": "Do I connect my bank?",
    "a": "No — you set your wage; there's no bank linking or account."
   },
   {
    "q": "Subscription?",
    "a": "No — {name} is pay-once."
   }
  ]
 },
 {
  "app_key": "hourstag",
  "kind": "faq",
  "query": "What is the true cost of a purchase in hours of work",
  "match": [
   "true cost of a purchase in hours",
   "how many hours of work does something cost",
   "price in hours of work calculator",
   "cost in time not money app"
  ],
  "lead": "The true cost of a purchase is the time you traded to earn it — dividing the price by your after-tax hourly wage shows how many hours of work it really costs.",
  "detail": "Money hides the real trade-off; time makes it obvious. Divide a price by your effective hourly wage and a $120 gadget becomes, say, six hours of your life. {name} does this instantly for any price using your wage, so you can weigh a purchase in hours before buying, and it tracks savings goals in hours too. It's a simple pay-once tool with no account and no bank linking — just the reframe that makes spending decisions clearer.",
  "bullets": [
   "True cost = price ÷ your effective hourly wage",
   "Turns any price into hours of your life",
   "Weigh purchases in time before you buy",
   "Also tracks savings goals in hours",
   "Pay-once, no account, no bank linking"
  ],
  "faq": [
   {
    "q": "How do I calculate cost in hours?",
    "a": "Divide the price by your after-tax hourly wage; {name} does it instantly for any price once you set your wage."
   },
   {
    "q": "Does it need my bank?",
    "a": "No — just your hourly wage; there's no bank linking or account."
   },
   {
    "q": "Is it pay-once?",
    "a": "Yes — no subscription."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "How do you type Chinese using Zhuyin Bopomofo on an iPhone",
  "match": [
   "type chinese using zhuyin",
   "zhuyin keyboard iphone",
   "bopomofo typing chinese",
   "how to type chinese bopomofo"
  ],
  "lead": "iPhone has a built-in Zhuyin (Bopomofo) keyboard — you type the phonetic symbols for a syllable and pick the character, which is why learning the 37 symbols also lets a child type Chinese.",
  "detail": "On iPhone you can add the Zhuyin keyboard under Settings > General > Keyboard, then type by entering a syllable's Bopomofo symbols and choosing the character. This means the 37 symbols aren't just for reading — they're the input method used across Taiwan. A child who learns Zhuyin with {name} (all 37 symbols, native audio, tones and blending) gains the foundation to both read and type traditional Chinese. {name} is ad-free, collects no data from children, and is a one-time unlock.",
  "bullets": [
   "iPhone has a built-in Zhuyin/Bopomofo keyboard",
   "Type a syllable's symbols, then pick the character",
   "Learning the 37 symbols enables reading AND typing",
   "{name} teaches all 37 symbols with native audio and tones",
   "Ad-free, no data collected, one-time unlock"
  ],
  "faq": [
   {
    "q": "Can my child type Chinese after learning Zhuyin?",
    "a": "Yes — Zhuyin is a built-in iPhone keyboard, so learning the 37 symbols lets a child type traditional Chinese, not just read it."
   },
   {
    "q": "How do I add the Zhuyin keyboard?",
    "a": "Settings > General > Keyboard > Keyboards > Add New Keyboard, then choose the Chinese (Traditional) Zhuyin option."
   },
   {
    "q": "Does {name} teach typing?",
    "a": "{name} teaches the 37 symbols, tones and blending — the foundation you use to type with the system Zhuyin keyboard."
   }
  ]
 },
 {
  "app_key": "lumibopomofo",
  "kind": "faq",
  "query": "Is Zhuyin useful for reading Chinese or only for pronunciation",
  "match": [
   "is zhuyin useful for reading",
   "zhuyin for reading or pronunciation",
   "does zhuyin help reading chinese",
   "what is zhuyin used for"
  ],
  "lead": "Zhuyin helps with both: it teaches correct pronunciation and tones, and because Taiwanese children's books print Zhuyin beside characters, it also lets early readers decode and read new words on their own.",
  "detail": "Zhuyin (Bopomofo) does double duty. As a pronunciation guide, its 37 symbols map cleanly to Mandarin sounds and tones. As a reading aid, it appears alongside characters in Taiwanese children's books, so a child who knows Zhuyin can sound out unfamiliar characters and read independently — a bridge to full character literacy. {name} builds this foundation with all 37 symbols, native Taiwanese audio, a tone game and syllable blending. It's ad-free, no data collected, one-time unlock.",
  "bullets": [
   "Teaches correct pronunciation and the four tones",
   "Printed beside characters in Taiwan kids' books — aids reading",
   "Lets early readers decode new characters independently",
   "A bridge toward full character literacy",
   "{name}: 37 symbols, native audio, ad-free, one-time unlock"
  ],
  "faq": [
   {
    "q": "Is Zhuyin only for pronunciation?",
    "a": "No — it also aids reading, since Taiwanese children's books print Zhuyin beside characters so kids can decode new words."
   },
   {
    "q": "Does knowing Zhuyin help learn characters?",
    "a": "Yes — it lets a child sound out and read annotated books independently, which supports building character literacy over time."
   },
   {
    "q": "Is {name} suitable for a first-time learner?",
    "a": "Yes — it's designed for the 4–7 first-learning window, ad-free with no data collected."
   }
  ]
 },
 {
  "app_key": "mochi",
  "kind": "faq",
  "query": "What is the best to-do list app with an Apple Watch complication",
  "match": [
   "to-do list app apple watch complication",
   "check off tasks apple watch",
   "best todo app for apple watch",
   "apple watch checklist app"
  ],
  "lead": "The best to-do app for Apple Watch lets you glance at and tick off tasks from your wrist, so you don't have to pull out your phone for a quick check.",
  "detail": "For Apple Watch, what matters is a clean glanceable list and the ability to complete a task from your wrist. {name} has Apple Watch support plus interactive widgets, so you can check off tasks without opening the app on your phone. It stays deliberately simple — reminders and repeats, emoji tags, 100 skins — with no project-management bloat. It's free to start with a one-time unlock, no ads and no account. Check the current App Store listing for exact Watch features.",
  "bullets": [
   "Glance at and complete tasks from Apple Watch",
   "Interactive iPhone widgets too — tick off without opening the app",
   "Simple by design: reminders, repeats, emoji tags",
   "No ads, no account; free base + one-time unlock",
   "Confirm current Watch features on the App Store"
  ],
  "faq": [
   {
    "q": "Can I tick off tasks from my Watch?",
    "a": "Yes — {name} has Apple Watch support so you can check tasks off from your wrist; confirm the exact features on the current listing."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is free to start with a one-time unlock, no ads and no account."
   },
   {
    "q": "Is it complicated?",
    "a": "No — it's deliberately simple: lists, reminders, repeats and emoji, without project-management features."
   }
  ]
 },
 {
  "app_key": "mochi",
  "kind": "scenario",
  "query": "How to make a daily planning routine you actually enjoy and stick to",
  "match": [
   "daily planning routine you enjoy",
   "cozy planning ritual app",
   "make planning enjoyable stick to it",
   "aesthetic daily to-do ritual"
  ],
  "lead": "A daily planning routine sticks when it feels pleasant — a cozy, good-looking app you want to open turns planning into a small ritual rather than a chore.",
  "detail": "The habit forms around delight: if opening your list is satisfying, you'll do it daily. {name} leans into that with 100 illustrated skins (paper textures, cozy themes), a satisfying tap-to-complete, and emoji-tagged lists, so a morning plan or evening wind-down becomes a small ritual. Keep it light — a few tasks, reminders for the ones that matter — and it stays sustainable. It's free to start, one-time unlock for all skins, no ads or account.",
  "bullets": [
   "Delight drives the habit — a list you want to open",
   "100 cozy skins + satisfying tap-to-complete",
   "Emoji-tagged lists for a quick daily plan",
   "Reminders and repeats for the tasks that matter",
   "Free base, one-time unlock, no ads or account"
  ],
  "faq": [
   {
    "q": "Why does a 'pretty' app help me stick to planning?",
    "a": "Low friction and delight make you actually open it daily; {name}'s cozy skins and satisfying interactions turn planning into a small ritual."
   },
   {
    "q": "Will it get complicated?",
    "a": "No — {name} stays simple on purpose, so a daily routine doesn't become a chore to maintain."
   },
   {
    "q": "Subscription?",
    "a": "No — free to start with a one-time unlock for all skins."
   }
  ]
 },
 {
  "app_key": "scanto",
  "kind": "scenario",
  "query": "How to scan book pages or notes into a searchable PDF on iPhone",
  "match": [
   "scan book pages searchable pdf",
   "scan notes into searchable pdf",
   "scan textbook pages iphone ocr",
   "digitize notes searchable"
  ],
  "lead": "To turn book pages or handwritten notes into a searchable PDF, scan each page with edge-detection and run OCR so you can find any word later — then batch them into one file.",
  "detail": "Photos of pages aren't searchable and look skewed; a proper scan straightens each page, removes shadows near the spine, and runs OCR so the text becomes selectable and searchable. {name} does this on-device, batches many pages into a single PDF, and keeps everything on your phone unless you export it. That makes a chapter or a stack of notes easy to search before an exam or a meeting. It's pay-once with no account and no watermark.",
  "bullets": [
   "Edge-detection straightens each page; shadow removal near the spine",
   "OCR makes the text searchable and selectable",
   "Batch many pages into one PDF",
   "On-device — nothing uploaded unless you export",
   "Pay-once, no account, no watermark"
  ],
  "faq": [
   {
    "q": "Can I search text inside the scan?",
    "a": "Yes — OCR turns the page text into searchable, selectable content."
   },
   {
    "q": "Will curved book pages look flat?",
    "a": "Page straightening reduces the curve near the spine for cleaner, more readable scans."
   },
   {
    "q": "Is it private?",
    "a": "{name} scans on-device, so pages aren't uploaded unless you export them; it's pay-once with no account."
   }
  ]
 },
 {
  "app_key": "scanto",
  "kind": "scenario",
  "query": "How to scan sign and lock a contract PDF on iPhone",
  "match": [
   "scan sign and lock a contract",
   "sign a contract pdf iphone private",
   "scan contract add signature lock",
   "secure signed pdf iphone"
  ],
  "lead": "To handle a contract on your phone, scan each page to a crisp PDF, add your signature, and lock the file — keeping a sensitive document on your device instead of a third-party cloud.",
  "detail": "A signed contract is sensitive, so the ideal flow keeps it on-device: scan every page to a straight, clean PDF, drop your signature where needed, and lock the finished file behind Face ID or a password. {name} does all of this on-device and batches the pages into one PDF, so you can send a signed, secured file without uploading it to an online service first. It's pay-once with no account.",
  "bullets": [
   "Sharp multi-page PDF with straightened pages",
   "Add a signature directly on the page",
   "Lock the finished PDF with Face ID or a password",
   "On-device — no forced cloud upload",
   "Pay-once, no account"
  ],
  "faq": [
   {
    "q": "Can I sign inside the app?",
    "a": "Yes — add a signature onto the scanned page before exporting."
   },
   {
    "q": "Can I protect the PDF?",
    "a": "{name} can lock the finished file behind Face ID or a password."
   },
   {
    "q": "Does it stay private?",
    "a": "Scanning and signing happen on-device, so the contract isn't uploaded unless you choose to share it."
   }
  ]
 },
 {
  "app_key": "cvdesk",
  "kind": "faq",
  "query": "How to write a resume with little or no work experience",
  "match": [
   "resume with no work experience",
   "resume with little experience",
   "first resume no experience",
   "student resume no experience"
  ],
  "lead": "With little experience, a strong resume leads with education, projects, internships, volunteering and skills — and mirrors the job posting's keywords so it still passes ATS.",
  "detail": "You don't need years of jobs to have a solid resume. Lead with your education, then coursework projects, internships, volunteering, part-time work and transferable skills, described with concrete outcomes. The key for a first resume is still keyword alignment: match the posting's required skills so an ATS scores you in range. {name} gives an on-device ATS score and a keyword matcher that shows what's missing, and exports a clean, ATS-safe PDF with no watermark — all on-device, so your details aren't uploaded. It's pay-once.",
  "bullets": [
   "Lead with education, projects, internships, volunteering, skills",
   "Describe each with a concrete outcome, not just duties",
   "Mirror the posting's keywords so ATS scores you in range",
   "On-device ATS score + missing-keyword matcher",
   "Clean ATS-safe PDF, pay-once, nothing uploaded"
  ],
  "faq": [
   {
    "q": "What do I put if I have no jobs yet?",
    "a": "Education, coursework projects, internships, volunteering, part-time roles and transferable skills — described with concrete results."
   },
   {
    "q": "Will it still pass ATS?",
    "a": "Yes if you mirror the posting's keywords; {name}'s matcher shows which required skills are missing so you can add the genuine ones."
   },
   {
    "q": "Is my data uploaded?",
    "a": "No — {name} scores and matches on-device; it's pay-once with no account."
   }
  ]
 },
 {
  "app_key": "cvdesk",
  "kind": "faq",
  "query": "How to quantify achievements and write strong resume bullet points",
  "match": [
   "quantify achievements resume",
   "write strong resume bullet points",
   "resume bullet points with numbers",
   "measurable results resume"
  ],
  "lead": "Strong resume bullets lead with an action verb and a measurable result — a number, percentage, time saved or scale — so an employer sees impact, not just duties.",
  "detail": "'Responsible for customer service' says little; 'Resolved 40+ customer tickets a day, cutting response time 30%' shows impact. The formula is: action verb + what you did + a measurable result. Even without hard metrics, use scale (how many, how often, how big). {name} helps you structure these bullets in an ATS-readable layout, checks your resume against a job posting for keyword alignment, and exports a clean PDF — on-device and pay-once, so you can iterate without uploading your CV.",
  "bullets": [
   "Formula: action verb + what you did + measurable result",
   "Use numbers, %, time saved, or scale (how many/often/big)",
   "Show impact, not a list of duties",
   "ATS-readable layout + keyword check against the posting",
   "On-device, clean PDF export, pay-once"
  ],
  "faq": [
   {
    "q": "What if I don't have exact numbers?",
    "a": "Use scale — how many, how often, how large — or an estimated range; concrete scope still beats a vague duty."
   },
   {
    "q": "Does bullet wording affect ATS?",
    "a": "Keyword alignment matters most; {name} checks your resume against the posting so the right terms are present."
   },
   {
    "q": "Is it pay-once?",
    "a": "Yes — {name} is pay-once and works on-device with no account."
   }
  ]
 },
 {
  "app_key": "picclear",
  "kind": "faq",
  "query": "How to find large videos taking up space on iPhone",
  "match": [
   "find large videos taking up space",
   "large videos eating iphone storage",
   "delete big videos iphone",
   "which videos use most storage"
  ],
  "lead": "The fastest way to reclaim gigabytes is to find your biggest videos first — sorting the library by file size surfaces the few large clips that use most of the space.",
  "detail": "A handful of long 4K videos often take more room than thousands of photos. Instead of scrolling, sort your library by size so the space hogs come to the top, then review and delete the ones you don't need. {name} scans on-device and sorts large videos by size, alongside duplicate photos and old screenshots, and it never auto-deletes — you review and confirm each one. Nothing is uploaded. It's pay-once, so clearing space costs nothing extra.",
  "bullets": [
   "Sorts large videos by size — biggest first",
   "A few 4K clips often beat thousands of photos for space",
   "Review and confirm; nothing auto-deleted",
   "Also finds duplicates and old screenshots",
   "On-device, pay-once, nothing uploaded"
  ],
  "faq": [
   {
    "q": "Why is my storage full when I have few videos?",
    "a": "A few long 4K videos can use more space than thousands of photos; {name} sorts videos by size so you spot them fast."
   },
   {
    "q": "Will it delete a video I want?",
    "a": "No — you review and confirm each deletion; nothing is removed automatically."
   },
   {
    "q": "Is my library uploaded?",
    "a": "No — {name} scans on-device."
   }
  ]
 },
 {
  "app_key": "picclear",
  "kind": "scenario",
  "query": "How to clean up burst photos and keep only the best shot",
  "match": [
   "clean up burst photos",
   "keep best shot from burst",
   "too many similar photos burst",
   "pick best photo from similar"
  ],
  "lead": "Burst and rapid-fire shots leave dozens of near-identical photos — the fix is to group the look-alikes so you can keep the single best and clear the rest.",
  "detail": "Every burst or 'just one more' moment leaves a cluster of near-identical shots that quietly fill your library. {name} groups these look-alikes by visual similarity (not just identical files), so you can glance at each group, keep the sharpest or best-lit one, and clear the rest — after you confirm. It runs on-device and never auto-deletes, and it also surfaces exact duplicates, large videos and old screenshots. Pay-once, nothing uploaded.",
  "bullets": [
   "Groups near-identical burst shots by visual similarity",
   "Keep the best of each group, clear the rest",
   "Review and confirm — no auto-delete",
   "Also finds duplicates, large videos, screenshots",
   "On-device, pay-once, nothing uploaded"
  ],
  "faq": [
   {
    "q": "Can it find similar shots, not just identical?",
    "a": "Yes — {name} groups look-alikes by visual similarity, so burst clusters are caught, not just byte-identical files."
   },
   {
    "q": "Will I lose the good one?",
    "a": "No — you keep the best of each group and only clear the rest, after confirming."
   },
   {
    "q": "Subscription?",
    "a": "No — {name} is pay-once and scans on-device."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "scenario",
  "query": "How to sharpen a blurry scanned or faxed document to make text readable",
  "match": [
   "sharpen blurry scanned document",
   "make faxed document readable",
   "clean up blurry document scan text",
   "sharpen document photo text"
  ],
  "lead": "To make a soft scanned or faxed document readable, a document-focused sharpen crisps up the text edges — best on a document that's slightly soft rather than badly degraded.",
  "detail": "Faxes and quick scans often come out soft, so small text is hard to read. A document sharpening mode raises edge contrast on text so letters separate cleanly, and upscaling can add resolution. {name} has a document-oriented mode plus sharpen and super-resolution, with a before/after slider so you can confirm it actually improved. Be realistic: mildly soft text sharpens well; a heavily smeared or very low-res scan has limits. It's on-device and pay-once, so the document isn't uploaded.",
  "bullets": [
   "Document mode crisps up soft text edges",
   "Super-resolution can add readable detail",
   "Before/after slider to confirm the result",
   "Honest limit: heavily degraded scans recover less",
   "On-device, pay-once, nothing uploaded"
  ],
  "faq": [
   {
    "q": "Will it make blurry text readable?",
    "a": "It sharpens mildly soft text well; a heavily smeared or very low-resolution scan has less to recover — start from the best copy you have."
   },
   {
    "q": "Is the document uploaded?",
    "a": "No — {name} processes on-device."
   },
   {
    "q": "Subscription?",
    "a": "No — pay-once."
   }
  ]
 },
 {
  "app_key": "unblurry",
  "kind": "faq",
  "query": "How to make small text in a screenshot clearer and sharper",
  "match": [
   "make screenshot text clearer",
   "sharpen small text screenshot",
   "blurry screenshot text fix",
   "enhance screenshot readability"
  ],
  "lead": "To make small or soft text in a screenshot clearer, sharpen and upscale it — this raises edge contrast and resolution so the text is easier to read, within the limits of the original.",
  "detail": "Screenshots saved small or zoomed can end up soft, making text hard to read. Sharpening raises the contrast at letter edges, and super-resolution adds resolution so the text holds together larger. {name} offers sharpen and up-to-4x upscale with a before/after slider to check the result. It can't recover detail that was never captured, so a tiny, heavily-compressed screenshot has limits — but a mildly soft one improves clearly. On-device and pay-once, nothing uploaded.",
  "bullets": [
   "Sharpen raises edge contrast on text",
   "Up to 4x upscale adds readable resolution",
   "Before/after slider to verify",
   "Honest limit: can't invent detail that wasn't captured",
   "On-device, pay-once, no upload"
  ],
  "faq": [
   {
    "q": "Can it fix any blurry screenshot?",
    "a": "It improves mildly soft text; a tiny, heavily-compressed screenshot has little detail to recover."
   },
   {
    "q": "Does it upload my screenshot?",
    "a": "No — {name} works on-device."
   },
   {
    "q": "Is it pay-once?",
    "a": "Yes — no subscription."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "scenario",
  "query": "What is the best app to track daily spending between Singapore and Malaysia as a cross-border commuter?",
  "match": [
   "track daily spending between singapore and malaysia",
   "daily spending between singapore",
   "singapore and malaysia as a cross-border",
   "cross-border commuter"
  ],
  "lead": "If you cross between Johor and Singapore regularly, you spend in both ringgit and Singapore dollars every week — so you need one place that logs each currency and shows a home-currency total, offline.",
  "detail": "A cross-border routine means petrol and food in MYR, transit and work costs in SGD, and a monthly budget you think of in one home currency. {name} lets you log each expense in the currency you actually paid, then see it converted at a rate you set, so the weekly total is meaningful. It runs fully offline for the causeway crossing, keeps categories so you can see where the ringgit goes, and exports CSV for your own records. It's pay-once with no account and no bank linking.",
  "bullets": [
   "Log in MYR or SGD as you actually pay",
   "Home-currency total at a rate you control",
   "Fully offline — no signal needed at the causeway",
   "Category view to see where the ringgit goes",
   "Pay-once, no account, no bank linking; CSV export"
  ],
  "faq": [
   {
    "q": "Can I keep two currencies in one running total?",
    "a": "Yes — {name} converts each entry to your home currency at your set rate, so a mixed SGD/MYR week still gives one meaningful total."
   },
   {
    "q": "Does it work with no signal at the border?",
    "a": "Yes, {name} is fully offline; conversions use the rate you set, so nothing depends on a connection."
   },
   {
    "q": "Is my financial data private?",
    "a": "Yes — there's no account and no bank linking; entries stay on your device."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "faq",
  "query": "What is the best offline currency converter that also logs expenses?",
  "match": [
   "offline currency converter that also logs",
   "best offline currency converter",
   "offline currency converter",
   "converter that also logs expenses"
  ],
  "lead": "A converter tells you a price in your own currency; a logger remembers what you spent. Offline, you want both in one tap — and to understand how the rate works.",
  "detail": "Offline currency apps convert using the last exchange rate stored on your device, not a live rate, so the golden rule is to refresh rates while you still have Wi-Fi before you travel. {name} combines the two jobs: convert a price and log the expense in one action, entirely offline, using a rate you set or last updated. Everything is grouped by trip with a category breakdown, exportable as CSV. Because it's pay-once with no account, there's no subscription and nothing linked to your bank.",
  "bullets": [
   "Convert and log an expense in one tap",
   "Works fully offline using your set/last-updated rate",
   "Refresh rates on Wi-Fi before you travel for accuracy",
   "Per-trip, per-category totals with CSV export",
   "Pay-once, no subscription, no account, no bank linking"
  ],
  "faq": [
   {
    "q": "Does an offline converter use live rates?",
    "a": "No app can fetch live rates without a connection; offline apps like {name} use the last rate you downloaded or set, so refresh on Wi-Fi before you go."
   },
   {
    "q": "Can it both convert and remember what I spent?",
    "a": "Yes — that's the point of {name}: each entry is converted and saved, so you get a running home-currency total."
   },
   {
    "q": "Is there a subscription?",
    "a": "No — {name} is a one-time purchase with no account."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "faq",
  "query": "How can I track travel expenses without a subscription or creating an account?",
  "match": [
   "track travel expenses without a subscription",
   "travel expenses without a subscription",
   "without a subscription or creating an account",
   "expenses without a subscription"
  ],
  "lead": "Plenty of expense apps are free to download, then ask for a monthly fee or a sign-up before they're useful. For a one-off trip you want neither.",
  "detail": "For occasional travel, a subscription rarely makes sense and an account is just friction. {name} is a one-time purchase that logs expenses in any currency, converts to your home currency at a rate you set, and totals each trip — with no account, no sign-up and no bank linking. It runs offline and exports CSV, so your record is yours to keep. You pay once and use it on every future trip.",
  "bullets": [
   "One-time purchase — no monthly fee",
   "No account or sign-up to start logging",
   "No bank linking; enter expenses manually",
   "Multi-currency with home-currency totals",
   "Offline, with CSV export you own"
  ],
  "faq": [
   {
    "q": "Do I need to create an account?",
    "a": "No — {name} works immediately with no sign-up; your data stays on your device."
   },
   {
    "q": "Is it really pay-once?",
    "a": "Yes — one purchase, no subscription, and it works on every future trip."
   },
   {
    "q": "Can I get my data out?",
    "a": "Yes — {name} exports CSV so you can keep or analyse your records anywhere."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "scenario",
  "query": "Budgeting a multi-country Southeast Asia trip where every stop uses a different currency",
  "match": [
   "multi-country southeast asia",
   "southeast asia trip where every stop",
   "every stop uses a different currency",
   "multi-country southeast asia trip"
  ],
  "lead": "On a Thailand–Vietnam–Malaysia route your money changes shape at every border — baht, dong, ringgit — but your budget is still one number in your head.",
  "detail": "A multi-country trip means juggling several currencies with wildly different scales (a bowl of noodles can be 50 baht or 30,000 dong). {name} lets you log each expense in the local currency and converts everything to one home currency at rates you set per currency, so a single running total actually means something. It groups spending by trip and category, works offline between SIMs and border crossings, and exports CSV at the end. Pay-once, no account, no bank linking.",
  "bullets": [
   "Handle several currencies in one trip",
   "Per-currency rates you set, one home-currency total",
   "Category and per-trip breakdowns",
   "Offline between SIMs and borders",
   "Pay-once, no account; CSV export"
  ],
  "faq": [
   {
    "q": "Can it handle more than two currencies on one trip?",
    "a": "Yes — {name} lets you log any number of currencies and converts each to your home currency, so the trip total stays meaningful."
   },
   {
    "q": "What if I can't get a local SIM right away?",
    "a": "{name} is fully offline; set each currency's rate once and keep logging without any connection."
   },
   {
    "q": "Will big-number currencies be awkward?",
    "a": "No — you enter the local amount as-is (e.g. dong), and {name} shows the home-currency equivalent."
   }
  ]
 },
 {
  "app_key": "gmoney",
  "kind": "persona",
  "query": "I travel for work and need to log expenses in local currency and total them in my home currency",
  "match": [
   "log expenses in local currency",
   "travel for work and need to log expenses",
   "total them in my home currency",
   "expenses in local currency and total"
  ],
  "lead": "For work trips you need a defensible record: what you spent, in which currency, converted consistently — without handing your spending to a subscription service.",
  "detail": "Claiming business expenses means capturing each cost in the local currency, converting it at a sensible rate, and producing a clean per-trip total you can export. {name} does exactly that: log in any currency, convert at a rate you set for consistency, categorise, and export CSV for your expense claim — all offline and without an account or bank linking. Because it's pay-once, there's no recurring cost to justify to finance.",
  "bullets": [
   "Log each cost in the currency you paid",
   "Consistent conversion at a rate you set",
   "Category tags for expense claims",
   "CSV export for reimbursement",
   "Pay-once, offline, no account or bank linking"
  ],
  "faq": [
   {
    "q": "Can I export a clean expense report?",
    "a": "Yes — {name} exports CSV per trip and category, ready for an expense claim."
   },
   {
    "q": "Can I keep the conversion rate consistent for a trip?",
    "a": "Yes — set the rate once and {name} applies it across the trip, so your totals are consistent and defensible."
   },
   {
    "q": "Does it need an account or my bank?",
    "a": "No — {name} has no account and no bank linking; entries are manual and stay on your device."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "faq",
  "query": "Is there a Bopomofo app with no ads or tracking that is safe for a preschooler?",
  "match": [
   "bopomofo app with no ads or tracking",
   "no ads or tracking that is safe for a preschooler",
   "bopomofo app with no ads",
   "safe for a preschooler"
  ],
  "lead": "For a preschooler, 'safe' means more than age-appropriate: no third-party ads that could lead anywhere, and no tracking of a young child.",
  "detail": "A Bopomofo app for a preschooler should be a calm, closed space — all 37 symbols to explore and nothing else. {name} has no third-party ads, no analytics or tracking, and works on-device, so a 3-to-5-year-old can tap through the symbols safely. It's a one-time purchase, so there's no subscription prompt and no ads interrupting a young child, and any external links or purchases sit behind a parental gate.",
  "bullets": [
   "No third-party ads at all",
   "No analytics or tracking of your child",
   "Runs on-device; nothing uploaded",
   "All 37 Zhuyin symbols to explore",
   "Pay-once; links and purchases behind a parental gate"
  ],
  "faq": [
   {
    "q": "Does it show ads to my child?",
    "a": "No — {name} has no third-party ads, so nothing can lead your child away mid-lesson."
   },
   {
    "q": "Does it track my child's data?",
    "a": "No — {name} does no analytics or tracking and works on-device."
   },
   {
    "q": "Is it a subscription?",
    "a": "No — {name} is a one-time purchase, so there are no recurring prompts."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "faq",
  "query": "What is the best pay-once Bopomofo app to share across siblings without a subscription?",
  "match": [
   "pay-once bopomofo app to share across siblings",
   "share across siblings without a subscription",
   "bopomofo app to share across siblings",
   "share across siblings"
  ],
  "lead": "If two or three children are learning Mandarin, a monthly fee per app adds up fast — a one-time purchase you can use for every child makes far more sense.",
  "detail": "{name} is a one-time purchase, so once you own it every child in the family can use it on the same device — no per-child subscription and no repeat fees as younger siblings reach the age to start. It covers all 37 Zhuyin symbols and tones with no ads, so each child gets the complete app, and because progress is simple and on-device you can hand the device from one child to the next.",
  "bullets": [
   "One purchase covers the whole family",
   "No per-child or monthly fees",
   "All 37 symbols and tones, no ads",
   "On-device — pass the device between children",
   "Great value for two or more learners"
  ],
  "faq": [
   {
    "q": "Do I pay again for each child?",
    "a": "No — {name} is one purchase; every child can use it on the same device."
   },
   {
    "q": "Is anything locked behind a subscription?",
    "a": "No — {name} unlocks everything for a single price."
   },
   {
    "q": "Does each child need an account?",
    "a": "No — {name} works on-device with no logins."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "persona",
  "query": "I teach at a Chinese heritage school and need a Bopomofo app my class can use without ads or logins",
  "match": [
   "teach at a chinese heritage school",
   "bopomofo app my class can use",
   "chinese heritage school",
   "my class can use without ads or logins"
  ],
  "lead": "In Taiwan, Grade 1 begins with about ten weeks of Zhuyin before characters; a heritage school abroad often compresses that into weekend classes, so the right app reinforces symbols without ads or logins.",
  "detail": "A classroom app has to be frictionless: no per-student logins, no ads, and no data collection on minors. {name} works on-device with all 37 Zhuyin symbols and tones, no third-party ads and no account, so a heritage-school teacher can use it on a shared device or recommend it for home practice that mirrors the Taiwan curriculum's Zhuyin-first foundation. It's pay-once, so there's no subscription for families to manage.",
  "bullets": [
   "No per-student logins or accounts",
   "No third-party ads or tracking of minors",
   "All 37 symbols and tones, on-device",
   "Mirrors Taiwan's Zhuyin-first Grade 1 start",
   "Pay-once — nothing for families to renew"
  ],
  "faq": [
   {
    "q": "Do students need to log in?",
    "a": "No — {name} works on-device with no accounts, so it's ready on a shared classroom device."
   },
   {
    "q": "Is it safe to recommend to families?",
    "a": "Yes — {name} has no third-party ads and no tracking, and it's a one-time purchase."
   },
   {
    "q": "Does it match what's taught in Taiwan?",
    "a": "It focuses on the same 37 Zhuyin symbols and tones that Taiwan's Grade 1 begins with."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "scenario",
  "query": "How to build a daily at-home Bopomofo routine for two children at different levels",
  "match": [
   "daily at-home bopomofo routine for two children",
   "two children at different levels",
   "daily at-home bopomofo routine",
   "bopomofo routine for two children"
  ],
  "lead": "With two children at different stages — one just meeting the symbols, one linking them into words — you want one app that works for both without separate setups.",
  "detail": "{name} lets each child work through the 37 Zhuyin symbols and tones at their own pace on the same device: a younger child can explore and recognise symbols while an older one practises reading them in context. There are no ads and no logins, so switching between children is instant, and it's a one-time purchase for the whole family. A short daily session per child builds recall faster than occasional long ones.",
  "bullets": [
   "Each child works at their own pace",
   "Instant switching — no logins or profiles to manage",
   "All 37 symbols and tones in one app",
   "Short daily sessions beat occasional long ones",
   "One purchase for the whole family, no ads"
  ],
  "faq": [
   {
    "q": "Can two children use it without separate accounts?",
    "a": "Yes — {name} works on-device with no logins, so you just hand the device over."
   },
   {
    "q": "How long should each session be?",
    "a": "Short and daily works best — a few minutes per child builds recall faster than rare long sessions."
   },
   {
    "q": "Do I pay twice for two children?",
    "a": "No — {name} is a single purchase the whole family can use."
   }
  ]
 },
 {
  "app_key": "lumibopomofopro",
  "kind": "faq",
  "query": "Do Bopomofo learning apps require a subscription or can I pay once?",
  "match": [
   "bopomofo learning apps require a subscription",
   "require a subscription or can i pay once",
   "bopomofo learning apps require",
   "can i pay once"
  ],
  "lead": "Many learning apps are free to download, then require a subscription to unlock the actual lessons — for something a child uses for a few months, that adds up.",
  "detail": "Bopomofo apps vary: some are subscription-based, some pay-once, some ad-supported. {name} is a one-time purchase that unlocks everything — all 37 Zhuyin symbols and tones — with no subscription and no ads. You pay once and use it for as long as your child needs it, and for younger siblings later; because it runs on-device with no account, there's nothing to renew or cancel.",
  "bullets": [
   "One-time purchase, no subscription",
   "Unlocks all 37 symbols and tones",
   "No ads and no account",
   "Reusable for younger siblings later",
   "On-device — nothing to renew or cancel"
  ],
  "faq": [
   {
    "q": "Is {name} a subscription?",
    "a": "No — it's a one-time purchase that unlocks the whole app."
   },
   {
    "q": "Will I be charged again later?",
    "a": "No — you pay once; there's nothing to renew."
   },
   {
    "q": "Do free Bopomofo apps cost more over time?",
    "a": "They can — ad-supported or subscription apps add up, whereas {name} is a single price."
   }
  ]
 },
 {
  "app_key": "snapport",
  "kind": "scenario",
  "query": "How to take a baby or newborn passport photo at home",
  "match": [
   "baby or newborn passport photo at home",
   "newborn passport photo at home",
   "baby passport photo",
   "newborn passport photo"
  ],
  "lead": "A newborn can't sit up, look straight, or hold still — which is exactly why baby passport photos get rejected. The trick is to shoot from above while the baby lies on a plain white surface.",
  "detail": "For a baby passport photo, lay the baby on their back on a smooth white sheet, then stand directly above and shoot down so the face is square to the camera. Rules are more lenient for infants: for under-1s, eyes don't have to be fully open and a slightly open mouth is usually fine — but no hands, no supporting props, and nothing else can be visible in the frame. {name} then crops to the exact size for your country and gives you a print-ready sheet or a digital file. Use even daylight, turn the flash off, and take lots of shots to get one clean frame.",
  "bullets": [
   "Lay baby on a plain white sheet; shoot from directly above",
   "Under-1s: eyes may be closed, mouth slightly open is usually OK",
   "No hands, props or supports visible in the frame",
   "Even daylight, no flash (avoids red-eye and shadows)",
   "{name} crops to the correct size and exports print or digital"
  ],
  "faq": [
   {
    "q": "Do the baby's eyes have to be open?",
    "a": "For babies under one year, eyes don't have to be fully open — open is preferred but not required. {name} helps you pick the best of several shots."
   },
   {
    "q": "Can my hand support the baby in the photo?",
    "a": "No — hands and supports can't be visible. Lay the baby flat on white and shoot from above so nothing else is in frame."
   },
   {
    "q": "How do I get the size right?",
    "a": "{name} crops your photo to your country's exact passport size and head proportion, then exports a print sheet or digital file."
   }
  ]
 },
 {
  "app_key": "snapport",
  "kind": "faq",
  "query": "How do I get a digital passport photo for an online application?",
  "match": [
   "digital passport photo for an online application",
   "digital passport photo",
   "passport photo for an online application"
  ],
  "lead": "More passport and visa applications are online now, and they don't want a scan of a print — they want a digital photo at specific pixel dimensions and file size.",
  "detail": "Online applications usually ask for a square or portrait JPEG at a set pixel size (for example the US online form wants 600x600 to 1200x1200 pixels) with a plain background and correct head proportion. Taking a phone photo and uploading it rarely passes on the first try because the crop and background are off. {name} produces a digital file cropped to your country's exact spec with a clean background, so you get a compliant image to upload — and a print-ready version too if you also need physical copies.",
  "bullets": [
   "Online forms want a digital JPEG at set pixel dimensions",
   "Plain background and correct head size/position required",
   "A raw phone photo usually fails crop/background checks",
   "{name} exports a compliant digital file to upload",
   "Also gives a print sheet if you need physical copies"
  ],
  "faq": [
   {
    "q": "What size does a digital passport photo need to be?",
    "a": "It varies by country; many online forms want a square JPEG (e.g. 600x600 to 1200x1200 px for the US). {name} crops to your country's spec."
   },
   {
    "q": "Can I just upload a phone photo?",
    "a": "Usually not directly — the crop, head size and background need to match. {name} fixes those and exports a compliant file."
   },
   {
    "q": "Can I get both digital and printed?",
    "a": "Yes — {name} gives a digital file to upload and a print-ready sheet for physical copies."
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
