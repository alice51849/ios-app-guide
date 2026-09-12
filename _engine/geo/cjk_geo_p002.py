"""The twelve P0-02 owned-GEO repairs; no metadata, social or layout writes."""

from __future__ import annotations

import html
import re

AUDIT_LOCALES = ("ja", "ko", "zh-Hans", "zh-Hant", "id", "ms", "th", "vi", "ar-SA", "ur-PK")
REPAIRED_LOCALES = ("zh-Hans", "id", "ms", "th", "vi", "ar-SA")
APP_IDS = {"lumibopomofopro": "6775773117", "lumiletterspro": "6778491147"}
TARGET_CELLS = frozenset((key, locale) for key in APP_IDS for locale in REPAIRED_LOCALES)
ENGLISH_PARAGRAPHS = {
    "lumibopomofopro": (
        "Pro edition unlocks the full 37-symbol journey in one purchase, "
        "with no ads, offline play and privacy-first learning."
    ),
    "lumiletterspro": (
        "Pro edition includes the full calm ABC journey in one purchase, "
        "with no ads, offline play and privacy-first learning."
    ),
}

NATIVE_PARAGRAPHS = {
    "lumibopomofopro": {
        "zh-Hans": (
            "Pro 完整版包含全部 37 个注音符号及相关学习内容，可离线使用，不含广告。"
            "下载时一次付费即可使用完整内容，没有额外的应用内购买或订阅。"
        ),
        "id": (
            "Edisi Pro mencakup semua 37 simbol Zhuyin beserta latihan bunyi dan nada. "
            "Bayar sekali saat mengunduh untuk memperoleh versi lengkap, tanpa pembelian "
            "tambahan di dalam aplikasi atau langganan. Dapat digunakan tanpa koneksi "
            "internet dan tanpa iklan."
        ),
        "ms": (
            "Edisi Pro merangkumi kesemua 37 simbol Zhuyin serta latihan bunyi dan nada. "
            "Bayar sekali ketika memuat turun untuk mendapatkan versi penuh, tanpa "
            "pembelian tambahan dalam aplikasi atau langganan. Boleh digunakan di luar "
            "talian tanpa iklan."
        ),
        "th": (
            "รุ่น Pro รวมสัญลักษณ์จู้อินครบทั้ง 37 ตัว พร้อมกิจกรรมฝึกเสียงและวรรณยุกต์ "
            "ชำระเงินครั้งเดียวตอนดาวน์โหลดเพื่อรับเนื้อหาครบทั้งหมด "
            "ไม่มีการซื้อเพิ่มเติมในแอปหรือการสมัครสมาชิก ใช้งานออฟไลน์ได้และไม่มีโฆษณา"
        ),
        "vi": (
            "Phiên bản Pro có đủ 37 ký hiệu chú âm Zhuyin cùng các bài luyện âm và "
            "thanh điệu. Thanh toán một lần khi tải ứng dụng để dùng toàn bộ nội dung; "
            "không có khoản mua thêm trong ứng dụng hay gói đăng ký. Có thể dùng ngoại "
            "tuyến và không có quảng cáo."
        ),
        "ar-SA": (
            "يتضمن إصدار Pro جميع رموز Zhuyin وعددها 37 رمزًا، مع أنشطة للأصوات والنغمات. "
            "تدفع مرة واحدة عند تنزيل التطبيق للحصول على جميع المحتويات، بلا مشتريات "
            "إضافية داخل التطبيق أو اشتراك. يعمل دون اتصال بالإنترنت ولا يعرض إعلانات."
        ),
    },
    "lumiletterspro": {
        "zh-Hans": (
            "Pro 完整版涵盖全部 26 个英文字母、字母发音和描红练习，可离线使用，不含广告。"
            "下载时一次付费即可使用完整内容，没有额外的应用内购买或订阅。"
        ),
        "id": (
            "Edisi Pro menyediakan semua 26 huruf bahasa Inggris, bunyi huruf, dan latihan "
            "menebalkan huruf. Bayar sekali saat mengunduh untuk memperoleh versi lengkap, "
            "tanpa pembelian tambahan di dalam aplikasi atau langganan. Dapat digunakan "
            "tanpa koneksi internet dan tanpa iklan."
        ),
        "ms": (
            "Edisi Pro menyediakan kesemua 26 huruf bahasa Inggeris, bunyi huruf dan latihan "
            "menyurih huruf. Bayar sekali ketika memuat turun untuk mendapatkan versi penuh, "
            "tanpa pembelian tambahan dalam aplikasi atau langganan. Boleh digunakan "
            "di luar talian tanpa iklan."
        ),
        "th": (
            "รุ่น Pro รวมตัวอักษรภาษาอังกฤษทั้ง 26 ตัว เสียงตัวอักษร และแบบฝึกลากเส้น "
            "ชำระเงินครั้งเดียวตอนดาวน์โหลดเพื่อรับเนื้อหาครบทั้งหมด "
            "ไม่มีการซื้อเพิ่มเติมในแอปหรือการสมัครสมาชิก ใช้งานออฟไลน์ได้และไม่มีโฆษณา"
        ),
        "vi": (
            "Phiên bản Pro có đủ 26 chữ cái tiếng Anh, âm chữ cái và bài tập tô chữ. "
            "Thanh toán một lần khi tải ứng dụng để dùng toàn bộ nội dung; không có "
            "khoản mua thêm trong ứng dụng hay gói đăng ký. Có thể dùng ngoại tuyến "
            "và không có quảng cáo."
        ),
        "ar-SA": (
            "يتضمن إصدار Pro جميع الحروف الإنجليزية وعددها 26 حرفًا، وأصواتها وتمارين "
            "تتبّع كتابتها. تدفع مرة واحدة عند تنزيل التطبيق للحصول على جميع المحتويات، "
            "بلا مشتريات إضافية داخل التطبيق أو اشتراك. يعمل دون اتصال بالإنترنت ولا يعرض إعلانات."
        ),
    },
}
DISCLOSURES = {
    "zh-Hans": "本指南由应用开发者 Lumi Studio 编写，并非独立评测或竞品测试。",
    "id": "Panduan ini disusun oleh Lumi Studio, pengembang aplikasi ini, bukan ulasan independen atau pengujian produk pesaing.",
    "ms": "Panduan ini disediakan oleh Lumi Studio, pembangun aplikasi ini. Panduan ini bukan ulasan bebas atau ujian produk pesaing.",
    "th": "คู่มือนี้จัดทำโดย Lumi Studio ผู้พัฒนาแอป ไม่ใช่รีวิวอิสระหรือผลทดสอบผลิตภัณฑ์คู่แข่ง",
    "vi": "Hướng dẫn này do Lumi Studio, nhà phát triển ứng dụng, biên soạn; đây không phải bài đánh giá độc lập hay thử nghiệm sản phẩm cạnh tranh.",
    "ar-SA": "هذا دليل من إعداد Lumi Studio، مطوّر التطبيق، وليس مراجعة مستقلة أو اختبارًا لمنتجات منافسة.",
}

