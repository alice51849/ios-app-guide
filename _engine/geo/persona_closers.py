#!/usr/bin/env python3
"""Native closing sentences for publisher persona leads.

Why this module exists
----------------------
Every persona lead used to end with one hard-coded clause::

    <first sentence> — <AppName> is built for this.

That single shape was translated once per locale and then reused for every
app, so 1,200+ rows of ``lumi-studio-publisher-search-intent-catalog.json``
(and every social post built from them) closed on the same em-dash formula:
``… — PhotoCream 就是為此設計``, ``… — PhotoCream はそのために作られています``.
Readers recognise that rhythm as machine output, and it is the single largest
source of AI tone in the cloud social copy.

What replaces it
----------------
Five structurally different closing sentences per locale, written natively --
not translated from one English source -- plus a sixth "no closer" shape that
simply lets the lead end on the reader's problem.  The shapes differ in
sentence-initial element, length and register, so no two neighbouring rows
share a cadence:

``gap``    the missing piece, app named last
``cond``   conditional, addressed to the reader
``scope``  app named first, deliberately limiting
``start``  app named first, origin of the product
``why``    short rhetorical close
``none``   no closing sentence at all

Which shape an app gets is decided by the app's real situation (kids app,
privacy tool, travel companion, focus tool …) plus a stable hash of its key,
so the assignment is deterministic, reproducible, and spreads shapes across
apps that sit next to each other in the catalog.

Honesty rules (00_Standards/AGENTS.md): no superlatives, no guarantees, and
none of the banned product claims about permanent purchases, hand illustration
or recorded human speech.  Every shape here is a plain statement of intent or
an invitation to look.
"""

from __future__ import annotations

import hashlib


SHAPES: tuple[str, ...] = ("gap", "cond", "scope", "start", "why", "none")

# Sentence terminator to restore when the legacy tail is cut off a lead.
TERMINATORS: dict[str, str] = {
    "ja": "。",
    "zh-Hans": "。",
    "zh-Hant": "。",
    "hi": "।",
    "mr-IN": "।",
    "bn-BD": "।",
    "pa-IN": "।",
    "or-IN": "।",
    "ur-PK": "۔",
    "th": "",
}
DEFAULT_TERMINATOR = "."

# Locales that do not put a space between sentences.
NO_SPACE_LOCALES = frozenset({"ja", "zh-Hans", "zh-Hant"})


def terminator(locale: str) -> str:
    return TERMINATORS.get(locale, DEFAULT_TERMINATOR)


def join(locale: str, head: str, closer: str) -> str:
    """Attach `closer` to `head` using the locale's own sentence spacing."""
    head = " ".join(head.split()).rstrip()
    closer = " ".join(closer.split()).strip()
    if not closer:
        return head
    end = terminator(locale)
    if end and not head.endswith(tuple(".!?。！？।۔؟")):
        head = head + end
    glue = "" if locale in NO_SPACE_LOCALES else " "
    return f"{head}{glue}{closer}"


# --------------------------------------------------------------------------
# Situations.  These describe what the reader is actually trying to do, which
# is what decides the register of the closing sentence.
# --------------------------------------------------------------------------
SITUATIONS: dict[str, str] = {
    # children / family learning
    "lumibopomofo": "kids",
    "lumibopomofopro": "kids",
    "lumiletters": "kids",
    "lumiletterspro": "kids",
    "lumimath": "kids",
    "lumimathpro": "kids",
    "lumimission": "kids",
    "lumimissionpro": "kids",
    "lumiweather": "kids",
    "tripplanet": "kids",
    # adult learning / exams
    "aim990": "learning",
    "aim990plus": "learning",
    "dailymate": "learning",
    "dailymatelite": "learning",
    "wordmate": "learning",
    "wordmatelite": "learning",
    # privacy-critical
    "cyca": "privacy",
    "maskmyfile": "privacy",
    "scanto": "privacy",
    # travel
    "gmoney": "travel",
    "gmoneylite": "travel",
    "tripbee": "travel",
    "tripbeelite": "travel",
    # money
    "hourstag": "money",
    "hourstaglite": "money",
    "moneytag": "money",
    # focus / routine
    "lockhour": "focus",
    "mochi": "focus",
    "mochidonestamp": "focus",
    # creative
    "photocream": "creative",
    "unblurry": "creative",
    # work
    "aibriefpack": "work",
    "cvdesk": "work",
    "notesstudio100": "work",
    "onepageppt": "work",
    "sononote": "work",
    # rest / wellbeing
    "sereno": "wellbeing",
    # everyday utilities
    "battai": "utility",
    "caldaily": "utility",
    "picclear": "utility",
    "savetag": "utility",
    "shotinbox": "utility",
    "snapport": "utility",
    "snapportlite": "utility",
    "wifiaid": "utility",
    "wifiaidlite": "utility",
}
DEFAULT_SITUATION = "utility"

