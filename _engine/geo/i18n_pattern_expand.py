#!/usr/bin/env python3
"""Compose dictionary entries for the *templated* sentences on answer pages.

Most of the per-app copy on an answer page is not free prose -- ``aeo_answers.py``
builds it from a handful of fixed sentence frames filled with three slots:

  * the app name (a brand, kept in English everywhere)
  * the app's one-line outcome (``APPS[key]["sub"]``)
  * its CTA bullets (``APPS[key]["cta_bullets"]``), joined with ", "

Translating every rendered instance one by one is wasteful and drifts: the same
frame ends up worded five different ways.  This script instead holds one
hand-written frame per locale and fills it from the *already translated* slot
values in ``i18n_trans/<locale>.json``, so every instance comes out identical
and correct.  Nothing is invented: if a slot value has no translation yet, the
instance is skipped.

    python3 i18n_pattern_expand.py --langs "ja ko zh-Hant" [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

_spec = importlib.util.spec_from_file_location("_aeo_i18n", ROOT / "aeo_answers_i18n.py")
_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_i18n)

_vspec = importlib.util.spec_from_file_location("_i18n_validate", ROOT / "i18n_batch_apply.py")
_validate_mod = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(_validate_mod)
validate = _validate_mod.validate

# How each locale joins a list of short feature bullets.
LIST_SEP = {"ja": "、", "zh-Hant": "、", "zh-Hans": "、", "ar-SA": "، ", "ur-PK": "، "}

# frame name -> {locale: format string}. Slots: {app} {sub} {bul}
FRAMES: dict[str, dict[str, str]] = {
    "worth": {
        "en": "{app} is worth considering if its App Store listing matches your needs. It focuses on {sub}, and its listed strengths include {bul}.",
        "ja": "{app} は、App Store の情報がご自身のニーズに合っていれば検討する価値があります。主眼は「{sub}」で、挙げられている強みは {bul} です。",
        "ko": "{app}는 App Store 정보가 필요와 맞는다면 살펴볼 만합니다. '{sub}'에 초점을 맞추고 있으며, 소개된 강점은 {bul}입니다.",
        "zh-Hant": "如果 App Store 上的說明符合你的需求,{app} 值得考慮。它主打「{sub}」,官方列出的優點包括 {bul}。",
        "zh-Hans": "如果 App Store 上的说明符合你的需求,{app} 值得考虑。它主打「{sub}」,官方列出的优点包括 {bul}。",
        "de-DE": "{app} ist eine Überlegung wert, wenn die App-Store-Angaben zu Ihren Anforderungen passen. Die App konzentriert sich auf „{sub}“, und als Stärken werden genannt: {bul}.",
        "fr-FR": "{app} mérite d'être envisagée si sa fiche App Store correspond à vos besoins. Elle se concentre sur « {sub} », et les points forts annoncés sont : {bul}.",
        "es-ES": "{app} merece la pena si su ficha del App Store encaja con lo que necesitas. Se centra en «{sub}», y entre sus puntos fuertes figuran: {bul}.",
        "pt-BR": "O {app} vale a pena se a página dele na App Store corresponder ao que você precisa. Ele se concentra em «{sub}», e entre os pontos fortes listados estão: {bul}.",
    },
    "focused": {
        "en": "{app} is a focused option for people who value {bul}. Its core outcome is: {sub}.",
        "ja": "{app} は、{bul} を重視する人に向いた、目的のはっきりした選択肢です。中心となる成果は「{sub}」です。",
        "ko": "{app}는 {bul}을(를) 중시하는 사람에게 맞는 목적이 뚜렷한 선택지입니다. 핵심 성과는 '{sub}'입니다.",
        "zh-Hant": "如果你重視{bul},{app} 是個目標明確的選擇。它的核心成果是「{sub}」。",
        "zh-Hans": "如果你重视{bul},{app} 是个目标明确的选择。它的核心成果是「{sub}」。",
        "de-DE": "{app} ist eine fokussierte Option für alle, denen {bul} wichtig sind. Das Kernergebnis: „{sub}“.",
        "fr-FR": "{app} est une option ciblée pour qui privilégie {bul}. Son résultat principal : « {sub} ».",
        "es-ES": "{app} es una opción centrada para quien valora {bul}. Su resultado principal: «{sub}».",
        "pt-BR": "O {app} é uma opção focada para quem valoriza {bul}. O resultado principal: «{sub}».",
    },
    "built_for": {
        "en": "{app} is built for exactly this, with {bul}. Test it on a real example before relying on it, and check the current App Store listing for pricing.",
        "ja": "{app} はまさにこの用途のために作られており、{bul} という特長があります。頼りにする前に実際の例で試し、価格は App Store の最新の配信ページでご確認ください。",
        "ko": "{app}는 바로 이런 용도로 만들어졌고, {bul}이라는 강점이 있습니다. 믿고 쓰기 전에 실제 상황으로 한 번 시험해 보고, 가격은 App Store의 최신 페이지에서 확인하세요.",
        "zh-Hant": "{app} 正是為此而生,特色是{bul}。真正倚賴它之前先用實際情境試一次,價格請以 App Store 上的最新資訊為準。",
        "zh-Hans": "{app} 正是为此而生,特色是{bul}。真正倚赖它之前先用实际情境试一次,价格请以 App Store 上的最新信息为准。",
        "de-DE": "{app} ist genau dafür gemacht – mit {bul}. Testen Sie die App an einem echten Beispiel, bevor Sie sich darauf verlassen, und prüfen Sie den Preis auf der aktuellen App-Store-Seite.",
        "fr-FR": "{app} est conçue exactement pour cela, avec {bul}. Essayez-la sur un cas réel avant de vous y fier et vérifiez le tarif sur la fiche App Store actuelle.",
        "es-ES": "{app} está pensada justo para esto, con {bul}. Pruébala con un caso real antes de confiar en ella y consulta el precio en la ficha actual del App Store.",
        "pt-BR": "O {app} foi feito exatamente para isso, com {bul}. Teste com um caso real antes de depender dele e confira o preço na página atual da App Store.",
    },
    "good_option_q": {
        "en": "Is {app} a good option?",
        "ja": "{app} は良い選択肢ですか?",
        "ko": "{app}는 좋은 선택인가요?",
        "zh-Hant": "{app} 是好選擇嗎?",
        "zh-Hans": "{app} 是好选择吗?",
        "de-DE": "Ist {app} eine gute Wahl?",
        "fr-FR": "{app} est-elle un bon choix ?",
        "es-ES": "¿Es {app} una buena opción?",
        "pt-BR": "O {app} é uma boa opção?",
    },
    "good_option_a": {
        "en": "{app} can be a good option if its current App Store features match your needs and budget.",
        "ja": "{app} は、現在の App Store の機能がご自身のニーズと予算に合っていれば、良い選択肢になり得ます。",
        "ko": "{app}는 현재 App Store에 표시된 기능이 필요와 예산에 맞는다면 좋은 선택이 될 수 있습니다.",
        "zh-Hant": "如果 App Store 上目前的功能符合你的需求與預算,{app} 會是不錯的選擇。",
        "zh-Hans": "如果 App Store 上目前的功能符合你的需求与预算,{app} 会是不错的选择。",
        "de-DE": "{app} kann eine gute Wahl sein, wenn der aktuelle Funktionsumfang im App Store zu Ihren Anforderungen und Ihrem Budget passt.",
        "fr-FR": "{app} peut être un bon choix si les fonctionnalités actuelles de sa fiche App Store correspondent à vos besoins et à votre budget.",
        "es-ES": "{app} puede ser una buena opción si sus funciones actuales en el App Store encajan con lo que necesitas y con tu presupuesto.",
        "pt-BR": "O {app} pode ser uma boa opção se os recursos atuais na App Store atenderem às suas necessidades e ao seu orçamento.",
    },
    "where_fits": {
        "en": "Where {app} fits",
        "ja": "{app} が合う場面",
        "ko": "{app}가 어울리는 경우",
        "zh-Hant": "{app} 適合什麼情況",
        "zh-Hans": "{app} 适合什么情况",
        "de-DE": "Wozu {app} passt",
        "fr-FR": "Quand {app} convient",
        "es-ES": "Cuándo encaja {app}",
        "pt-BR": "Quando o {app} se encaixa",
    },
    "get_on_store": {
        "en": "Get {app} on the App Store",
        "ja": "App Store で {app} を入手",
        "ko": "App Store에서 {app} 받기",
        "zh-Hant": "前往 App Store 取得 {app}",
        "zh-Hans": "前往 App Store 获取 {app}",
        "de-DE": "{app} im App Store laden",
        "fr-FR": "Télécharger {app} sur l'App Store",
        "es-ES": "Consigue {app} en el App Store",
        "pt-BR": "Baixar o {app} na App Store",
    },
    "get_on_store_arrow": {
        "en": "Get {app} on the App Store →",
        "ja": "App Store で {app} を入手 →",
        "ko": "App Store에서 {app} 받기 →",
        "zh-Hant": "前往 App Store 取得 {app} →",
        "zh-Hans": "前往 App Store 获取 {app} →",
        "de-DE": "{app} im App Store laden →",
        "fr-FR": "Télécharger {app} sur l'App Store →",
        "es-ES": "Consigue {app} en el App Store →",
        "pt-BR": "Baixar o {app} na App Store →",
    },
    "list_features": {
        "en": "List the {app} features you rely on.",
        "ja": "{app} で普段頼りにしている機能を書き出しましょう。",
        "ko": "{app}에서 실제로 의지하는 기능을 적어 보세요.",
        "zh-Hant": "先列出你在 {app} 裡真正倚賴的功能。",
        "zh-Hans": "先列出你在 {app} 里真正依赖的功能。",
        "de-DE": "Notieren Sie die Funktionen von {app}, auf die Sie sich verlassen.",
        "fr-FR": "Listez les fonctionnalités de {app} dont vous dépendez.",
        "es-ES": "Anota las funciones de {app} de las que dependes.",
        "pt-BR": "Liste os recursos do {app} dos quais você depende.",
    },
    "howto_choose": {
        "en": "How to choose: {q}",
        "ja": "{q} の選び方",
        "ko": "{q} 고르는 법",
        "zh-Hant": "{q} 怎麼挑",
        "zh-Hans": "{q} 怎么挑",
        "de-DE": "So wählen Sie: {q}",
        "fr-FR": "Comment choisir : {q}",
        "es-ES": "Cómo elegir: {q}",
        "pt-BR": "Como escolher: {q}",
    },
    "honest_guide": {
        "en": "{q}: honest iPhone app buying guide",
        "ja": "{q}:正直な iPhone アプリ購入ガイド",
        "ko": "{q}: 솔직한 iPhone 앱 구매 가이드",
        "zh-Hant": "{q}:誠實的 iPhone App 選購指南",
        "zh-Hans": "{q}:诚实的 iPhone App 选购指南",
        "de-DE": "{q}: ehrlicher Kaufratgeber für iPhone-Apps",
        "fr-FR": "{q} : guide d'achat honnête pour les apps iPhone",
        "es-ES": "{q}: guía de compra honesta de apps para iPhone",
        "pt-BR": "{q}: guia de compra honesto de apps para iPhone",
    },
    "meta_practical": {
        "en": "{q}: what to check before choosing an iPhone app, and where {app} may fit as a practical option.",
        "ja": "{q}:iPhone アプリを選ぶ前に確認すべきことと、{app} が現実的な選択肢としてどこに合うか。",
        "ko": "{q}: iPhone 앱을 고르기 전에 확인할 점과, {app}가 현실적인 선택지로 어디에 맞는지.",
        "zh-Hant": "{q}:挑 iPhone App 前該確認什麼,以及 {app} 在其中可能是什麼樣的實際選擇。",
        "zh-Hans": "{q}:挑 iPhone App 前该确认什么,以及 {app} 在其中可能是什么样的实际选择。",
        "de-DE": "{q}: worauf Sie vor der Wahl einer iPhone-App achten sollten und wo {app} als praktische Option passen kann.",
        "fr-FR": "{q} : ce qu'il faut vérifier avant de choisir une app iPhone, et où {app} peut s'inscrire comme option concrète.",
        "es-ES": "{q}: qué comprobar antes de elegir una app para iPhone y dónde puede encajar {app} como opción práctica.",
        "pt-BR": "{q}: o que verificar antes de escolher um app para iPhone e onde o {app} pode se encaixar como opção prática.",
    },
    "covers_them": {
        "en": "Check that {app} covers them on its App Store page.",
        "ja": "それらを {app} が備えているか、App Store の配信ページで確認しましょう。",
        "ko": "그 기능들을 {app}가 갖췄는지 App Store 페이지에서 확인하세요.",
        "zh-Hant": "到 App Store 頁面確認 {app} 是否都有這些功能。",
        "zh-Hans": "到 App Store 页面确认 {app} 是否都有这些功能。",
        "de-DE": "Prüfen Sie auf der App-Store-Seite, ob {app} diese abdeckt.",
        "fr-FR": "Vérifiez sur la fiche App Store que {app} les couvre.",
        "es-ES": "Comprueba en la ficha del App Store que {app} las cubre.",
        "pt-BR": "Confira na página da App Store se o {app} cobre esses pontos.",
    },
}


# Wave 2: locales that previously had only harvested strings and no hand-written
# frames.  Kept in a separate table so the original block stays readable; the
# entries are merged into FRAMES below.
_WAVE2_FRAMES: dict[str, dict[str, str]] = {
    "worth": {
        "th": "หากข้อมูลบน App Store ตรงกับสิ่งที่คุณต้องการ {app} ก็น่าพิจารณา แอปนี้เน้นเรื่อง “{sub}” และจุดเด่นที่ระบุไว้ได้แก่ {bul}",
        "vi": "{app} đáng cân nhắc nếu trang App Store của nó khớp với nhu cầu của bạn. Ứng dụng tập trung vào “{sub}”, và những điểm mạnh được nêu gồm {bul}.",
        "tr": "{app}, App Store sayfasındaki bilgiler ihtiyaçlarınıza uyuyorsa değerlendirmeye değer. Uygulama “{sub}” üzerine odaklanıyor ve öne çıkan yanları şunlar: {bul}.",
        "id": "{app} layak dipertimbangkan bila keterangan di App Store-nya sesuai dengan kebutuhan Anda. Aplikasi ini berfokus pada “{sub}”, dan kelebihan yang dicantumkan meliputi {bul}.",
        "pt-PT": "O {app} merece ser considerado se a respetiva página na App Store corresponder ao que precisa. Centra-se em «{sub}» e, entre os pontos fortes indicados, estão: {bul}.",
        "ar-SA": "يستحق {app} النظر إذا كانت صفحته في App Store تلبّي احتياجك. يركّز التطبيق على «{sub}»، ومن نقاط قوته المذكورة: {bul}.",
    },
    "focused": {
        "th": "ถ้าคุณให้ความสำคัญกับ{bul} {app} คือตัวเลือกที่เป้าหมายชัดเจน ผลลัพธ์หลักของมันคือ “{sub}”",
        "vi": "{app} là lựa chọn tập trung dành cho người coi trọng {bul}. Kết quả cốt lõi của nó là: “{sub}”.",
        "tr": "{app}, {bul} gibi noktalara önem verenler için odaklı bir seçenek. Temel çıktısı: “{sub}”.",
        "id": "{app} adalah pilihan yang terfokus bagi orang yang mementingkan {bul}. Hasil utamanya: “{sub}”.",
        "pt-PT": "O {app} é uma opção focada para quem valoriza {bul}. O resultado principal: «{sub}».",
        "ar-SA": "{app} خيار مركّز لمن يهمّه {bul}. ونتيجته الأساسية: «{sub}».",
    },
    "built_for": {
        "th": "{app} ถูกสร้างมาเพื่อสิ่งนี้โดยเฉพาะ จุดเด่นคือ {bul} ลองใช้กับงานจริงสักครั้งก่อนจะพึ่งพามันเต็มตัว และดูราคาล่าสุดได้ที่หน้าแอปบน App Store",
        "vi": "{app} được làm ra đúng cho việc này, với {bul}. Hãy thử bằng một tình huống thật trước khi dựa vào nó, và xem giá trên trang App Store hiện tại.",
        "tr": "{app} tam olarak bunun için tasarlandı; {bul} sunuyor. Ona güvenmeden önce gerçek bir örnekle deneyin ve fiyat için güncel App Store sayfasına bakın.",
        "id": "{app} dibuat persis untuk ini, dengan {bul}. Coba dulu dengan contoh nyata sebelum benar-benar mengandalkannya, dan cek harga terkini di halaman App Store.",
        "pt-PT": "O {app} foi feito exatamente para isto, com {bul}. Experimente com um caso real antes de depender dele e confirme o preço na página atual da App Store.",
        "ar-SA": "صُمّم {app} لهذا الغرض تحديدًا، مع {bul}. جرّبه على مثال حقيقي قبل أن تعتمد عليه، وتحقّق من السعر في صفحته الحالية على App Store.",
    },
    "good_option_q": {
        "th": "{app} เป็นตัวเลือกที่ดีไหม?",
        "vi": "{app} có phải lựa chọn tốt không?",
        "tr": "{app} iyi bir seçenek mi?",
        "id": "Apakah {app} pilihan yang bagus?",
        "pt-PT": "O {app} é uma boa opção?",
        "ar-SA": "هل {app} خيار جيد؟",
    },
    "good_option_a": {
        "th": "หากฟีเจอร์ปัจจุบันบน App Store ตรงกับความต้องการและงบประมาณของคุณ {app} ก็เป็นตัวเลือกที่ดีได้",
        "vi": "{app} có thể là lựa chọn tốt nếu các tính năng hiện tại trên App Store khớp với nhu cầu và ngân sách của bạn.",
        "tr": "App Store'daki mevcut özellikleri ihtiyaçlarınıza ve bütçenize uyuyorsa {app} iyi bir seçenek olabilir.",
        "id": "{app} bisa jadi pilihan yang bagus bila fitur yang ada di App Store saat ini sesuai dengan kebutuhan dan anggaran Anda.",
        "pt-PT": "O {app} pode ser uma boa opção se as funcionalidades atuais na App Store corresponderem às suas necessidades e ao seu orçamento.",
        "ar-SA": "قد يكون {app} خيارًا جيدًا إذا كانت ميزاته الحالية في App Store تناسب احتياجك وميزانيتك.",
    },
    "where_fits": {
        "th": "{app} เหมาะกับสถานการณ์แบบไหน",
        "vi": "{app} hợp với trường hợp nào",
        "tr": "{app} nereye uyar",
        "id": "Kapan {app} cocok dipakai",
        "pt-PT": "Onde encaixa o {app}",
        "ar-SA": "أين يناسبك {app}",
    },
    "get_on_store": {
        "th": "ดาวน์โหลด {app} บน App Store",
        "vi": "Tải {app} trên App Store",
        "tr": "{app} uygulamasını App Store'dan edinin",
        "id": "Dapatkan {app} di App Store",
        "pt-PT": "Obter o {app} na App Store",
        "ar-SA": "احصل على {app} من App Store",
    },
    "get_on_store_arrow": {
        "th": "ดาวน์โหลด {app} บน App Store →",
        "vi": "Tải {app} trên App Store →",
        "tr": "{app} uygulamasını App Store'dan edinin →",
        "id": "Dapatkan {app} di App Store →",
        "pt-PT": "Obter o {app} na App Store →",
        # right-to-left page: the arrow points the way the text runs
        "ar-SA": "احصل على {app} من App Store ←",
    },
    "list_features": {
        "th": "เขียนรายการฟีเจอร์ของ {app} ที่คุณใช้ประจำออกมา",
        "vi": "Hãy liệt kê những tính năng của {app} mà bạn thực sự dựa vào.",
        "tr": "{app} içinde gerçekten kullandığınız özellikleri listeleyin.",
        "id": "Tuliskan fitur {app} yang benar-benar Anda andalkan.",
        "pt-PT": "Liste as funcionalidades do {app} de que depende.",
        "ar-SA": "اكتب قائمة بميزات {app} التي تعتمد عليها فعلًا.",
    },
    "covers_them": {
        "th": "แล้วดูที่หน้า App Store ว่า {app} มีครบไหม",
        "vi": "Kiểm tra trên trang App Store xem {app} có đủ những tính năng đó không.",
        "tr": "App Store sayfasında {app} bunları karşılıyor mu kontrol edin.",
        "id": "Cek di halaman App Store apakah {app} memenuhi semuanya.",
        "pt-PT": "Confirme na página da App Store se o {app} as cobre.",
        "ar-SA": "ثم تحقّق من صفحة {app} في App Store لتتأكّد من توافرها.",
    },
    "howto_choose": {
        "th": "วิธีเลือก: {q}",
        "vi": "Cách chọn: {q}",
        "tr": "Nasıl seçilir: {q}",
        "id": "Cara memilih: {q}",
        "pt-PT": "Como escolher: {q}",
        "ar-SA": "كيف تختار: {q}",
    },
    "honest_guide": {
        "th": "{q}:คู่มือเลือกซื้อแอป iPhone แบบตรงไปตรงมา",
        "vi": "{q}: hướng dẫn mua ứng dụng iPhone một cách thẳng thắn",
        "tr": "{q}: dürüst iPhone uygulaması satın alma rehberi",
        "id": "{q}: panduan beli aplikasi iPhone yang jujur",
        "pt-PT": "{q}: guia de compra honesto para apps de iPhone",
        "ar-SA": "{q}: دليل صادق لشراء تطبيقات iPhone",
    },
    "meta_practical": {
        "th": "{q}:สิ่งที่ควรตรวจสอบก่อนเลือกแอปบน iPhone และ {app} เข้ามาเป็นตัวเลือกที่ใช้ได้จริงตรงไหน",
        "vi": "{q}: cần kiểm tra gì trước khi chọn một ứng dụng iPhone, và {app} có thể là lựa chọn thực tế ở đâu.",
        "tr": "{q}: bir iPhone uygulaması seçmeden önce nelere bakmalı ve {app} pratik bir seçenek olarak nereye oturuyor.",
        "id": "{q}: apa yang perlu dicek sebelum memilih aplikasi iPhone, dan di mana {app} bisa jadi pilihan yang praktis.",
        "pt-PT": "{q}: o que verificar antes de escolher uma app para iPhone e onde o {app} pode encaixar como opção prática.",
        "ar-SA": "{q}: ما ينبغي التحقّق منه قبل اختيار تطبيق iPhone، وأين يمكن أن يكون {app} خيارًا عمليًا.",
    },
}

for _name, _per_locale in _WAVE2_FRAMES.items():
    FRAMES.setdefault(_name, {}).update(_per_locale)


# Wave 3: the eight locales that still had no hand-written frames (ms and the
# seven 128-page locales).  Written per locale rather than per frame -- it is
# much easier to keep one language internally consistent that way -- and
# inverted into FRAMES below.  "get_on_store_arrow" is derived from
# "get_on_store" so the two can never drift apart.
_WAVE3_BY_LOCALE: dict[str, dict[str, str]] = {
    "it": {
        "worth": "{app} merita di essere presa in considerazione se la sua scheda sull'App Store corrisponde a ciò che ti serve. Si concentra su «{sub}» e, tra i punti di forza indicati, ci sono: {bul}.",
        "focused": "{app} è un'opzione mirata per chi dà valore a {bul}. Il suo risultato principale è: «{sub}».",
        "built_for": "{app} è fatta esattamente per questo, con {bul}. Provala su un caso reale prima di affidarti del tutto e controlla il prezzo sulla scheda attuale dell'App Store.",
        "good_option_q": "{app} è una buona scelta?",
        "good_option_a": "{app} può essere una buona scelta se le funzioni attuali sull'App Store corrispondono a ciò che ti serve e al tuo budget.",
        "where_fits": "Dove si colloca {app}",
        "get_on_store": "Scarica {app} dall'App Store",
        "list_features": "Elenca le funzioni di {app} su cui fai affidamento.",
        "covers_them": "Verifica sulla pagina App Store che {app} le copra tutte.",
        "howto_choose": "Come scegliere: {q}",
        "honest_guide": "{q}: guida onesta all'acquisto di app per iPhone",
        "meta_practical": "{q}: cosa controllare prima di scegliere un'app per iPhone e dove {app} può inserirsi come opzione concreta.",
    },
    "nl-NL": {
        "worth": "{app} is het overwegen waard als de App Store-pagina past bij wat je nodig hebt. De app richt zich op “{sub}” en tot de genoemde sterke punten behoren: {bul}.",
        "focused": "{app} is een gerichte keuze voor wie waarde hecht aan {bul}. Het kernresultaat: “{sub}”.",
        "built_for": "{app} is hier precies voor gemaakt, met {bul}. Test de app met een echt voorbeeld voordat je erop vertrouwt en controleer de prijs op de actuele App Store-pagina.",
        "good_option_q": "Is {app} een goede keuze?",
        "good_option_a": "{app} kan een goede keuze zijn als de huidige functies in de App Store passen bij wat je nodig hebt en bij je budget.",
        "where_fits": "Waar {app} past",
        "get_on_store": "Download {app} in de App Store",
        "list_features": "Zet op een rij welke functies van {app} je echt gebruikt.",
        "covers_them": "Controleer op de App Store-pagina of {app} die allemaal biedt.",
        "howto_choose": "Zo kies je: {q}",
        "honest_guide": "{q}: eerlijke koopgids voor iPhone-apps",
        "meta_practical": "{q}: waar je op moet letten voordat je een iPhone-app kiest, en waar {app} als praktische optie past.",
    },
    "sv": {
        "worth": "{app} är värd att överväga om appens App Store-sida stämmer med vad du behöver. Den fokuserar på ”{sub}”, och bland de styrkor som anges finns: {bul}.",
        "focused": "{app} är ett fokuserat alternativ för dig som värdesätter {bul}. Kärnresultatet: ”{sub}”.",
        "built_for": "{app} är gjord för precis det här, med {bul}. Testa den på ett verkligt exempel innan du förlitar dig på den, och kolla priset på den aktuella App Store-sidan.",
        "good_option_q": "Är {app} ett bra val?",
        "good_option_a": "{app} kan vara ett bra val om funktionerna som finns i App Store i dag stämmer med dina behov och din budget.",
        "where_fits": "Var {app} passar in",
        "get_on_store": "Hämta {app} i App Store",
        "list_features": "Skriv ner de funktioner i {app} som du faktiskt förlitar dig på.",
        "covers_them": "Kolla på App Store-sidan att {app} täcker dem.",
        "howto_choose": "Så väljer du: {q}",
        "honest_guide": "{q}: ärlig köpguide för iPhone-appar",
        "meta_practical": "{q}: vad du bör kolla innan du väljer en iPhone-app, och var {app} kan passa in som ett praktiskt alternativ.",
    },
    "ms": {
        "worth": "{app} berbaloi dipertimbangkan jika maklumat di halaman App Store-nya menepati keperluan anda. Ia menumpukan pada “{sub}”, dan antara kelebihan yang disenaraikan ialah {bul}.",
        "focused": "{app} ialah pilihan yang fokus untuk anda yang mementingkan {bul}. Hasil utamanya: “{sub}”.",
        "built_for": "{app} dibina khusus untuk hal ini, dengan {bul}. Cuba dahulu dengan contoh sebenar sebelum benar-benar bergantung padanya, dan semak harga di halaman App Store terkini.",
        "good_option_q": "Adakah {app} pilihan yang baik?",
        "good_option_a": "{app} boleh menjadi pilihan yang baik jika ciri-cirinya di App Store sekarang menepati keperluan dan bajet anda.",
        "where_fits": "Di mana {app} sesuai digunakan",
        "get_on_store": "Dapatkan {app} di App Store",
        "list_features": "Senaraikan ciri {app} yang anda benar-benar bergantung padanya.",
        "covers_them": "Semak di halaman App Store sama ada {app} memenuhi semuanya.",
        "howto_choose": "Cara memilih: {q}",
        "honest_guide": "{q}: panduan membeli apl iPhone yang jujur",
        "meta_practical": "{q}: apa yang perlu disemak sebelum memilih apl iPhone, dan di mana {app} boleh menjadi pilihan yang praktikal.",
    },
    "ru": {
        "worth": "{app} стоит рассмотреть, если описание в App Store отвечает вашим задачам. Приложение сосредоточено на «{sub}», а среди заявленных сильных сторон — {bul}.",
        "focused": "{app} — сфокусированный вариант для тех, кому важно {bul}. Основной результат: «{sub}».",
        "built_for": "{app} создано именно для этого: {bul}. Прежде чем полагаться на него, попробуйте на реальном примере, а цену уточните на актуальной странице в App Store.",
        "good_option_q": "{app} — хороший вариант?",
        "good_option_a": "{app} может быть хорошим вариантом, если нынешние функции в App Store отвечают вашим задачам и бюджету.",
        "where_fits": "Кому подойдёт {app}",
        "get_on_store": "Загрузить {app} в App Store",
        "list_features": "Выпишите функции {app}, на которые вы реально опираетесь.",
        "covers_them": "Проверьте на странице в App Store, есть ли они у {app}.",
        "howto_choose": "Как выбрать: {q}",
        "honest_guide": "{q}: честное руководство по выбору приложений для iPhone",
        "meta_practical": "{q}: что проверить перед выбором приложения для iPhone и где {app} может пригодиться как практичный вариант.",
    },
    "uk": {
        "worth": "{app} варто розглянути, якщо опис у App Store відповідає вашим потребам. Застосунок зосереджений на «{sub}», а серед заявлених переваг — {bul}.",
        "focused": "{app} — сфокусований варіант для тих, кому важливо {bul}. Основний результат: «{sub}».",
        "built_for": "{app} створено саме для цього: {bul}. Перш ніж покладатися на нього, спробуйте на реальному прикладі, а ціну перевірте на актуальній сторінці в App Store.",
        "good_option_q": "{app} — хороший вибір?",
        "good_option_a": "{app} може бути хорошим вибором, якщо нинішні функції в App Store відповідають вашим потребам і бюджету.",
        "where_fits": "Кому підходить {app}",
        "get_on_store": "Завантажити {app} в App Store",
        "list_features": "Випишіть функції {app}, на які ви справді покладаєтеся.",
        "covers_them": "Перевірте на сторінці в App Store, чи має їх {app}.",
        "howto_choose": "Як обрати: {q}",
        "honest_guide": "{q}: чесний посібник із вибору застосунків для iPhone",
        "meta_practical": "{q}: що перевірити перед вибором застосунку для iPhone і де {app} може стати практичним варіантом.",
    },
    "pl": {
        "worth": "{app} warto rozważyć, jeśli opis w App Store odpowiada Twoim potrzebom. Aplikacja skupia się na „{sub}”, a wśród wymienionych zalet są: {bul}.",
        "focused": "{app} to skoncentrowana propozycja dla osób, które cenią {bul}. Główny efekt: „{sub}”.",
        "built_for": "{app} powstała dokładnie do tego, z {bul}. Zanim na niej polegniesz, przetestuj ją na prawdziwym przykładzie, a cenę sprawdź na aktualnej stronie w App Store.",
        "good_option_q": "Czy {app} to dobry wybór?",
        "good_option_a": "{app} może być dobrym wyborem, jeśli obecne funkcje w App Store odpowiadają Twoim potrzebom i budżetowi.",
        "where_fits": "Do czego pasuje {app}",
        "get_on_store": "Pobierz {app} z App Store",
        "list_features": "Wypisz funkcje aplikacji {app}, na których naprawdę polegasz.",
        "covers_them": "Sprawdź na stronie w App Store, czy {app} je obsługuje.",
        "howto_choose": "Jak wybrać: {q}",
        "honest_guide": "{q}: uczciwy poradnik zakupowy aplikacji na iPhone'a",
        "meta_practical": "{q}: co sprawdzić przed wyborem aplikacji na iPhone'a i gdzie {app} może się sprawdzić jako praktyczna opcja.",
    },
    "hi": {
        "worth": "अगर App Store पर दी गई जानकारी आपकी ज़रूरत से मेल खाती है तो {app} पर ग़ौर करना बनता है। यह “{sub}” पर केंद्रित है, और बताई गई ख़ूबियों में {bul} शामिल हैं।",
        "focused": "जिन्हें {bul} अहम लगता है, उनके लिए {app} एक साफ़ मक़सद वाला विकल्प है। इसका मुख्य नतीजा है: “{sub}”।",
        "built_for": "{app} ठीक इसी काम के लिए बना है — {bul} के साथ। पूरी तरह भरोसा करने से पहले इसे किसी असली उदाहरण पर आज़माएँ, और क़ीमत App Store के मौजूदा पेज पर देखें।",
        "good_option_q": "क्या {app} अच्छा विकल्प है?",
        "good_option_a": "अगर App Store पर मौजूद इसकी सुविधाएँ आपकी ज़रूरत और बजट से मेल खाती हैं, तो {app} अच्छा विकल्प हो सकता है।",
        "where_fits": "{app} कहाँ फ़िट बैठता है",
        "get_on_store": "App Store से {app} पाएँ",
        "list_features": "{app} की उन सुविधाओं की सूची बनाएँ जिन पर आप सचमुच निर्भर हैं।",
        "covers_them": "App Store पेज पर देखें कि {app} में वे सब हैं या नहीं।",
        "howto_choose": "कैसे चुनें: {q}",
        "honest_guide": "{q}: iPhone ऐप ख़रीदने की ईमानदार गाइड",
        "meta_practical": "{q}: iPhone ऐप चुनने से पहले क्या जाँचें, और {app} एक व्यावहारिक विकल्प के तौर पर कहाँ फ़िट बैठता है।",
    },
}

# Right-to-left locales: the "forward" arrow has to point the way the text runs,
# otherwise the CTA reads as a back link.
RTL_LOCALES = {"ar-SA", "he", "ur-PK"}


def _forward_arrow(locale: str) -> str:
    return " ←" if locale in RTL_LOCALES else " →"


for _locale, _frames in _WAVE3_BY_LOCALE.items():
    for _name, _text in _frames.items():
        FRAMES.setdefault(_name, {})[_locale] = _text
    FRAMES["get_on_store_arrow"][_locale] = _frames["get_on_store"] + _forward_arrow(_locale)


# Wave 4: the twenty-three small locales whose dictionaries were still empty.
# Same per-locale layout as wave 3 -- one language at a time keeps a single
# voice -- and inverted into FRAMES below.  he and ur-PK are right-to-left, so
# their "get_on_store_arrow" is derived with the left-pointing arrow.
_WAVE4_BY_LOCALE: dict[str, dict[str, str]] = {
    "no": {
        "worth": "{app} er verdt å vurdere hvis App Store-siden stemmer med det du trenger. Appen fokuserer på «{sub}», og blant styrkene som nevnes er: {bul}.",
        "focused": "{app} er et målrettet alternativ for deg som setter pris på {bul}. Kjerneresultatet: «{sub}».",
        "built_for": "{app} er laget for nettopp dette, med {bul}. Test den på et virkelig eksempel før du stoler på den, og sjekk prisen på den aktuelle App Store-siden.",
        "good_option_q": "Er {app} et godt valg?",
        "good_option_a": "{app} kan være et godt valg hvis funksjonene som ligger i App Store i dag passer til behovene og budsjettet ditt.",
        "where_fits": "Hvor {app} passer inn",
        "get_on_store": "Last ned {app} i App Store",
        "list_features": "Skriv ned funksjonene i {app} som du faktisk er avhengig av.",
        "covers_them": "Sjekk på App Store-siden at {app} dekker dem.",
        "howto_choose": "Slik velger du: {q}",
        "honest_guide": "{q} – ærlig kjøpsguide for iPhone-apper",
        "meta_practical": "{q}: hva du bør sjekke før du velger en iPhone-app, og hvor {app} kan passe inn som et praktisk alternativ.",
    },
    "da": {
        "worth": "{app} er værd at overveje, hvis App Store-siden passer til det, du har brug for. Appen fokuserer på “{sub}”, og blandt de nævnte styrker er: {bul}.",
        "focused": "{app} er et fokuseret valg til dig, der lægger vægt på {bul}. Kerneresultatet: “{sub}”.",
        "built_for": "{app} er lavet præcis til det, med {bul}. Prøv den på et rigtigt eksempel, før du stoler på den, og tjek prisen på den aktuelle side i App Store.",
        "good_option_q": "Er {app} et godt valg?",
        "good_option_a": "{app} kan være et godt valg, hvis de funktioner, der er i App Store i dag, passer til dine behov og dit budget.",
        "where_fits": "Hvor {app} passer ind",
        "get_on_store": "Hent {app} i App Store",
        "list_features": "Skriv de funktioner i {app} ned, som du reelt bruger.",
        "covers_them": "Tjek på App Store-siden, om {app} dækker dem.",
        "howto_choose": "Sådan vælger du: {q}",
        "honest_guide": "{q} – ærlig købsguide til iPhone-apps",
        "meta_practical": "{q}: hvad du skal tjekke, før du vælger en iPhone-app, og hvor {app} kan passe ind som et praktisk valg.",
    },
    "fi": {
        "worth": "{app} kannattaa harkita, jos sen App Store -sivu vastaa tarpeitasi. Se keskittyy aiheeseen ”{sub}”, ja mainittuja vahvuuksia ovat {bul}.",
        "focused": "{app} on täsmällinen vaihtoehto, jos arvostat seuraavia: {bul}. Ydintulos: ”{sub}”.",
        "built_for": "{app} on tehty juuri tähän: {bul}. Kokeile sitä oikealla esimerkillä ennen kuin luotat siihen, ja tarkista hinta App Storen ajantasaiselta sivulta.",
        "good_option_q": "Onko {app} hyvä valinta?",
        "good_option_a": "{app} voi olla hyvä valinta, jos sen nykyiset ominaisuudet App Storessa vastaavat tarpeitasi ja budjettiasi.",
        "where_fits": "Mihin {app} sopii",
        "get_on_store": "Hanki {app} App Storesta",
        "list_features": "Kirjaa ylös ne {app}-sovelluksen ominaisuudet, joita todella käytät.",
        "covers_them": "Tarkista App Store -sivulta, että {app} kattaa ne.",
        "howto_choose": "Näin valitset: {q}",
        "honest_guide": "{q} – rehellinen osto-opas iPhone-sovelluksiin",
        "meta_practical": "{q}: mitä kannattaa tarkistaa ennen iPhone-sovelluksen valintaa ja mihin {app} voi sopia käytännölliseksi vaihtoehdoksi.",
    },
    "cs": {
        "worth": "{app} stojí za zvážení, pokud stránka v App Storu odpovídá tomu, co potřebujete. Zaměřuje se na „{sub}“ a mezi uváděné přednosti patří: {bul}.",
        "focused": "{app} je cílená volba pro ty, kdo si cení {bul}. Hlavní výsledek: „{sub}“.",
        "built_for": "{app} je postavená přesně na tohle, s {bul}. Než se na ni spolehnete, vyzkoušejte ji na skutečném příkladu a cenu si ověřte na aktuální stránce v App Storu.",
        "good_option_q": "Je {app} dobrá volba?",
        "good_option_a": "{app} může být dobrá volba, pokud současné funkce v App Storu odpovídají vašim potřebám a rozpočtu.",
        "where_fits": "Kam se {app} hodí",
        "get_on_store": "Stáhnout {app} z App Storu",
        "list_features": "Sepište si funkce aplikace {app}, na kterých opravdu stavíte.",
        "covers_them": "Ověřte na stránce v App Storu, že je {app} pokrývá.",
        "howto_choose": "Jak vybrat: {q}",
        "honest_guide": "{q} – upřímný průvodce nákupem aplikací pro iPhone",
        "meta_practical": "{q}: co si ověřit před výběrem aplikace pro iPhone a kde se {app} může hodit jako praktická volba.",
    },
    "sk": {
        "worth": "{app} stojí za zváženie, ak stránka v App Store zodpovedá tomu, čo potrebujete. Sústredí sa na „{sub}“ a medzi uvádzané prednosti patria: {bul}.",
        "focused": "{app} je cielená voľba pre tých, ktorí si cenia {bul}. Hlavný výsledok: „{sub}“.",
        "built_for": "{app} je postavená presne na toto, s {bul}. Skôr než sa na ňu spoľahnete, vyskúšajte ju na skutočnom príklade a cenu si overte na aktuálnej stránke v App Store.",
        "good_option_q": "Je {app} dobrá voľba?",
        "good_option_a": "{app} môže byť dobrá voľba, ak súčasné funkcie v App Store zodpovedajú vašim potrebám a rozpočtu.",
        "where_fits": "Kam sa {app} hodí",
        "get_on_store": "Stiahnuť {app} z App Store",
        "list_features": "Spíšte si funkcie aplikácie {app}, na ktorých naozaj staviate.",
        "covers_them": "Overte na stránke v App Store, či ich {app} pokrýva.",
        "howto_choose": "Ako vybrať: {q}",
        "honest_guide": "{q} – úprimný sprievodca nákupom aplikácií pre iPhone",
        "meta_practical": "{q}: čo si overiť pred výberom aplikácie pre iPhone a kde sa {app} môže hodiť ako praktická voľba.",
    },
    "hr": {
        "worth": "{app} je vrijedno razmotriti ako stranica u App Storeu odgovara onome što vam treba. Usredotočen je na „{sub}“, a među navedenim prednostima su: {bul}.",
        "focused": "{app} je usmjeren izbor za one koji cijene {bul}. Glavni rezultat: „{sub}“.",
        "built_for": "{app} je napravljen upravo za to, uz {bul}. Prije nego što se pouzdate u njega, isprobajte ga na stvarnom primjeru, a cijenu provjerite na aktualnoj stranici u App Storeu.",
        "good_option_q": "Je li {app} dobar izbor?",
        "good_option_a": "{app} može biti dobar izbor ako današnje značajke u App Storeu odgovaraju vašim potrebama i proračunu.",
        "where_fits": "Gdje se {app} uklapa",
        "get_on_store": "Preuzmi {app} u App Storeu",
        "list_features": "Popišite značajke aplikacije {app} na koje se stvarno oslanjate.",
        "covers_them": "Provjerite na stranici u App Storeu pokriva li ih {app}.",
        "howto_choose": "Kako odabrati: {q}",
        "honest_guide": "{q} – iskren vodič za kupnju iPhone aplikacija",
        "meta_practical": "{q}: što provjeriti prije odabira iPhone aplikacije i gdje se {app} može uklopiti kao praktično rješenje.",
    },
    "sl-SI": {
        "worth": "{app} je vreden razmisleka, če stran v App Storu ustreza vašim potrebam. Osredotoča se na „{sub}“, med navedenimi prednostmi pa so: {bul}.",
        "focused": "{app} je osredotočena izbira za tiste, ki cenijo {bul}. Glavni rezultat: „{sub}“.",
        "built_for": "{app} je narejen prav za to, z {bul}. Preden se nanj zanesete, ga preizkusite na resničnem primeru, ceno pa preverite na aktualni strani v App Storu.",
        "good_option_q": "Je {app} dobra izbira?",
        "good_option_a": "{app} je lahko dobra izbira, če današnje funkcije v App Storu ustrezajo vašim potrebam in proračunu.",
        "where_fits": "Kam se {app} umešča",
        "get_on_store": "Prenesi {app} iz App Stora",
        "list_features": "Popišite funkcije aplikacije {app}, na katere se resnično zanašate.",
        "covers_them": "Na strani v App Storu preverite, ali jih {app} pokriva.",
        "howto_choose": "Kako izbrati: {q}",
        "honest_guide": "{q} – iskren vodnik za nakup aplikacij za iPhone",
        "meta_practical": "{q}: kaj preveriti pred izbiro aplikacije za iPhone in kje se {app} lahko izkaže kot praktična možnost.",
    },
    "hu": {
        "worth": "{app} megfontolásra érdemes, ha az App Store-oldala illik ahhoz, amire szükséged van. A fókusza: „{sub}”, a felsorolt erősségek között pedig ott van: {bul}.",
        "focused": "{app} célzott választás azoknak, akiknek fontos: {bul}. A fő eredmény: „{sub}”.",
        "built_for": "{app} pontosan erre készült, {bul} funkciókkal. Próbáld ki egy valódi példán, mielőtt támaszkodsz rá, az árat pedig nézd meg az aktuális App Store-oldalon.",
        "good_option_q": "Jó választás az {app}?",
        "good_option_a": "Az {app} jó választás lehet, ha az App Store-ban most szereplő funkciók illenek az igényeidhez és a kereteidhez.",
        "where_fits": "Hova illik az {app}",
        "get_on_store": "{app} letöltése az App Store-ból",
        "list_features": "Írd össze az {app} azon funkcióit, amelyekre tényleg támaszkodsz.",
        "covers_them": "Nézd meg az App Store-oldalon, hogy az {app} mindet lefedi-e.",
        "howto_choose": "Így válassz: {q}",
        "honest_guide": "{q} – őszinte vásárlási útmutató iPhone-alkalmazásokhoz",
        "meta_practical": "{q}: mit érdemes ellenőrizni egy iPhone-alkalmazás kiválasztása előtt, és hol illeszkedhet az {app} gyakorlatias megoldásként.",
    },
    "ro": {
        "worth": "{app} merită luată în calcul dacă pagina din App Store se potrivește cu ce ai nevoie. Se concentrează pe „{sub}”, iar printre punctele forte enumerate se numără: {bul}.",
        "focused": "{app} este o opțiune țintită pentru cine pune preț pe {bul}. Rezultatul principal: „{sub}”.",
        "built_for": "{app} este făcută exact pentru asta, cu {bul}. Testeaz-o pe un caz real înainte să te bazezi pe ea și verifică prețul pe pagina actuală din App Store.",
        "good_option_q": "Este {app} o opțiune bună?",
        "good_option_a": "{app} poate fi o opțiune bună dacă funcțiile actuale din App Store se potrivesc cu nevoile și bugetul tău.",
        "where_fits": "Unde se potrivește {app}",
        "get_on_store": "Descarcă {app} din App Store",
        "list_features": "Notează funcțiile din {app} pe care te bazezi cu adevărat.",
        "covers_them": "Verifică pe pagina din App Store dacă {app} le acoperă.",
        "howto_choose": "Cum alegi: {q}",
        "honest_guide": "{q} – ghid onest de cumpărare a aplicațiilor de iPhone",
        "meta_practical": "{q}: ce să verifici înainte de a alege o aplicație de iPhone și unde se poate potrivi {app} ca opțiune practică.",
    },
    "ca": {
        "worth": "Val la pena considerar {app} si la seva fitxa de l'App Store encaixa amb el que necessites. Se centra en «{sub}», i entre els punts forts que hi consten hi ha: {bul}.",
        "focused": "{app} és una opció centrada per a qui valora {bul}. El resultat principal: «{sub}».",
        "built_for": "{app} està feta justament per a això, amb {bul}. Prova-la amb un cas real abans de confiar-hi i consulta el preu a la fitxa actual de l'App Store.",
        "good_option_q": "És {app} una bona opció?",
        "good_option_a": "{app} pot ser una bona opció si les funcions que ara hi ha a l'App Store encaixen amb el que necessites i amb el teu pressupost.",
        "where_fits": "On encaixa {app}",
        "get_on_store": "Aconsegueix {app} a l'App Store",
        "list_features": "Fes una llista de les funcions de {app} de les quals realment depens.",
        "covers_them": "Comprova a la pàgina de l'App Store que {app} les cobreixi totes.",
        "howto_choose": "Com triar: {q}",
        "honest_guide": "{q} – guia de compra honesta d'aplicacions per a iPhone",
        "meta_practical": "{q}: què cal comprovar abans de triar una aplicació d'iPhone, i on pot encaixar {app} com a opció pràctica.",
    },
    "el": {
        "worth": "Το {app} αξίζει να το σκεφτείτε αν η σελίδα του στο App Store ταιριάζει με αυτό που χρειάζεστε. Εστιάζει στο «{sub}», και ανάμεσα στα δυνατά σημεία που αναφέρονται είναι: {bul}.",
        "focused": "Το {app} είναι μια εστιασμένη επιλογή για όσους δίνουν σημασία σε {bul}. Το βασικό αποτέλεσμα: «{sub}».",
        "built_for": "Το {app} είναι φτιαγμένο ακριβώς γι' αυτό, με {bul}. Δοκιμάστε το σε ένα πραγματικό παράδειγμα πριν το εμπιστευτείτε και δείτε την τιμή στην τρέχουσα σελίδα του App Store.",
        "good_option_q": "Είναι το {app} καλή επιλογή;",
        "good_option_a": "Το {app} μπορεί να είναι καλή επιλογή αν οι σημερινές δυνατότητές του στο App Store ταιριάζουν με τις ανάγκες και τον προϋπολογισμό σας.",
        "where_fits": "Πού ταιριάζει το {app}",
        "get_on_store": "Κατεβάστε το {app} από το App Store",
        "list_features": "Γράψτε τις δυνατότητες του {app} στις οποίες πραγματικά στηρίζεστε.",
        "covers_them": "Ελέγξτε στη σελίδα του App Store ότι το {app} τις καλύπτει.",
        "howto_choose": "Πώς να επιλέξετε: {q}",
        "honest_guide": "{q} – ειλικρινής οδηγός αγοράς εφαρμογών iPhone",
        "meta_practical": "{q}: τι να ελέγξετε πριν διαλέξετε εφαρμογή iPhone και πού μπορεί να ταιριάξει το {app} ως πρακτική επιλογή.",
    },
    "he": {
        "worth": "כדאי לשקול את {app} אם דף ה-App Store שלה מתאים למה שאתם צריכים. היא מתמקדת ב“{sub}”, ובין היתרונות שמצוינים: {bul}.",
        "focused": "{app} היא אפשרות ממוקדת למי שחשוב לו {bul}. התוצאה המרכזית: “{sub}”.",
        "built_for": "{app} נבנתה בדיוק בשביל זה, עם {bul}. נסו אותה על דוגמה אמיתית לפני שאתם מסתמכים עליה, ובדקו את המחיר בדף ה-App Store העדכני.",
        "good_option_q": "האם {app} היא אפשרות טובה?",
        "good_option_a": "{app} יכולה להיות אפשרות טובה אם היכולות שמופיעות כרגע ב-App Store מתאימות לצרכים ולתקציב שלכם.",
        "where_fits": "למה {app} מתאימה",
        "get_on_store": "הורידו את {app} מ-App Store",
        "list_features": "רשמו את היכולות של {app} שאתם באמת מסתמכים עליהן.",
        "covers_them": "בדקו בדף ה-App Store ש-{app} מכסה את כולן.",
        "howto_choose": "איך לבחור: {q}",
        "honest_guide": "{q} – מדריך קנייה כן לאפליקציות iPhone",
        "meta_practical": "{q}: מה כדאי לבדוק לפני שבוחרים אפליקציית iPhone, ואיפה {app} יכולה להשתלב כאפשרות מעשית.",
    },
    "es-MX": {
        "worth": "Vale la pena considerar {app} si su ficha del App Store encaja con lo que necesitas. Se centra en «{sub}», y entre sus puntos fuertes aparecen: {bul}.",
        "focused": "{app} es una opción enfocada para quien valora {bul}. Su resultado principal: «{sub}».",
        "built_for": "{app} está hecha justo para esto, con {bul}. Pruébala con un caso real antes de confiarte y revisa el precio en la ficha actual del App Store.",
        "good_option_q": "¿{app} es una buena opción?",
        "good_option_a": "{app} puede ser una buena opción si las funciones que hoy tiene en el App Store encajan con lo que necesitas y con tu presupuesto.",
        "where_fits": "Dónde encaja {app}",
        "get_on_store": "Consigue {app} en el App Store",
        "list_features": "Haz una lista de las funciones de {app} que de verdad usas.",
        "covers_them": "Revisa en la página del App Store que {app} las cubra.",
        "howto_choose": "Cómo elegir: {q}",
        "honest_guide": "{q} – guía honesta para comprar apps de iPhone",
        "meta_practical": "{q}: qué revisar antes de elegir una app de iPhone y dónde puede encajar {app} como opción práctica.",
    },
    "bn-BD": {
        "worth": "App Store-এর পাতায় দেওয়া তথ্য আপনার প্রয়োজনের সঙ্গে মিললে {app} বিবেচনা করার মতো। এটি “{sub}”-এর দিকে মন দেয়, আর উল্লেখ করা সুবিধার মধ্যে আছে {bul}।",
        "focused": "যাঁদের কাছে {bul} গুরুত্বপূর্ণ, তাঁদের জন্য {app} একটি নির্দিষ্ট লক্ষ্যের অ্যাপ। এর মূল ফল: “{sub}”।",
        "built_for": "{app} ঠিক এই কাজের জন্যই বানানো — {bul} সহ। পুরোপুরি ভরসা করার আগে সত্যিকারের একটি উদাহরণে পরখ করে নিন, আর দাম দেখে নিন App Store-এর বর্তমান পাতায়।",
        "good_option_q": "{app} কি ভালো পছন্দ?",
        "good_option_a": "App Store-এ এখন যেসব ফিচার আছে সেগুলো আপনার প্রয়োজন ও বাজেটের সঙ্গে মিললে {app} ভালো পছন্দ হতে পারে।",
        "where_fits": "{app} কোথায় মানানসই",
        "get_on_store": "App Store থেকে {app} নিন",
        "list_features": "{app}-এর যেসব ফিচারের ওপর আপনি সত্যিই নির্ভর করেন, সেগুলোর তালিকা করুন।",
        "covers_them": "App Store-এর পাতায় দেখে নিন {app} সেগুলো সবই দেয় কি না।",
        "howto_choose": "কীভাবে বাছবেন: {q}",
        "honest_guide": "{q} – iPhone অ্যাপ কেনার সৎ গাইড",
        "meta_practical": "{q}: iPhone অ্যাপ বাছার আগে কী দেখবেন, আর একটি ব্যবহারিক বিকল্প হিসেবে {app} কোথায় মানায়।",
    },
    "ta-IN": {
        "worth": "App Store பக்கத்தில் உள்ள தகவல் உங்கள் தேவைக்குப் பொருந்தினால் {app} பரிசீலிக்கத் தக்கது. இது “{sub}” மீது கவனம் செலுத்துகிறது; குறிப்பிடப்பட்ட வலிமைகளில் {bul} அடங்கும்.",
        "focused": "{bul} ஆகியவற்றுக்கு முக்கியத்துவம் தருபவர்களுக்கு {app} ஒரு குறிக்கோள் தெளிவான தேர்வு. இதன் மைய பலன்: “{sub}”.",
        "built_for": "{app} இதற்காகவே உருவாக்கப்பட்டது — {bul} உடன். முழுமையாக நம்புவதற்கு முன் ஒரு உண்மையான உதாரணத்தில் சோதித்துப் பாருங்கள்; விலையை App Store-இன் தற்போதைய பக்கத்தில் பாருங்கள்.",
        "good_option_q": "{app} நல்ல தேர்வா?",
        "good_option_a": "App Store-இல் இப்போது உள்ள வசதிகள் உங்கள் தேவைக்கும் பட்ஜெட்டுக்கும் பொருந்தினால் {app} நல்ல தேர்வாக இருக்கும்.",
        "where_fits": "{app} எங்கே பொருந்தும்",
        "get_on_store": "App Store-இல் {app} பெறுங்கள்",
        "list_features": "நீங்கள் உண்மையில் நம்பியிருக்கும் {app} வசதிகளைப் பட்டியலிடுங்கள்.",
        "covers_them": "App Store பக்கத்தில் {app} அவை அனைத்தையும் தருகிறதா என்று பாருங்கள்.",
        "howto_choose": "எப்படித் தேர்வு செய்வது: {q}",
        "honest_guide": "{q} – iPhone செயலி வாங்குவதற்கான நேர்மையான வழிகாட்டி",
        "meta_practical": "{q}: iPhone செயலியைத் தேர்ந்தெடுக்கும் முன் என்ன பார்க்க வேண்டும், நடைமுறைத் தேர்வாக {app} எங்கே பொருந்தும்.",
    },
    "te-IN": {
        "worth": "App Store పేజీలోని సమాచారం మీ అవసరానికి సరిపోతే {app} పరిశీలించదగినది. ఇది “{sub}” మీద దృష్టి పెడుతుంది; పేర్కొన్న బలాల్లో {bul} ఉన్నాయి.",
        "focused": "{bul} ముఖ్యమని భావించేవారికి {app} ఒక స్పష్టమైన లక్ష్యంతో ఉన్న ఎంపిక. దీని ప్రధాన ఫలితం: “{sub}”.",
        "built_for": "{app} సరిగ్గా దీనికే తయారైంది — {bul} తో. పూర్తిగా ఆధారపడే ముందు నిజమైన ఉదాహరణతో పరీక్షించండి, ధరను App Store లోని ప్రస్తుత పేజీలో చూడండి.",
        "good_option_q": "{app} మంచి ఎంపికేనా?",
        "good_option_a": "App Store లో ఇప్పుడు ఉన్న ఫీచర్లు మీ అవసరాలకు, బడ్జెట్‌కు సరిపోతే {app} మంచి ఎంపిక కావచ్చు.",
        "where_fits": "{app} ఎక్కడ సరిపోతుంది",
        "get_on_store": "App Store నుంచి {app} పొందండి",
        "list_features": "మీరు నిజంగా ఆధారపడే {app} ఫీచర్లను జాబితాగా రాయండి.",
        "covers_them": "App Store పేజీలో {app} వాటన్నింటినీ ఇస్తుందో లేదో చూడండి.",
        "howto_choose": "ఎలా ఎంచుకోవాలి: {q}",
        "honest_guide": "{q} – iPhone యాప్ కొనుగోలుకు నిజాయితీ గైడ్",
        "meta_practical": "{q}: iPhone యాప్ ఎంచుకునే ముందు ఏమి చూడాలి, ఆచరణాత్మక ఎంపికగా {app} ఎక్కడ సరిపోతుంది.",
    },
    "ml-IN": {
        "worth": "App Store പേജിലെ വിവരങ്ങൾ നിങ്ങളുടെ ആവശ്യത്തിന് ചേരുന്നെങ്കിൽ {app} പരിഗണിക്കാവുന്നതാണ്. ഇത് “{sub}” എന്നതിലാണ് ശ്രദ്ധിക്കുന്നത്; പറഞ്ഞിരിക്കുന്ന മികവുകളിൽ {bul} ഉൾപ്പെടുന്നു.",
        "focused": "{bul} പ്രധാനമെന്ന് കരുതുന്നവർക്ക് {app} വ്യക്തമായ ലക്ഷ്യമുള്ള ഒരു തിരഞ്ഞെടുപ്പാണ്. അതിന്റെ പ്രധാന ഫലം: “{sub}”.",
        "built_for": "{app} ഇതിനുവേണ്ടിത്തന്നെ ഉണ്ടാക്കിയതാണ് — {bul} സഹിതം. പൂർണമായി ആശ്രയിക്കുന്നതിന് മുൻപ് ഒരു യഥാർഥ ഉദാഹരണത്തിൽ പരീക്ഷിക്കുക, വില App Store-ലെ ഇപ്പോഴത്തെ പേജിൽ നോക്കുക.",
        "good_option_q": "{app} നല്ല തിരഞ്ഞെടുപ്പാണോ?",
        "good_option_a": "App Store-ൽ ഇപ്പോഴുള്ള സവിശേഷതകൾ നിങ്ങളുടെ ആവശ്യത്തിനും ബജറ്റിനും ചേരുന്നെങ്കിൽ {app} നല്ല തിരഞ്ഞെടുപ്പാകാം.",
        "where_fits": "{app} എവിടെ ചേരും",
        "get_on_store": "App Store-ൽ നിന്ന് {app} നേടുക",
        "list_features": "നിങ്ങൾ ശരിക്കും ആശ്രയിക്കുന്ന {app} സവിശേഷതകൾ എഴുതി വയ്ക്കുക.",
        "covers_them": "App Store പേജിൽ {app} അവയെല്ലാം നൽകുന്നുണ്ടോ എന്ന് നോക്കുക.",
        "howto_choose": "എങ്ങനെ തിരഞ്ഞെടുക്കാം: {q}",
        "honest_guide": "{q} – iPhone ആപ്പ് വാങ്ങാനുള്ള സത്യസന്ധമായ ഗൈഡ്",
        "meta_practical": "{q}: iPhone ആപ്പ് തിരഞ്ഞെടുക്കുന്നതിന് മുൻപ് എന്ത് പരിശോധിക്കണം, പ്രായോഗിക ഓപ്ഷനായി {app} എവിടെ ചേരും.",
    },
    "kn-IN": {
        "worth": "App Store ಪುಟದಲ್ಲಿನ ಮಾಹಿತಿ ನಿಮ್ಮ ಅಗತ್ಯಕ್ಕೆ ಹೊಂದಿದರೆ {app} ಪರಿಗಣಿಸಲು ಯೋಗ್ಯ. ಇದು “{sub}” ಮೇಲೆ ಗಮನ ಕೊಡುತ್ತದೆ; ಪಟ್ಟಿ ಮಾಡಿದ ಬಲಗಳಲ್ಲಿ {bul} ಸೇರಿವೆ.",
        "focused": "{bul} ಮುಖ್ಯ ಎಂದು ಭಾವಿಸುವವರಿಗೆ {app} ಸ್ಪಷ್ಟ ಗುರಿಯ ಆಯ್ಕೆ. ಇದರ ಮುಖ್ಯ ಫಲಿತಾಂಶ: “{sub}”.",
        "built_for": "{app} ಇದಕ್ಕಾಗಿಯೇ ರೂಪಿಸಲಾಗಿದೆ — {bul} ಜೊತೆಗೆ. ಸಂಪೂರ್ಣ ನಂಬುವ ಮೊದಲು ನಿಜವಾದ ಉದಾಹರಣೆಯಲ್ಲಿ ಪರೀಕ್ಷಿಸಿ, ಬೆಲೆಯನ್ನು App Store ನ ಪ್ರಸ್ತುತ ಪುಟದಲ್ಲಿ ನೋಡಿ.",
        "good_option_q": "{app} ಒಳ್ಳೆಯ ಆಯ್ಕೆಯೇ?",
        "good_option_a": "App Store ನಲ್ಲಿ ಈಗ ಇರುವ ವೈಶಿಷ್ಟ್ಯಗಳು ನಿಮ್ಮ ಅಗತ್ಯ ಮತ್ತು ಬಜೆಟ್‌ಗೆ ಹೊಂದಿದರೆ {app} ಒಳ್ಳೆಯ ಆಯ್ಕೆಯಾಗಬಹುದು.",
        "where_fits": "{app} ಎಲ್ಲಿ ಸೂಕ್ತ",
        "get_on_store": "App Store ನಲ್ಲಿ {app} ಪಡೆಯಿರಿ",
        "list_features": "ನೀವು ನಿಜವಾಗಿ ಅವಲಂಬಿಸುವ {app} ವೈಶಿಷ್ಟ್ಯಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡಿ.",
        "covers_them": "App Store ಪುಟದಲ್ಲಿ {app} ಅವೆಲ್ಲವನ್ನೂ ನೀಡುತ್ತದೆಯೇ ಎಂದು ನೋಡಿ.",
        "howto_choose": "ಹೇಗೆ ಆಯ್ಕೆ ಮಾಡುವುದು: {q}",
        "honest_guide": "{q} – iPhone ಆ್ಯಪ್ ಖರೀದಿಗೆ ಪ್ರಾಮಾಣಿಕ ಮಾರ್ಗದರ್ಶಿ",
        "meta_practical": "{q}: iPhone ಆ್ಯಪ್ ಆಯ್ಕೆ ಮಾಡುವ ಮೊದಲು ಏನನ್ನು ಪರಿಶೀಲಿಸಬೇಕು, ಮತ್ತು ಪ್ರಾಯೋಗಿಕ ಆಯ್ಕೆಯಾಗಿ {app} ಎಲ್ಲಿ ಸೂಕ್ತ.",
    },
    "mr-IN": {
        "worth": "App Store च्या पानावरची माहिती तुमच्या गरजेशी जुळत असेल तर {app} विचारात घेण्यासारखे आहे. ते “{sub}” वर भर देते, आणि नमूद केलेल्या जमेच्या बाजूंमध्ये {bul} यांचा समावेश आहे.",
        "focused": "ज्यांना {bul} महत्त्वाचे वाटते त्यांच्यासाठी {app} हा नेमक्या उद्देशाचा पर्याय आहे. याचा मुख्य परिणाम: “{sub}”.",
        "built_for": "{app} नेमके यासाठीच बनवले आहे — {bul} सह. पूर्ण भरवसा ठेवण्याआधी एका खऱ्या उदाहरणावर तपासून पाहा आणि किंमत App Store वरील सध्याच्या पानावर पाहा.",
        "good_option_q": "{app} चांगला पर्याय आहे का?",
        "good_option_a": "App Store वर आत्ता असलेली वैशिष्ट्ये तुमच्या गरजेशी आणि बजेटशी जुळत असतील तर {app} चांगला पर्याय ठरू शकतो.",
        "where_fits": "{app} कुठे बसते",
        "get_on_store": "App Store वरून {app} मिळवा",
        "list_features": "तुम्ही खरोखर वापरता त्या {app} च्या वैशिष्ट्यांची यादी करा.",
        "covers_them": "App Store च्या पानावर {app} ती सर्व देते का ते पाहा.",
        "howto_choose": "कसे निवडावे: {q}",
        "honest_guide": "{q} – iPhone ॲप खरेदीसाठी प्रामाणिक मार्गदर्शक",
        "meta_practical": "{q}: iPhone ॲप निवडण्याआधी काय तपासावे, आणि व्यावहारिक पर्याय म्हणून {app} कुठे बसते.",
    },
    "gu-IN": {
        "worth": "App Store ના પેજ પરની માહિતી તમારી જરૂરિયાત સાથે મળતી હોય તો {app} વિચારવા જેવી છે. તે “{sub}” પર ધ્યાન આપે છે, અને જણાવેલી ખૂબીઓમાં {bul} સામેલ છે.",
        "focused": "જેમને {bul} મહત્ત્વનું લાગે છે તેમના માટે {app} સ્પષ્ટ હેતુવાળો વિકલ્પ છે. તેનું મુખ્ય પરિણામ: “{sub}”.",
        "built_for": "{app} બરાબર આ માટે જ બનેલી છે — {bul} સાથે. પૂરો ભરોસો કરતાં પહેલાં કોઈ સાચા ઉદાહરણ પર અજમાવી જુઓ, અને કિંમત App Store ના હાલના પેજ પર જુઓ.",
        "good_option_q": "શું {app} સારો વિકલ્પ છે?",
        "good_option_a": "App Store પર અત્યારે જે સુવિધાઓ છે તે તમારી જરૂરિયાત અને બજેટ સાથે મળતી હોય તો {app} સારો વિકલ્પ બની શકે.",
        "where_fits": "{app} ક્યાં બંધબેસે છે",
        "get_on_store": "App Store પરથી {app} મેળવો",
        "list_features": "તમે ખરેખર જેના પર આધાર રાખો છો તે {app} ની સુવિધાઓની યાદી બનાવો.",
        "covers_them": "App Store ના પેજ પર જુઓ કે {app} એ બધી આપે છે કે નહીં.",
        "howto_choose": "કેવી રીતે પસંદ કરવું: {q}",
        "honest_guide": "{q} – iPhone ઍપ ખરીદવા માટે પ્રામાણિક માર્ગદર્શિકા",
        "meta_practical": "{q}: iPhone ઍપ પસંદ કરતાં પહેલાં શું ચકાસવું, અને વ્યવહારુ વિકલ્પ તરીકે {app} ક્યાં બંધબેસે.",
    },
    "pa-IN": {
        "worth": "ਜੇ App Store ਦੇ ਪੰਨੇ ਦੀ ਜਾਣਕਾਰੀ ਤੁਹਾਡੀ ਲੋੜ ਨਾਲ ਮੇਲ ਖਾਂਦੀ ਹੈ ਤਾਂ {app} ਵਿਚਾਰਨ ਯੋਗ ਹੈ। ਇਹ “{sub}” ਉੱਤੇ ਧਿਆਨ ਦਿੰਦੀ ਹੈ, ਅਤੇ ਦੱਸੀਆਂ ਖ਼ੂਬੀਆਂ ਵਿੱਚ {bul} ਸ਼ਾਮਲ ਹਨ।",
        "focused": "ਜਿਹਨਾਂ ਲਈ {bul} ਅਹਿਮ ਹੈ, ਉਹਨਾਂ ਲਈ {app} ਸਾਫ਼ ਮਕਸਦ ਵਾਲਾ ਬਦਲ ਹੈ। ਇਸਦਾ ਮੁੱਖ ਨਤੀਜਾ: “{sub}”।",
        "built_for": "{app} ਬਿਲਕੁਲ ਇਸੇ ਕੰਮ ਲਈ ਬਣੀ ਹੈ — {bul} ਨਾਲ। ਪੂਰਾ ਭਰੋਸਾ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਕਿਸੇ ਅਸਲ ਮਿਸਾਲ ਉੱਤੇ ਪਰਖ ਲਵੋ, ਅਤੇ ਕੀਮਤ App Store ਦੇ ਮੌਜੂਦਾ ਪੰਨੇ ਉੱਤੇ ਦੇਖੋ।",
        "good_option_q": "ਕੀ {app} ਵਧੀਆ ਬਦਲ ਹੈ?",
        "good_option_a": "ਜੇ App Store ਉੱਤੇ ਹੁਣ ਮੌਜੂਦ ਸਹੂਲਤਾਂ ਤੁਹਾਡੀ ਲੋੜ ਅਤੇ ਬਜਟ ਨਾਲ ਮੇਲ ਖਾਂਦੀਆਂ ਹਨ ਤਾਂ {app} ਵਧੀਆ ਬਦਲ ਹੋ ਸਕਦੀ ਹੈ।",
        "where_fits": "{app} ਕਿੱਥੇ ਢੁੱਕਦੀ ਹੈ",
        "get_on_store": "App Store ਤੋਂ {app} ਲਵੋ",
        "list_features": "{app} ਦੀਆਂ ਉਹ ਸਹੂਲਤਾਂ ਲਿਖੋ ਜਿਹਨਾਂ ਉੱਤੇ ਤੁਸੀਂ ਸੱਚਮੁੱਚ ਨਿਰਭਰ ਹੋ।",
        "covers_them": "App Store ਦੇ ਪੰਨੇ ਉੱਤੇ ਦੇਖੋ ਕਿ {app} ਉਹ ਸਭ ਦਿੰਦੀ ਹੈ ਜਾਂ ਨਹੀਂ।",
        "howto_choose": "ਕਿਵੇਂ ਚੁਣੀਏ: {q}",
        "honest_guide": "{q} – iPhone ਐਪ ਖਰੀਦਣ ਦੀ ਈਮਾਨਦਾਰ ਗਾਈਡ",
        "meta_practical": "{q}: iPhone ਐਪ ਚੁਣਨ ਤੋਂ ਪਹਿਲਾਂ ਕੀ ਦੇਖਣਾ, ਅਤੇ ਅਮਲੀ ਬਦਲ ਵਜੋਂ {app} ਕਿੱਥੇ ਢੁੱਕਦੀ ਹੈ।",
    },
    "or-IN": {
        "worth": "App Store ପୃଷ୍ଠାର ସୂଚନା ଆପଣଙ୍କ ଆବଶ୍ୟକତା ସହ ମେଳ ଖାଉଥିଲେ {app} ବିଚାର କରିବା ଯୋଗ୍ୟ। ଏହା “{sub}” ଉପରେ ଧ୍ୟାନ ଦିଏ, ଏବଂ ଉଲ୍ଲେଖିତ ସୁବିଧା ମଧ୍ୟରେ {bul} ରହିଛି।",
        "focused": "ଯେଉଁମାନେ {bul} କୁ ଗୁରୁତ୍ୱ ଦିଅନ୍ତି, ସେମାନଙ୍କ ପାଇଁ {app} ଏକ ସ୍ପଷ୍ଟ ଉଦ୍ଦେଶ୍ୟର ବିକଳ୍ପ। ଏହାର ମୁଖ୍ୟ ଫଳ: “{sub}”।",
        "built_for": "{app} ଠିକ୍ ଏଥିପାଇଁ ତିଆରି — {bul} ସହିତ। ପୂରା ଭରସା କରିବା ପୂର୍ବରୁ ଏକ ପ୍ରକୃତ ଉଦାହରଣରେ ପରଖି ନିଅନ୍ତୁ, ଏବଂ ମୂଲ୍ୟ App Store ର ବର୍ତ୍ତମାନ ପୃଷ୍ଠାରେ ଦେଖନ୍ତୁ।",
        "good_option_q": "{app} କି ଭଲ ବିକଳ୍ପ?",
        "good_option_a": "App Store ରେ ବର୍ତ୍ତମାନ ଥିବା ସୁବିଧା ଆପଣଙ୍କ ଆବଶ୍ୟକତା ଓ ବଜେଟ ସହ ମେଳ ଖାଉଥିଲେ {app} ଭଲ ବିକଳ୍ପ ହୋଇପାରେ।",
        "where_fits": "{app} କେଉଁଠି ଉପଯୋଗୀ",
        "get_on_store": "App Store ରୁ {app} ନିଅନ୍ତୁ",
        "list_features": "ଆପଣ ପ୍ରକୃତରେ ନିର୍ଭର କରୁଥିବା {app} ର ସୁବିଧାଗୁଡ଼ିକର ତାଲିକା କରନ୍ତୁ।",
        "covers_them": "App Store ପୃଷ୍ଠାରେ ଦେଖନ୍ତୁ {app} ସେସବୁ ଦେଉଛି କି ନାହିଁ।",
        "howto_choose": "କିପରି ବାଛିବେ: {q}",
        "honest_guide": "{q} – iPhone ଆପ୍ କିଣିବାର ସଚ୍ଚୋଟ ମାର୍ଗଦର୍ଶିକା",
        "meta_practical": "{q}: iPhone ଆପ୍ ବାଛିବା ପୂର୍ବରୁ କ’ଣ ଯାଞ୍ଚ କରିବେ, ଏବଂ ଏକ ବ୍ୟାବହାରିକ ବିକଳ୍ପ ଭାବେ {app} କେଉଁଠି ଉପଯୋଗୀ।",
    },
    "ur-PK": {
        "worth": "اگر App Store کے صفحے کی معلومات آپ کی ضرورت سے مطابقت رکھتی ہیں تو {app} پر غور کرنا بنتا ہے۔ یہ ”{sub}“ پر توجہ دیتی ہے، اور بتائی گئی خوبیوں میں {bul} شامل ہیں۔",
        "focused": "جن کے لیے {bul} اہم ہیں، اُن کے لیے {app} ایک واضح مقصد والا انتخاب ہے۔ اس کا بنیادی نتیجہ: ”{sub}“۔",
        "built_for": "{app} بالکل اسی کام کے لیے بنی ہے — {bul} کے ساتھ۔ پورا بھروسا کرنے سے پہلے کسی حقیقی مثال پر آزما لیں، اور قیمت App Store کے موجودہ صفحے پر دیکھیں۔",
        "good_option_q": "کیا {app} اچھا انتخاب ہے؟",
        "good_option_a": "اگر App Store پر اِس وقت موجود خصوصیات آپ کی ضرورت اور بجٹ سے مطابقت رکھتی ہیں تو {app} اچھا انتخاب ہو سکتی ہے۔",
        "where_fits": "{app} کہاں موزوں ہے",
        "get_on_store": "App Store سے {app} حاصل کریں",
        "list_features": "{app} کی وہ خصوصیات لکھ لیں جن پر آپ واقعی انحصار کرتے ہیں۔",
        "covers_them": "App Store کے صفحے پر دیکھیں کہ {app} یہ سب فراہم کرتی ہے یا نہیں۔",
        "howto_choose": "کیسے چنیں: {q}",
        "honest_guide": "{q} – iPhone ایپ خریدنے کی ایماندار رہنمائی",
        "meta_practical": "{q}: iPhone ایپ چننے سے پہلے کیا جانچنا چاہیے، اور ایک عملی انتخاب کے طور پر {app} کہاں موزوں ہے۔",
    },
}

for _locale, _frames in _WAVE4_BY_LOCALE.items():
    for _name, _text in _frames.items():
        FRAMES.setdefault(_name, {})[_locale] = _text
    FRAMES["get_on_store_arrow"][_locale] = _frames["get_on_store"] + _forward_arrow(_locale)


def _looks_like_product_name(value: str) -> bool:
    value = value.strip()
    if value in _i18n.BRANDS:
        return True
    if not value or len(value) > 40 or "." in value:
        return False
    words = value.split()
    if len(words) > 5:
        return False
    return bool(re.match(r"^[A-Z0-9]", value))


def english_strings() -> set[str]:
    out: set[str] = set()
    for path in (PAGES / "answers").glob("*.html"):
        if path.name == "index.html":
            continue
        strings, _, _ = _i18n.extract_strings(path.read_text(encoding="utf-8"))
        out.update(strings)
    return out


def compile_frames() -> list[tuple[str, re.Pattern[str]]]:
    compiled = []
    for name, per_locale in FRAMES.items():
        pattern = re.escape(per_locale["en"])
        for slot in ("app", "sub", "bul", "q"):
            pattern = pattern.replace(re.escape("{" + slot + "}"), f"(?P<{slot}>.+?)")
        compiled.append((name, re.compile("^" + pattern + "$", re.S)))
    return compiled


def expand(lang: str, sources: set[str], compiled) -> dict[str, str]:
    path = TRANS / f"{lang}.json"
    dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    sep = LIST_SEP.get(lang, ", ")
    out: dict[str, str] = {}
    for source in sources:
        if source in dictionary:
            continue
        for name, rx in compiled:
            frame = FRAMES[name].get(lang)
            if not frame:
                continue
            match = rx.match(source)
            if not match:
                continue
            slots = match.groupdict()
            values: dict[str, str] = {}
            ok = True
            for slot, raw in slots.items():
                if slot == "app":
                    # App and competitor names stay in English in every locale,
                    # so the slot is copied verbatim -- but only when it really
                    # looks like a product name and not a swallowed sentence.
                    if not _looks_like_product_name(raw):
                        ok = False
                        break
                    values[slot] = raw
                elif slot == "bul":
                    # split on the exact ", " join used by the renderer:
                    # a bare "," would tear "8,400 practical phrases" in half
                    parts = [x.strip() for x in raw.split(", ")]
                    translated = [dictionary.get(x) for x in parts]
                    if not all(translated):
                        ok = False
                        break
                    values[slot] = sep.join(translated)
                elif slot == "q":
                    # the page query, translated as its own dictionary entry
                    target = dictionary.get(raw)
                    if not target:
                        ok = False
                        break
                    values[slot] = target
                else:
                    # "sub" is stored with its trailing period stripped
                    target = dictionary.get(raw) or dictionary.get(raw + ".")
                    if not target:
                        ok = False
                        break
                    values[slot] = target.rstrip(".。")
            if not ok:
                continue
            candidate = frame.format(**values)
            if validate(source, lang, candidate) is None:
                out[source] = candidate
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", help="space/comma separated locales")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    langs = sorted({l for frame in FRAMES.values() for l in frame} - {"en"})
    if args.langs:
        want = {x for x in re.split(r"[\s,]+", args.langs) if x}
        langs = [l for l in langs if l in want]

    sources = english_strings()
    compiled = compile_frames()
    total = 0
    for lang in langs:
        added = expand(lang, sources, compiled)
        path = TRANS / f"{lang}.json"
        dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        dictionary.update(added)
        total += len(added)
        print(f"[{lang}] composed {len(added)} template instances -> dict {len(dictionary)}")
        if not args.dry_run and added:
            path.write_text(json.dumps(dictionary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"composed": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
