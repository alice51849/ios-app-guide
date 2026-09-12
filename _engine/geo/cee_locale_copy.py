"""Reviewed CEE outreach copy; never a source for ASC or historical posts.

Only the ten audited locales are overridden. Store prices remain the concern
of verified storefront facts, not these editorial strings.
"""

from __future__ import annotations

import re

CEE_LOCALES = ("cs", "hu", "pl", "ro", "ru", "sk", "sl-SI", "tr", "uk", "he")

PURCHASE_NOTES = {
    "cs": (
        "Placené stažení: za kompletní aplikaci zaplatíte jednou, bez dalších nákupů v aplikaci a bez předplatného.",
        "Základní funkce můžete používat zdarma. Plnou verzi odemknete volitelným jednorázovým nákupem v aplikaci, bez předplatného.",
    ),
    "hu": (
        "A teljes alkalmazásért a letöltéskor egyszer kell fizetni. Nincs további alkalmazáson belüli vásárlás vagy előfizetés.",
        "Az alapfunkciók ingyen használhatók. A teljes verzió egy választható, egyszeri alkalmazáson belüli vásárlással oldható fel, előfizetés nélkül.",
    ),
    "pl": (
        "Za pełną aplikację płacisz raz, przy pobieraniu. Bez dodatkowych zakupów w aplikacji i bez subskrypcji.",
        "Podstawowe funkcje są bezpłatne. Pełną wersję możesz odblokować jednorazowym zakupem w aplikacji, bez subskrypcji.",
    ),
    "ro": (
        "Plătești o singură dată la descărcare și primești aplicația completă, fără alte achiziții în aplicație sau abonament.",
        "Funcțiile de bază sunt gratuite. Poți debloca versiunea completă printr-o achiziție unică în aplicație, fără abonament.",
    ),
    "ru": (
        "Полная версия оплачивается один раз при скачивании. Дополнительных покупок внутри приложения и подписки нет.",
        "Основные функции доступны бесплатно. Полную версию можно открыть разовой покупкой внутри приложения, без подписки.",
    ),
    "sk": (
        "Za úplnú aplikáciu zaplatíte raz pri stiahnutí. Bez ďalších nákupov v aplikácii a bez predplatného.",
        "Základné funkcie sú bezplatné. Úplnú verziu môžete odomknúť jednorazovým nákupom v aplikácii, bez predplatného.",
    ),
    "sl-SI": (
        "Celotno aplikacijo plačaš enkrat ob prenosu. Brez dodatnih nakupov v aplikaciji in brez naročnine.",
        "Osnovne funkcije so brezplačne. Celotno različico lahko odkleneš z enkratnim nakupom v aplikaciji, brez naročnine.",
    ),
    "tr": (
        "Tam sürüm için indirirken bir kez ödeme yaparsınız. Ek uygulama içi satın alma veya abonelik yoktur.",
        "Temel özellikler ücretsizdir. Tam sürümü isteğe bağlı, tek seferlik bir uygulama içi satın almayla açabilirsiniz. Abonelik yoktur.",
    ),
    "uk": (
        "Повну версію купуєте один раз під час завантаження. Без додаткових покупок у застосунку та без підписки.",
        "Основні функції безкоштовні. Повну версію можна відкрити одноразовою покупкою в застосунку, без підписки.",
    ),
    "he": (
        "משלמים פעם אחת בעת ההורדה ומקבלים את האפליקציה המלאה. אין רכישות נוספות באפליקציה ואין מנוי.",
        "האפשרויות הבסיסיות זמינות בחינם. אפשר לפתוח את הגרסה המלאה ברכישה חד־פעמית בתוך האפליקציה, ללא מנוי.",
    ),
}

IDENTITIES = {
    "lumiletterspro": "Lumi Letters Pro: ABC Phonics",
    "lumibopomofopro": "Lumi Bopomofo Pro: Zhuyin",
    "lumimathpro": "Lumi Math Pro: Kids Numbers",
    "lumimissionpro": "Lumi Mission Planet Pro",
    "tripplanet": "Trip Planet: Kids Quest",
    "tripbee": "TripBee Pro: Trip Planner",
    "aim990": "Aim990",
    "unblurry": "Unblurry Pro",
}
PAID_UPFRONT = frozenset({
    "lumiletterspro", "lumibopomofopro", "lumimathpro",
    "lumimissionpro", "tripbee",
})