# Which shapes suit which situation.  A parent skimming a kids-app page wants
# an invitation, not a product-origin story; a privacy tool reads better when
# the sentence limits the claim or says nothing extra at all.
SITUATION_SHAPES: dict[str, tuple[str, ...]] = {
    "kids": ("cond", "why", "gap"),
    "learning": ("gap", "start", "cond"),
    "privacy": ("scope", "none", "start"),
    "travel": ("cond", "gap", "why"),
    "creative": ("scope", "gap", "none"),
    "money": ("start", "scope", "cond"),
    "focus": ("why", "none", "scope"),
    "work": ("start", "gap", "scope"),
    "wellbeing": ("why", "cond", "none"),
    "utility": ("scope", "start", "none"),
}


def situation(app_key: str) -> str:
    return SITUATIONS.get(app_key, DEFAULT_SITUATION)


def shape_for(app_key: str) -> str:
    """Deterministic, situation-driven shape choice for one app."""
    shapes = SITUATION_SHAPES[situation(app_key)]
    digest = hashlib.sha256(app_key.encode("utf-8")).hexdigest()
    return shapes[int(digest, 16) % len(shapes)]


# --------------------------------------------------------------------------
# The phrasebook.  Written per locale, not translated from one English line.
# `{name}` is the app's localized display name.
# --------------------------------------------------------------------------
CLOSERS: dict[str, dict[str, str]] = {
    "en-US": {
        "gap": "That is the gap {name} was built to close.",
        "cond": "If that is your situation, {name} is worth a look.",
        "scope": "{name} sticks to that one job and leaves the rest out.",
        "start": "{name} started from exactly that problem.",
        "why": "That is why {name} exists.",
    },
    "en-GB": {
        "gap": "That's the gap {name} was built to close.",
        "cond": "If that sounds like your situation, {name} is worth a look.",
        "scope": "{name} sticks to that one job and leaves the rest out.",
        "start": "{name} began with exactly that problem.",
        "why": "That's why {name} exists.",
    },
    "en-AU": {
        "gap": "That's the gap {name} was built to close.",
        "cond": "If that sounds familiar, {name} is worth a look.",
        "scope": "{name} does that one job and leaves the rest alone.",
        "start": "{name} started from exactly that problem.",
        "why": "That's why {name} exists.",
    },
    "en-CA": {
        "gap": "That's the gap {name} was built to close.",
        "cond": "If that's your situation, {name} is worth a look.",
        "scope": "{name} keeps to that one job and leaves the rest out.",
        "start": "{name} started from exactly that problem.",
        "why": "That's why {name} exists.",
    },
    "es-ES": {
        "gap": "Ese es justo el hueco que {name} intenta cubrir.",
        "cond": "Si te ves reflejado, échale un vistazo a {name}.",
        "scope": "{name} hace solo eso y deja fuera lo demás.",
        "start": "{name} nació precisamente de ese problema.",
        "why": "Por eso existe {name}.",
    },
    "es-MX": {
        "gap": "Ese es justo el hueco que {name} busca cubrir.",
        "cond": "Si te suena conocido, échale un ojo a {name}.",
        "scope": "{name} hace solo eso y deja fuera lo demás.",
        "start": "{name} nació justo de ese problema.",
        "why": "Por eso existe {name}.",
    },
    "ca": {
        "gap": "Aquest és el buit que {name} vol cobrir.",
        "cond": "Si t'hi veus reflectit, dona-li un cop d'ull a {name}.",
        "scope": "{name} fa només això i deixa la resta fora.",
        "start": "{name} va néixer precisament d'aquest problema.",
        "why": "Per això existeix {name}.",
    },
    "fr-FR": {
        "gap": "C'est précisément ce manque que {name} cherche à combler.",
        "cond": "Si ça vous parle, jetez un œil à {name}.",
        "scope": "{name} fait uniquement cela et laisse le reste de côté.",
        "start": "{name} est parti exactement de ce problème.",
        "why": "C'est pour ça que {name} existe.",
    },
    "fr-CA": {
        "gap": "C'est exactement ce manque que {name} cherche à combler.",
        "cond": "Si ça vous ressemble, jetez un coup d'œil à {name}.",
        "scope": "{name} fait seulement ça et laisse le reste de côté.",
        "start": "{name} est né précisément de ce problème.",
        "why": "C'est pour ça que {name} existe.",
    },
    "de-DE": {
        "gap": "Genau diese Lücke soll {name} schließen.",
        "cond": "Wenn dir das bekannt vorkommt, schau dir {name} an.",
        "scope": "{name} macht genau das eine und lässt den Rest weg.",
        "start": "{name} ist genau aus diesem Problem entstanden.",
        "why": "Dafür gibt es {name}.",
    },
    "it": {
        "gap": "È proprio questo il vuoto che {name} cerca di colmare.",
        "cond": "Se ti ci ritrovi, dai un'occhiata a {name}.",
        "scope": "{name} fa solo questo e lascia fuori il resto.",
        "start": "{name} nasce esattamente da questo problema.",
        "why": "È per questo che esiste {name}.",
    },
    "pt-PT": {
        "gap": "É essa a lacuna que {name} procura preencher.",
        "cond": "Se lhe soa familiar, dê uma vista de olhos a {name}.",
        "scope": "{name} faz só isso e deixa o resto de fora.",
        "start": "{name} nasceu precisamente desse problema.",
        "why": "É por isso que existe {name}.",
    },
    "pt-BR": {
        "gap": "É justamente essa lacuna que o {name} quer preencher.",
        "cond": "Se você se identificou, dá uma olhada no {name}.",
        "scope": "{name} faz só isso e deixa o resto de fora.",
        "start": "{name} nasceu exatamente desse problema.",
        "why": "É por isso que o {name} existe.",
    },
    "nl-NL": {
        "gap": "Precies dat gat wil {name} dichten.",
        "cond": "Herken je dat, kijk dan eens naar {name}.",
        "scope": "{name} doet alleen dat en laat de rest weg.",
        "start": "{name} is precies uit dat probleem ontstaan.",
        "why": "Daarvoor is {name} gemaakt.",
    },
    "da": {
        "gap": "Det er præcis det hul, {name} skal lukke.",
        "cond": "Lyder det bekendt, så kig på {name}.",
        "scope": "{name} gør kun det ene og lader resten være.",
        "start": "{name} er opstået præcis af det problem.",
        "why": "Det er derfor {name} findes.",
    },
    "no": {
        "gap": "Det er nettopp det hullet {name} skal tette.",
        "cond": "Kjenner du deg igjen, ta en titt på {name}.",
        "scope": "{name} gjør bare det ene og lar resten være.",
        "start": "{name} kom nettopp ut av det problemet.",
        "why": "Det er derfor {name} finnes.",
    },
    "sv": {
        "gap": "Det är precis den luckan {name} ska fylla.",
        "cond": "Känner du igen dig, ta en titt på {name}.",
        "scope": "{name} gör bara det ena och lämnar resten.",
        "start": "{name} växte fram just ur det problemet.",
        "why": "Det är därför {name} finns.",
    },
    "fi": {
        "gap": "Juuri tuon aukon {name} on tarkoitus täyttää.",
        "cond": "Jos tunnistat tilanteen, katso {name}.",
        "scope": "{name} tekee vain sen yhden asian ja jättää muun pois.",
        "start": "{name} lähti liikkeelle juuri tuosta ongelmasta.",
        "why": "Siksi {name} on olemassa.",
    },
    "pl": {
        "gap": "To właśnie tę lukę ma wypełnić {name}.",
        "cond": "Jeśli to brzmi znajomo, zajrzyj do {name}.",
        "scope": "{name} robi tylko to jedno i pomija resztę.",
        "start": "{name} wziął się dokładnie z tego problemu.",
        "why": "Po to właśnie powstał {name}.",
    },
    "cs": {
        "gap": "Přesně tuhle mezeru má {name} zaplnit.",
        "cond": "Jestli to znáte, mrkněte na {name}.",
        "scope": "{name} dělá jen tohle jedno a zbytek vynechává.",
        "start": "{name} vznikl přesně z tohohle problému.",
        "why": "Právě proto {name} vznikl.",
    },
    "sk": {
        "gap": "Presne túto medzeru má {name} zaplniť.",
        "cond": "Ak to poznáte, pozrite sa na {name}.",
        "scope": "{name} robí len toto jedno a zvyšok vynecháva.",
        "start": "{name} vznikol presne z tohto problému.",
        "why": "Práve preto {name} vznikol.",
    },
    "hr": {
        "gap": "Upravo tu prazninu {name} želi popuniti.",
        "cond": "Ako vam to zvuči poznato, pogledajte {name}.",
        "scope": "{name} radi samo to jedno i ostalo izostavlja.",
        "start": "{name} je nastao točno iz tog problema.",
        "why": "Upravo zato {name} postoji.",
    },
    "sl-SI": {
        "gap": "Prav to vrzel želi {name} zapolniti.",
        "cond": "Če vam je to znano, si oglejte {name}.",
        "scope": "{name} dela samo to eno in ostalo izpusti.",
        "start": "{name} je nastal prav iz te težave.",
        "why": "Prav zato {name} obstaja.",
    },
    "hu": {
        "gap": "Pontosan ezt a hiányt szeretné betölteni a {name}.",
        "cond": "Ha ismerős a helyzet, nézd meg a {name} appot.",
        "scope": "A {name} csak ezt az egyet csinálja, a többit kihagyja.",
        "start": "A {name} pontosan ebből a problémából indult.",
        "why": "Ezért készült a {name}.",
    },
    "ro": {
        "gap": "Exact acest gol vrea să îl acopere {name}.",
        "cond": "Dacă te regăsești, aruncă o privire la {name}.",
        "scope": "{name} face doar atât și lasă restul deoparte.",
        "start": "{name} a pornit exact de la această problemă.",
        "why": "De aceea există {name}.",
    },
    "el": {
        "gap": "Αυτό ακριβώς το κενό θέλει να καλύψει το {name}.",
        "cond": "Αν σου θυμίζει κάτι, ρίξε μια ματιά στο {name}.",
        "scope": "Το {name} κάνει μόνο αυτό και αφήνει τα υπόλοιπα έξω.",
        "start": "Το {name} ξεκίνησε ακριβώς από αυτό το πρόβλημα.",
        "why": "Γι' αυτό υπάρχει το {name}.",
    },
    "ru": {
        "gap": "Именно этот пробел и закрывает {name}.",
        "cond": "Если это про вас, посмотрите {name}.",
        "scope": "{name} делает только это и не берётся за остальное.",
        "start": "{name} вырос как раз из этой проблемы.",
        "why": "Ради этого {name} и сделан.",
    },
    "uk": {
        "gap": "Саме цю прогалину й закриває {name}.",
        "cond": "Якщо це про вас, погляньте на {name}.",
        "scope": "{name} робить лише це й не береться за решту.",
        "start": "{name} виріс саме з цієї проблеми.",
        "why": "Заради цього {name} і зроблено.",
    },
    "tr": {
        "gap": "{name} tam da bu boşluğu kapatmak için var.",
        "cond": "Tanıdık geldiyse {name} uygulamasına bir göz atın.",
        "scope": "{name} sadece bunu yapar, gerisini bırakır.",
        "start": "{name} tam olarak bu sorundan doğdu.",
        "why": "İşte {name} bu yüzden ortaya çıktı.",
    },
    "he": {
        "gap": "בדיוק את הפער הזה {name} מנסה לסגור.",
        "cond": "אם זה נשמע לכם מוכר, שווה להציץ ב-{name}.",
        "scope": "{name} עושה רק את זה ומשאיר את השאר בחוץ.",
        "start": "{name} התחיל בדיוק מהבעיה הזאת.",
        "why": "בשביל זה {name} נבנה.",
    },
    "ar-SA": {
        "gap": "هذه الفجوة بالذات هي ما يسعى {name} لسدّها.",
        "cond": "إن كان هذا حالك، فألقِ نظرة على {name}.",
        "scope": "{name} يفعل هذا الأمر وحده ويترك ما عداه.",
        "start": "{name} انطلق من هذه المشكلة بالذات.",
        "why": "لهذا وُجد {name}.",
    },
    "ur-PK": {
        "gap": "یہی خلا {name} پُر کرنا چاہتا ہے۔",
        "cond": "اگر بات جانی پہچانی لگے تو {name} پر ایک نظر ڈالیں۔",
        "scope": "{name} صرف یہی ایک کام کرتا ہے، باقی چھوڑ دیتا ہے۔",
        "start": "{name} کی شروعات بالکل اسی مسئلے سے ہوئی۔",
        "why": "اسی لیے {name} بنایا گیا۔",
    },
    "hi": {
        "gap": "यही कमी {name} पूरी करना चाहता है।",
        "cond": "अगर बात जानी-पहचानी लगे तो {name} देख लीजिए।",
        "scope": "{name} बस यही एक काम करता है, बाकी छोड़ देता है।",
        "start": "{name} की शुरुआत ठीक इसी दिक्कत से हुई।",
        "why": "इसीलिए {name} बना।",
    },
    "mr-IN": {
        "gap": "हीच उणीव {name} भरून काढू पाहतो.",
        "cond": "ओळखीचं वाटत असेल तर {name} एकदा पाहा.",
        "scope": "{name} फक्त हेच एक काम करतो, बाकीचं टाळतो.",
        "start": "{name} ची सुरुवात नेमकी याच अडचणीतून झाली.",
        "why": "म्हणूनच {name} तयार झाला.",
    },
    "bn-BD": {
        "gap": "ঠিক এই ফাঁকটাই {name} পূরণ করতে চায়।",
        "cond": "চেনা মনে হলে {name} একবার দেখে নিন।",
        "scope": "{name} শুধু এই কাজটাই করে, বাকিটা বাদ রাখে।",
        "start": "{name}-এর শুরুটা ঠিক এই সমস্যা থেকেই।",
        "why": "এ জন্যই {name} তৈরি হয়েছে।",
    },
    "gu-IN": {
        "gap": "આ જ ખાલીપો {name} ભરવા માગે છે.",
        "cond": "જાણીતું લાગે તો {name} એક વાર જોઈ લો.",
        "scope": "{name} ફક્ત આ એક જ કામ કરે છે, બાકીનું છોડી દે છે.",
        "start": "{name} ની શરૂઆત બરાબર આ જ મુશ્કેલીથી થઈ.",
        "why": "એટલા માટે જ {name} બન્યું.",
    },
    "pa-IN": {
        "gap": "ਇਹੀ ਘਾਟ {name} ਪੂਰੀ ਕਰਨਾ ਚਾਹੁੰਦਾ ਹੈ।",
        "cond": "ਜਾਣੀ-ਪਛਾਣੀ ਗੱਲ ਲੱਗੇ ਤਾਂ {name} ਇੱਕ ਵਾਰ ਵੇਖੋ।",
        "scope": "{name} ਸਿਰਫ਼ ਇਹੀ ਇੱਕ ਕੰਮ ਕਰਦਾ ਹੈ, ਬਾਕੀ ਛੱਡ ਦਿੰਦਾ ਹੈ।",
        "start": "{name} ਦੀ ਸ਼ੁਰੂਆਤ ਠੀਕ ਇਸੇ ਦਿੱਕਤ ਤੋਂ ਹੋਈ।",
        "why": "ਇਸੇ ਲਈ {name} ਬਣਿਆ।",
    },
    "or-IN": {
        "gap": "ଏହି ଅଭାବକୁ ହିଁ {name} ପୂରଣ କରିବାକୁ ଚାହେଁ।",
        "cond": "ପରିଚିତ ଲାଗିଲେ {name} ଥରେ ଦେଖନ୍ତୁ।",
        "scope": "{name} କେବଳ ଏହି ଗୋଟିଏ କାମ କରେ, ବାକି ଛାଡ଼ିଦିଏ।",
        "start": "{name}ର ଆରମ୍ଭ ଠିକ୍ ଏହି ସମସ୍ୟାରୁ ହିଁ।",
        "why": "ସେଥିପାଇଁ ହିଁ {name} ତିଆରି ହେଲା।",
    },
    "ta-IN": {
        "gap": "இந்த இடைவெளியைத்தான் {name} நிரப்ப முயல்கிறது.",
        "cond": "பரிச்சயமாகத் தோன்றினால் {name} ஒரு முறை பாருங்கள்.",
        "scope": "{name} இந்த ஒரு வேலையை மட்டும் செய்கிறது, மற்றதை விட்டுவிடுகிறது.",
        "start": "{name} தொடங்கியதே இந்தச் சிக்கலில் இருந்துதான்.",
        "why": "அதற்காகவே {name} உருவானது.",
    },
    "te-IN": {
        "gap": "ఈ ఖాళీనే {name} పూరించాలనుకుంటుంది.",
        "cond": "పరిచయమైన సమస్యే అనిపిస్తే {name} ఒకసారి చూడండి.",
        "scope": "{name} ఈ ఒక్క పనే చేస్తుంది, మిగతావి వదిలేస్తుంది.",
        "start": "{name} మొదలైంది సరిగ్గా ఈ ఇబ్బంది నుంచే.",
        "why": "అందుకే {name} తయారైంది.",
    },
    "kn-IN": {
        "gap": "ಈ ಕೊರತೆಯನ್ನೇ {name} ತುಂಬಲು ಬಯಸುತ್ತದೆ.",
        "cond": "ಪರಿಚಿತ ಎನಿಸಿದರೆ {name} ಒಮ್ಮೆ ನೋಡಿ.",
        "scope": "{name} ಈ ಒಂದೇ ಕೆಲಸ ಮಾಡುತ್ತದೆ, ಉಳಿದದ್ದನ್ನು ಬಿಟ್ಟುಬಿಡುತ್ತದೆ.",
        "start": "{name} ಶುರುವಾಗಿದ್ದೇ ಈ ಸಮಸ್ಯೆಯಿಂದ.",
        "why": "ಅದಕ್ಕಾಗಿಯೇ {name} ರೂಪುಗೊಂಡಿತು.",
    },
    "ml-IN": {
        "gap": "ഈ വിടവാണ് {name} നികത്താൻ ശ്രമിക്കുന്നത്.",
        "cond": "പരിചിതമായി തോന്നുന്നെങ്കിൽ {name} ഒന്നു നോക്കൂ.",
        "scope": "{name} ഈ ഒരു കാര്യം മാത്രം ചെയ്യുന്നു, ബാക്കി വിട്ടുകളയുന്നു.",
        "start": "{name} തുടങ്ങിയത് ഈ പ്രശ്നത്തിൽ നിന്നു തന്നെയാണ്.",
        "why": "അതിനുവേണ്ടിയാണ് {name} ഉണ്ടാക്കിയത്.",
    },
    "th": {
        "gap": "ช่องว่างตรงนี้แหละที่ {name} อยากอุด",
        "cond": "ถ้าฟังดูคุ้น ๆ ลองดู {name}",
        "scope": "{name} ทำแค่เรื่องนี้เรื่องเดียว ที่เหลือไม่ยุ่ง",
        "start": "{name} เริ่มต้นจากปัญหานี้พอดี",
        "why": "{name} ถึงเกิดขึ้นมาด้วยเหตุนี้",
    },
    "vi": {
        "gap": "Đúng khoảng trống đó là thứ {name} muốn lấp.",
        "cond": "Nếu thấy quen, bạn thử xem {name}.",
        "scope": "{name} chỉ làm đúng việc đó và bỏ qua phần còn lại.",
        "start": "{name} khởi đi đúng từ vấn đề này.",
        "why": "{name} ra đời chính vì thế.",
    },
    "id": {
        "gap": "Celah itulah yang ingin ditutup {name}.",
        "cond": "Kalau terasa familier, coba lihat {name}.",
        "scope": "{name} mengerjakan satu hal itu saja dan meninggalkan sisanya.",
        "start": "{name} berangkat persis dari masalah ini.",
        "why": "Untuk itulah {name} dibuat.",
    },
    "ms": {
        "gap": "Itulah jurang yang cuba ditutup oleh {name}.",
        "cond": "Kalau bunyinya biasa, cuba lihat {name}.",
        "scope": "{name} buat satu perkara itu sahaja dan tinggalkan yang lain.",
        "start": "{name} bermula tepat daripada masalah ini.",
        "why": "Sebab itulah {name} dibina.",
    },
    "ja": {
        "gap": "その隙間を埋めるために{name}を作りました。",
        "cond": "心当たりがあるなら、{name}を試してみてください。",
        "scope": "{name}はその一点だけに絞って、あとは削ぎ落としています。",
        "start": "{name}はまさにその困りごとから始まりました。",
        "why": "だから{name}を作りました。",
    },
    "ko": {
        "gap": "그 간극을 메우려고 만든 앱이 {name}입니다.",
        "cond": "이런 상황이라면 {name} 한번 살펴보세요.",
        "scope": "{name}, 딱 그 한 가지에만 집중합니다.",
        "start": "{name}, 바로 그 문제에서 출발했습니다.",
        "why": "그래서 만든 것이 {name}입니다.",
    },
    "zh-Hant": {
        "gap": "這個缺口，就是 {name} 想補上的。",
        "cond": "如果你也是這種狀況，可以看看 {name}。",
        "scope": "{name} 只做這一件事，其他一律不加。",
        "start": "{name} 就是從這個問題開始做的。",
        "why": "所以才有了 {name}。",
    },
    "zh-Hans": {
        "gap": "这个缺口，正是 {name} 想补上的。",
        "cond": "如果你也是这种情况，可以看看 {name}。",
        "scope": "{name} 只做这一件事，其余一概不加。",
        "start": "{name} 就是从这个问题开始做的。",
        "why": "所以才有了 {name}。",
    },
}


