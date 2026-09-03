#!/usr/bin/env python3
"""每語言「答案 hub」索引頁生成器(2026-07-07 新方法)。
為何:低競爭語言(ms/vi/th/id/tr…)的在地化答案頁已存在,但沒有語言專屬的索引入口,
AI 爬蟲與搜尋引擎難以整批發現。此工具為每個有答案頁的語言產生 <lang>/answers/index.html:
  - 在地化標題/描述(agent 自產,不用任何付費 API)
  - 列出該語言全部答案頁(內部連結 → 可爬性)
  - ItemList JSON-LD(讓 AI/搜尋理解這是一個問答集合)
  - hreflang(en + 該語言)+ canonical
產完自動刷新 answers sitemap。純本機、免 key。
用法:python3 gen_answer_hubs.py [--langs ms,vi,...]
"""
import os, re, sys, html, json, argparse
from pathlib import Path
from site_config import PUBLIC_SITE  # noqa: E402

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
PAGES = HERE / "pages"
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")

# 各語言 hub 的在地化文案(agent 母語自產;繁中用台灣用語)。
L10N = {
    "ms": {"lang": "ms", "title": "Panduan Memilih Aplikasi iPhone — Jawapan Jujur",
           "desc": "Panduan jujur untuk memilih aplikasi iPhone: privasi, guna luar talian, dan bayar sekali tanpa langganan.",
           "h1": "Panduan memilih aplikasi iPhone", "all": "Semua panduan jawapan",
           "lead": "Panduan ringkas dan jujur untuk soalan sebenar sebelum anda memasang sesebuah aplikasi."},
    "vi": {"lang": "vi", "title": "Hướng dẫn chọn ứng dụng iPhone — Câu trả lời trung thực",
           "desc": "Hướng dẫn trung thực để chọn ứng dụng iPhone: riêng tư, dùng ngoại tuyến, trả một lần không thuê bao.",
           "h1": "Hướng dẫn chọn ứng dụng iPhone", "all": "Tất cả hướng dẫn trả lời",
           "lead": "Hướng dẫn ngắn gọn, trung thực cho những câu hỏi thực tế trước khi bạn cài đặt một ứng dụng."},
    "th": {"lang": "th", "title": "คู่มือเลือกแอป iPhone — คำตอบที่ตรงไปตรงมา",
           "desc": "คู่มือเลือกแอป iPhone อย่างซื่อสัตย์: ความเป็นส่วนตัว ใช้งานออฟไลน์ และจ่ายครั้งเดียวไม่มีค่าสมาชิก",
           "h1": "คู่มือเลือกแอป iPhone", "all": "คู่มือคำตอบทั้งหมด",
           "lead": "คู่มือสั้น ๆ ที่ซื่อสัตย์สำหรับคำถามจริงก่อนที่คุณจะติดตั้งแอป"},
    "id": {"lang": "id", "title": "Panduan Memilih Aplikasi iPhone — Jawaban Jujur",
           "desc": "Panduan jujur untuk memilih aplikasi iPhone: privasi, penggunaan offline, dan bayar sekali tanpa langganan.",
           "h1": "Panduan memilih aplikasi iPhone", "all": "Semua panduan jawaban",
           "lead": "Panduan singkat dan jujur untuk pertanyaan nyata sebelum Anda memasang sebuah aplikasi."},
    "tr": {"lang": "tr", "title": "iPhone Uygulaması Seçme Rehberleri — Dürüst Yanıtlar",
           "desc": "iPhone uygulaması seçmek için dürüst rehberler: gizlilik, çevrimdışı kullanım ve abonelik olmadan tek seferlik ödeme.",
           "h1": "iPhone uygulaması seçme rehberleri", "all": "Tüm yanıt rehberleri",
           "lead": "Bir uygulamayı yüklemeden önce gerçek sorular için kısa ve dürüst rehberler."},
    "it": {"lang": "it", "title": "Guide alla scelta delle app per iPhone — Risposte oneste",
           "desc": "Guide oneste per scegliere le app per iPhone: privacy, uso offline e pagamento una tantum senza abbonamento.",
           "h1": "Guide alla scelta delle app per iPhone", "all": "Tutte le guide con risposte",
           "lead": "Guide brevi e oneste per le domande reali prima di installare un'app."},
    "pl": {"lang": "pl", "title": "Poradniki wyboru aplikacji na iPhone'a — Szczere odpowiedzi",
           "desc": "Szczere poradniki wyboru aplikacji na iPhone'a: prywatność, praca offline i jednorazowa płatność bez subskrypcji.",
           "h1": "Poradniki wyboru aplikacji na iPhone'a", "all": "Wszystkie poradniki z odpowiedziami",
           "lead": "Krótkie i szczere poradniki na realne pytania, zanim zainstalujesz aplikację."},
    "hi": {"lang": "hi", "title": "iPhone ऐप चुनने की गाइड — ईमानदार जवाब",
           "desc": "iPhone ऐप चुनने की ईमानदार गाइड: प्राइवेसी, ऑफ़लाइन उपयोग और बिना सब्सक्रिप्शन एक बार भुगतान।",
           "h1": "iPhone ऐप चुनने की गाइड", "all": "सभी उत्तर गाइड",
           "lead": "कोई ऐप इंस्टॉल करने से पहले असली सवालों के लिए छोटी और ईमानदार गाइड।"},
    "ar-SA": {"lang": "ar", "title": "أدلة اختيار تطبيقات iPhone — إجابات صادقة",
           "desc": "أدلة صادقة لاختيار تطبيقات iPhone: الخصوصية والاستخدام دون اتصال والدفع مرة واحدة بدون اشتراك.",
           "h1": "أدلة اختيار تطبيقات iPhone", "all": "كل أدلة الإجابات",
           "lead": "أدلة قصيرة وصادقة للأسئلة الحقيقية قبل تثبيت أي تطبيق."},
    "pt-PT": {"lang": "pt", "title": "Guias para escolher apps de iPhone — Respostas honestas",
           "desc": "Guias honestos para escolher apps de iPhone: privacidade, uso offline e pagamento único sem subscrição.",
           "h1": "Guias para escolher apps de iPhone", "all": "Todos os guias de respostas",
           "lead": "Guias curtos e honestos para as perguntas reais antes de instalar uma app."},
    "ru": {"lang": "ru", "title": "Гиды по выбору приложений для iPhone — честные ответы",
           "desc": "Честные гиды по выбору приложений для iPhone: приватность, работа офлайн и разовая оплата без подписки.",
           "h1": "Гиды по выбору приложений для iPhone", "all": "Все гиды с ответами",
           "lead": "Короткие и честные гиды на реальные вопросы перед установкой приложения."},
    "uk": {"lang": "uk", "title": "Гіди з вибору застосунків для iPhone — чесні відповіді",
           "desc": "Чесні гіди з вибору застосунків для iPhone: приватність, робота офлайн і разова оплата без підписки.",
           "h1": "Гіди з вибору застосунків для iPhone", "all": "Усі гіди з відповідями",
           "lead": "Короткі та чесні гіди на реальні запитання перед встановленням застосунку."},
    "sv": {"lang": "sv", "title": "Guider för att välja iPhone-appar — ärliga svar",
           "desc": "Ärliga guider för att välja iPhone-appar: integritet, offlineanvändning och engångsbetalning utan prenumeration.",
           "h1": "Guider för att välja iPhone-appar", "all": "Alla svarsguider",
           "lead": "Korta och ärliga guider för de verkliga frågorna innan du installerar en app."},
    "nl-NL": {"lang": "nl", "title": "Gidsen om iPhone-apps te kiezen — eerlijke antwoorden",
           "desc": "Eerlijke gidsen om iPhone-apps te kiezen: privacy, offline gebruik en eenmalige betaling zonder abonnement.",
           "h1": "Gidsen om iPhone-apps te kiezen", "all": "Alle antwoordgidsen",
           "lead": "Korte en eerlijke gidsen voor de echte vragen voordat je een app installeert."},
    "en-US": {"lang": "en", "title": "iPhone App Choosing Guides — Honest Answers",
           "desc": "Honest guides to choosing iPhone apps: privacy, offline use, and pay-once with no subscription.",
           "h1": "iPhone app choosing guides", "all": "All answer guides",
           "lead": "Short, honest guides to the real questions before you install an app."},
    "en-GB": {"lang": "en", "title": "iPhone App Choosing Guides — Honest Answers",
           "desc": "Honest guides to choosing iPhone apps: privacy, offline use, and pay-once with no subscription.",
           "h1": "iPhone app choosing guides", "all": "All answer guides",
           "lead": "Short, honest guides to the real questions before you install an app."},
    "en-CA": {"lang": "en", "title": "iPhone App Choosing Guides — Honest Answers",
           "desc": "Honest guides to choosing iPhone apps: privacy, offline use, and pay-once with no subscription.",
           "h1": "iPhone app choosing guides", "all": "All answer guides",
           "lead": "Short, honest guides to the real questions before you install an app."},
    "en-AU": {"lang": "en", "title": "iPhone App Choosing Guides — Honest Answers",
           "desc": "Honest guides to choosing iPhone apps: privacy, offline use, and pay-once with no subscription.",
           "h1": "iPhone app choosing guides", "all": "All answer guides",
           "lead": "Short, honest guides to the real questions before you install an app."},
    "es-MX": {"lang": "es", "title": "Guías para elegir apps de iPhone — Respuestas honestas",
           "desc": "Guías honestas para elegir apps de iPhone: privacidad, uso sin conexión y pago único sin suscripción.",
           "h1": "Guías para elegir apps de iPhone", "all": "Todas las guías de respuestas",
           "lead": "Guías breves y honestas para las preguntas reales antes de instalar una app."},
    "fr-CA": {"lang": "fr", "title": "Guides pour choisir des applis iPhone — Réponses honnêtes",
           "desc": "Guides honnêtes pour choisir des applis iPhone : confidentialité, usage hors ligne et paiement unique sans abonnement.",
           "h1": "Guides pour choisir des applis iPhone", "all": "Tous les guides de réponses",
           "lead": "Des guides courts et honnêtes pour les vraies questions avant d'installer une appli."},
    "ca": {"lang": "ca", "title": "Guies per triar apps d'iPhone — Respostes honestes",
           "desc": "Guies honestes per triar apps d'iPhone: privadesa, ús sense connexió i pagament únic sense subscripció.",
           "h1": "Guies per triar apps d'iPhone", "all": "Totes les guies de respostes",
           "lead": "Guies breus i honestes per a les preguntes reals abans d'instal·lar una app."},
    "cs": {"lang": "cs", "title": "Průvodci výběrem aplikací pro iPhone — upřímné odpovědi",
           "desc": "Upřímní průvodci výběrem aplikací pro iPhone: soukromí, offline použití a jednorázová platba bez předplatného.",
           "h1": "Průvodci výběrem aplikací pro iPhone", "all": "Všichni průvodci s odpověďmi",
           "lead": "Krátcí a upřímní průvodci pro skutečné otázky, než si nainstalujete aplikaci."},
    "da": {"lang": "da", "title": "Guides til at vælge iPhone-apps — ærlige svar",
           "desc": "Ærlige guides til at vælge iPhone-apps: privatliv, offline-brug og engangsbetaling uden abonnement.",
           "h1": "Guides til at vælge iPhone-apps", "all": "Alle svarguides",
           "lead": "Korte og ærlige guides til de rigtige spørgsmål, før du installerer en app."},
    "el": {"lang": "el", "title": "Οδηγοί επιλογής εφαρμογών iPhone — Ειλικρινείς απαντήσεις",
           "desc": "Ειλικρινείς οδηγοί για την επιλογή εφαρμογών iPhone: ιδιωτικότητα, χρήση εκτός σύνδεσης και εφάπαξ πληρωμή χωρίς συνδρομή.",
           "h1": "Οδηγοί επιλογής εφαρμογών iPhone", "all": "Όλοι οι οδηγοί απαντήσεων",
           "lead": "Σύντομοι και ειλικρινείς οδηγοί για τις πραγματικές ερωτήσεις πριν εγκαταστήσετε μια εφαρμογή."},
    "fi": {"lang": "fi", "title": "Oppaat iPhone-sovellusten valintaan — rehellisiä vastauksia",
           "desc": "Rehelliset oppaat iPhone-sovellusten valintaan: yksityisyys, offline-käyttö ja kertamaksu ilman tilausta.",
           "h1": "Oppaat iPhone-sovellusten valintaan", "all": "Kaikki vastausoppaat",
           "lead": "Lyhyitä ja rehellisiä oppaita todellisiin kysymyksiin ennen sovelluksen asentamista."},
    "he": {"lang": "he", "title": "מדריכים לבחירת אפליקציות iPhone — תשובות כנות",
           "desc": "מדריכים כנים לבחירת אפליקציות iPhone: פרטיות, שימוש לא מקוון ותשלום חד-פעמי ללא מנוי.",
           "h1": "מדריכים לבחירת אפליקציות iPhone", "all": "כל מדריכי התשובות",
           "lead": "מדריכים קצרים וכנים לשאלות האמיתיות לפני שמתקינים אפליקציה."},
    "hr": {"lang": "hr", "title": "Vodiči za odabir iPhone aplikacija — iskreni odgovori",
           "desc": "Iskreni vodiči za odabir iPhone aplikacija: privatnost, offline uporaba i jednokratno plaćanje bez pretplate.",
           "h1": "Vodiči za odabir iPhone aplikacija", "all": "Svi vodiči s odgovorima",
           "lead": "Kratki i iskreni vodiči za prava pitanja prije instaliranja aplikacije."},
    "hu": {"lang": "hu", "title": "Útmutatók iPhone-alkalmazások kiválasztásához — őszinte válaszok",
           "desc": "Őszinte útmutatók iPhone-alkalmazások kiválasztásához: adatvédelem, offline használat és egyszeri fizetés előfizetés nélkül.",
           "h1": "Útmutatók iPhone-alkalmazások kiválasztásához", "all": "Minden válaszútmutató",
           "lead": "Rövid és őszinte útmutatók a valódi kérdésekhez, mielőtt telepítenél egy alkalmazást."},
    "no": {"lang": "no", "title": "Guider for å velge iPhone-apper — ærlige svar",
           "desc": "Ærlige guider for å velge iPhone-apper: personvern, offline-bruk og engangsbetaling uten abonnement.",
           "h1": "Guider for å velge iPhone-apper", "all": "Alle svarguider",
           "lead": "Korte og ærlige guider til de virkelige spørsmålene før du installerer en app."},
    "ro": {"lang": "ro", "title": "Ghiduri pentru alegerea aplicațiilor iPhone — răspunsuri oneste",
           "desc": "Ghiduri oneste pentru alegerea aplicațiilor iPhone: confidențialitate, utilizare offline și plată unică fără abonament.",
           "h1": "Ghiduri pentru alegerea aplicațiilor iPhone", "all": "Toate ghidurile cu răspunsuri",
           "lead": "Ghiduri scurte și oneste pentru întrebările reale înainte de a instala o aplicație."},
    "sk": {"lang": "sk", "title": "Sprievodcovia výberom aplikácií pre iPhone — úprimné odpovede",
           "desc": "Úprimní sprievodcovia výberom aplikácií pre iPhone: súkromie, offline použitie a jednorazová platba bez predplatného.",
           "h1": "Sprievodcovia výberom aplikácií pre iPhone", "all": "Všetci sprievodcovia s odpoveďami",
           "lead": "Krátki a úprimní sprievodcovia pre skutočné otázky pred inštaláciou aplikácie."},
    "sl-SI": {"lang": "sl", "title": "Vodniki za izbiro iPhone aplikacij — iskreni odgovori",
           "desc": "Iskreni vodniki za izbiro iPhone aplikacij: zasebnost, uporaba brez povezave in enkratno plačilo brez naročnine.",
           "h1": "Vodniki za izbiro iPhone aplikacij", "all": "Vsi vodniki z odgovori",
           "lead": "Kratki in iskreni vodniki za prava vprašanja, preden namestite aplikacijo."},
    "bn-BD": {"lang": "bn", "title": "iPhone অ্যাপ বেছে নেওয়ার গাইড — সৎ উত্তর",
           "desc": "iPhone অ্যাপ বেছে নেওয়ার সৎ গাইড: গোপনীয়তা, অফলাইন ব্যবহার এবং সাবস্ক্রিপশন ছাড়া একবার পেমেন্ট।",
           "h1": "iPhone অ্যাপ বেছে নেওয়ার গাইড", "all": "সব উত্তর গাইড",
           "lead": "অ্যাপ ইনস্টল করার আগে আসল প্রশ্নের সংক্ষিপ্ত ও সৎ গাইড।"},
    "gu-IN": {"lang": "gu", "title": "iPhone ઍપ પસંદ કરવાની ગાઈડ — પ્રામાણિક જવાબો",
           "desc": "iPhone ઍપ પસંદ કરવાની પ્રામાણિક ગાઈડ: ગોપનીયતા, ઑફલાઇન ઉપયોગ અને સબ્સ્ક્રિપ્શન વગર એક વાર ચુકવણી.",
           "h1": "iPhone ઍપ પસંદ કરવાની ગાઈડ", "all": "બધી જવાબ ગાઈડ",
           "lead": "ઍપ ઇન્સ્ટૉલ કરતાં પહેલાં સાચા પ્રશ્નો માટે ટૂંકી અને પ્રામાણિક ગાઈડ."},
    "kn-IN": {"lang": "kn", "title": "iPhone ಆ್ಯಪ್ ಆಯ್ಕೆ ಮಾರ್ಗದರ್ಶಿಗಳು — ಪ್ರಾಮಾಣಿಕ ಉತ್ತರಗಳು",
           "desc": "iPhone ಆ್ಯಪ್ ಆಯ್ಕೆಗೆ ಪ್ರಾಮಾಣಿಕ ಮಾರ್ಗದರ್ಶಿಗಳು: ಗೌಪ್ಯತೆ, ಆಫ್‌ಲೈನ್ ಬಳಕೆ ಮತ್ತು ಚಂದಾ ಇಲ್ಲದೆ ಒಮ್ಮೆ ಪಾವತಿ.",
           "h1": "iPhone ಆ್ಯಪ್ ಆಯ್ಕೆ ಮಾರ್ಗದರ್ಶಿಗಳು", "all": "ಎಲ್ಲಾ ಉತ್ತರ ಮಾರ್ಗದರ್ಶಿಗಳು",
           "lead": "ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡುವ ಮೊದಲು ನಿಜವಾದ ಪ್ರಶ್ನೆಗಳಿಗೆ ಚಿಕ್ಕ ಮತ್ತು ಪ್ರಾಮಾಣಿಕ ಮಾರ್ಗದರ್ಶಿಗಳು."},
    "ml-IN": {"lang": "ml", "title": "iPhone ആപ്പ് തിരഞ്ഞെടുക്കൽ ഗൈഡുകൾ — സത്യസന്ധമായ ഉത്തരങ്ങൾ",
           "desc": "iPhone ആപ്പ് തിരഞ്ഞെടുക്കാൻ സത്യസന്ധമായ ഗൈഡുകൾ: സ്വകാര്യത, ഓഫ്‌ലൈൻ ഉപയോഗം, സബ്‌സ്‌ക്രിപ്ഷൻ ഇല്ലാതെ ഒറ്റത്തവണ പേയ്‌മെന്റ്.",
           "h1": "iPhone ആപ്പ് തിരഞ്ഞെടുക്കൽ ഗൈഡുകൾ", "all": "എല്ലാ ഉത്തര ഗൈഡുകളും",
           "lead": "ഒരു ആപ്പ് ഇൻസ്റ്റാൾ ചെയ്യുന്നതിന് മുമ്പ് യഥാർത്ഥ ചോദ്യങ്ങൾക്ക് ചെറുതും സത്യസന്ധവുമായ ഗൈഡുകൾ."},
    "mr-IN": {"lang": "mr", "title": "iPhone ॲप निवडण्याचे मार्गदर्शक — प्रामाणिक उत्तरे",
           "desc": "iPhone ॲप निवडण्यासाठी प्रामाणिक मार्गदर्शक: गोपनीयता, ऑफलाइन वापर आणि सदस्यत्वाशिवाय एकदाच पेमेंट.",
           "h1": "iPhone ॲप निवडण्याचे मार्गदर्शक", "all": "सर्व उत्तर मार्गदर्शक",
           "lead": "ॲप इंस्टॉल करण्यापूर्वी खऱ्या प्रश्नांसाठी छोटे आणि प्रामाणिक मार्गदर्शक."},
    "or-IN": {"lang": "or", "title": "iPhone ଆପ୍ ବାଛିବା ଗାଇଡ୍ — ସଚ୍ଚୋଟ ଉତ୍ତର",
           "desc": "iPhone ଆପ୍ ବାଛିବା ପାଇଁ ସଚ୍ଚୋଟ ଗାଇଡ୍: ଗୋପନୀୟତା, ଅଫଲାଇନ୍ ବ୍ୟବହାର ଓ ସବସ୍କ୍ରିପସନ୍ ବିନା ଥରେ ପେମେଣ୍ଟ।",
           "h1": "iPhone ଆପ୍ ବାଛିବା ଗାଇଡ୍", "all": "ସମସ୍ତ ଉତ୍ତର ଗାଇଡ୍",
           "lead": "ଆପ୍ ଇନଷ୍ଟଲ୍ କରିବା ପୂର୍ବରୁ ପ୍ରକୃତ ପ୍ରଶ୍ନ ପାଇଁ ଛୋଟ ଓ ସଚ୍ଚୋଟ ଗାଇଡ୍।"},
    "pa-IN": {"lang": "pa", "title": "iPhone ਐਪ ਚੁਣਨ ਦੀਆਂ ਗਾਈਡਾਂ — ਇਮਾਨਦਾਰ ਜਵਾਬ",
           "desc": "iPhone ਐਪ ਚੁਣਨ ਲਈ ਇਮਾਨਦਾਰ ਗਾਈਡਾਂ: ਪਰਦੇਦਾਰੀ, ਆਫਲਾਈਨ ਵਰਤੋਂ ਅਤੇ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਬਿਨਾਂ ਇੱਕ ਵਾਰ ਭੁਗਤਾਨ।",
           "h1": "iPhone ਐਪ ਚੁਣਨ ਦੀਆਂ ਗਾਈਡਾਂ", "all": "ਸਾਰੀਆਂ ਜਵਾਬ ਗਾਈਡਾਂ",
           "lead": "ਐਪ ਇੰਸਟਾਲ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਅਸਲੀ ਸਵਾਲਾਂ ਲਈ ਛੋਟੀਆਂ ਅਤੇ ਇਮਾਨਦਾਰ ਗਾਈਡਾਂ।"},
    "ta-IN": {"lang": "ta", "title": "iPhone ஆப்ஸ் தேர்வு வழிகாட்டிகள் — நேர்மையான பதில்கள்",
           "desc": "iPhone ஆப்ஸ் தேர்வுக்கு நேர்மையான வழிகாட்டிகள்: தனியுரிமை, ஆஃப்லைன் பயன்பாடு, சந்தா இல்லாமல் ஒருமுறை கட்டணம்.",
           "h1": "iPhone ஆப்ஸ் தேர்வு வழிகாட்டிகள்", "all": "அனைத்து பதில் வழிகாட்டிகள்",
           "lead": "ஒரு ஆப்பை நிறுவும் முன் உண்மையான கேள்விகளுக்கு சுருக்கமான, நேர்மையான வழிகாட்டிகள்."},
    "te-IN": {"lang": "te", "title": "iPhone యాప్ ఎంపిక గైడ్‌లు — నిజాయితీ సమాధానాలు",
           "desc": "iPhone యాప్ ఎంపికకు నిజాయితీ గైడ్‌లు: గోప్యత, ఆఫ్‌లైన్ వాడకం, సబ్‌స్క్రిప్షన్ లేకుండా ఒకసారి చెల్లింపు.",
           "h1": "iPhone యాప్ ఎంపిక గైడ్‌లు", "all": "అన్ని సమాధాన గైడ్‌లు",
           "lead": "యాప్ ఇన్‌స్టాల్ చేయడానికి ముందు నిజమైన ప్రశ్నలకు చిన్న, నిజాయితీ గైడ్‌లు."},
    "ur-PK": {"lang": "ur", "title": "iPhone ایپ منتخب کرنے کی گائیڈز — ایماندار جوابات",
           "desc": "iPhone ایپ منتخب کرنے کی ایماندار گائیڈز: پرائیویسی، آف لائن استعمال اور سبسکرپشن کے بغیر ایک بار ادائیگی۔",
           "h1": "iPhone ایپ منتخب کرنے کی گائیڈز", "all": "تمام جواب گائیڈز",
           "lead": "ایپ انسٹال کرنے سے پہلے حقیقی سوالات کے لیے مختصر اور ایماندار گائیڈز۔"},
}