REVISIONS = {
    ("lumibopomofopro", "zh-Hans"): (("Lumi 注音星球", "Lumi Bopomofo Pro"),),
    ("lumibopomofopro", "id"): (
        ("sistem fonetik Mandarin Tionghoa", "sistem notasi fonetik untuk bahasa Mandarin"),
        ("Bisa dimainkan offline, tanpa iklan", "Bisa dimainkan tanpa koneksi internet, tanpa iklan"),
        ("Sekali beli dengan pembuka kunci dalam app", "Semua 37 simbol termasuk dalam versi Pro"),
    ),
    ("lumibopomofopro", "ms"): (
        ("Pembelian sekali dengan buka kunci dalam app", "Kesemua 37 simbol disertakan dalam versi Pro"),
    ),
    ("lumibopomofopro", "th"): (
        ("Lumi โปโปโมโฟ", "Lumi Bopomofo Pro "),
        ("ซื้อครั้งเดียวเพื่อปลดล็อกในแอป", "รวมสัญลักษณ์จู้อินครบทั้ง 37 ตัวในรุ่น Pro"),
    ),
    ("lumibopomofopro", "vi"): (
        ("Mua một lần để mở khóa trong ứng dụng", "Phiên bản Pro có đủ 37 ký hiệu chú âm"),
    ),
    ("lumibopomofopro", "ar-SA"): (
        ("Lumi بوبوموفو", "Lumi Bopomofo Pro"),
        ("شراء لمرة واحدة مع فتح داخل التطبيق", "يتضمن إصدار Pro جميع الرموز وعددها 37 رمزًا"),
    ),
    ("lumiletterspro", "zh-Hans"): (
        ("描写练习", "描红练习"),
        ("按正确笔顺描写大写和小写字母", "按正确笔顺练习大写和小写字母的描红"),
    ),
    ("lumiletterspro", "id"): (
        ("Tanpa iklan, bisa offline, aman untuk keluarga", "Tanpa iklan dan bisa digunakan tanpa koneksi internet"),
    ),
    ("lumiletterspro", "ms"): (
        ("susunan goresan yang betul", "urutan garisan yang betul"),
        ("Ketik untuk mendengar bunyi huruf dan sebutan", "Sentuh huruf untuk mendengar bunyi dan sebutannya"),
        ("melalui bermain", "sambil bermain"),
        ("Tiada iklan, boleh digunakan offline dan selamat", "Tiada iklan dan boleh digunakan di luar talian"),
    ),
    ("lumiletterspro", "th"): (
        ("Lumi ABC เด็ก Pro", "Lumi Letters Pro"),
        ("ฝึกลากตัวพิมพ์ใหญ่และพิมพ์เล็ก", "ฝึกลากเส้นตัวพิมพ์ใหญ่และพิมพ์เล็ก"),
    ),
    ("lumiletterspro", "vi"): (
        ("Lumi Chữ Cái Pro", "Lumi Letters Pro"),
        ("âm chữ rõ ràng", "âm chữ cái rõ ràng"),
    ),
    ("lumiletterspro", "ar-SA"): (
        ("Lumi حروف Pro", "Lumi Letters Pro"),
        ("تحديات الكواكب تنمّي التركيز والذاكرة من خلال اللعب", "تحديات كوكبية تتضمن أنشطة للتذكر والانتباه أثناء اللعب"),
    ),
}
LTR_RUN = re.compile(r"[A-Za-z0-9]+(?:[ \t:/+&.#'’@%=_~?()\-–‑]+[A-Za-z0-9]+)*")