LEGACY_EN_SUFFIX = " — {name} is built for this."


# `decision_context` in the publisher intent catalog is schema-bound to at
# least this many characters.  A short CJK lead plus the `none` shape can fall
# under it, so the floor decides when a closing sentence is not optional.
MIN_DECISION_CONTEXT_CHARS = 20


def _written_shape(app_key: str) -> str:
    """A non-empty shape, for leads too short to stand on their own."""
    written = tuple(s for s in SHAPES if s != "none")
    digest = hashlib.sha256(f"written:{app_key}".encode("utf-8")).hexdigest()
    return written[int(digest, 16) % len(written)]


def closer(
    locale: str,
    app_key: str,
    name: str,
    *,
    require_sentence: bool = False,
) -> str:
    """The closing sentence for one app in one locale ('' for the `none` shape)."""
    shape = shape_for(app_key)
    if shape == "none":
        if not require_sentence:
            return ""
        shape = _written_shape(app_key)
    try:
        phrases = CLOSERS[locale]
    except KeyError as error:
        raise KeyError(f"No persona closers for locale {locale!r}") from error
    return phrases[shape].replace("{name}", name)


def close_lead(locale: str, head: str, app_key: str, name: str) -> str:
    """Join a lead head to its closer, never dropping under the schema floor."""
    text = join(locale, head, closer(locale, app_key, name))
    if len(text) >= MIN_DECISION_CONTEXT_CHARS:
        return text
    return join(
        locale, head, closer(locale, app_key, name, require_sentence=True)
    )