CSS = ("body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
       "background:linear-gradient(180deg,#fff,#f7f7fb);color:#161622;line-height:1.6}a{color:#3840d0}"
       ".wrap{width:min(1040px,100% - 32px);margin:auto}.hero{padding:40px 0 10px}"
       ".eyebrow{color:#5b5ff2;font-weight:800;text-transform:uppercase;letter-spacing:.08em;font-size:.78rem}"
       "h1{font-size:clamp(1.8rem,5vw,3rem);line-height:1.06;margin:.2em 0}p.lead{font-size:1.12rem;color:#5d6370;max-width:780px}"
       "ul.list{list-style:none;padding:0;margin:18px 0 40px;columns:2;column-gap:26px}@media(max-width:640px){ul.list{columns:1}}"
       "ul.list li{break-inside:avoid;margin:.4em 0;padding:10px 12px;background:#fff;border:1px solid #e6e7ef;border-radius:12px}"
       ".footer{margin-top:24px;padding:24px 0;border-top:1px solid #e6e7ef;color:#5d6370;font-size:.92rem}")


def page_title(p: Path) -> str:
    m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"), re.S)
    return html.unescape(m.group(1).strip()) if m else p.stem.replace("-", " ")


def build_hub(lang: str) -> int:
    d = PAGES / lang / "answers"
    files = sorted(f for f in d.glob("*.html") if f.name != "index.html")
    if not files:
        return 0
    t = L10N.get(lang)
    if not t:
        return 0
    canon = f"{SITE}/{lang}/answers/index.html"
    en_canon = f"{SITE}/answers/index.html"
    items, li = [], []
    for i, f in enumerate(files, 1):
        title = page_title(f)
        url = f"{SITE}/{lang}/answers/{f.name}"
        li.append(f'<li><a href="{html.escape(url)}">{html.escape(title)}</a></li>')
        items.append({"@type": "ListItem", "position": i, "url": url, "name": title})
    itemlist = {"@context": "https://schema.org", "@type": "ItemList",
                "name": t["title"], "numberOfItems": len(files), "itemListElement": items}
    _dir = ' dir="rtl"' if t["lang"] in ("ar", "he", "fa", "ur") else ""
    doc = (f'<!DOCTYPE html><html lang="{t["lang"]}"{_dir}><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>{html.escape(t["title"])}</title>'
           f'<meta name="description" content="{html.escape(t["desc"])}">'
           f'<link rel="canonical" href="{canon}">'
           f'<link rel="alternate" hreflang="en" href="{en_canon}">'
           f'<link rel="alternate" hreflang="{t["lang"]}" href="{canon}">'
           f'<link rel="alternate" hreflang="x-default" href="{en_canon}">'
           f'<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(t["title"])}">'
           f'<meta property="og:url" content="{canon}">'
           f'<style>{CSS}</style>'
           f'<script type="application/ld+json">{json.dumps(itemlist, ensure_ascii=False)}</script>'
           f'</head><body><div class="wrap">'
           f'<div class="hero"><div class="eyebrow">iOS App Guide</div>'
           f'<h1>{html.escape(t["h1"])}</h1><p class="lead">{html.escape(t["lead"])}</p></div>'
           f'<h2>{html.escape(t["all"])} ({len(files)})</h2>'
           f'<ul class="list">{"".join(li)}</ul>'
           f'<div class="footer">{html.escape(t["desc"])}</div>'
           f'</div></body></html>')
    (d / "index.html").write_text(doc, encoding="utf-8")
    return len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", help="逗號分隔;預設所有有答案頁的支援語言")
    a = ap.parse_args()
    langs = a.langs.split(",") if a.langs else list(L10N)
    total = 0
    for lang in langs:
        n = build_hub(lang)
        if n:
            print(f"hub {lang}/answers/index.html — {n} 頁", flush=True)
            total += 1
    print(json.dumps({"hubs": total}, ensure_ascii=False), flush=True)
    # 刷新 answers sitemap 以納入新 hub
    try:
        sys.path.insert(0, str(HERE))
        import aeo_answers
        aeo_answers.write_sitemap()
    except Exception as exc:
        print(f"sitemap refresh skipped: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
