#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate topic hub pages linking to all language variants for key topics."""
import json, os, sys
from pathlib import Path
from site_config import PUBLIC_SITE  # noqa: E402

HERE = Path(__file__).parent
PAGES = HERE / "pages"
HUBS = PAGES / "topic-hubs"
HUBS.mkdir(parents=True, exist_ok=True)

GEO_SITE = os.getenv("GEO_SITE", PUBLIC_SITE)
CSS = """body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#222}
h1{font-size:1.6rem;line-height:1.3}h2{font-size:1.1rem;color:#555;margin-top:2rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.6rem;margin:1rem 0}
.lang-link{display:block;padding:.5rem .8rem;background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;
  text-decoration:none;color:#007aff;font-weight:600;font-size:.85rem;transition:background .15s}
.lang-link:hover{background:#e0f2fe}.count{color:#888;font-size:.9rem;margin:.5rem 0}
.back{color:#007aff;text-decoration:none;font-size:.9rem}
"""

# Topic definitions: (slug, title, desc, lang_subdir, page_slug_pattern)
TOPICS = [
    {
        "slug": "photo-privacy-all-languages",
        "title": "Best iPhone App for Photo Privacy — All Languages",
        "desc": "Best iPhone photo privacy apps — available in 171 languages. Find your language version.",
        "subdir": "best-for",
        "page_slug": "iphone-best-app-photo-hide",
        "emoji": "🔒",
    },
    {
        "slug": "offline-scanner-all-languages",
        "title": "Best Offline Document Scanner iPhone App — All Languages",
        "desc": "Best offline iPhone PDF scanner with no cloud upload — available in 171 languages.",
        "subdir": "best-for",
        "page_slug": "iphone-best-app-scan-offline",
        "emoji": "📄",
    },
    {
        "slug": "passport-photo-all-languages",
        "title": "Best iPhone App for Passport Photos at Home — All Languages",
        "desc": "Make passport photos at home on iPhone — available in 171 languages.",
        "subdir": "best-for",
        "page_slug": "iphone-best-app-passport-photo",
        "emoji": "📷",
    },
    {
        "slug": "document-redaction-all-languages",
        "title": "Best iPhone App to Mask Document Data — All Languages",
        "desc": "Hide sensitive data in documents on iPhone — available in 171 languages.",
        "subdir": "best-for",
        "page_slug": "iphone-best-app-document-mask",
        "emoji": "📋",
    },
    {
        "slug": "privacy-workflow-all-languages",
        "title": "iPhone Privacy Workflow Guide — All Languages",
        "desc": "Complete iPhone privacy setup guide — available in 171 languages.",
        "subdir": "workflow",
        "page_slug": "iphone-privacy",
        "emoji": "🛡️",
    },
    {
        "slug": "freelancer-workflow-all-languages",
        "title": "iPhone Apps for Freelancers — All Languages",
        "desc": "iPhone app workflow for freelancers working offline — available in 171 languages.",
        "subdir": "workflow",
        "page_slug": "iphone-workflow-freelancer",
        "emoji": "💼",
    },
    {
        "slug": "student-workflow-all-languages",
        "title": "iPhone Apps for Students — All Languages",
        "desc": "iPhone app toolkit for students — scan, store and protect documents — 171 languages.",
        "subdir": "workflow",
        "page_slug": "iphone-workflow-student",
        "emoji": "🎓",
    },
    {
        "slug": "back-to-school-apps-all-languages",
        "title": "Back to School iPhone Apps — All Languages",
        "desc": "Best iPhone apps for back-to-school season — available in 171 languages.",
        "subdir": "seasonal",
        "page_slug": "iphone-apps-school",
        "emoji": "📚",
    },
    {
        "slug": "year-end-apps-all-languages",
        "title": "Year-End iPhone Apps — All Languages",
        "desc": "Best iPhone apps for year-end document and privacy reviews — 171 languages.",
        "subdir": "seasonal",
        "page_slug": "iphone-apps-year-end",
        "emoji": "🗓️",
    },
    {
        "slug": "summer-travel-apps-all-languages",
        "title": "Summer Travel iPhone Apps — All Languages",
        "desc": "Best iPhone apps for summer travel — passport photos, scanning, privacy — 171 languages.",
        "subdir": "seasonal",
        "page_slug": "iphone-apps-summer",
        "emoji": "✈️",
    },
    {
        "slug": "zafe-vs-hidden-album-all-languages",
        "title": "Zafe vs Hidden Album — All Languages",
        "desc": "Compare Zafe vs iPhone's built-in Hidden Album for photo security — 171 languages.",
        "subdir": "vs",
        "page_slug": "zafe-vs-hidden-album",
        "emoji": "⚔️",
    },
    {
        "slug": "scanto-vs-apple-notes-all-languages",
        "title": "ScanTo Pro vs Apple Notes Scanning — All Languages",
        "desc": "Compare ScanTo Pro vs Apple Notes for offline document scanning — 171 languages.",
        "subdir": "vs",
        "page_slug": "scanto-vs-apple-notes",
        "emoji": "⚖️",
    },
    {
        "slug": "snapport-vs-photographer-all-languages",
        "title": "Snapport vs Professional Photographer — All Languages",
        "desc": "Make passport photos at home vs hiring a photographer — 171 languages.",
        "subdir": "vs",
        "page_slug": "snapport-vs-photographer",
        "emoji": "🥊",
    },
    {
        "slug": "social-block-apps-all-languages",
        "title": "Best iPhone App to Block Social Media Distraction — All Languages",
        "desc": "Best iPhone apps to block social media and stay focused — 171 languages.",
        "subdir": "best-for",
        "page_slug": "iphone-best-app-social-block",
        "emoji": "🚫",
    },
    {
        "slug": "tax-season-iphone-apps-all-languages",
        "title": "Best iPhone Apps for Tax Season — All Languages",
        "desc": "Best iPhone apps for tax season — scan receipts, protect TFN/SIN/PAN, redact documents offline. Available in 150+ languages.",
        "subdir": "seasonal",
        "page_slug": "iphone-apps-year-end",
        "emoji": "🧾",
    },
    {
        "slug": "maskmyfile-review-all-languages",
        "title": "MaskMyFile App Review — All Languages",
        "desc": "Honest MaskMyFile review — permanently redact personal data from documents on iPhone. Available in 150+ languages.",
        "subdir": "reviews",
        "page_slug": "maskmyfile-review-2026",
        "emoji": "📋",
    },
    {
        "slug": "scanto-offline-scanner-review-all-languages",
        "title": "ScanTo Pro Offline Scanner Review — All Languages",
        "desc": "Honest ScanTo Pro review — offline PDF scanner for iPhone with no cloud upload. 150+ languages.",
        "subdir": "reviews",
        "page_slug": "scanto-review-2026",
        "emoji": "📄",
    },
]