def external_values(key, locale, source, *, app_id, purchase_model):
    values = dict(source)
    if (key, locale) not in TARGET_CELLS:
        return values
    if str(app_id) != APP_IDS[key] or purchase_model != "paid_upfront":
        raise ValueError(f"P0-02 identity or purchase model changed: {key}/{locale}")
    description = values.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"P0-02 description missing: {key}/{locale}")
    native = NATIVE_PARAGRAPHS[key][locale]
    marker = ENGLISH_PARAGRAPHS[key]
    if marker in description:
        if description.count(marker) != 1:
            raise ValueError(f"Duplicated P0-02 English paragraph: {key}/{locale}")
        description = description.replace(marker, native)
    elif native not in description:
        raise ValueError(f"P0-02 source changed; native review required: {key}/{locale}")
    for old, new in REVISIONS.get((key, locale), ()):
        description = description.replace(old, new)
    if re.search(r"\bPro edition\b", description):
        raise ValueError(f"Unreviewed English fallback: {key}/{locale}")
    if DISCLOSURES[locale] not in description:
        description += "\n\n" + DISCLOSURES[locale]
    values["description"] = description
    return values


def html_text(key, locale, value):
    """Isolate mixed Latin tokens only in the two repaired Arabic pages."""
    if (key, locale) not in TARGET_CELLS or locale != "ar-SA":
        return html.escape(value)
    parts, end = [], 0
    for match in LTR_RUN.finditer(value):
        parts.append(html.escape(value[end:match.start()]))
        parts.append(f'<bdi dir="ltr">{html.escape(match.group())}</bdi>')
        end = match.end()
    parts.append(html.escape(value[end:]))
    return "".join(parts)