# Each row contains a complete headline, native editorial copy and search terms.
COPY = {
    "lumiletterspro": {
        "cs": (
            "Kompletní anglická abeceda hrou",
            "Lumi Letters Pro pomáhá dětem poznávat všech 26 anglických písmen, jejich názvy a hlásky.\n\nVelká i malá písmena si mohou obtahovat podle správného pořadí tahů a procvičovat jejich rozpoznávání. Kompletní edice Pro funguje offline a bez reklam.",
            "anglická abeceda, hlásky, obtahování písmen, velká písmena, malá písmena, angličtina pro děti, učení hrou, předškoláci",
        ),
        "hu": (
            "A teljes angol ábécé játékosan",
            "A Lumi Letters Pro segít a gyerekeknek megismerni mind a 26 angol betűt, a nevüket és a hangjukat.\n\nA kis- és nagybetűket a helyes vonássorrendet követve írhatják át, majd játékosan gyakorolhatják a felismerésüket. A teljes Pro kiadás internetkapcsolat nélkül, reklámmentesen használható.",
            "angol ábécé, betűhangok, betűírás, kisbetűk, nagybetűk, angol gyerekeknek, játékos tanulás, óvodások",
        ),
        "pl": (
            "Cały angielski alfabet przez zabawę",
            "Lumi Letters Pro pomaga dzieciom poznawać wszystkie 26 liter angielskiego alfabetu, ich nazwy i dźwięki.\n\nDzieci wodzą palcem po małych i wielkich literach zgodnie z kolejnością kresek i ćwiczą ich rozpoznawanie. Pełna edycja Pro działa bez internetu i reklam.",
            "angielski alfabet, głoski, pisanie po śladzie, małe litery, wielkie litery, angielski dla dzieci, nauka przez zabawę, przedszkolaki",
        ),
        "ro": (
            "Întregul alfabet englez, prin joacă",
            "Lumi Letters Pro îi ajută pe copii să descopere toate cele 26 de litere englezești, numele și sunetele lor.\n\nCopiii trasează literele mari și mici în ordinea corectă și exersează recunoașterea lor. Ediția Pro include întregul alfabet și funcționează fără internet și fără reclame.",
            "alfabet englez, sunetele literelor, trasarea literelor, litere mari, litere mici, engleză pentru copii, învățare prin joacă, preșcolari",
        ),
        "ru": (
            "Весь английский алфавит в игре",
            "Lumi Letters Pro помогает детям знакомиться со всеми 26 английскими буквами, их названиями и звуками.\n\nРебёнок обводит заглавные и строчные буквы в правильном порядке и учится их узнавать. Полная версия Pro включает весь алфавит, работает без интернета и не содержит рекламы.",
            "английский алфавит, звуки букв, обводить буквы, заглавные буквы, строчные буквы, английский для детей, обучение в игре, дошкольники",
        ),
        "sk": (
            "Celá anglická abeceda hrou",
            "Lumi Letters Pro pomáha deťom spoznať všetkých 26 anglických písmen, ich názvy a hlásky.\n\nVeľké aj malé písmená môžu obťahovať v správnom poradí ťahov a precvičovať si ich rozpoznávanie. Úplná edícia Pro obsahuje celú abecedu, funguje offline a je bez reklám.",
            "anglická abeceda, hlásky, obťahovanie písmen, veľké písmená, malé písmená, angličtina pre deti, učenie hrou, predškoláci",
        ),
        "sl-SI": (
            "Celotna angleška abeceda skozi igro",
            "Lumi Letters Pro otrokom pomaga spoznati vseh 26 angleških črk, njihova imena in glasove.\n\nS prstom sledijo velikim in malim črkam v pravilnem vrstnem redu potez ter vadijo njihovo prepoznavanje. Celotna različica Pro vključuje vso abecedo ter deluje brez povezave in oglasov.",
            "angleška abeceda, glasovi, pisanje črk, velike črke, male črke, angleščina za otroke, učenje skozi igro, predšolski otroci",
        ),
        "tr": (
            "İngilizce alfabenin tamamı oyunla",
            "Lumi Letters Pro, çocukların İngilizcedeki 26 harfin tamamını, adlarını ve seslerini tanımasına yardımcı olur.\n\nÇocuklar büyük ve küçük harflerin üzerinden doğru çizgi sırasıyla geçer ve harfleri tanıma alıştırmaları yapar. Tam Pro sürümü bütün alfabeyi içerir; çevrimdışı ve reklamsız çalışır.",
            "İngilizce alfabe, harf sesleri, harf çizme, büyük harfler, küçük harfler, çocuklar için İngilizce, oyunla öğrenme, okul öncesi",
        ),
        "uk": (
            "Уся англійська абетка через гру",
            "Lumi Letters Pro допомагає дітям познайомитися з усіма 26 англійськими літерами, їхніми назвами та звуками.\n\nДіти обводять великі й малі літери в правильному порядку та вчаться їх упізнавати. Повна версія Pro містить усю абетку, працює без інтернету й не має реклами.",
            "англійська абетка, звуки літер, обведення літер, великі літери, малі літери, англійська для дітей, навчання через гру, дошкільнята",
        ),
        "he": (
            "כל אותיות האנגלית דרך משחק",
            "לומדים להכיר את כל 26 אותיות האנגלית, את שמותיהן ואת הצלילים שלהן עם Lumi Letters Pro.\n\nהילדים מתרגלים כתיבה באצבע של אותיות גדולות וקטנות לפי סדר הקווים, ומשחקים בזיהוי אותיות וצלילים. מהדורת Pro כוללת את כל האלפבית ופועלת ללא חיבור לאינטרנט וללא פרסומות.",
            "אותיות באנגלית, צלילי אותיות, כתיבה באצבע, אותיות גדולות, אותיות קטנות, אנגלית לילדים, למידה במשחק, ילדי גן",
        ),
    },
    "lumibopomofopro": {
        "cs": (
            "Všech 37 znaků čínské fonetiky hrou",
            "Lumi Bopomofo Pro seznamuje děti se všemi 37 znaky ču-jinu, fonetického systému mandarínské čínštiny.\n\nPoslech, přiřazování, obtahování znaků a cvičení tónů pomáhají propojovat znak se zvukem. Kompletní edice Pro je připravená k učení offline, bez reklam.",
            "ču-jin, bopomofo, mandarínština, čínská výslovnost, tóny, obtahování znaků, poslech, čínština pro děti",
        ),
        "hu": (
            "Mind a 37 kínai hangjel játékosan",
            "A Lumi Bopomofo Pro a mandarin kínai hangjelölő rendszer, a csujin mind a 37 jelével ismerteti meg a gyerekeket.\n\nHallgatás, párosítás, jelírás és hanglejtésgyakorlatok segítenek összekapcsolni a jeleket a hangokkal. A teljes Pro kiadás internetkapcsolat nélkül, reklámmentesen használható.",
            "csujin, bopomofo, mandarin kínai, kínai kiejtés, hanglejtés, jelírás, hallás utáni tanulás, kínai gyerekeknek",
        ),
        "pl": (
            "Wszystkie 37 znaków fonetycznych",
            "Lumi Bopomofo Pro pomaga dzieciom poznać wszystkie 37 znaków zhuyin, systemu zapisu wymowy języka mandaryńskiego.\n\nSłuchanie, dopasowywanie, pisanie po śladzie i ćwiczenia tonów łączą znaki z dźwiękami. Pełna edycja Pro jest gotowa do nauki bez internetu i reklam.",
            "zhuyin, bopomofo, język mandaryński, chińska wymowa, tony, pisanie po śladzie, słuchanie, chiński dla dzieci",
        ),
        "ro": (
            "Toate cele 37 de semne fonetice",
            "Lumi Bopomofo Pro îi ajută pe copii să cunoască toate cele 37 de semne zhuyin, folosite pentru pronunția limbii chineze mandarine.\n\nExercițiile de ascultare, asociere, trasare și tonuri leagă semnele de sunete. Ediția Pro include întregul set și funcționează fără internet și fără reclame.",
            "zhuyin, bopomofo, chineză mandarină, pronunție chineză, tonuri, trasarea semnelor, ascultare, chineză pentru copii",
        ),
        "ru": (
            "Все 37 знаков китайской фонетики",
            "Lumi Bopomofo Pro знакомит детей со всеми 37 знаками чжуинь — системы записи произношения китайского языка путунхуа.\n\nРебёнок слушает звуки, подбирает соответствующие знаки, обводит их и тренирует тоны. Полная версия Pro содержит весь набор знаков, работает без интернета и рекламы.",
            "чжуинь, бопомофо, китайский язык, китайское произношение, тоны, обводить знаки, слушать звуки, китайский для детей",
        ),
        "sk": (
            "Všetkých 37 znakov čínskej fonetiky",
            "Lumi Bopomofo Pro pomáha deťom spoznať všetkých 37 znakov ču-jinu, fonetického systému mandarínskej čínštiny.\n\nPočúvanie, priraďovanie, obťahovanie znakov a precvičovanie tónov prepájajú znaky so zvukmi. Úplná edícia Pro obsahuje celú súpravu a funguje offline, bez reklám.",
            "ču-jin, bopomofo, mandarínska čínština, čínska výslovnosť, tóny, obťahovanie znakov, počúvanie, čínština pre deti",
        ),
        "sl-SI": (
            "Vseh 37 znakov kitajske izgovarjave",
            "Lumi Bopomofo Pro otrokom predstavi vseh 37 znakov zhuyin, sistema za zapis izgovarjave mandarinščine.\n\nPoslušanje, povezovanje, sledenje znakom s prstom in vaje za tone pomagajo povezati znak z glasom. Celotna različica Pro vključuje vse znake ter deluje brez povezave in oglasov.",
            "zhuyin, bopomofo, mandarinščina, kitajska izgovarjava, toni, pisanje znakov, poslušanje, kitajščina za otroke",
        ),
        "tr": (
            "Çince sesler için 37 işaretin tamamı",
            "Lumi Bopomofo Pro, çocuklara Mandarin Çincesinin seslerini gösteren Zhuyin sistemindeki 37 işaretin tamamını tanıtır.\n\nDinleme, eşleştirme, işaret çizme ve ton alıştırmaları seslerle işaretler arasında bağ kurar. Tam Pro sürümü bütün işaretleri içerir; çevrimdışı ve reklamsız çalışır.",
            "Zhuyin, bopomofo, Mandarin Çincesi, Çince telaffuz, tonlar, işaret çizme, dinleme, çocuklar için Çince",
        ),
        "uk": (
            "Усі 37 знаків китайської фонетики",
            "Lumi Bopomofo Pro знайомить дітей з усіма 37 знаками чжуїнь — системи запису вимови китайської мови путунхуа.\n\nСлухання, добір відповідного знака, обведення та вправи на тони допомагають поєднати знак зі звуком. Повна версія Pro містить усі знаки й працює без інтернету та реклами.",
            "чжуїнь, бопомофо, китайська мова, китайська вимова, тони, обведення знаків, слухання, китайська для дітей",
        ),
        "he": (
            "כל 37 הסימנים להגייה בסינית",
            "מכירים את כל 37 סימני ג׳ו־יין, מערכת הכתב הפונטית של סינית מנדרינית, עם Lumi Bopomofo Pro.\n\nהאזנה, התאמה, כתיבה באצבע ותרגול טונים עוזרים לחבר בין סימן לצליל. מהדורת Pro כוללת את כל הסימנים ופועלת ללא חיבור לאינטרנט וללא פרסומות.",
            "ג׳ו־יין, בופומופו, סינית מנדרינית, הגייה בסינית, טונים, כתיבה באצבע, האזנה, סינית לילדים",
        ),
    },
    "lumimathpro": {
        "cs": (
            "Kompletní matematická dobrodružství",
            "Lumi Math Pro nabízí kompletní edici matematických her pro děti, které chtějí procvičovat čísla a počítání.\n\nDěti řeší početní úkoly a logické výzvy vlastním tempem. Edice Pro zahrnuje úplný obsah pro další procvičování, funguje offline a neobsahuje reklamy.",
            "matematika pro děti, čísla, počítání, početní úkoly, logické hry, matematické hry, procvičování, učení hrou",
        ),
        "hu": (
            "Teljes matematikai játékkaland",
            "A Lumi Math Pro a matematikai játékok teljes kiadását kínálja a számokkal és számolással ismerkedő gyerekeknek.\n\nA számolási feladatokat és logikai kihívásokat saját tempójukban oldhatják meg. A Pro kiadás a teljes gyakorlóanyagot tartalmazza, és internetkapcsolat nélkül, reklámmentesen működik.",
            "matematika gyerekeknek, számok, számolás, számolási feladatok, logikai játékok, matematikai játékok, gyakorlás, játékos tanulás",
        ),
        "pl": (
            "Pełna matematyczna przygoda",
            "Lumi Math Pro to pełna edycja gier matematycznych dla dzieci poznających liczby i ćwiczących liczenie.\n\nDzieci rozwiązują zadania rachunkowe i wyzwania logiczne we własnym tempie. Edycja Pro obejmuje cały materiał do ćwiczeń, działa bez internetu i nie zawiera reklam.",
            "matematyka dla dzieci, liczby, liczenie, zadania rachunkowe, gry logiczne, gry matematyczne, ćwiczenia, nauka przez zabawę",
        ),
        "ro": (
            "Aventura matematică în ediție completă",
            "Lumi Math Pro este ediția completă de jocuri matematice pentru copiii care descoperă numerele și exersează calculele.\n\nCopiii rezolvă exerciții de calcul și provocări de logică în ritmul lor. Ediția Pro include întregul conținut de exersare și funcționează fără internet și fără reclame.",
            "matematică pentru copii, numere, numărare, exerciții de calcul, jocuri de logică, jocuri matematice, exersare, învățare prin joacă",
        ),
        "ru": (
            "Полное математическое приключение",
            "Lumi Math Pro — полная версия математических игр для детей, которые знакомятся с числами и тренируют счёт.\n\nРебёнок решает примеры и логические задачи в своём темпе. Версия Pro включает весь материал для занятий, работает без интернета и не содержит рекламы.",
            "математика для детей, числа, счёт, примеры, логические задачи, математические игры, упражнения, обучение в игре",
        ),
        "sk": (
            "Úplné matematické dobrodružstvo",
            "Lumi Math Pro ponúka úplnú edíciu matematických hier pre deti, ktoré spoznávajú čísla a precvičujú si počítanie.\n\nDeti riešia počtové úlohy a logické výzvy vlastným tempom. Edícia Pro obsahuje všetok učebný obsah na ďalšie precvičovanie, funguje offline a je bez reklám.",
            "matematika pre deti, čísla, počítanie, počtové úlohy, logické hry, matematické hry, precvičovanie, učenie hrou",
        ),
        "sl-SI": (
            "Celotna matematična pustolovščina",
            "Lumi Math Pro je celotna različica matematičnih iger za otroke, ki spoznavajo števila in vadijo računanje.\n\nRačunske naloge in logične izzive rešujejo v svojem tempu. Različica Pro vključuje vso vsebino za vadbo ter deluje brez povezave in oglasov.",
            "matematika za otroke, števila, štetje, računske naloge, logične igre, matematične igre, vaje, učenje skozi igro",
        ),
        "tr": (
            "Eksiksiz matematik oyunları",
            "Lumi Math Pro, sayıları öğrenen ve işlem pratiği yapan çocuklar için matematik oyunlarının tam sürümünü sunar.\n\nÇocuklar işlem sorularını ve mantık bulmacalarını kendi hızlarında çözer. Pro sürümü alıştırma içeriğinin tamamını kapsar; çevrimdışı ve reklamsız çalışır.",
            "çocuklar için matematik, sayılar, sayma, işlem soruları, mantık oyunları, matematik oyunları, alıştırma, oyunla öğrenme",
        ),
        "uk": (
            "Повна математична пригода",
            "Lumi Math Pro — повна версія математичних ігор для дітей, які знайомляться з числами та тренують лічбу.\n\nДіти розв’язують приклади й логічні завдання у власному темпі. Версія Pro містить увесь матеріал для вправ, працює без інтернету й не має реклами.",
            "математика для дітей, числа, лічба, приклади, логічні завдання, математичні ігри, вправи, навчання через гру",
        ),
        "he": (
            "הרפתקת חשבון במהדורה מלאה",
            "מכירים מספרים ומתרגלים חשבון עם Lumi Math Pro, המהדורה המלאה של משחקי המתמטיקה לילדים.\n\nהילדים פותרים תרגילי חשבון ואתגרי היגיון בקצב שלהם. מהדורת Pro כוללת את כל תוכן התרגול ופועלת ללא חיבור לאינטרנט וללא פרסומות.",
            "מתמטיקה לילדים, מספרים, ספירה, תרגילי חשבון, משחקי היגיון, משחקי חשבון, תרגול, למידה במשחק",
        ),
    },
    "lumimissionpro": {
        "cs": (
            "Kompletní úkoly a odměny pro děti",
            "Lumi Mission Planet Pro mění čištění zubů, oblékání, úklid hraček a přípravu na spaní v malé vesmírné úkoly.\n\nKompletní edice Pro zahrnuje úkoly, odměny i nastavení pro každodenní rodinný režim. Děti získávají hvězdy za snahu a rodiče mohou sledovat jejich pokrok. Bez reklam.",
            "denní režim dětí, dětské úkoly, návyky, odměny, čištění zubů, úklid hraček, večerní rutina, rodiče",
        ),
        "hu": (
            "Teljes gyerekfeladat- és jutalomrendszer",
            "A Lumi Mission Planet Pro a fogmosást, öltözést, játékpakolást és esti készülődést apró űrküldetésekké alakítja.\n\nA teljes Pro kiadás a családi napirendhez tartozó feladatokat, jutalmakat és beállításokat is tartalmazza. A gyerekek az igyekezetükért csillagokat kapnak, a szülők pedig követhetik a haladásukat. Reklámmentes.",
            "gyerekek napirendje, gyerekfeladatok, szokások, jutalmak, fogmosás, játékpakolás, esti rutin, szülők",
        ),
        "pl": (
            "Pełny zestaw zadań i nagród dla dzieci",
            "Lumi Mission Planet Pro zamienia mycie zębów, ubieranie, sprzątanie zabawek i przygotowanie do snu w małe kosmiczne misje.\n\nPełna edycja Pro zawiera zadania, nagrody i ustawienia wspierające rodzinny rytm dnia. Dzieci zbierają gwiazdki za wysiłek, a rodzice mogą śledzić ich postępy. Bez reklam.",
            "rytm dnia dziecka, zadania dla dzieci, nawyki, nagrody, mycie zębów, sprzątanie zabawek, wieczorna rutyna, rodzice",
        ),
        "ro": (
            "Toate misiunile și recompensele pentru copii",
            "Lumi Mission Planet Pro transformă spălatul pe dinți, îmbrăcatul, strânsul jucăriilor și pregătirea de somn în mici misiuni spațiale.\n\nEdiția Pro include toate misiunile, recompensele și setările pentru rutina familiei. Copiii primesc steluțe pentru efort, iar părinții le pot urmări progresul. Fără reclame.",
            "rutina copiilor, sarcini pentru copii, obiceiuri, recompense, spălat pe dinți, strânsul jucăriilor, rutina de seară, părinți",
        ),
        "ru": (
            "Все детские задания и награды",
            "Lumi Mission Planet Pro превращает чистку зубов, одевание, уборку игрушек и подготовку ко сну в небольшие космические задания.\n\nПолная версия Pro включает задания, награды и настройки для семейного распорядка. Дети получают звёзды за старание, а родители могут следить за их успехами. Без рекламы.",
            "распорядок дня ребёнка, детские задания, привычки, награды, чистка зубов, уборка игрушек, вечерний распорядок, родители",
        ),
        "sk": (
            "Všetky detské úlohy a odmeny",
            "Lumi Mission Planet Pro mení čistenie zubov, obliekanie, upratovanie hračiek a prípravu na spánok na malé vesmírne úlohy.\n\nÚplná edícia Pro zahŕňa úlohy, odmeny aj nastavenia pre každodenný rodinný režim. Deti získavajú hviezdy za snahu a rodičia môžu sledovať ich pokrok. Bez reklám.",
            "denný režim detí, detské úlohy, návyky, odmeny, čistenie zubov, upratovanie hračiek, večerná rutina, rodičia",
        ),
        "sl-SI": (
            "Vse otroške naloge in nagrade",
            "Lumi Mission Planet Pro spremeni umivanje zob, oblačenje, pospravljanje igrač in pripravo na spanje v majhne vesoljske naloge.\n\nCelotna različica Pro vključuje naloge, nagrade in nastavitve za družinsko rutino. Otroci za trud dobivajo zvezdice, starši pa lahko spremljajo njihov napredek. Brez oglasov.",
            "otroška rutina, naloge za otroke, navade, nagrade, umivanje zob, pospravljanje igrač, večerna rutina, starši",
        ),
        "tr": (
            "Çocuklar için tüm görev ve ödüller",
            "Lumi Mission Planet Pro; diş fırçalama, giyinme, oyuncak toplama ve uyku hazırlığını küçük uzay görevlerine dönüştürür.\n\nTam Pro sürümü, aile düzeni için görevleri, ödülleri ve ayarları içerir. Çocuklar çabaları karşılığında yıldız kazanırken ebeveynler ilerlemelerini takip edebilir. Reklam içermez.",
            "çocuk rutini, çocuk görevleri, alışkanlıklar, ödüller, diş fırçalama, oyuncak toplama, akşam rutini, ebeveynler",
        ),
        "uk": (
            "Усі дитячі завдання та винагороди",
            "Lumi Mission Planet Pro перетворює чищення зубів, одягання, прибирання іграшок і підготовку до сну на маленькі космічні завдання.\n\nПовна версія Pro містить завдання, винагороди й налаштування для щоденного сімейного розпорядку. Діти отримують зірочки за старання, а батьки можуть стежити за поступом. Без реклами.",
            "розпорядок дня дитини, дитячі завдання, звички, винагороди, чищення зубів, прибирання іграшок, вечірній розпорядок, батьки",
        ),
        "he": (
            "כל המשימות והפרסים לילדים",
            "הופכים צחצוח שיניים, התלבשות, סידור צעצועים והכנה לשינה למשימות חלל קטנות עם Lumi Mission Planet Pro.\n\nמהדורת Pro כוללת את כל המשימות, הפרסים וההגדרות לשגרת המשפחה. הילדים מקבלים כוכבים על המאמץ, וההורים יכולים לעקוב אחר ההתקדמות. ללא פרסומות.",
            "שגרת ילדים, משימות לילדים, הרגלים, פרסים, צחצוח שיניים, סידור צעצועים, שגרת ערב, הורים",
        ),
    },
    "tripplanet": {
        "cs": (
            "Rodinné cestování s dětskými úkoly",
            "Trip Planet: Kids Quest promění rodinnou cestu v dobrodružství, do kterého se zapojí i děti.\n\nRodiče vytvoří cestu a děti plní drobné úkoly v letadle, hotelu, restauraci i na výletě. Odměny, odznaky a vzpomínkové karty uchovají společné zážitky. Nákupy a vnější odkazy chrání rodičovská brána.",
            "cestování s dětmi, rodinná dovolená, cestovní úkoly, hry na cestu, dětské odměny, výlety, vzpomínky, rodinné aktivity",
        ),
        "hu": (
            "Családi utazás gyerekeknek szóló küldetésekkel",
            "A Trip Planet: Kids Quest a családi utazást közös kalanddá alakítja, amelyben a gyerekek is részt vesznek.\n\nA szülők létrehozzák az utat, a gyerekek pedig apró feladatokat teljesítenek a repülőn, a szállodában, az étteremben és kirándulás közben. Jutalmak, jelvények és emlékkártyák őrzik az élményeket. A vásárlásokat és külső hivatkozásokat szülői ellenőrzés védi.",
            "utazás gyerekekkel, családi nyaralás, utazási feladatok, úti játékok, gyerekjutalmak, kirándulás, emlékek, családi programok",
        ),
        "pl": (
            "Rodzinne podróże z misjami dla dzieci",
            "Trip Planet: Kids Quest zamienia rodzinny wyjazd we wspólną przygodę, w której dzieci mają swoje zadania.\n\nRodzice tworzą podróż, a dzieci wykonują małe misje w samolocie, hotelu, restauracji i podczas zwiedzania. Nagrody, odznaki i karty wspomnień utrwalają przeżycia. Zakupy i linki zewnętrzne wymagają przejścia bramki rodzicielskiej.",
            "podróże z dziećmi, rodzinne wakacje, zadania w podróży, zabawy w drodze, nagrody dla dzieci, wycieczki, wspomnienia, rodzinne aktywności",
        ),
        "ro": (
            "Călătorii în familie cu misiuni pentru copii",
            "Trip Planet: Kids Quest transformă călătoria în familie într-o aventură la care participă și copiii.\n\nPărinții creează călătoria, iar copiii îndeplinesc mici misiuni în avion, la hotel, la restaurant și la obiectivele vizitate. Recompensele, insignele și cartonașele cu amintiri păstrează experiențele. Achizițiile și linkurile externe sunt protejate prin verificare parentală.",
            "călătorii cu copii, vacanță în familie, misiuni de călătorie, jocuri pe drum, recompense pentru copii, excursii, amintiri, activități în familie",
        ),
        "ru": (
            "Семейные поездки с заданиями для детей",
            "Trip Planet: Kids Quest превращает семейную поездку в приключение, в котором у детей есть свои задания.\n\nРодители создают путешествие, а дети выполняют небольшие задания в самолёте, отеле, ресторане и на экскурсиях. Награды, значки и памятные карточки сохраняют впечатления. Покупки и внешние ссылки защищены родительской проверкой.",
            "путешествия с детьми, семейный отдых, задания в поездке, игры в дороге, детские награды, экскурсии, воспоминания, семейные занятия",
        ),
        "sk": (
            "Rodinné cestovanie s úlohami pre deti",
            "Trip Planet: Kids Quest mení rodinnú cestu na spoločné dobrodružstvo, do ktorého sa zapoja aj deti.\n\nRodičia vytvoria cestu a deti plnia malé úlohy v lietadle, hoteli, reštaurácii aj na výlete. Odmeny, odznaky a spomienkové karty uchovajú spoločné zážitky. Nákupy a externé odkazy chráni rodičovská brána.",
            "cestovanie s deťmi, rodinná dovolenka, cestovné úlohy, hry na cestu, detské odmeny, výlety, spomienky, rodinné aktivity",
        ),
        "sl-SI": (
            "Družinska potovanja z nalogami za otroke",
            "Trip Planet: Kids Quest spremeni družinsko potovanje v skupno pustolovščino, pri kateri sodelujejo tudi otroci.\n\nStarši ustvarijo potovanje, otroci pa opravljajo majhne naloge na letalu, v hotelu, restavraciji in med ogledi. Nagrade, značke in spominske kartice ohranijo skupna doživetja. Nakupe in zunanje povezave varuje starševsko preverjanje.",
            "potovanja z otroki, družinske počitnice, potovalne naloge, igre na poti, otroške nagrade, izleti, spomini, družinske dejavnosti",
        ),
        "tr": (
            "Çocuk görevleriyle ailece seyahat",
            "Trip Planet: Kids Quest, aile yolculuğunu çocukların da katıldığı ortak bir maceraya dönüştürür.\n\nEbeveynler seyahati oluşturur; çocuklar uçakta, otelde, restoranda ve gezilerde küçük görevler tamamlar. Ödüller, rozetler ve anı kartları yaşananları saklar. Satın almalar ve dış bağlantılar ebeveyn kontrolüyle korunur.",
            "çocuklarla seyahat, aile tatili, seyahat görevleri, yol oyunları, çocuk ödülleri, geziler, anılar, aile etkinlikleri",
        ),
        "uk": (
            "Сімейні подорожі із завданнями для дітей",
            "Trip Planet: Kids Quest перетворює сімейну мандрівку на спільну пригоду, до якої долучаються діти.\n\nБатьки створюють подорож, а діти виконують невеликі завдання в літаку, готелі, ресторані та під час екскурсій. Винагороди, значки й пам’ятні картки зберігають враження. Покупки та зовнішні посилання захищені батьківською перевіркою.",
            "подорожі з дітьми, сімейний відпочинок, завдання в подорожі, ігри в дорозі, дитячі винагороди, екскурсії, спогади, сімейні заняття",
        ),
        "he": (
            "טיולים משפחתיים עם משימות לילדים",
            "הופכים טיול משפחתי להרפתקה משותפת עם Trip Planet: Kids Quest.\n\nההורים יוצרים טיול, והילדים משלימים משימות קטנות במטוס, במלון, במסעדה ובאתרי הביקור. פרסים, תגים וכרטיסי זיכרונות שומרים את החוויות. רכישות וקישורים חיצוניים מוגנים בבדיקת הורים.",
            "טיולים עם ילדים, חופשה משפחתית, משימות בטיול, משחקים בדרך, פרסים לילדים, טיולי משפחות, זיכרונות, פעילויות משפחתיות",
        ),
    },
    "tripbee": {
        "cs": (
            "Kompletní plánovač vašich cest",
            "TripBee Pro udržuje lety, ubytování, aktivity a cestovní poznámky na jednom přehledném místě.\n\nNaplánujte si jednotlivé dny a mějte podklady k cestě po ruce. Jde o samostatnou placenou edici Pro, nikoli o bezplatnou aplikaci TripBee Lite.",
            "plánovač cest, itinerář, lety, ubytování, cestovní poznámky, denní plán, dovolená, organizace cest",
        ),
        "hu": (
            "Teljes utazástervező minden úthoz",
            "A TripBee Pro egyetlen átlátható helyen rendezi a repülőjáratokat, szállásokat, programokat és úti jegyzeteket.\n\nTervezd meg a napokat, és tartsd kéznél az utazás fontos adatait. Ez az önálló, fizetős Pro kiadás, nem az ingyenes TripBee Lite.",
            "utazástervező, útiterv, repülőjáratok, szállás, úti jegyzetek, napi terv, nyaralás, utazásszervezés",
        ),
        "pl": (
            "Pełny planer twoich podróży",
            "TripBee Pro porządkuje loty, noclegi, atrakcje i notatki z podróży w jednym czytelnym miejscu.\n\nZaplanuj poszczególne dni i miej ważne informacje pod ręką. To osobna, płatna edycja Pro, a nie bezpłatna aplikacja TripBee Lite.",
            "planer podróży, plan wyjazdu, loty, noclegi, notatki podróżne, plan dnia, wakacje, organizacja podróży",
        ),
        "ro": (
            "Planificatorul complet al călătoriilor tale",
            "TripBee Pro adună zborurile, cazările, activitățile și notițele de călătorie într-un singur loc, ușor de urmărit.\n\nPlanifică fiecare zi și păstrează la îndemână informațiile importante. Aceasta este ediția Pro, o aplicație plătită separată, nu versiunea gratuită TripBee Lite.",
            "planificator de călătorii, itinerar, zboruri, cazare, notițe de călătorie, program zilnic, vacanță, organizarea călătoriei",
        ),
        "ru": (
            "Полный планировщик ваших путешествий",
            "TripBee Pro собирает перелёты, жильё, занятия и путевые заметки в одном понятном плане.\n\nРаспределите дела по дням и держите важные сведения о поездке под рукой. Это отдельная платная версия Pro, а не бесплатное приложение TripBee Lite.",
            "планировщик путешествий, маршрут, перелёты, жильё, путевые заметки, план дня, отпуск, организация поездки",
        ),
        "sk": (
            "Úplný plánovač vašich ciest",
            "TripBee Pro usporiada lety, ubytovanie, aktivity a cestovné poznámky na jednom prehľadnom mieste.\n\nNaplánujte si jednotlivé dni a majte dôležité podklady k ceste poruke. Ide o samostatnú platenú edíciu Pro, nie o bezplatnú aplikáciu TripBee Lite.",
            "plánovač ciest, itinerár, lety, ubytovanie, cestovné poznámky, denný plán, dovolenka, organizácia ciest",
        ),
        "sl-SI": (
            "Celoten načrtovalnik tvojih potovanj",
            "TripBee Pro združi lete, nastanitve, dejavnosti in potovalne zapiske na enem preglednem mestu.\n\nNačrtuj posamezne dni in imej pomembne podatke o poti pri roki. To je samostojna plačljiva različica Pro, ne brezplačna aplikacija TripBee Lite.",
            "načrtovalnik potovanj, načrt poti, leti, nastanitve, potovalni zapiski, dnevni načrt, počitnice, organizacija potovanj",
        ),
        "tr": (
            "Seyahatleriniz için tam planlayıcı",
            "TripBee Pro; uçuşları, konaklamaları, etkinlikleri ve seyahat notlarını tek bir düzenli yerde toplar.\n\nGünleri planlayın ve önemli yolculuk bilgilerini elinizin altında tutun. Bu, ücretsiz TripBee Lite değil, ayrı olarak satılan tam Pro sürümüdür.",
            "seyahat planlayıcı, gezi planı, uçuşlar, konaklama, seyahat notları, günlük plan, tatil, seyahat düzeni",
        ),
        "uk": (
            "Повний планувальник ваших подорожей",
            "TripBee Pro збирає перельоти, житло, заняття та дорожні нотатки в одному зрозумілому плані.\n\nРозплануйте кожен день і тримайте важливі відомості про поїздку під рукою. Це окрема платна версія Pro, а не безкоштовний застосунок TripBee Lite.",
            "планувальник подорожей, маршрут, перельоти, житло, дорожні нотатки, план дня, відпустка, організація поїздки",
        ),
        "he": (
            "תכנון מלא של הטיולים שלך",
            "מרכזים טיסות, מקומות לינה, פעילויות והערות לטיול במקום מסודר אחד עם TripBee Pro.\n\nמתכננים כל יום ושומרים את פרטי הנסיעה בהישג יד. זו מהדורת Pro נפרדת בתשלום, ולא האפליקציה החינמית TripBee Lite.",
            "תכנון טיולים, מסלול טיול, טיסות, לינה, הערות לטיול, תוכנית יומית, חופשה, ארגון נסיעות",
        ),
    },
    "aim990": {
        "cs": (
            "Denní příprava na poslech a čtení",
            "Aim990 pomáhá s přípravou na TOEIC pomocí poslechových a čtenářských cvičení, práce na slabších místech a sledování pokroku.\n\nProcvičujte si zkouškové tempo podle vlastních potřeb. Aplikace neslibuje konkrétní skóre ani výsledek v daném termínu. TOEIC je ochranná známka ETS; Aim990 není oficiálním produktem ETS.",
            "příprava na TOEIC, angličtina, poslech, čtení, slabší místa, cvičení, zkouškové tempo, pokrok",
        ),
        "hu": (
            "Napi felkészülés hallásértésből és olvasásból",
            "Az Aim990 hallásértési és olvasási gyakorlatokkal, a gyengébb területek célzott fejlesztésével és a haladás követésével segít felkészülni a TOEIC-ra.\n\nA vizsgatempót a saját igényeid szerint gyakorolhatod. Az alkalmazás nem ígér meghatározott pontszámot vagy határidőre elért eredményt. A TOEIC az ETS védjegye; az Aim990 nem az ETS hivatalos terméke.",
            "TOEIC felkészülés, angol, hallásértés, szövegértés, gyenge pontok, gyakorlás, vizsgatempó, haladás",
        ),
        "pl": (
            "Codzienna praktyka słuchania i czytania",
            "Aim990 wspiera przygotowanie do TOEIC przez ćwiczenia ze słuchania i czytania, pracę nad słabszymi obszarami oraz śledzenie postępów.\n\nĆwicz tempo egzaminacyjne zgodnie z własnymi potrzebami. Aplikacja nie obiecuje konkretnego wyniku ani osiągnięcia go w określonym terminie. TOEIC jest znakiem towarowym ETS; Aim990 nie jest oficjalnym produktem ETS.",
            "przygotowanie do TOEIC, angielski, słuchanie, czytanie, słabe strony, ćwiczenia, tempo egzaminacyjne, postępy",
        ),
        "ro": (
            "Practică zilnică de ascultare și citire",
            "Aim990 sprijină pregătirea pentru TOEIC prin exerciții de ascultare și citire, lucru pe punctele slabe și urmărirea progresului.\n\nExersează ritmul de examen în funcție de nevoile tale. Aplicația nu promite un anumit punctaj sau un rezultat într-un termen fix. TOEIC este o marcă ETS; Aim990 nu este un produs oficial ETS.",
            "pregătire TOEIC, engleză, ascultare, citire, puncte slabe, exerciții, ritm de examen, progres",
        ),
        "ru": (
            "Ежедневная практика аудирования и чтения",
            "Aim990 помогает готовиться к TOEIC: тренировать аудирование и чтение, разбирать слабые места и отслеживать прогресс.\n\nОтрабатывайте экзаменационный темп с учётом своих потребностей. Приложение не обещает определённого балла или результата к заданному сроку. TOEIC — товарный знак ETS; Aim990 не является официальным продуктом ETS.",
            "подготовка к TOEIC, английский, аудирование, чтение, слабые места, упражнения, темп экзамена, прогресс",
        ),
        "sk": (
            "Denná príprava na počúvanie a čítanie",
            "Aim990 pomáha s prípravou na TOEIC pomocou počúvania, čítania, precvičovania slabších oblastí a sledovania pokroku.\n\nTrénujte skúškové tempo podľa vlastných potrieb. Aplikácia nesľubuje konkrétne skóre ani výsledok v určenom termíne. TOEIC je ochranná známka ETS; Aim990 nie je oficiálnym produktom ETS.",
            "príprava na TOEIC, angličtina, počúvanie, čítanie, slabšie oblasti, cvičenia, skúškové tempo, pokrok",
        ),
        "sl-SI": (
            "Vsakodnevne vaje poslušanja in branja",
            "Aim990 pomaga pri pripravi na TOEIC z vajami poslušanja in branja, obravnavo šibkejših področij in spremljanjem napredka.\n\nČasovno omejena vadba omogoča urjenje izpitnega tempa glede na tvoje potrebe. Aplikacija ne obljublja določene ocene ali rezultata v določenem roku. TOEIC je znamka ETS; Aim990 ni uradni izdelek ETS.",
            "priprava na TOEIC, angleščina, poslušanje, branje, šibkejša področja, vaje, izpitni tempo, napredek",
        ),
        "tr": (
            "Günlük dinleme ve okuma çalışması",
            "Aim990; dinleme ve okuma alıştırmaları, eksik konulara yönelik çalışma ve ilerleme takibiyle TOEIC hazırlığına yardımcı olur.\n\nSüreli alıştırmalarla sınav temponuzu ihtiyaçlarınıza göre geliştirin. Uygulama belirli bir puan veya belirli sürede sonuç vaat etmez. TOEIC, ETS'nin ticari markasıdır; Aim990 resmî bir ETS ürünü değildir.",
            "TOEIC hazırlığı, İngilizce, dinleme, okuma, eksik konular, alıştırma, sınav temposu, ilerleme",
        ),
        "uk": (
            "Щоденні вправи з аудіювання та читання",
            "Aim990 допомагає готуватися до TOEIC: тренувати аудіювання й читання, працювати над слабкими темами та відстежувати поступ.\n\nПрактикуйте темп іспиту відповідно до своїх потреб. Застосунок не обіцяє певного бала чи результату за визначений строк. TOEIC — торговельна марка ETS; Aim990 не є офіційним продуктом ETS.",
            "підготовка до TOEIC, англійська, аудіювання, читання, слабкі теми, вправи, темп іспиту, поступ",
        ),
        "he": (
            "תרגול יומי בהבנת הנשמע והנקרא",
            "מתכוננים למבחן TOEIC עם Aim990: מתרגלים הבנת הנשמע והנקרא, עובדים על נקודות חולשה ועוקבים אחר ההתקדמות.\n\nתרגול עם מגבלת זמן עוזר להכיר את קצב הבחינה. האפליקציה אינה מבטיחה ציון מסוים או תוצאה בתוך פרק זמן קבוע. TOEIC הוא סימן מסחר של ETS; האפליקציה אינה מוצר רשמי של ETS.",
            "הכנה למבחן TOEIC, אנגלית, הבנת הנשמע, הבנת הנקרא, נקודות חולשה, תרגול, קצב הבחינה, התקדמות",
        ),
    },
    "unblurry": {
        "cs": (
            "Upravte ostrost a porovnejte výsledek",
            "Unblurry Pro nabízí doostření a úpravu fotografií přímo na iPhonu. Výsledek můžete před uložením porovnat s původním snímkem.\n\nMíra zlepšení závisí na původní fotografii. Silné rozmazání může přetrvat a chybějící detaily nelze spolehlivě obnovit. Bezplatné ukládání má limity; plnou kvalitu a další možnosti odemknete v aplikaci.",
            "doostření fotografií, rozmazané fotky, úprava fotografií, náhled, porovnání snímků, kvalita obrazu, staré fotografie, uložení fotek",
        ),
        "hu": (
            "Élesítés, összehasonlítás, mentés",
            "Az Unblurry Pro közvetlenül az iPhone-on kínál képélesítést és fotójavítást. Mentés előtt összehasonlíthatod az eredményt az eredeti képpel.\n\nA javulás az eredeti fotótól függ. Az erősen bemozdult kép homályos maradhat, a hiányzó részletek nem állíthatók vissza megbízhatóan. Az ingyenes mentés korlátozott; a teljes képminőség és a további lehetőségek az alkalmazásban oldhatók fel. Nincs előfizetés és nincs reklám.",
            "képélesítés, homályos fotó, fotójavítás, előnézet, képek összehasonlítása, képminőség, régi fényképek, fotómentés",
        ),
        "pl": (
            "Wyostrz zdjęcie i porównaj efekt",
            "Unblurry Pro pozwala wyostrzać i poprawiać zdjęcia bezpośrednio na iPhonie. Przed zapisaniem możesz porównać efekt z oryginałem.\n\nPoprawa zależy od zdjęcia źródłowego. Silne rozmycie może pozostać, a brakujących szczegółów nie da się wiarygodnie odtworzyć. Bezpłatny zapis ma ograniczenia; pełną jakość i dodatkowe możliwości odblokujesz w aplikacji.",
            "wyostrzanie zdjęć, rozmyte zdjęcia, poprawa zdjęć, podgląd, porównanie zdjęć, jakość obrazu, stare fotografie, zapisywanie zdjęć",
        ),
        "ro": (
            "Îmbunătățește claritatea și compară rezultatul",
            "Unblurry Pro oferă ajustarea clarității și îmbunătățirea fotografiilor direct pe iPhone. Poți compara rezultatul cu originalul înainte de salvare.\n\nÎmbunătățirea depinde de fotografia inițială. Neclaritatea puternică poate persista, iar detaliile lipsă nu pot fi recuperate cu certitudine. Salvarea gratuită are limite; calitatea completă și opțiunile suplimentare se deblochează în aplicație.",
            "claritate foto, fotografii neclare, îmbunătățire foto, previzualizare, compararea fotografiilor, calitatea imaginii, fotografii vechi, salvare foto",
        ),
        "ru": (
            "Настройте резкость и сравните результат",
            "Unblurry Pro позволяет настраивать резкость и улучшать фотографии прямо на iPhone. Перед сохранением можно сравнить результат с оригиналом.\n\nУлучшение зависит от исходного снимка. Сильное размытие может сохраниться, а отсутствующие детали нельзя достоверно восстановить. Бесплатное сохранение имеет ограничения; полное качество и дополнительные возможности открываются внутри приложения.",
            "резкость фотографий, размытые фото, улучшение фото, предпросмотр, сравнение снимков, качество изображения, старые фотографии, сохранение фото",
        ),
        "sk": (
            "Upravte ostrosť a porovnajte výsledok",
            "Unblurry Pro ponúka doostrenie a úpravu fotografií priamo na iPhone. Pred uložením môžete výsledok porovnať s pôvodným záberom.\n\nMiera zlepšenia závisí od pôvodnej fotografie. Silné rozmazanie môže pretrvať a chýbajúce detaily sa nedajú spoľahlivo obnoviť. Bezplatné ukladanie má limity; plnú kvalitu a ďalšie možnosti odomknete v aplikácii.",
            "doostrenie fotografií, rozmazané fotky, úprava fotografií, náhľad, porovnanie záberov, kvalita obrazu, staré fotografie, ukladanie fotiek",
        ),
        "sl-SI": (
            "Prilagodi ostrino in primerjaj rezultat",
            "Unblurry Pro omogoča ostrenje in izboljšanje fotografij neposredno v iPhonu. Pred shranjevanjem lahko rezultat primerjaš z izvirnikom.\n\nIzboljšava je odvisna od izvirne fotografije. Močna zamegljenost lahko ostane, manjkajočih podrobnosti pa ni mogoče zanesljivo obnoviti. Brezplačno shranjevanje ima omejitve; polno kakovost in dodatne možnosti odkleneš v aplikaciji.",
            "ostrenje fotografij, zamegljene fotografije, izboljšanje fotografij, predogled, primerjava posnetkov, kakovost slike, stare fotografije, shranjevanje fotografij",
        ),
        "tr": (
            "Netliği ayarlayın, sonucu karşılaştırın",
            "Unblurry Pro, fotoğrafları doğrudan iPhone'da keskinleştirme ve iyileştirme olanağı sunar. Kaydetmeden önce sonucu orijinal fotoğrafla karşılaştırabilirsiniz.\n\nİyileşme orijinal fotoğrafa bağlıdır. Yoğun bulanıklık devam edebilir; eksik ayrıntılar güvenilir biçimde geri getirilemez. Ücretsiz kaydetmenin sınırları vardır; tam kalite ve ek olanaklar uygulama içinde açılır.",
            "fotoğraf keskinleştirme, bulanık fotoğraf, fotoğraf iyileştirme, önizleme, fotoğraf karşılaştırma, görüntü kalitesi, eski fotoğraflar, fotoğraf kaydetme",
        ),
        "uk": (
            "Налаштуйте різкість і порівняйте результат",
            "Unblurry Pro дає змогу налаштовувати різкість і поліпшувати фотографії просто на iPhone. Перед збереженням можна порівняти результат з оригіналом.\n\nПоліпшення залежить від початкового знімка. Сильне розмиття може залишитися, а відсутні деталі неможливо достовірно відновити. Безкоштовне збереження має обмеження; повна якість і додаткові можливості відкриваються в застосунку.",
            "різкість фотографій, розмиті фото, поліпшення фото, попередній перегляд, порівняння знімків, якість зображення, старі фотографії, збереження фото",
        ),
        "he": (
            "מחדדים ומשווים לפני ששומרים",
            "משפרים חדות ומעבדים תמונות ישירות ב־iPhone עם Unblurry Pro. אפשר להשוות את התוצאה לתמונה המקורית לפני השמירה.\n\nמידת השיפור תלויה בתמונה המקורית. טשטוש חזק עשוי להישאר, ואי אפשר לשחזר באופן אמין פרטים שחסרים במקור. השמירה החינמית מוגבלת; איכות מלאה ואפשרויות נוספות נפתחות ברכישה באפליקציה.",
            "חידוד תמונות, תמונה מטושטשת, שיפור תמונות, תצוגה מקדימה, השוואת תמונות, איכות תמונה, תמונות ישנות, שמירת תמונות",
        ),
    },
    "lockhour": {
        "sk": (
            "Pokojný čas na sústredenú prácu",
            "LockHour pomáha chrániť čas na prácu, učenie aj oddych od telefónu.\n\nNaplánujte si blok sústredenia, sledujte priebeh časovača a obmedzte vyrušovanie vybranými aplikáciami. Nastavenia si prispôsobte svojmu dňu, nie naopak.",
            "sústredenie, blokovanie aplikácií, časovač, čas pri obrazovke, učenie, pokojná práca, riadenie času, menej vyrušovania",
        ),
    },
    "lumiletters": {
        "sk": (
            "Prvé anglické písmená hrou",
            "Lumi Letters Lite pomáha deťom spoznávať anglické písmená, ich hlásky a správne poradie ťahov.\n\nPísmeno A si môžu precvičovať bezplatne. Ostatné písmená a ich obsah zostávajú viditeľné na prezretie; na precvičovanie ich odomkne rodič jednorazovým nákupom za rodičovskou bránou.",
            "anglická abeceda, hlásky, obťahovanie písmen, angličtina pre deti, veľké písmená, malé písmená, učenie hrou, predškoláci",
        ),
    },
    "lumibopomofo": {
        "sk": (
            "Prvé znaky a hlásky mandarínskej čínštiny",
            "Lumi Bopomofo pomáha deťom učiť sa ču-jin, systém na zapisovanie výslovnosti mandarínskej čínštiny.\n\nZnak ㄅ si môžu precvičovať bezplatne a vláčik si vyskúšať trikrát. Ďalší obsah si môžu prezrieť; na jeho používanie je potrebné jednorazové odomknutie rodičom za rodičovskou bránou.",
            "ču-jin, bopomofo, mandarínska čínština, výslovnosť, tóny, obťahovanie znakov, detské hry, čínština pre deti",
        ),
    },
    "sereno": {
        "cs": (
            "Zvuky a šum pro spánek i soustředění",
            "Sereno umožňuje míchat zvuky deště, moře a barevného šumu pro odpočinek, spánek nebo soustředění.\n\nHlasitost jednotlivých zvuků si upravíte podle sebe a časovač přehrávání postupně ztiší. Funguje offline. Jde o zvukový nástroj, nikoli léčbu nespavosti nebo tinnitu.",
            "zvuky na spaní, bílý šum, déšť, moře, soustředění, relaxace, časovač, míchání zvuků",
        ),
        "sk": (
            "Zvuky a šum na spánok aj sústredenie",
            "Sereno umožňuje miešať zvuky dažďa, mora a farebného šumu na oddych, spánok alebo sústredenie.\n\nHlasitosť jednotlivých zvukov si upravíte podľa seba a časovač prehrávanie postupne stíši. Funguje offline. Je to zvukový nástroj, nie liečba nespavosti alebo tinnitu.",
            "zvuky na spanie, biely šum, dážď, more, sústredenie, relaxácia, časovač, miešanie zvukov",
        ),
        "sl-SI": (
            "Zvoki in šum za spanje ter zbranost",
            "Sereno omogoča mešanje zvokov dežja, morja in barvnega šuma za počitek, spanje ali zbranost.\n\nGlasnost posameznih zvokov prilagodiš po svoje, časovnik pa predvajanje postopoma utiša. Deluje brez povezave. To je zvočno orodje, ne zdravljenje nespečnosti ali tinitusa.",
            "zvoki za spanje, beli šum, dež, morje, zbranost, sprostitev, časovnik, mešanje zvokov",
        ),
        "tr": (
            "Uyku ve odaklanma için sesler ve beyaz gürültü",
            "Sereno; dinlenmek, uyumak veya odaklanmak için yağmur, deniz ve renkli gürültü seslerini karıştırmanıza olanak tanır.\n\nHer sesin düzeyini ayrı ayrı ayarlayabilir, zamanlayıcıyla sesi yavaşça kısabilirsiniz. Çevrimdışı çalışır. Bir ses aracıdır; uykusuzluk veya kulak çınlaması tedavisi değildir.",
            "uyku sesleri, beyaz gürültü, yağmur, deniz, odaklanma, rahatlama, zamanlayıcı, ses karıştırma",
        ),
    },
}