# Language display names for major languages (others show the code)
LANG_NAMES = {
    "en": "English", "zh-Hant": "繁體中文", "zh-Hans": "简体中文", "ja": "日本語",
    "ko": "한국어", "es-ES": "Español (España)", "es-MX": "Español (México)",
    "fr-FR": "Français", "fr-CA": "Français (Canada)", "de-DE": "Deutsch",
    "it": "Italiano", "pt-BR": "Português (Brasil)", "pt-PT": "Português",
    "ru": "Русский", "ar-SA": "العربية", "hi": "हिन्दी", "th": "ภาษาไทย",
    "vi": "Tiếng Việt", "id": "Bahasa Indonesia", "ms": "Bahasa Melayu",
    "tr": "Türkçe", "nl-NL": "Nederlands", "pl": "Polski", "uk": "Українська",
    "cs": "Čeština", "sv": "Svenska", "no": "Norsk", "da": "Dansk",
    "fi": "Suomi", "hu": "Magyar", "ro": "Română", "sk": "Slovenčina",
    "hr": "Hrvatski", "bg": "Български", "el": "Ελληνικά", "he": "עברית",
    "fa": "فارسی", "ur": "اردو", "bn": "বাংলা", "ta": "தமிழ்",
    "te": "తెలుగు", "ml": "മലയാളം", "kn": "ಕನ್ನಡ", "mr": "मराठी",
    "gu": "ગુજરાતી", "pa": "ਪੰਜਾਬੀ", "sw": "Kiswahili", "am": "አማርኛ",
    "af": "Afrikaans", "ca": "Català", "eu": "Euskara", "gl": "Galego",
    "cy": "Cymraeg", "ga": "Gaeilge", "sq": "Shqip", "sr": "Српски",
    "mk": "Македонски", "sl": "Slovenščina", "lt": "Lietuvių", "lv": "Latviešu",
    "et": "Eesti", "is": "Íslenska", "mt": "Malti", "lb": "Lëtzebuergesch",
    "az": "Azərbaycan", "kk": "Қазақ", "ky": "Кыргыз", "uz": "O'zbek",
    "tg": "Тоҷикӣ", "mn": "Монгол", "ka": "ქართული", "hy": "Հայերեն",
    "my": "မြန်မာ", "km": "ខ្មែរ", "lo": "ລາວ", "si": "සිංහල",
    "ne": "नेपाली", "bo": "བོད་སྐད", "ug": "ئۇيغۇرچە", "ti": "ትግርኛ",
    "so": "Soomaali", "rw": "Kinyarwanda", "yo": "Yorùbá", "ig": "Igbo",
    "ha": "Hausa", "zu": "isiZulu", "xh": "isiXhosa", "st": "Sesotho",
    "tn": "Setswana", "sn": "ChiShona", "ny": "Chichewa", "mg": "Malagasy",
    "sa": "संस्कृत", "la": "Latina", "eo": "Esperanto", "ia": "Interlingua",
    "es-AR": "Español (Argentina)", "es-CO": "Español (Colombia)", "es-US": "Español (EE.UU.)",
    "es-CL": "Español (Chile)", "es-PE": "Español (Perú)",
    "fr-BE": "Français (Belgique)", "fr-CH": "Français (Suisse)", "fr-MA": "Français (Maroc)",
    "de-AT": "Deutsch (Österreich)", "de-CH": "Deutsch (Schweiz)",
    "ar-EG": "العربية (مصر)",
    "en-GB": "English (UK)", "en-AU": "English (Australia)", "en-CA": "English (Canada)", "en-IN": "English (India)",
    "nl-BE": "Nederlands (België)", "pt-AO": "Português (Angola)",
    "es-VE": "Español (Venezuela)",
    "en-NZ": "English (New Zealand)", "en-SG": "English (Singapore)",
    "en-PH": "English (Philippines)", "en-ZA": "English (South Africa)",
    "ar-DZ": "العربية (الجزائر)",
    "en-NG": "English (Nigeria)", "en-MY": "English (Malaysia)", "fr-DZ": "Français (Algérie)",
    "en-KE": "English (Kenya)", "en-PK": "English (Pakistan)", "pt-MZ": "Português (Moçambique)",
    "en-GH": "English (Ghana)", "en-TZ": "English (Tanzania)", "en-UG": "English (Uganda)",
    "es-GT": "Español (Guatemala)", "es-DO": "Español (Rep. Dominicana)", "ar-IQ": "العربية (العراق)",
    "es-BO": "Español (Bolivia)", "es-EC": "Español (Ecuador)", "fr-SN": "Français (Sénégal)", "fr-CI": "Français (Côte d'Ivoire)",
    "fr-CM": "Français (Cameroun)", "en-ZW": "English (Zimbabwe)",
    "es-PY": "Español (Paraguay)", "es-UY": "Español (Uruguay)", "fr-TN": "Français (Tunisie)", "ar-MA": "العربية (المغرب)",
    "ar-LY": "العربية (ليبيا)", "ar-SD": "العربية (السودان)", "en-ET": "English (Ethiopia)", "en-RW": "English (Rwanda)",
    "en-ZM": "English (Zambia)", "en-MW": "English (Malawi)", "fr-GN": "Français (Guinée)", "fr-ML": "Français (Mali)", "fr-BF": "Français (Burkina Faso)",
    "es-CR": "Español (Costa Rica)", "es-HN": "Español (Honduras)", "es-SV": "Español (El Salvador)", "ar-JO": "العربية (الأردن)",
    "ar-YE": "العربية (اليمن)", "fr-TD": "Français (Tchad)", "en-SL": "English (Sierra Leone)", "en-LR": "English (Liberia)",
    "fr-CD": "Français (RD Congo)", "fr-NE": "Français (Niger)", "fr-BJ": "Français (Bénin)", "fr-TG": "Français (Togo)", "es-NI": "Español (Nicaragua)",
    "ar-KW": "العربية (الكويت)", "ar-OM": "العربية (عُمان)", "ar-QA": "العربية (قطر)", "fr-CG": "Français (Congo)", "fr-MR": "Français (Mauritanie)", "es-PA": "Español (Panamá)",
    "ar-BH": "العربية (البحرين)", "fr-GA": "Français (Gabon)", "en-NA": "English (Namibia)", "en-BW": "English (Botswana)", "fr-RW": "Français (Rwanda)",
    "fr-HT": "Français (Haïti)", "fr-MG": "Français (Madagascar)", "en-LS": "English (Lesotho)", "en-SS": "English (South Sudan)",
    "sw-KE": "Kiswahili (Kenya/Tanzania)", "en-GM": "English (Gambia)", "fr-BI": "Français (Burundi)", "fr-CV": "Français (Cap-Vert)",
    "es-PR": "Español (Puerto Rico)", "fr-DJ": "Français (Djibouti)", "ar-PS": "العربية (فلسطين)", "pt-GW": "Português (Guiné-Bissau)", "en-ER": "English (Eritrea)",
    "pt-ST": "Português (São Tomé)", "en-SO": "English (Somalia)", "fr-KM": "Français (Comores)", "en-ZW2": "English (Zimbabwe II)", "fr-SN2": "Français (Sénégal II)",
    "am-ET": "አማርኛ (ኢትዮጵያ)", "ti-ER": "ትግርኛ (ኤርትራ)", "ha-NG": "Hausa (Najeriya)", "ig-NG": "Igbo (Naịjirịa)", "yo-NG": "Yorùbá (Nàìjíríà)",
    "ne-NP": "नेपाली (नेपाल)", "si-LK": "සිංහල (ශ්‍රී ලංකා)", "my-MM": "မြန်မာ", "km-KH": "ភាសាខ្មែរ (កម្ពុជា)", "lo-LA": "ລາວ (ລາວ)",
    "mn-MN": "Монгол", "ka-GE": "ქართული (საქართველო)", "az-AZ": "Azərbaycan dili", "hy-AM": "Հայերեն (Հայաստան)", "uz-UZ": "O'zbek tili",
    "kk-KZ": "Қазақ тілі (Қазақстан)", "tg-TJ": "Тоҷикӣ", "tk-TM": "Türkmen dili", "ky-KG": "Кыргыз тили", "sq-AL": "Shqip (Shqipëri)",
    "bs-BA": "Bosanski (Bosna)", "mk-MK": "Македонски", "sr-ME": "Srpski (Crna Gora)", "lv-LV": "Latviešu (Latvija)", "lt-LT": "Lietuvių (Lietuva)",
    "af-ZA": "Afrikaans (Suid-Afrika)", "zu-ZA": "IsiZulu (iNingizimu Afrika)", "sn-ZW": "ChiShona (Zimbabwe)", "rw-RW": "Kinyarwanda (Rwanda)", "om-ET": "Afaan Oromo (Oromiyaa)",
    "tl-PH": "Filipino (Pilipinas)", "xh-ZA": "IsiXhosa (Mzantsi Afrika)", "ny-MW": "Chichewa (Malawi)", "lg-UG": "Luganda (Uganda)", "so-SO": "Soomaali (Soomaaliya)",
    "gu-IN": "ગુજરાતી (ભારત)", "mr-IN": "मराठी (भारत)", "te-IN": "తెలుగు (భారత్)", "kn-IN": "ಕನ್ನಡ (ಭಾರತ)", "ml-IN": "മലയാളം (ഇന്ത്യ)",
    "et-EE": "Eesti (Eestis)", "sl-SI": "Slovenščina (Slovenija)", "is-IS": "Íslenska (Ísland)", "mt-MT": "Malti (Malta)", "cy-GB": "Cymraeg (Cymru)",
    "ga-IE": "Gaeilge (Éire)", "ca-ES": "Català (Catalunya)", "eu-ES": "Euskera (Euskal Herria)", "gl-ES": "Galego (Galicia)", "or-IN": "ଓଡ଼ିଆ (ଭାରତ)",
    "pa-IN": "ਪੰਜਾਬੀ (ਭਾਰਤ)", "as-IN": "অসমীয়া (ভাৰত)", "ps-AF": "پښتو (افغانستان)", "sd-PK": "سنڌي (پاڪستان)", "ceb-PH": "Cebuano (Pilipinas)",
    "wo-SN": "Wolof (Sénégal)", "ff-SN": "Fulfulde (Senegaal)", "tw-GH": "Twi (Ghana)", "st-ZA": "Sesotho (Afrika Borwa)", "lb-LU": "Lëtzebuergesch (Lëtzebuerg)",
    "qu-PE": "Runasimi (Perú)", "ht-HT": "Kreyòl Ayisyen (Ayiti)", "mg-MG": "Malagasy (Madagasikara)", "gn-PY": "Avañe'ẽ (Paraguay)", "tt-RU": "Татар теле (Татарстан)",
    "ay-BO": "Aymara (Bolivia)", "bo-CN": "བོད་སྐད། (Böd)", "dz-BT": "རྫོང་ཁ (འབྲུག)", "sm-WS": "Gagana Samoa (Samoa)", "to-TO": "Lea Fakatonga (Tonga)",
    "jv-ID": "Basa Jawa (Indonesia)", "su-ID": "Basa Sunda (Indonesia)", "mi-NZ": "Te Reo Māori (Aotearoa)", "fj-FJ": "Na Vosa Vakaviti (Viti)", "ba-RU": "Башҡорт теле (Башҡортостан)",
    "ug-CN": "ئۇيغۇرچە (شىنجاڭ)", "kab-DZ": "Taqbaylit (Ldzayer)", "sc-IT": "Sardu (Sardigna)", "br-FR": "Brezhoneg (Breizh)", "cv-RU": "Чăваш теле (Чăваш Республики)",
    "tn-ZA": "Setswana (Aforika Borwa)", "ve-ZA": "Tshivenda (Vhembe)", "ss-SZ": "SiSwati (eSwatini)", "mad-ID": "Madhurâ (Indonesia)", "min-ID": "Baso Minang (Indonesia)",
    "bho": "भोजपुरी (भारत)", "mai-IN": "मैथिली (भारत)", "sat-IN": "ᱥᱟᱱᱛᱟᱲᱤ (ᱥᱟᱱᱛᱟᱲ)", "gom-IN": "कोंकणी (भारत)", "ks-IN": "کٲشُر (جموں و کشمیر)",
    "nap": "Napoletano (Napule)", "vec-IT": "Vèneto (Italia)", "lmo": "Lombard (Lombardia)", "bug-ID": "Basa Ugi (Sulawesi)", "sah-RU": "Сахалыы (Саха Өрөспүүбүлүкэтэ)",
    "awa": "अवधी (भारत)", "bgc": "हरयाणवी (हरयाणा)", "dgo-IN": "डोगरी (जम्मू)", "os-RU": "Ирон æвзаг (Ирыстон)", "che-RU": "Нохчийн мотт (Нохчийчоь)",
    "ban-ID": "Basa Bali (Bali)", "ace-ID": "Basa Acèh (Nanggroe Aceh)", "hne": "छत्तीसगढ़ी (भारत)", "mag": "मगही (बिहार)", "new-NP": "नेवाः (नेपाल)",
    "mnw-MM": "မည်သည်မဆိုကျောင်း (မျန်မာ)", "shn-MM": "ၽႃႇသႃႇတႆး (မျန်မာ)", "zgh-MA": "ⵜⴰⵎⴰⵣⵉⵖⵜ (ⵍⵎⵖⵔⵉⴱ)", "fur-IT": "Furlan (Friûl)", "oc-FR": "Occitan (Occitania)",
    "lij": "Zenéize (Liguria)", "rm-CH": "Rumantsch (Svizra)", "co-FR": "Corsu (Corsica)", "scn-IT": "Sicilianu (Sicilia)", "wa-BE": "Walon (Walonreye)",
    "pam-PH": "Kapampangan (Pampanga)", "ilo-PH": "Ilokano (Ilocos)", "war-PH": "Winaray (Samar-Leyte)", "bcl-PH": "Bikol Sentral (Bikolnon)", "pag-PH": "Pangasinan (Pangasinan)",
    "lua-CD": "Tshiluba (Kasaï)", "mhr": "Олык Марий (Марий Эл)", "myv": "Эрзянь кель (Мордовия)", "udm": "Удмурт кыл (Удмуртия)", "koi": "Пермяцкöй кыв (Коми-Пермяция)",
    "bjn-ID": "Banjar (Kalimantan Selatan)", "mak-ID": "Makassarese (Sulawesi Selatan)", "brx-IN": "Bodo (Assam)", "mni-IN": "Meitei (Manipur)", "bm-ML": "Bambara (Mali)",
    "ewe-GH": "Eʋegbe (Ghana/Togo)", "twi-GH": "Twi (Ghana)", "dyu-CI": "Dioula (Côte d'Ivoire)", "tcy": "Tulu (Karnataka)", "gag-MD": "Gagauz (Moldova)",
    "nso-ZA": "Sesotho sa Leboa (South Africa)", "ts-ZA": "Xitsonga (South Africa)", "nr-ZA": "isiNdebele (South Africa)", "pap": "Papiamento (Aruba/Curaçao)", "krl": "Karjala (Karelia)",
    "srn": "Sranantongo (Suriname)", "gcr": "Antillean Creole (Guadeloupe)", "kea": "Kabuverdianu (Cabo Verde)", "mfe": "Morisyen (Mauritius)", "hat": "Kreyòl Ayisyen (Haiti)",
    "luo-KE": "Dholuo (Kenya)", "kam-KE": "Kikamba (Kenya)", "kln-KE": "Kalenjin (Kenya)", "nyn-UG": "Nyankole (Uganda)", "swc-CD": "Kiswahili cha Kongo (DRC)",
    "wuu": "吳語（上海/江浙）", "gan": "贛語（江西）", "hsn": "湘語（湖南）", "cdo": "閩東語（福建）", "tet": "Tetun (Timor-Leste)",
    "bci": "Baoulé (Côte d'Ivoire)", "dag": "Dagbani (Ghana)", "gor-ID": "Gorontalo (Sulawesi Utara)", "maz": "Mazahua (México)", "tzh": "Tzeltal (Chiapas)",
    "nym-TZ": "Kinyamwezi (Tanzania)", "suk": "Kisukuma (Tanzania)", "guz-KE": "Ekegusii (Kenya)", "mer-KE": "Kimeru (Kenya)", "cgg-UG": "Rukiga/Chiga (Uganda)",
    "xog-UG": "Lusoga (Uganda)", "ach-UG": "Acholi (Uganda)", "teo-UG": "Ateso (Uganda/Kenya)", "mas-KE": "Maa/Maasai (Kenya/Tanzania)", "nus-SS": "Thok Naath (South Sudan)",
    "bej": "Beja/Bedawi (Horn of Africa)", "din": "Thuɔŋjäŋ/Dinka (South Sudan)", "fij": "Fijian (Fiji)", "sah": "Саха тыла/Yakut (Russia)", "kaa": "Qaraqalpaq (Uzbekistan)",
    "sm": "Gagana Sāmoa (Samoa)", "to": "Lea Faka-Tonga (Tonga)", "ty": "Reo Tahiti (French Polynesia)", "yua": "Maya Yucateco (México)", "che": "Нохчийн мотт/Chechen (Russia)",
    "bua": "Буряад хэлэн/Buryat (Russia)", "tyv": "Тыва дыл/Tuvan (Russia)", "inh": "ГIалгIай мотт/Ingush (Russia)", "av": "Авар мацI/Avar (North Caucasus)", "nah": "Nāhuatl (México)",
    "mh": "Kajin M̧ajeļ/Marshallese", "pau": "A Tekoi er a Belau/Palauan", "chk": "Chuukese (Micronesia)", "pon": "Pohnpeian (Pohnpei)", "cos": "Corsu/Corsican (France)",
    "sc": "Sardu (Sardigna/Italy)", "vec": "Vèneto (Italy)", "scn": "Sicilianu (Sicily)", "fur": "Furlan/Friulian (Friûl)", "lij": "Ligure/Ligurian (Liguria)",
    "nap": "Napulitano/Neapolitan (Italy)", "pms": "Piemontèis/Piedmontese (Italy)", "rup": "Armãneashce/Aromanian (Balkans)", "nds": "Plattdüütsch/Low German", "zza": "Zazaca/Zaza (Turkey)",
    "gsw": "Alemannisch/Swiss German", "lb": "Lëtzebuergesch/Luxembourgish", "wln": "Wallon/Walloon (Belgium)", "rmy": "Romani/Romany (Europe)", "oc": "Occitan/Lenga d'òc",
    "cre": "Nēhiyawēwin/Cree (Canada)", "oji": "Anishinaabemowin/Ojibwe (Canada/US)", "iku": "ᐃᓄᒃᑎᑐᑦ/Inuktitut (Canada)", "ndc-ZW": "Chindau/Ndau (Zimbabwe)", "sus": "Sosoxui/Susu (Guinea)",
    "shn": "တႆး/Shan (Myanmar)", "kac": "Jinghpaw/Kachin (Myanmar)", "tem": "Kotokoli/Tem (Togo/Ghana/Benin)", "tum": "Chitumbuka/Tumbuka (Malawi/Zambia)", "seh": "Cisena/Sena (Mozambique)",
    "new": "नेपाल भाषा/Newari (Nepal)", "lez": "Лезги чIал/Lezgin (Russia/Azerbaijan)", "dar": "Дарган мез/Dargwa (Russia)", "kpe": "Kpɛlɛwoo/Kpelle (Liberia/Guinea)", "tiv": "Tiv (Nigeria)",
    "edo": "Ẹdo (Nigeria)", "fon": "Fɔngbe/Fon (Benin)", "luy": "Luluyia/Luhya (Kenya)", "sat": "ᱥᱟᱱᱛᱟᱲᱤ/Santali (India)", "kok": "कोंकणी/Konkani (India)",
    "wol": "Wolof (Senegaal/Gambia)", "ace": "Acèh (Indonesia)", "bug": "Ugi'/Buginese (Sulawesi)", "quz": "Qhichwa/Quechua (Peru/Bolivia)", "grn": "Avañe'ẽ/Guaraní (Paraguay)",
    "ibb": "Ibibio (Nigeria)", "tvl": "Te Ggana Tuvalu (Tuvalu)", "chr": "ᏣᎳᎩ/Cherokee (USA)", "qom": "Qom/Toba (Argentina)", "mak": "Makassar/Makasar (Sulawesi)",
    "ewe": "Eʋegbe/Ewe (Ghana/Togo)", "mos": "Mooré/Mossi (Burkina Faso)", "dyu": "Julakan/Dyula (West Africa)", "aym": "Aymar aru/Aymara (Bolivia/Peru)", "tzm": "ⵜⴰⵎⴰⵣⵉⵖⵜ/Tamazight (Morocco)",
    "nso": "Sesotho sa Leboa/Northern Sotho (South Africa)", "pcm": "Naijíriá Pijin/Nigerian Pidgin", "hil": "Ilonggo/Hiligaynon (Pilipinas)", "war": "Winaray/Waray (Pilipinas)", "ilo": "Ilokano/Ilocano (Pilipinas)",
    "pag": "Pangasinan (Pilipinas)", "bcl": "Bikol/Bicolano (Pilipinas)", "krj": "Kinaray-a (Pilipinas)", "tsg": "Bahasa Sug/Tausug (Philippines/Malaysia)", "mdh": "Maguindanao/Maguindanaon (Pilipinas)",
    "kri": "Krio (Salone/Sierra Leone)", "ven": "Tshivenḓa/Venda (South Africa)", "tso": "Xitsonga/Tsonga (South Africa/Mozambique)", "jam": "Jamaican Patwa (Jamaica)", "mwr": "मारवाड़ी/Marwari (India/Pakistan)",
    "crs": "Kreol Seselwa (Seychelles)", "pis": "Pijin (Solomon Islands)", "bis": "Bislama (Vanuatu)", "gcf": "Gwadloupéyen/Créole guadeloupéen", "swb": "Shimaore/Comorian (Mayotte/Comoros)",
    "rap": "Rapa Nui (Easter Island)", "niu": "Niue (Niue Island)", "raj": "राजस्थानी/Rajasthani (India)", "gil": "Taetae ni Kiribati/Gilbertese", "nhx": "Nāhuatl Xochimilco (México)",
    "nan": "Bân-lâm-gú/Hokkien (Taiwan/SE Asia)", "yue": "粵語/Cantonese (Hong Kong/Guangdong)", "hak": "客家話/Hakka (Taiwan/Diaspora)", "min": "閩東語/Min Dong (Fujian)", "akl": "Aklan/Aklanon (Pilipinas)",
    "szl": "Ślůnsko godka/Silesian (Polska)", "kab": "Taqbaylit/Kabyle (Algérie)", "mfe": "Kreol Morisyen/Mauritian Creole (Moris)", "pap": "Papiamentu (Kòrsou/Aruba)", "shi": "Tachelhit/Shilha (Maroc)",
    "csb": "Kaszëbsczi/Kashubian (Pòlskô)", "rue": "Русиньскый/Rusyn (Карпати)", "dsb": "Dolnoserbšćina/Lower Sorbian (Germany)", "hsb": "Hornjoserbšćina/Upper Sorbian (Germany)", "pcd": "Picard/Chti (Belgique/France)",
    "ext": "Estremeñu/Extremaduran (Extremadura)", "mwl": "Mirandés (Portugal)", "lld": "Ladin (Südtirol/Trentin)", "frp": "Arpitan/Franco-Provençal (Savoie/Aoste)", "sco": "Scots (Scotland/Ulster)",
    "gag": "Gagavuz/Gagauz (Moldava/Ukraina)", "xal": "Хальмг/Kalmyk (Россия)", "krc": "Таулу тил/Karachay-Balkar (Россия)", "ady": "Адыгабзэ/Adyghe (Адыгея)", "kbd": "Адыгэбзэ/Kabardian (Кабарда)",
    "mdf": "Мокшень кяль/Moksha (Россия)", "kpv": "Коми кыв/Komi-Zyrian (Россия)", "liv": "Līvõ kēļ/Livonian (Latvia)", "sma": "Åarjelsaemien/Southern Sami (Sweden)", "smj": "Julevsámegiella/Lule Sami (Norway/Sweden)",
    "sms": "Nuõrttsäʹmm/Skolt Sami (Finland)", "smn": "Anarâšgiella/Inari Sami (Finland)", "olo": "Livvi-karjala/Livvi-Karelian (Russia/Finland)", "mer": "Kimĩrũ/Meru (Kenya)", "guz": "Ekegusii/Gusii (Kenya)",
    "kam": "Kikamba/Kamba (Kenya)", "luo": "Dholuo/Luo (Kenya/Tanzania)", "saq": "Samburu/Kisamburu (Kenya)", "mas": "Maa/Maasai (Kenya/Tanzania)", "dav": "Kitaita/Dawida (Kenya)",
    "teo": "Ateso/Teso (Uganda/Kenya)", "cgg": "Rukiga/Chiga (Uganda)", "nyn": "Runyankore/Ankole (Uganda)", "xog": "Lusoga/Soga (Uganda)", "ach": "Acholi/Luo Acholi (Uganda)",
    "laj": "Leblango/Lango (Uganda)", "niq": "Nandi/Kalenjin (Kenya)", "bas": "Ɓàsàa/Bassa (Cameroun)", "bum": "Bulu (Cameroun)", "mgo": "Metaʼ/Meta (Cameroun)",
    "aeb": "Tūnsi/Tunisian Arabic (تونس)", "zgh": "ⵜⴰⵎⴰⵣⵉⵖⵜ/Standard Moroccan Tamazight (Maroc)", "sid": "Sidaamu Afoo/Sidama (Ethiopia)", "wal": "Wolaitta Doone/Wolaitta (Ethiopia)", "amo": "Amo (Plateau State, Nigeria)",
    "rif": "Tarifit/Riffian Berber (Maroc)", "gez": "ግዕዝ/Ge'ez Classical Ethiopic", "snn": "ChiSena/Sena (Mozambique)", "tig": "ትግረ/Tigre (Eritrea)", "fub": "Fulfude/Fula Adamawa (Nigeria/Cameroon)",
    "twi": "Twi/Akan (Ghana)", "fat": "Fante/Mfantse (Ghana)", "gaa": "Gã/Ga (Ghana)", "ada": "Dangme/Ada (Ghana)", "nmg": "Kwasio/Ngumba (Cameroun)",
    "nnh": "Shüpamem/Ngiemboon (Cameroun)", "agq": "Aghem (Cameroun)", "jgo": "Ngomba (Cameroun)", "ksf": "Bafia (Cameroun)", "mua": "Mundang (Cameroun/Tchad)",
    "dua": "Duala (Cameroun)", "kkj": "Kako (Cameroun)", "yav": "Yangben (Cameroun)", "byv": "Medumba (Cameroun)", "bkm": "Kom (Cameroun)",
    "ebu": "Kĩembu/Embu (Kenya)", "vun": "Kivunjo/Vunjo-Chaga (Tanzania)", "asa": "Kipare/Asu (Tanzania)", "bez": "Kibena/Bena (Tanzania)", "kde": "Chimakonde/Makonde (Tanzania)",
    "lag": "Kilangi/Langi (Tanzania)", "rwk": "Kiarumeru/Rwo (Tanzania)", "sbp": "Kisangu/Sangu (Tanzania)", "jmc": "Kimachame/Machame (Tanzania)", "rof": "Kirombo/Rombo (Tanzania)",
    "kln": "Kalenjin/Nandi (Kenya)", "dga": "Dagaare (Ghana)", "mgh": "Makhuwa-Meetto (Mozambique)", "brx": "बड़ो/Bodo (Northeast India)", "mzn": "مازرونی/Mazanderani (Iran)",
    "glk": "گیلکی/Gilaki (Iran)", "lrc": "لۊری شومالی/Northern Luri (Iran)", "haz": "هزارگی/Hazaragi (Afghanistan)", "dcc": "دکنی/Deccani (India)", "wtm": "मेवाती/Mewati (India)",
    "skr": "سرائیکی/Saraiki (Pakistan)", "bgn": "بلوچی مکرانی/Western Balochi (Pakistan)", "xmf": "მარგალური/Mingrelian (Georgia)", "kum": "Къумукъ/Kumyk (Russia)", "kpy": "Kpelle (Liberia/Guinea)",
    "tab": "Табасаран/Tabasaran (Russia)", "nog": "Ногай/Nogai (Russia)", "lbe": "Лакку/Lak (Russia)", "tay": "泰雅語/Atayal (Taiwan)", "ami": "阿美語/Amis (Taiwan)",
    "dtp": "Dusun/Central Dusun (Malaysia)", "hnj": "Hmoob Ntsuab/Hmong Njua (SE Asia)", "blt": "ภาษาไทดำ/Tai Dam (SE Asia)", "mfa": "Pattani Malay (Thailand)", "cjy": "晉語/Jinyu Chinese (China)",
    "kek": "Q'eqchi' (Guatemala/Belize)", "quc": "K'iche' (Guatemala)", "cak": "Kaqchikel (Guatemala)", "tzo": "Tzotzil (Mexico)", "mam": "Mam (Guatemala/Mexico)",
    "nav": "Diné Bizaad/Navajo (USA)", "arn": "Mapudungun (Chile/Argentina)", "toj": "Tojolabal (Mexico)", "ikt": "ᐃᓄᒃᑎᑐᑦ/Inuktitut (Canada)", "tzj": "Tz'utujil (Guatemala)",
    "guc": "Wayuunaiki/Wayuu (Colombia/Venezuela)", "urh": "Urhobo (Nigeria)", "idu": "Idoma (Nigeria)", "ixl": "Ixil (Guatemala)", "cni": "Asháninka (Peru)",
    "pwo": "ပဝိုၤကရေဝ်/Pwo Karen (Myanmar/Thailand)", "mnw": "မောန်/Mon (Myanmar/Thailand)", "blk": "ပအိုဝ်/Pa'O (Myanmar)", "igl": "Igala (Nigeria)", "bin": "Ẹ̀dó/Bini (Nigeria)",
    "tpi": "Tok Pisin (Papua New Guinea)", "pam": "Kapampangan (Pilipinas)", "dzo": "རྫོང་ཁ (Bhutan)", "kha": "Khasi (Meghalaya, India)", "nia": "Li Niha / Nias (Indonesia)",
    "ndc": "Ndau (Zimbabwe/Mozambique)", "mni": "মৈতৈলোন্ (Manipur, India)", "doi": "डोगरी (Jammu & Kashmir, India)", "lug": "Luganda (Uganda)", "kin": "Kinyarwanda (Rwanda)",
    "run": "Kirundi (Burundi)", "lmn": "Lambadi / Banjara (India)", "gon": "Gondi / Koitur (India)", "crh": "Qırımtatarca / Crimean Tatar", "ton": "Lea fakatonga / Tongan (Tonga)",
    "lad": "Ladino / Judeo-Español", "bhi": "Bhilali / Bhili (India)", "tly": "Tolışi / Talysh (Iran/Azerbaijan)", "bew": "Betawi (Jakarta, Indonesia)", "bgp": "Balochi Sharqi / Eastern Balochi (Pakistan/Iran)",
    "sot": "Sesotho (South Africa/Lesotho)", "ssw": "SiSwati / Swati (Eswatini/South Africa)", "loz": "Silozi / Lozi (Zambia)", "mah": "Kajin M̧ajeļ / Marshallese (Marshall Islands)", "que": "Quechua (Peru/Bolivia)",
    "ckb": "Soranî Kurdish / Central Kurdish",
    "ksb": "Kishambaa / Shambala (Tanzania)", "nus": "Thok Nath / Nuer (South Sudan/Ethiopia)",
    "bsq": "Bassa (Liberia/Cameroon)", "men": "Mende (Sierra Leone/Guinea)",
    "naq": "Khoekhoegowab / Nama (Namibia)",
    "fuv": "Fulfulde (Nigeria/Cameroon)", "kmb": "Kimbundu (Angola)",
    "lua": "Tshiluba / Luba-Kasai (DR Congo)", "mnk": "Mandinka (Gambia/Senegal)",
    "lus": "Mizo / Lushai (Mizoram, India)",
    "kby": "Kabiyé (Togo)", "ybb": "Yemba / Nda'nda' (Cameroon)",
    "dan": "Dangme / Adangme (Ghana)", "bsc": "Oniyan / Bassari (Senegal/Guinea-Bissau)",
    "hif": "Fiji Hindi / Hindustani Fiji (Fiji)",
    "meu": "Motu (Papua New Guinea)", "lkt": "Lakota (USA/Canada)", "moh": "Mohawk (Canada/USA)", "cho": "Choctaw (USA)", "rop": "Kriol (Australia Aboriginal)",
    "ktu": "Kituba / Munukutuba (Congo/DRC)", "guw": "Gun-Gbe / Gungbe (Benin)", "nde": "isiNdebele North (Zimbabwe)",
    "bem": "Ichibemba / Bemba (Zambia)", "efi": "Efịk (Nigeria)", "vai": "ꕙꔤ / Vai (Liberia)",
    "lun": "Chilunda / Lunda (Zambia)", "kqn": "Kikaonde / Kaonde (Zambia)",
    "kck": "Kalanga (Zimbabwe/Botswana)", "toi": "Chitonga / Tonga (Zambia/Zimbabwe)", "lue": "Luvale (Zambia/Angola)", "nya": "Chinyanja / Nyanja (Zambia/Malawi)", "bax": "Shüpamem / Bamun (Cameroon)",
    "dyo": "Jóola-Fóoñi / Jola (Senegal)", "dip": "Thuɔŋjäŋ / Dinka (South Sudan)", "cce": "Cicopi / Chopi (Mozambique)", "ndh": "Chindali / Ndali (Tanzania/Malawi)", "knf": "Mankanya (Senegal/Guinea-Bissau)",
    "lgg": "Lugbara (Uganda/DR Congo)", "alz": "Alur (Uganda/DR Congo)", "myx": "Lumasaaba / Masaaba (Uganda)", "nyo": "Runyoro / Nyoro (Uganda)", "bfa": "Bari (South Sudan)",
    "kdj": "Ŋakarimojoŋ / Karamojong (Uganda)", "lot": "Otuho / Lotuko (South Sudan)", "keo": "Kakwa (Uganda/South Sudan)", "kcg": "Tyap / Kataf (Nigeria)", "avn": "Sìyà / Avatime (Ghana)",
    "gog": "Cigogo / Gogo (Tanzania)", "hay": "Oluhaya / Haya (Tanzania)", "heh": "Kihehe / Hehe (Tanzania)", "rim": "Kinyaturu / Nyaturu (Tanzania)", "nyf": "Kigiryama / Giryama (Kenya)",
    "rag": "Lulogooli / Logooli (Kenya)", "thk": "Kĩtharaka / Tharaka (Kenya)", "frr": "Frasch / North Frisian (Germany)", "vro": "Võro kiil / Võro (Estonia)", "rmc": "Romani (Carpathian, Central Europe)",
    "sas": "Base Sasak / Sasak (Indonesia)", "bbc": "Batak Toba (Indonesia)", "nij": "Bahasa Ngaju / Ngaju (Indonesia)", "rej": "Baso Jang / Rejang (Indonesia)", "abs": "Melayu Ambon / Ambonese Malay (Indonesia)",
    "bbj": "Ghomálá' (Cameroon)", "bfd": "Bafut (Cameroon)", "sef": "Cebaara Senoufo (Côte d'Ivoire)", "gej": "Gen / Mina (Togo/Benin)", "bqi": "Bakhtiari (Iran)",
    "cjk": "Chokwe (Angola/DR Congo)", "anu": "Anuak (South Sudan/Ethiopia)", "shk": "Shilluk / Dhøg Cøllø (South Sudan)", "kdh": "Tem / Kotokoli (Togo)", "kus": "Kusaal (Ghana)",
    "ewo": "Kolo Ewondo / Ewondo (Cameroon)", "rmn": "Romani (Balkan, SE Europe)", "ket": "Ket (Siberia, Russia)", "evn": "Evenki / Эвэдыл (Siberia/China)", "niv": "Nivkh / Нивхгу (Sakhalin, Russia)",
    "hmo": "Hiri Motu (Papua New Guinea)", "cnh": "Laiholh / Hakha Chin (Myanmar)", "agr": "Awajún / Aguaruna (Peru)", "shp": "Shipibo-Konibo (Peru)", "poh": "Poqomchi' (Guatemala)",
    "kru": "कुड़ुख़ / Kurukh (India)", "hoc": "𑢹𑣉𑣉 / Ho (India)", "kfy": "कुमाऊँनी / Kumaoni (India)", "gbm": "गढ़वळि / Garhwali (India)", "xnr": "कांगड़ी / Kangri (India)",
    "mrw": "Mëranaw / Maranao (Philippines)", "cbk": "Chavacano / Zamboangueño (Philippines)", "msb": "Minasbate / Masbatenyo (Philippines)", "tbw": "Aborlan Tagbanwa (Philippines)", "hnn": "Hanunuo Mangyan (Philippines)",
    "any": "Anyin / Agni (Côte d'Ivoire)", "abr": "Bono / Abron-Brong (Ghana)", "nzi": "Nzema (Ghana)", "gjn": "Ngbanyito / Gonja (Ghana)", "yom": "Kiyombe / Yombe (DR Congo/Angola)",
    "mfq": "Moba (Togo/Ghana)", "luc": "Aringa / Low Lugbara (Uganda)", "bud": "Ntcham / Bassari (Togo/Ghana)", "yre": "Yaouré (Côte d'Ivoire)", "bss": "Akoose / Bakossi (Cameroon)",
    "bfo": "Birifor (Burkina Faso/Ghana)", "dop": "Lukpa / Dompago (Togo/Benin)", "xon": "Konkomba (Ghana/Togo)", "ncu": "Chumburung (Ghana)", "gng": "Ngangam (Togo/Benin)",
    "bqc": "Boko (Benin/Nigeria)", "mcp": "Maka / Makaa (Cameroon)", "tik": "Tikar (Cameroon)", "koq": "Kota (Gabon)", "bex": "Jur Modo (South Sudan)",
    "avu": "Avokaya (South Sudan/DR Congo)", "las": "Lama (Togo)", "ntr": "Delo / Ntrubo (Ghana/Togo)", "gud": "Yocoboué Dida (Côte d'Ivoire)", "bwu": "Buli (Ghana)",
    "nmz": "Nawdm (Togo/Ghana)", "dgo": "Dogon / Toro So (Mali)", "kao": "Xaasongaxango / Khassonke (Mali)", "myk": "Sénoufo Mamara (Mali)", "bze": "Jenaama Bozo (Mali)",
    "snk": "Soninké (Mali/Senegal)", "kbn": "Kare (Central African Rep.)", "sg2": "Gbanu (Central African Rep.)", "nup": "Nupe (Nigeria)", "gbr": "Gbagyi (Nigeria)",
    "bqv": "Koro Wachi (Nigeria)", "etu": "Ejagham (Nigeria/Cameroon)", "mfi": "Wandala / Mandara (Cameroon/Nigeria)", "mcn": "Masana / Massa (Chad/Cameroon)", "gid": "Gidar (Chad/Cameroon)",
    "kbp2": "Bwamu (Burkina Faso)", "bwq": "Southern Bobo (Burkina Faso)", "dga2": "Dagaare (Ghana/Burkina Faso)",
    "mfz": "Mari (South Sudan)", "bfa2": "Bari-Kuku (South Sudan)", "bjt": "Balanta-Ganja (Senegal/Guinea-Bissau)", "bsc2": "Bassari (Senegal/Guinea)", "csk": "Jola-Kasa (Senegal)",
    "kdc2": "Kutu (Tanzania)", "vid": "Vidunda (Tanzania)", "zga": "Kinga (Tanzania)", "nim": "Nilamba (Tanzania)", "rag2": "Logoli-Idakho (Kenya)",
    "sba": "Ngambay (Chad)", "tui": "Tupuri (Chad/Cameroon)", "daa": "Dangaléat (Chad)", "ngb": "Northern Ngbandi (Central African Rep./DRC)", "ttj": "Rutooro / Tooro (Uganda)",
    "gwr": "Lugwere / Gwere (Uganda)", "pko": "Pökoot (Kenya/Uganda)", "saf": "Safaliba (Ghana)", "mzw": "Deg / Mo (Ghana/Côte d'Ivoire)", "hag": "Hanga (Ghana)",
    "fuf": "Pular / Fula (Guinea)", "xpe": "Kpɛlɛ / Kpelle (Liberia)", "gkp": "Kpɛlɛwoo / Guinea Kpelle (Guinea)", "kqs": "Kisiei / Northern Kissi (Guinea/Sierra Leone)", "bza": "Bandi (Liberia)",
    "snf": "Noon (Senegal)", "mcu": "Mambila (Cameroon/Nigeria)", "nnq": "Ngindo (Tanzania)", "tnr": "Ménik / Bedik (Senegal)", "mfk": "North Mofu (Cameroon)",
    "knc": "Kanuri (Nigeria/Niger/Chad)", "dnj": "Dan / Yacouba (Côte d'Ivoire)", "lom": "Löömà / Loma (Liberia/Guinea)", "gbo": "Grebo (Liberia)", "grj": "Southern Grebo (Liberia)",
    "dee": "Dewoin (Liberia)", "wob": "Wè Northern (Côte d'Ivoire)", "bmq": "Bomu (Mali/Burkina Faso)", "box": "Buamu (Burkina Faso)", "kel": "Kela (DR Congo)",
    "grt": "A·chik / Garo (India/Bangladesh)", "nag": "Nagamese (Nagaland, India)", "njo": "Ao / Ao Naga (Nagaland, India)", "wbm": "Vo / Wa (Myanmar)", "tdg": "Tamang (Nepal)",
    "tsj": "Tshangla / Sharchop (Bhutan)", "lep": "Lepcha (Sikkim, India)", "sip": "Sikkimese / Bhutia (Sikkim, India)", "jya": "rGyalrong / Jarong (Sichuan, China)", "mtr": "Mewari (Rajasthan, India)",
    "wbr": "वागड़ी / Wagdi (Rajasthan, India)", "hoj": "हाड़ौती / Hadothi (Rajasthan, India)", "noe": "निमाड़ी / Nimadi (Madhya Pradesh, India)", "dhd": "ढूंढाड़ी / Dhundari (Rajasthan, India)", "bra": "ब्रज भाषा / Braj (Uttar Pradesh, India)",
    "gju": "गुज्जरी / Gujari (India/Pakistan)", "anp": "अंगिका / Angika (Bihar, India)", "kjo": "कच्छी कोली / Kachi Koli (India)", "gdx": "गोडवाड़ी / Godwari (Rajasthan, India)", "kvx": "पारकरी कोली / Parkari Koli (Pakistan)",
    "vah": "वऱ्हाडी / Varhadi (Maharashtra, India)", "bfy": "बघेली / Bagheli (Madhya Pradesh, India)", "unr": "मुंडारी / Mundari (Jharkhand, India)", "sgj": "सरगुजिया / Surgujia (Chhattisgarh, India)", "dhn": "डूंगरा भील / Dungra Bhil (India)",
    "kfx": "कोया / Koya (Telangana, India)", "gwc": "کالامي / Kalami (Pakistan)", "bsh": "کتی / Kati (Afghanistan/Pakistan)", "kfe": "कोटा / Kota (Tamil Nadu, India)", "emx": "Erromintra (India)",
    "aec": "اللهجة الصعيدية / Saidi Arabic (Egypt)", "acm": "اللهجة العراقية / Mesopotamian Arabic (Iraq)", "afb": "اللهجة الخليجية / Gulf Arabic", "acw": "اللهجة الحجازية / Hijazi Arabic", "acq": "اللهجة التعزية / Ta'izzi-Adeni Arabic (Yemen)",
    "arz": "اللهجة المصرية / Egyptian Arabic", "ary": "الدارجة المغربية / Moroccan Darija", "apd": "اللهجة السودانية / Sudanese Arabic", "apc": "اللهجة الشامية / Levantine Arabic",
    "hno": "Northern Hindko (Pakistan)", "hnd": "Southern Hindko (Pakistan)", "pmu": "Mirpur Panjabi / Pahari-Pothwari (Pakistan)", "bgq": "Bagri (India/Pakistan)", "ymm": "Maay (Somalia)",
    "gbk": "Gaddi (Himachal Pradesh, India)", "xnj": "Kingoni / Ngoni (Tanzania)", "odk": "Od (Pakistan/India)", "kxp": "Wadiyara Koli (Pakistan/India)", "pce": "Ruching Palaung (Myanmar)",
    "rkt": "রংপুরী / Rangpuri-Kamta (Bangladesh/India)", "ctg": "চাটগাঁইয়া / Chittagonian (Bangladesh)", "syl": "ছিলটী / Sylheti (Bangladesh/India)", "swv": "शेखावाटी / Shekhawati (Rajasthan, India)", "kfq": "कोरकू / Korku (Maharashtra/MP, India)",
    "bpy": "বিষ্ণুপ্রিয়া মণিপুরী / Bishnupriya (India)", "tdb": "पंचपरगनिया / Panchpargania (Jharkhand, India)", "xsr": "ཤར་པ / Sherpa (Nepal)", "kxv": "କୁୱି / Kuvi (Odisha, India)", "gbj": "गुटोब / Bodo Gadaba (Odisha, India)",
    "sdr": "सादरी / Sadri-Oraon (Jharkhand, India)", "mjl": "मंडियाली / Mandeali (Himachal, India)", "kex": "कुकणा / Kukna (Gujarat/Maharashtra, India)", "mjz": "माझी / Majhi (Nepal)", "srx": "सिरमौरी / Sirmauri (Himachal, India)",
    "mjt": "माल्तो / Sauria Paharia (Jharkhand, India)", "xka": "کلکوٹی / Kalkoti (Pakistan)", "agi": "अगरिया / Agariya (Madhya Pradesh, India)",
    "cps": "Capiznon (Philippines)", "tbl": "Tboli (Philippines)", "agn": "Agutaynen (Palawan, Philippines)", "mta": "Cotabato Manobo (Philippines)", "obo": "Obo Manobo (Mindanao, Philippines)",
    "msm": "Agusan Manobo (Mindanao, Philippines)", "bnj": "Eastern Tawbuid (Mindoro, Philippines)", "bkn": "Bukid / Binukid (Bukidnon, Philippines)",
    "bar": "Boarisch / Bavarian (Germany/Austria)", "vmf": "Fränkisch / Main-Franconian (Germany)", "swg": "Schwäbisch / Swabian (Germany)", "ksh": "Kölsch (Germany)", "pfl": "Pälzisch / Palatine German (Germany)",
    "rgn": "Rumagnôl / Romagnol (Italy)", "egl": "Emiliàn / Emilian (Italy)", "nrf": "Jèrriais / Guernésiais (Channel Islands)",
    "sxu": "Sächsisch / Upper Saxon (Germany)", "vls": "West-Vlams / West Flemish (Belgium)", "wae": "Walserdütsch / Walser (Switzerland/Italy)", "zea": "Zeêuws / Zeelandic (Netherlands)", "wep": "Westfäölsk / Westphalian (Germany)",
    "prv": "Provençau / Provençal (France)", "oci": "Lengadocian / Occitan (France)", "srd": "Sardu / Sardinian (Italy)",
    "fit": "Meänkieli (Sweden)", "fkv": "Kvääni / Kven (Norway)", "twd": "Twents (Netherlands)", "jut": "Jysk / Jutlandic (Denmark)", "ovd": "Övdalska / Elfdalian (Sweden)",
    "sju": "Ubmejensámien / Ume Sami (Sweden)", "sje": "Bidumsámegiella / Pite Sami (Sweden)", "gutn": "Gutamål / Gutnish (Gotland, Sweden)",
    "kjh": "Хакас / Khakas (Russia)", "alt": "Алтай / Southern Altai (Russia)", "cjs": "Шор / Shor (Russia)", "dlg": "Дулҕан / Dolgan (Russia)", "kim": "Тофа / Tofa (Russia)",
    "kdr": "Karaim (Lithuania/Ukraine)", "mrj": "Мары / Hill Mari (Russia)",
    "gas": "आदिवासी गरासिया / Adiwasi Garasia (Rajasthan, India)", "kdq": "कोच / Koch (Assam, India)", "anr": "आंध / Andh (Maharashtra, India)", "dry": "दरै / Darai (Nepal)", "unx": "मुंडा / Munda-Nihali (India)",
    "bfw": "बोंडो / Bondo (Odisha, India)",
    "bjj": "कन्नौजी / Kanauji (Uttar Pradesh, India)", "bns": "बुन्देली / Bundeli (Madhya Pradesh, India)", "mup": "मालवी / Malvi (Madhya Pradesh, India)", "bhb": "भीली / Bhili (Rajasthan/Gujarat, India)", "gom": "कोंकणी / Goan Konkani (Goa, India)",
    "ahr": "अहिराणी / Ahirani (Maharashtra, India)", "dty": "डोटेली / Doteli (Nepal)", "thl": "डँगौरा थारू / Dangaura Tharu (Nepal)",
    "pnb": "پنجابی شاہ مکھی / Western Punjabi (Pakistan)", "prs": "دری / Dari (Afghanistan)", "bal": "بلوچی / Balochi (Pakistan/Iran)", "kas": "کٲشُر / Kashmiri (India, Perso-Arabic)", "sdh": "کوردی خوارگ / Southern Kurdish (Iran/Iraq)",
    "khw": "کھوار / Khowar (Chitral, Pakistan)", "bcc": "جنوبی بلوچی / Southern Balochi (Makran)", "bft": "بلتی / Balti (Pakistan)",
    "thq": "कठरिया थारू / Kathoriya Tharu (Nepal)", "the": "चितवनिया थारू / Chitwania Tharu (Nepal)", "kfr": "कच्छी / Kachhi (Gujarat, India)", "gvr": "गुरुङ / Gurung (Nepal)", "lif": "लिम्बू / Limbu (Nepal/India)",
    "sck": "सादरी / Sadri-Oraon (Jharkhand, India)",
    "tts": "ภาษาอีสาน / Isan (NE Thailand)", "nod": "คำเมือง / Northern Thai · Lanna (Chiang Mai)", "sou": "ภาษาใต้ / Southern Thai (Nakhon Si Thammarat)", "khb": "ᦅᦴᧉᦑᦺ / Tai Lü (Xishuangbanna/Laos)", "ksw": "စှီၤကညီကျိာ် / S'gaw Karen (Myanmar/Thailand)",
    "rki": "ရခိုင်ဘာသာ / Rakhine (Myanmar)", "luz": "لری جنوبی / Southern Luri (Iran)",
    "mad": "Basa Madhura / Madurese (Madura, Indonesia)", "ban": "Basa Bali / Balinese (Bali, Indonesia)", "bjn": "Bahasa Banjar / Banjarese (Kalimantan, Indonesia)",
}