def persona_lead(lead: str, app_key: str, name: str, locale: str = "en-US") -> str:
    """Full localized lead: the reader's problem, then a closing sentence."""
    head = lead.split(". ")[0].rstrip(".")
    return close_lead(locale, head, app_key, name)


def self_check() -> None:
    """Fail loudly if the phrasebook drifts out of shape."""
    from official_locales import OFFICIAL_LOCALES

    missing = sorted(set(OFFICIAL_LOCALES) - set(CLOSERS))
    if missing:
        raise ValueError(f"persona closers missing locales: {missing}")
    extra = sorted(set(CLOSERS) - set(OFFICIAL_LOCALES))
    if extra:
        raise ValueError(f"persona closers has unknown locales: {extra}")
    written = tuple(s for s in SHAPES if s != "none")
    for locale, phrases in CLOSERS.items():
        if set(phrases) != set(written):
            raise ValueError(f"{locale}: expected shapes {written}, got {sorted(phrases)}")
        for shape, text in phrases.items():
            if "{name}" not in text:
                raise ValueError(f"{locale}/{shape}: missing {{name}} placeholder")
            if "—" in text or "–" in text:
                raise ValueError(f"{locale}/{shape}: reintroduces the em-dash tic")
        if len({t for t in phrases.values()}) != len(written):
            raise ValueError(f"{locale}: duplicate closer text")
    for shapes in SITUATION_SHAPES.values():
        for shape in shapes:
            if shape not in SHAPES:
                raise ValueError(f"unknown shape {shape!r}")


if __name__ == "__main__":
    self_check()
    used: dict[str, int] = {}
    for key in sorted(SITUATIONS):
        used[shape_for(key)] = used.get(shape_for(key), 0) + 1
    print(f"{len(CLOSERS)} locales x {len(SHAPES) - 1} written shapes + 'none'")
    print("shape distribution across apps:", dict(sorted(used.items())))