NAMES = {
    "lockhour": "LockHour Pro",
    "lumiletters": "Lumi Letters Lite: ABC Kids",
    "lumibopomofo": "Lumi Bopomofo",
    "sereno": "Sereno",
}

HEBREW_KEYWORDS = {
    "gmoney": "מעקב הוצאות, תקציב, ניהול הוצאות, המרת מטבע, שער חליפין, חיסכון, כספים, ארנק",
    "hourstag": "חיסכון, תקציב, הוצאות, קניות אימפולסיביות, שעות עבודה, שכר שעתי, צריכה מודעת, יעד חיסכון",
    "lockhour": "חסימת אפליקציות, ריכוז, זמן מסך, ניהול זמן, טיימר ללימודים, פחות הסחות דעת, עבודה ממוקדת, הרגלי שימוש",
    "lumimission": "טבלת פרסים, טבלת מדבקות, טבלת כוכבים, שגרת ילדים, שגרת בוקר, שגרת ערב, צחצוח שיניים, משימות לילדים",
    "lumiweather": "מזג אוויר, תחזית, תחזית שעתית, גשם, קרינה על־סגולה, טמפרטורה, רוח, מזג אוויר למשפחה",
    "photocream": "עריכת תמונות, מסנני צילום, מצלמת רטרו, סלפי, ריטוש, צילום בסגנון פילם, אפקטים, שיפור תמונות",
    "picclear": "ניקוי תמונות, פינוי מקום, תמונות כפולות, מחיקת תמונות, סידור גלריה, תמונות דומות, צילומי מסך, סרטונים גדולים",
}