def get_lang_dirs():
    """Return all language directories that exist."""
    dirs = []
    for d in sorted(PAGES.iterdir()):
        if d.is_dir() and d.name not in ("_engine", "hubs", "topic-hubs", "stories", "answers", "tools", "seasonal", "data", "resourcesync"):
            dirs.append(d.name)
    return dirs

def lang_display(code):
    return LANG_NAMES.get(code, code)

def build_hub(topic, lang_dirs):
    links = []
    for lang in lang_dirs:
        page_path = PAGES / lang / topic["subdir"] / f"{topic['page_slug']}-{lang}.html"
        if not page_path.exists():
            page_path = PAGES / lang / topic["subdir"] / f"{topic['page_slug']}-{lang.lower()}.html"
        if page_path.exists():
            url = f"{GEO_SITE}/{lang}/{topic['subdir']}/{topic['page_slug']}-{lang}.html"
            name = lang_display(lang)
            links.append((lang, name, url))

    if not links:
        return None, 0

    link_items = "\n".join(
        f'<a class="lang-link" href="{url}" hreflang="{lang}">{name}</a>'
        for lang, name, url in links
    )
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": topic["title"],
        "description": topic["desc"],
        "numberOfItems": len(links),
        "itemListElement": [
            {"@type": "ListItem", "position": i+1, "url": url, "name": name}
            for i, (lang, name, url) in enumerate(links)
        ]
    }, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{topic["title"]}</title>