TEXT_REPAIRS = {
    ("aibriefpack", "he"): (
        ("הפוך צילומי מסך, קבצים, פתקים ומסמכים ל-brief אחד ברור שמוכן ל-AI.",
         "הופכים צילומי מסך, קבצים, פתקים ומסמכים לתקציר ברור שמוכן לשימוש עם בינה מלאכותית."),
        ("הביאו את ההקשר המלא", "מרכזים את ההקשר המלא"),
        ("הוסף צילומי מסך, קובצי PDF, קבצים, טקסט שהועתק, פתקים או קישורים. אתה בוחר מה נשאר בתקציר הסופי.",
         "מוסיפים צילומי מסך, קובצי PDF, קבצים, טקסט שהועתק, פתקים או קישורים, ובוחרים מה נשאר בתקציר הסופי."),
        ("בחרו מקור אחד או יותר למעלה. העיבוד מתחיל רק כשתמשיכו.",
         "בוחרים מקור אחד או יותר. העיבוד מתחיל רק כשממשיכים לשלב הבא."),
        ("אמת את העובדות לפני שה-AI רואה אותן", "מאמתים את העובדות לפני העברתן לבינה מלאכותית"),
        ("כל עובדה שומרת על המקור והוודאות שלה. תקן כל דבר שדורש הקשר.",
         "לכל עובדה מצורפים המקור ורמת הוודאות שלה. מתקנים כל פרט שדורש הקשר נוסף."),
        ("מצא עובדות, סתירות ושאלות פתוחות", "מאתרים עובדות, סתירות ושאלות פתוחות"),
        ("בדקו כל עובדה, מקור ורמת ודאות לפני שה-AI יראה אותם.",
         "בודקים כל עובדה, מקור ורמת ודאות לפני העברתם לבינה מלאכותית."),
        ("הגן על פרטיות", "שומרים על הפרטיות"),
        ("השאר, החלף או הסר כל פריט לפני הייצוא.", "אפשר להשאיר, להחליף או להסיר כל פריט לפני הייצוא."),
        ("השאר, החלף או הסר כל זיהוי.", "אפשר להשאיר, להחליף או להסיר כל פרט שזוהה."),
        ("בנו הקשר פעם אחת. השתמשו בו בכל עת.", "בונים הקשר פעם אחת ומשתמשים בו בעת הצורך."),
        ("העתק בריף AI", "העתקת תקציר לבינה מלאכותית"),
        ("ההקשר שלך נשאר פרטי", "ההקשר נשאר בשליטתכם"),
        ("AI Brief אינו כולל", "האפליקציה AI Brief אינה כוללת"),
        ("סקור את התקציר לפני שליחתו לכל שירות AI.", "בודקים את התקציר לפני שליחתו לשירות בינה מלאכותית."),
    ),
    ("gmoney", "he"): (("נשארים על המכשיר", "נשארים במכשיר"),),
    ("hourstag", "he"): (("הוציאו את הזמן שלכם בכוונה", "השקיעו את הזמן שלכם במה שחשוב לכם"),),
    ("photocream", "he"): (
        ("פרטים cozy", "פרטים נעימים"),
        ("עדנו סלפי", "רככו את הסלפי"),
    ),
    ("wifiaidlite", "sl-SI"): (
        ("Začni Test", "Začni preizkus"),
        ("Deep Check", "Poglobljeni pregled"),
        ("Preveri Stran", "Preveri spletno stran"),
        ("Direct IP", "Neposredni naslov IP"),
        ("Nihanje (Jitter)", "Nihanje zakasnitve"),
        ("Zgodovina Testov", "Zgodovina preizkusov"),
    ),
    ("wordmate", "uk"): (
        ("передплати", "підписки"),
        ("передплата", "підписка"),
    ),
}


def reviewed_values(key: str, locale: str, source: dict) -> dict:
    """Return a copy without modifying metadata, other locales or receipts."""
    values = dict(source)
    if locale not in CEE_LOCALES:
        return values
    row = COPY.get(key, {}).get(locale)
    if row:
        subtitle, body, keywords = row
        values.update(
            name=IDENTITIES.get(key, NAMES.get(key, source.get("name", ""))),
            subtitle=subtitle,
            description=body + "\n\n" + PURCHASE_NOTES[locale][0 if key in PAID_UPFRONT else 1],
            promotionalText=body.split("\n\n", 1)[0],
            keywords=keywords,
        )
    if locale == "he" and key in HEBREW_KEYWORDS:
        values["keywords"] = HEBREW_KEYWORDS[key]
    for field in ("subtitle", "description", "promotionalText"):
        text = values.get(field)
        if not isinstance(text, str):
            continue
        for old, new in TEXT_REPAIRS.get((key, locale), ()):
            text = text.replace(old, new)
        if key == "shotinbox":
            text = re.sub(r"\s*US\s*\$\s*\d+(?:[.,]\d+)?", "", text)
        values[field] = text
    return values