<meta name="description" content="{topic["desc"]}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{GEO_SITE}/topic-hubs/{topic['slug']}.html">
<style>{CSS}</style>
<script type="application/ld+json">{ld}</script>
</head>
<body>
<p><a class="back" href="{GEO_SITE}/">← iOS App Guide</a></p>
<h1>{topic["emoji"]} {topic["title"]}</h1>
<p>{topic["desc"]}</p>
<p class="count">Available in {len(links)} languages:</p>
<div class="grid">
{link_items}
</div>
<p style="margin-top:2rem;font-size:.85rem;color:#888">
  Part of the <a href="{GEO_SITE}/">iOS App Guide</a> multilingual resource.
  Available in {len(links)} languages and growing.
</p>
</body>
</html>"""
    return html, len(links)

def build_index(topics_built):
    items = "\n".join(
        f'<a class="lang-link" style="font-size:.95rem" href="{GEO_SITE}/topic-hubs/{slug}.html">{emoji} {title} ({count} languages)</a>'
        for slug, title, emoji, count in topics_built
    )
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "iOS App Topic Hubs — All Languages",
        "description": "Cross-language topic hubs for iOS privacy, productivity and photo apps.",
        "url": f"{GEO_SITE}/topic-hubs/"
    }, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>iOS App Topic Hubs — All Languages</title>
<meta name="description" content="Find iOS app guides in your language. Privacy, scanning, passport photos, and more.">
<link rel="canonical" href="{GEO_SITE}/topic-hubs/">
<style>{CSS}</style>
<script type="application/ld+json">{ld}</script>
</head>
<body>
<p><a class="back" href="{GEO_SITE}/">← iOS App Guide</a></p>
<h1>📍 iOS App Topic Hubs — All Languages</h1>
<p>Find iOS app guides in your language. Each topic is available in 170+ languages.</p>
<div class="grid">
{items}
</div>
</body>
</html>"""

def main():
    lang_dirs = get_lang_dirs()
    topics_built = []
    sm_urls = []

    for topic in TOPICS:
        html, count = build_hub(topic, lang_dirs)
        if html:
            out = HUBS / f"{topic['slug']}.html"
            out.write_text(html, encoding="utf-8")
            topics_built.append((topic["slug"], topic["title"], topic["emoji"], count))
            sm_urls.append(f"{GEO_SITE}/topic-hubs/{topic['slug']}.html")

    # Index page
    if topics_built:
        (HUBS / "index.html").write_text(build_index(topics_built), encoding="utf-8")
        sm_urls.insert(0, f"{GEO_SITE}/topic-hubs/")

    # Sitemap
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "\n".join(f"<url><loc>{u}</loc></url>" for u in sm_urls) + "\n</urlset>\n"
    (PAGES / "sitemap_topic_hubs.xml").write_text(sm, encoding="utf-8")

    print(json.dumps({"hubs": len(topics_built), "langs_covered": topics_built}))

if __name__ == "__main__":
    main()
