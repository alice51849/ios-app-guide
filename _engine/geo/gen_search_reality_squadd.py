#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜尋實況母語意圖頁：千萬作戰小組 D（8 款 × 德文／日文／泰文）→ <Guide>/<lang>/seasonal/<slug>.html。

背景（aso/search_reality/<key>.json 與 reports/per_app/cards/<key>.md 的實測名次）：
- 遮個資（maskmyfile）德國「pdf schwärzen」第 49，前 10 一半以上是弱對手。
- PicClear（picclear）日本「容量を軽くするアプリ」搜尋建議第 1，前 10 一半以上是弱對手。
- QR Code Halo（qrcodehalo）德國「qr code prüfen」第 32。
- 麻糬打卡（mochidonestamp）泰國「บันทึกครั้งล่าสุด」第 3。
- 100 Notes Studio（notesstudio100）泰國「จดโน้ตด้วยลายมือ」第 16。
- PhotoCream（photocream）泰國「ฟิลเตอร์ฟิล์ม」第 8。
- MoneyTag（moneytag）德國「nebenjob einnahmen」第 6（日文頁已在 g3，不重做）。
- OnePage PPT（onepageppt）泰國「สรุปหน้าเดียว」第 1（簡中頁已在 g3，這頁守住泰國第 1）。

沿用第 3 組產生器（gen_search_reality_g3.py）的版面、檢查、Google Play 補連結與 sitemap 合併，只換頁面內容
（德文語系表照 gen_search_reality_easyam.py，泰文語系表照同格式新增）。規則：
- 功能句只取 data/<key>_full.json 該語系商店文案；不寫價格、免費、Free、Pro、試用、訂閱。
  商店名本身含「Pro」的兩款（PicClear Pro、PhotoCream Pro）只在品牌名裡出現，其餘 Pro 一律擋。
- 不寫摺疊、Duo 相關宣稱。
- 每頁一張主卡，附該國 App Store 直連（pt＋ct＋mt）；ct＝gw 階梯碼（gw_campaign.py，款 × 國家 × 詞群 sr）。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 專屬內容：日文 ≥450 字、德文 ≥450 詞、泰文 ≥450 個泰文字。只寫這些頁與各語系 sitemap_seasonal_<lang>.xml
  的這幾列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_squadd.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_squadd.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gen_search_reality_easyam as easyam  # noqa: E402
import gen_search_reality_g3 as g3  # noqa: E402

LANGS = dict(g3.LANGS)
LANGS["de-DE"] = easyam.LANGS["de-DE"]
LANGS["th"] = {"store": "th", "dir": "th", "cc": "th", "og": "th_TH", "html": "th",
               "home": "คู่มือแอป iOS", "answers": "คำตอบ", "about": "เกี่ยวกับเรา", "crumb": "แนะนำ",
               "updated": "อัปเดต", "cta": "ดาวน์โหลดบน App Store →", "more": "ดูรายละเอียดแอป",
               "faq": "คำถามที่พบบ่อย", "related": "หน้าที่เกี่ยวข้อง", "toc": "ในหน้านี้", "home_label": "หน้าแรก"}
APP_IDS = {
    "maskmyfile": "6792850916", "picclear": "6780223070", "qrcodehalo": "6806779853",
    "mochidonestamp": "6790800323", "notesstudio100": "6798813048", "photocream": "6781808054",
    "moneytag": "6801956402", "onepageppt": "6798814385",
}
# easyam 的禁用字＋泰文（ฟรี、ทดลองใช้、บาท、฿）＋德文試用字；Pro 只放行商店名裡的「PicClear Pro」「PhotoCream Pro」。
BANNED = re.compile(
    r"免費|免费|無料|무료|ฟรี|ทดลองใช้|บาท|฿|\bfree\b|(?<!PicClear )(?<!PhotoCream )\bpro\b|kostenlos|gratis|"
    r"Testversion|Probeabo|NT\$|US\$|\$\s?\d|€\s?\d|\d\s?€|¥\s?\d|￥|\d\s?円|\d\s?元|\d\s?원",
    re.IGNORECASE,
)
THAI = re.compile(r"[฀-๿]")


def dedicated_size(lang: str, text: str) -> int:
    if lang == "th":
        return len(THAI.findall(text))
    return easyam.dedicated_size(lang, text)


PAGE_SPECS: list[dict] = [
    # 1 遮個資 × 德國「pdf schwärzen」（第 49）
    {
        "key": "maskmyfile", "lang": "de-DE",
        "slug": "pdf-schwaerzen-iphone-dauerhaft-ohne-upload",
        "terms": ["pdf schwärzen", "dokumente schwärzen", "pdf anonymisieren"],
        "title": "PDF schwärzen auf dem iPhone: dauerhaft, ohne Upload – worauf es wirklich ankommt",
        "desc": "Mietbewerbung, Gehaltsabrechnung oder Ausweiskopie verschicken, aber Namen, Nummern und Kontodaten sollen weg? Woran du erkennst, ob ein PDF wirklich geschwärzt ist, und wie Mask My File das direkt auf dem iPhone erledigt. Mit Link zum deutschen App Store.",
        "h1": "PDF schwärzen auf dem iPhone: so verschwinden Daten wirklich, nicht nur optisch",
        "lead": "Wer im App Store nach „PDF schwärzen“ sucht, hat meistens gerade ein Dokument vor sich, das gleich verschickt werden soll: eine Mietbewerbung, eine Gehaltsabrechnung, eine Kundendatei oder die Kopie eines Ausweises.",
        "intro": [
            "Das Problem: Ein schwarzer Kasten, den man in einem PDF-Programm oder in der Fotos-App über den Text malt, ist oft nur eine Ebene obendrauf. Der Text darunter lässt sich je nach Datei weiterhin markieren, kopieren oder durchsuchen, und in den Metadaten stehen manchmal noch Name, Gerät oder Erstellungsdatum. Wer sicher gehen will, braucht ein Werkzeug, das die Stellen dauerhaft entfernt und das Ergebnis danach noch einmal prüft.",
            "Im Oktober 2026 haben wir im deutschen App Store nachgesehen: Bei „pdf schwärzen“ schlägt die Suche gleich mehrere kleine Apps mit genau diesem Namen vor, viele davon mit kaum Bewertungen. Unten steht, worauf du bei der Auswahl achten solltest und wie Mask My File konkret vorgeht.",
        ],
        "sections": [
            ("Fünf Dinge, die eine Schwärzen-App können muss", [], [
                "Dauerhaft statt nur abgedeckt: Mask My File schwärzt visuelle Dateien mit einem deckenden Balken oder entfernt die Stelle ganz.",
                "Selbst finden statt suchen: Die App findet Namen, Telefonnummern, E-Mail-Adressen, Anschriften sowie Konto- und Zahlungsdaten und schwärzt nur das, was du auswählst.",
                "Mehr als nur PDF: Fotos, Screenshots und Textdateien funktionieren genauso; bei Text, JSON, XML, HTML, CSV, TSV und RTF wählst du zwischen vollständiger Maske, Teilmaske, Platzhalter, Pseudonym oder Entfernen.",
                "Metadaten mitdenken: Wo das Format es zulässt, entfernt Mask My File auch Metadaten.",
                "Original bleibt unberührt: Das Original wird nie überschrieben. Du bekommst eine neue Kopie, die erneut geöffnet und geprüft wird.",
            ]),
            ("Drei typische Situationen", [
                "Mietbewerbung: Der Vermieter will eine Gehaltsabrechnung sehen, aber nicht deine Steuer-ID oder deine Kontonummer. Öffne das PDF, lass die App nach Nummern und Kontodaten suchen und arbeite Seite für Seite die Treffer durch, bevor du die neue Kopie verschickst.",
                "Ausweiskopie: Für eine Buchung reicht oft ein Teil der Angaben. Bei Fotos markiert die Gesichts- und Barcode-Erkennung nur Bereiche zu deiner Prüfung; du entscheidest selbst, was geschwärzt wird. Die Vorschau in voller Breite mit Zoom bis 5× hilft bei kleinen Zeilen.",
                "Kundendateien im Job: Wenn mehrere Dateien dieselben Namen enthalten, verarbeitest du bis zu 100 Dateien mit eigener Vorschau, dateiübergreifender Suche und manueller Auswahl für jede Datei.",
            ], []),
            ("Was mit deinen Daten passiert", [
                "Alles wird auf deinem Gerät verarbeitet. Es gibt kein Konto, keine Werbung, kein Tracking, keine Analyse und kein Hochladen von Inhalten. Apple Vision und das integrierte Tesseract OCR laufen lokal.",
                "Die Gesichtserkennung erstellt nur Bereiche: Sie identifiziert niemanden, erstellt keine Vorlage und teilt oder speichert keine Gesichtsdaten.",
            ], []),
        ],
        "steps_title": "In fünf Schritten zum geschwärzten PDF",
        "steps": [
            "Mask My File öffnen und das PDF, Foto oder den Screenshot auswählen.",
            "Die gefundenen Namen, Nummern und Adressen durchsehen.",
            "Auswählen, was geschwärzt oder entfernt werden soll; bei Bedarf manuell ergänzen.",
            "Die neue Kopie erstellen lassen; sie wird erneut geöffnet und geprüft.",
            "Erst dann die Kopie verschicken. Das Original bleibt unverändert.",
        ],
        "cards": [
            ("maskmyfile", "Schwärze persönliche Daten, bevor du teilst: Mask My File findet Namen, Telefonnummern, E-Mail-Adressen, Anschriften, Konto- und Zahlungsdaten und schwärzt dauerhaft nur das, was du auswählst. Funktioniert mit PDFs, Fotos, Screenshots und Textdateien und entfernt Metadaten, wo das Format es zulässt. Das Original wird nie überschrieben. Alles läuft auf deinem Gerät, ohne Konto und ohne Werbung."),
        ],
        "faqs": [
            ("Werden meine Dokumente hochgeladen?", "Nein. Alles wird auf deinem Gerät verarbeitet; es gibt kein Hochladen von Inhalten, kein Tracking und keine Analyse."),
            ("Kann man die Schwärzung später wieder entfernen?", "Mask My File schwärzt dauerhaft mit einem deckenden Balken oder entfernt die Stelle. Die neue Kopie wird erneut geöffnet und geprüft; das Original bleibt unverändert."),
            ("Funktioniert das auch mit Screenshots und Fotos?", "Ja. PDFs, Fotos, Screenshots und Textdateien werden unterstützt. Gesichts- und Barcode-Erkennung markieren nur Bereiche zu deiner Prüfung."),
            ("Brauche ich ein Konto?", "Nein. Mask My File funktioniert ohne Konto und ohne Werbung."),
        ],
        "related": [("de-DE/hubs/maskmyfile.html", "Mask My File: häufige Fragen"),
                    ("de-DE/answers/best-mask-app.html", "Ratgeber: Apps zum Schwärzen")],
        "legal": "Die vorgestellte App ist eine unabhängige Entwicklung. Die App-Store-Suchergebnisse stammen aus einer eigenen Abfrage im Oktober 2026; die Reihenfolge kann sich ändern.",
    },
    # 2 PicClear × 日本「容量を軽くするアプリ」（搜尋建議第 1）
    {
        "key": "picclear", "lang": "ja",
        "slug": "iphone-yoryo-karuku-suru-app-chofuku-shashin",
        "terms": ["容量を軽くするアプリ", "重複写真削除", "容量不足 解消"],
        "title": "iPhoneの容量を軽くするアプリの選び方：重複写真・スクショ・大きな動画から片付ける5つのポイント",
        "desc": "「ストレージがいっぱいです」と出て写真も撮れない。容量を軽くするアプリは、何を見つけて、削除前にどう確認できるかで選びましょう。重複写真・類似写真・古いスクショ・ピンボケ・大きな動画の片付け方と、日本の App Store へのリンクをまとめました。",
        "h1": "iPhoneの容量を軽くするアプリ：写真を消しすぎずに空き容量を取り戻す",
        "lead": "App Store で「容量を軽くするアプリ」と検索する人の多くは、ちょうど「ストレージがいっぱいです」という通知を見たところです。写真が撮れない、アップデートができない、でも大事な写真は消したくない。",
        "intro": [
            "iPhone の容量を一番使っているのは、たいてい写真と動画です。同じ写真が二重に保存されていたり、連写でほぼ同じ写真が何十枚も残っていたり、もう必要のないスクリーンショットがたまっていたり。一枚ずつ探して消すのは時間がかかりますし、勢いで消して大事な一枚まで失うのも怖いところです。",
            "2026年10月に日本の App Store を実際に検索したところ、「容量を軽くするアプリ」は検索候補の1番目に出てくる言葉でした。ここでは、アプリを選ぶときに見るべきポイントと、PicClear Pro の実際の使い方をまとめます。",
        ],
        "sections": [
            ("容量を軽くするアプリ、まずこの5点を確認", [], [
                "何を見つけられるか：重複写真、連写やほぼ同じ類似写真、古いスクショ、ピンボケ写真、大きな動画、大きな写真まで種類ごとに見つけます。",
                "残す1枚を提案してくれるか：似た写真や連写は自動でグループにまとめ、各グループで残すべきベストな1枚を提案します。",
                "削除前に確認できるか：サムネイルのプレビューで何が削除されるかを正確に確認でき、確認するまで何も削除しません。",
                "お気に入りが守られるか：「お気に入り」は保護され、自動で選択されることはありません。",
                "写真が外に出ないか：分析はすべて iPhone 上で行い、写真はアップロードされません。アカウント登録も不要です。",
            ]),
            ("よくある3つの場面", [
                "旅行のあと：連写や同じ構図の写真が大量に残りがちです。類似写真のグループを順に見て、提案されたベストな1枚を残せば、思い出はそのままで枚数だけ減らせます。",
                "仕事や買い物のスクショ：レシート、地図、乗り換え案内など、その時だけ必要だったスクリーンショットは意外と多いものです。スクリーンショットだけをまとめて確認して片付けられます。",
                "子どもやペットの動画：数分の動画が何本もあると、それだけで数GBになることがあります。ライブラリで最も容量を使う原因になっている大きな動画から見直すのが近道です。",
            ], []),
            ("消したあとが心配なとき", [
                "削除した項目はまず「写真」の「最近削除した項目」に移動するので、一定期間は復元できます。あとから必要だったと気づいても、すぐに取り戻せます。",
                "完全オフラインで動作し、広告やトラッキング、サードパーティ解析もありません。Siri・Spotlight・ショートカット・アクションボタンからスマートスキャンを始めることもできます。",
            ], []),
        ],
        "steps_title": "はじめての片付け、5ステップ",
        "steps": [
            "PicClear Pro を開いて、写真へのアクセスを許可します。",
            "スマートスキャンで、重複・類似・スクショ・ピンボケ・大きな動画を探します。",
            "グループごとにプレビューして、提案された残す1枚を確認します。",
            "消してよいものだけを選んで削除します。",
            "必要なら「最近削除した項目」から一定期間は復元できます。",
        ],
        "cards": [
            ("picclear", "重複写真、類似写真、古いスクショ、ピンボケ写真、大きな動画を端末内で見つけ、削除前に1枚ずつ確認できます。似た写真や連写は自動でグループにまとめ、残すべきベストな1枚を提案。「お気に入り」が自動で選ばれることはありません。分析はすべて iPhone 上で行い、写真はアップロードされません。アカウント登録不要、広告なし。"),
        ],
        "faqs": [
            ("写真がどこかにアップロードされませんか？", "されません。分析はすべて iPhone 上で行い、完全オフラインで動作します。アカウント登録も不要です。"),
            ("間違って消してしまったら？", "削除した項目はまず「写真」の「最近削除した項目」に移動するので、一定期間は復元できます。"),
            ("大事な写真まで選ばれてしまいませんか？", "確認するまで何も削除しません。「お気に入り」は保護され、自動で選択されることはありません。"),
            ("どんなものを見つけてくれますか？", "重複写真、類似写真、スクリーンショット、ぼやけた写真、大きな動画、大きな写真です。"),
        ],
        "related": [("ja/hubs/picclear.html", "PicClear Pro のよくある質問")],
        "legal": "本ページで紹介するアプリは独立開発です。App Store の検索結果は2026年10月に実際に検索したもので、順位は変わることがあります。",
    },
    # 3 QR Code Halo × 德國「qr code prüfen」（第 32）
    {
        "key": "qrcodehalo", "lang": "de-DE",
        "slug": "qr-code-pruefen-vor-dem-oeffnen-iphone",
        "terms": ["qr code prüfen", "qr code scanner sicher", "safe qr scanner"],
        "title": "QR-Code prüfen, bevor er sich öffnet: So erkennst du verdächtige Links auf dem iPhone",
        "desc": "Ein QR-Code auf dem Parkautomaten, im Brief oder auf dem Restauranttisch – und die Frage, ob er echt ist. Worauf ein sicherer QR-Scanner achten sollte und wie QR Code Halo jeden Code direkt auf dem Gerät als sicher, Vorsicht oder blockiert einstuft. Mit Link zum deutschen App Store.",
        "h1": "QR-Code prüfen: erst ansehen, dann öffnen",
        "lead": "Wer im App Store nach „QR Code prüfen“ sucht, hat meistens gerade einen Code vor sich, dem er nicht ganz traut: einen Aufkleber am Parkautomaten, einen Code in einem Brief oder eine Zahlungsaufforderung auf einem Zettel.",
        "intro": [
            "Die Kamera-App des iPhone zeigt beim Scannen nur kurz eine Adresse an, und ein Tipp genügt, um die Seite zu öffnen. Gefälschte Codes setzen genau darauf: Ein Aufkleber über dem echten Code führt auf eine Seite, die fast so aussieht wie die richtige. Ob eine Adresse echt ist, erkennt man auf dem kleinen Bildschirm schwer, vor allem wenn eine Domain Buchstaben aus verschiedenen Alphabeten mischt.",
            "Im Oktober 2026 haben wir im deutschen App Store nachgesehen: Bei „qr code prüfen“ stehen vor allem allgemeine Scanner vorn, die einen Link sofort öffnen. Unten steht, worauf du achten solltest und wie QR Code Halo das Prüfen löst.",
        ],
        "sections": [
            ("Fünf Dinge, die ein sicherer QR-Scanner können sollte", [], [
                "Nicht automatisch öffnen: Wenn du „Nach Scan ausführen“ ausschaltest, prüfst du bei QR Code Halo jeden Code, bevor etwas passiert.",
                "Den Link zerlegen: Direkt auf dem Gerät zerlegt die App den Inhalt in scheme, host, path, query und fragment, damit du siehst, wohin der Code wirklich führt.",
                "Klare Einstufung: Verdächtige URLs, Links ohne HTTPS und Domains mit gemischten Alphabeten werden als sicher, Vorsicht oder blockiert markiert.",
                "Gefährliche Arten nie öffnen: Codes mit javascript:, data: und file: werden nie geöffnet; eine Aktion, die sich nicht sicher interpretieren lässt, bleibt blockiert.",
                "Nachvollziehbar statt Punktwert: Feste Regeln liefern das Ergebnis mit nachvollziehbaren Befunden, ohne Online-Reputationsabfrage und ohne unscharfen Punktwert.",
            ]),
            ("Drei typische Situationen", [
                "Parkautomat oder Ladesäule: Scanne den Code, öffne ihn im Verlauf und tippe auf „Sicherheitscheck“. Wenn die Domain nicht zum Betreiber passt oder als Vorsicht markiert ist, zahlst du lieber über den bekannten Weg.",
                "Brief oder Paketbenachrichtigung: Auch Codes aus einem Foto lassen sich erkennen, mehrere Codes in einem Bild. So prüfst du einen Code aus einem Schreiben, ohne ihn erst mit der Kamera öffnen zu müssen.",
                "Eigener Code im Laden oder Verein: Sichere ein Ergebnis als lokale Referenz. Einen späteren Scan vergleicht QR Verification anhand des vollständigen SHA-256-Fingerabdrucks, des QR-Formats, des Inhaltstyps und der URL-Komponenten. So fällt auf, wenn jemand den Aufkleber ausgetauscht hat.",
            ], []),
            ("Mehr als nur prüfen", [
                "QR Code Halo scannt QR-Codes und Barcodes in 20 Formaten mit der Kamera oder aus einem Foto. WLAN-Codes zeigen direkt die Abfrage zum Verbinden, und du erstellst 9 Arten von QR-Codes, etwa für WLAN, Kontakte und Termine.",
                "Jeder Scan außerhalb des Stapel-Scans wird auf diesem Gerät im Verlauf gesichert, außer „Nicht im Verlauf sichern“ ist aktiv. Es gibt keine Werbung und kein Konto.",
            ], []),
        ],
        "steps_title": "Einen Code in fünf Schritten prüfen",
        "steps": [
            "In QR Code Halo „Nach Scan ausführen“ ausschalten.",
            "Den Code mit der Kamera scannen oder aus einem Foto erkennen lassen.",
            "Den Scan im Verlauf öffnen.",
            "Auf „Sicherheitscheck“ tippen und die Einstufung sicher, Vorsicht oder blockiert ansehen.",
            "Nur öffnen, wenn Domain und Einstufung passen.",
        ],
        "cards": [
            ("qrcodehalo", "Scanne QR-Codes und Barcodes in 20 Formaten mit der Kamera oder aus einem Foto. Im Verlauf tippst du auf „Sicherheitscheck“: Direkt auf dem Gerät zerlegt QR Code Halo den Link und markiert verdächtige URLs, Links ohne HTTPS und Domains mit gemischten Alphabeten als sicher, Vorsicht oder blockiert. Codes mit javascript:, data: und file: werden nie geöffnet. Ohne Werbung und ohne Konto."),
        ],
        "faqs": [
            ("Schickt die App meine Codes an einen Server?", "Nein. Der Sicherheitscheck läuft direkt auf dem Gerät mit festen Regeln; es gibt keine Online-Reputationsabfrage."),
            ("Kann ich verhindern, dass sich ein Link sofort öffnet?", "Ja. Schalte „Nach Scan ausführen“ aus, dann prüfst du jeden Code, bevor du ihn öffnest."),
            ("Woran erkennt die App einen verdächtigen Link?", "Sie markiert unter anderem verdächtige URLs, Links ohne HTTPS und Domains mit gemischten Alphabeten; Codes mit javascript:, data: und file: werden nie geöffnet."),
            ("Kann ich einen Code aus einem Foto prüfen?", "Ja. QR Code Halo erkennt Codes in Fotos, auch mehrere Codes in einem Bild."),
        ],
        "related": [("de-DE/hubs/qrcodehalo.html", "QR Code Halo: häufige Fragen")],
        "legal": "Die vorgestellte App ist eine unabhängige Entwicklung. Die App-Store-Suchergebnisse stammen aus einer eigenen Abfrage im Oktober 2026; die Reihenfolge kann sich ändern.",
    },
    # 4 麻糬打卡 × 泰國「บันทึกครั้งล่าสุด」（第 3）
    {
        "key": "mochidonestamp", "lang": "th",
        "slug": "app-bantuek-khrang-lasut-tuen-ngan-ban",
        "terms": ["บันทึกครั้งล่าสุด", "ทำครั้งล่าสุดเมื่อไร", "เตือนงานบ้าน"],
        "title": "แอปบันทึกครั้งล่าสุด: รู้ทันทีว่าทำไปเมื่อไร พร้อมเตือนเมื่อถึงรอบ",
        "desc": "เปลี่ยนผ้าปูที่นอน ล้างแผ่นกรองแอร์ เปลี่ยนน้ำมันเครื่องครั้งล่าสุดเมื่อไร? วิธีเลือกแอปบันทึกครั้งล่าสุด และวิธีใช้ Mochi DoneStamp แตะครั้งเดียวก็จำเวลาไว้ให้ พร้อมลิงก์ App Store ประเทศไทย",
        "h1": "บันทึกครั้งล่าสุด: แตะครั้งเดียว แล้วไม่ต้องนั่งนึกอีกว่าทำไปเมื่อไร",
        "lead": "คนที่ค้นหา “บันทึกครั้งล่าสุด” ใน App Store ส่วนใหญ่เพิ่งเจอคำถามเดิมอีกครั้ง: ผ้าปูที่นอนเปลี่ยนไปเมื่อไร แผ่นกรองแอร์ล้างครั้งล่าสุดตอนไหน รดน้ำต้นไม้ไปหรือยัง",
        "intro": [
            "งานในบ้านหลายอย่างไม่ได้ทำทุกวัน แต่ต้องทำเป็นรอบ พอผ่านไปสักพักก็จำไม่ได้ว่าทำครั้งล่าสุดเมื่อไร จดในปฏิทินก็ยุ่งยาก ตั้งเตือนทุกเดือนแบบตายตัวก็ไม่ตรงกับวันที่ทำจริง สิ่งที่ต้องการจริงๆ คือกดบันทึกตอนทำเสร็จ แล้วให้แอปบอกว่าผ่านมานานแค่ไหนแล้ว",
            "เราค้นหาใน App Store ประเทศไทยจริงในปี 2026 คำว่า “บันทึกครั้งล่าสุด” มีแอปเล็กๆ หลายตัวขึ้นมา ด้านล่างคือสิ่งที่ควรดูตอนเลือกแอป และวิธีใช้ Mochi DoneStamp แบบเป็นขั้นตอน",
        ],
        "sections": [
            ("เลือกแอปบันทึกครั้งล่าสุด ดู 5 ข้อนี้ก่อน", [], [
                "บันทึกได้ในแตะเดียว: ทำเสร็จแล้วแตะครั้งเดียว Mochi DoneStamp จะบันทึกเวลาที่แน่นอน และเลิกทำได้ถ้ากดพลาด",
                "เห็นว่าผ่านมานานแค่ไหน: ดูได้ตลอดว่าทำครั้งล่าสุดผ่านมานานเท่าไรแล้ว",
                "รอบนับจากวันที่ทำจริง: ตั้งรอบไว้เพื่อรับการแจ้งเตือนเมื่อถึงกำหนด วันถัดไปจะนับจากวันที่คุณทำจริงเสมอ",
                "รอบยืดหยุ่น: ตั้งรอบได้ทั้งแบบยืดหยุ่นหรือแม่นยำ ตั้งแต่นาทีถึงปี และเพิ่ม แก้ไข หรือลบเวลาในอดีตได้",
                "เตือนแล้วจัดการได้ทันที: การแจ้งเตือนในเครื่องมีปุ่มเสร็จแล้วและเตือนภายหลัง",
            ]),
            ("ใช้กับอะไรได้บ้าง", [
                "งานบ้านเป็นรอบ: เปลี่ยนผ้าปูที่นอน ล้างแผ่นกรองแอร์ เปลี่ยนไส้กรองน้ำ ทำเสร็จแล้วกดประทับว่าทำแล้ว Mochi จะจำไว้และเตือนเมื่อถึงรอบ",
                "รถและของใช้: บันทึกวันเปลี่ยนน้ำมันเครื่องรถ แล้วใส่โน้ตหรือรูปภาพแบบเลือกได้ไว้ดูภายหลัง",
                "ต้นไม้และสัตว์เลี้ยง: บันทึกการรดน้ำต้นไม้ แล้วดูสถิติช่วงเวลาว่าโดยเฉลี่ยทำห่างกันกี่วัน แชร์กับครอบครัวได้ด้วย จะได้ไม่ต้องถามกันว่าใครทำไปแล้ว",
            ], []),
            ("ใช้สะดวกทุกที่", [
                "มีวิดเจ็ตโต้ตอบบนหน้าจอโฮมและหน้าจอล็อก คำสั่งลัด Siri และแอป Apple Watch สำหรับดูครั้งล่าสุดและบันทึกได้จากข้อมือ รองรับโหมดมืด iPad VoiceOver และ Dynamic Type",
                "ไม่ต้องมีบัญชี ไม่มีโฆษณา การวิเคราะห์ หรือการติดตาม ข้อมูลหลักอยู่บนอุปกรณ์ สำรองข้อมูลเต็มและส่งออก JSON ได้",
            ], []),
        ],
        "steps_title": "เริ่มใช้ใน 1 นาที",
        "steps": [
            "เปิด Mochi DoneStamp แล้วเพิ่มเหตุการณ์ เช่น เปลี่ยนผ้าปูที่นอน",
            "ถ้าเคยทำไปแล้ว ใส่เวลาในอดีตย้อนหลังได้",
            "ตั้งรอบ เช่น ทุก 2 สัปดาห์ เพื่อรับการแจ้งเตือน",
            "ทำเสร็จเมื่อไรก็แตะครั้งเดียวเพื่อบันทึก",
            "เพิ่มวิดเจ็ตไว้บนหน้าจอโฮมเพื่อดูว่าผ่านมานานแค่ไหน",
        ],
        "cards": [
            ("mochidonestamp", "ไม่ต้องมานั่งนึกว่าทำครั้งล่าสุดเมื่อไร ทำเสร็จแล้วแตะครั้งเดียว Mochi DoneStamp จะบันทึกเวลาที่แน่นอน ให้เห็นได้ตลอดว่าผ่านมานานแค่ไหน ตั้งรอบไว้เพื่อรับการแจ้งเตือนเมื่อถึงกำหนด วันถัดไปนับจากวันที่ทำจริงเสมอ มีวิดเจ็ต Siri และ Apple Watch ไม่ต้องมีบัญชี ไม่มีโฆษณา"),
        ],
        "faqs": [
            ("ถ้าลืมกดบันทึกตอนทำเสร็จทำอย่างไร?", "เพิ่ม แก้ไข หรือลบเวลาในอดีตได้ จึงย้อนกลับมาใส่วันที่ทำจริงภายหลังได้"),
            ("การเตือนนับจากวันไหน?", "ตั้งรอบไว้แล้ว วันถัดไปจะนับจากวันที่คุณทำจริงเสมอ ไม่ใช่วันที่ตั้งไว้ตอนแรก"),
            ("ต้องสมัครบัญชีไหม?", "ไม่ต้องมีบัญชี ไม่มีโฆษณา การวิเคราะห์ หรือการติดตาม ข้อมูลหลักอยู่บนอุปกรณ์"),
            ("ใช้กับ Apple Watch ได้ไหม?", "ได้ ดูครั้งล่าสุดและบันทึกได้จากข้อมือ"),
        ],
        "related": [("th/hubs/mochidonestamp.html", "Mochi DoneStamp: คำถามที่พบบ่อย")],
        "legal": "แอปที่แนะนำในหน้านี้พัฒนาโดยอิสระ ผลการค้นหาใน App Store มาจากการค้นหาจริงในปี 2026 และลำดับอาจเปลี่ยนแปลงได้",
    },
    # 5 100 Notes Studio × 泰國「จดโน้ตด้วยลายมือ」（第 16）
    {
        "key": "notesstudio100", "lang": "th",
        "slug": "app-jot-note-duay-laimue-sarup-bot-rian-pdf",
        "terms": ["จดโน้ตด้วยลายมือ", "แอปจดโน้ต", "สรุปบทเรียน"],
        "title": "แอปจดโน้ตด้วยลายมือ: เลือกอย่างไรให้เขียนลื่นเหมือนกระดาษ และทบทวนก่อนสอบได้",
        "desc": "อยากจดโน้ตด้วยลายมือบน iPad หรือ iPhone ให้ฟีลเหมือนปากกาบนกระดาษ ขีดเน้นบน PDF ชีทเรียน และอัดเสียงคาบเรียนไว้ในหน้าเดียวกัน? วิธีเลือกแอปและวิธีใช้ 100 Notes Studio พร้อมลิงก์ App Store ประเทศไทย",
        "h1": "จดโน้ตด้วยลายมือ: เขียน ขีดเน้น อัดเสียง แล้วทบทวนในแอปเดียว",
        "lead": "คนที่ค้นหา “จดโน้ตด้วยลายมือ” ใน App Store ส่วนใหญ่เป็นนักเรียน นักศึกษา หรือคนทำงานที่อยากเลิกพกสมุดหลายเล่ม แต่ยังอยากเขียนด้วยมือเหมือนเดิม",
        "intro": [
            "การจดด้วยลายมือช่วยให้จำได้ดี แต่สมุดกระดาษค้นหาย้อนหลังยาก ชีทเรียนเป็นไฟล์ PDF ก็ต้องพิมพ์ออกมาก่อนถึงจะขีดเน้นได้ ส่วนเสียงที่อัดในคาบเรียนก็แยกอยู่อีกแอป พอถึงช่วงสอบจึงต้องเปิดหลายที่พร้อมกัน",
            "เราค้นหาใน App Store ประเทศไทยจริงในปี 2026 คำว่า “จดโน้ตด้วยลายมือ” มีทั้งแอปใหญ่และแอปเล็กปะปนกัน ด้านล่างคือสิ่งที่ควรดูตอนเลือก และวิธีใช้ 100 Notes Studio ช่วงปลายปีถึงช่วงสอบ",
        ],
        "sections": [
            ("เลือกแอปจดโน้ตด้วยลายมือ ดู 5 ข้อนี้", [], [
                "ฟีลการเขียน: มีปากกาและพู่กัน 29 แบบ ตั้งแต่ปากกาหมึกซึมและดินสอไปจนถึงพู่กันคัดลายมือและสีน้ำ แต่ละแบบมีพื้นผิวและน้ำหนักเส้นต่างกัน",
                "ปากกาดิจิทัล: ปากกาที่เข้ากันได้รองรับแรงกด มุมเอียง การกันฝ่ามือ การแตะสองครั้ง และการบีบด้าม",
                "ค้นหาลายมือได้: ค้นหาชื่อเรื่อง ข้อความ ลายมือ และไฟล์แนบด้วยการประมวลผลภายในอุปกรณ์",
                "ใช้กับ PDF ได้: นำเข้า PDF เพื่อไฮไลท์ ขีดเส้นใต้ ขีดทับ ใส่ข้อความ เขียน หมุน ตัดขอบ แทรก แยก รวมหน้า และส่งออกผลลัพธ์",
                "ใช้ออฟไลน์ได้: ฟังก์ชันแก้ไขหลักใช้งานได้แบบออฟไลน์ ไม่ต้องสร้างบัญชี",
            ]),
            ("ใช้ช่วงเรียนและช่วงสอบอย่างไร", [
                "ในคาบเรียน: เปิดชีทเรียน PDF แล้วเขียนทับได้เลย อัดเสียงไว้ในหน้าที่กำลังเขียน ไฟล์เสียงจะผูกกับหน้าที่เริ่มอัดเท่านั้น จึงกลับมาฟังพร้อมบริบทของหน้านั้นได้",
                "สรุปบทเรียน: เลือกหน้าคงที่หรือผืนผ้าใบไม่จำกัด ขนาด A4 A5 Letter หรือเท่าหน้าจอ ใช้ไม้บรรทัด เครื่องมือรูปทรง 8 แบบ และบ่วงเลือกจัดผังสรุปให้อ่านง่าย",
                "ก่อนสอบ: ทบทวนด้วยแฟลชการ์ด การ์ดเติมคำ และตารางเว้นระยะ FSRS เพื่อทวนเรื่องที่ใกล้ลืมก่อน",
            ], []),
            ("สมุดที่เป็นของคุณ", [
                "เลือกสไตล์สมุดได้ 100 แบบ มีทั้งมินิมอล ผ้าลินิน กระดาษจุด ตารางบันทึกการเรียน แผนงาน บรรทัดห้าเส้น ประชุม และสูตรอาหาร จัดระเบียบด้วยโฟลเดอร์ซ้อน แท็ก ปักหมุด และถังขยะที่กู้คืนได้",
                "ไม่มีโฆษณา ไม่มีตัวติดตามหรือระบบวิเคราะห์ของบุคคลที่สาม ข้อมูลเก็บในอุปกรณ์ และล็อกแอปหรือสมุดแต่ละเล่มด้วยการยืนยันตัวตนแบบชีวมิติของอุปกรณ์ได้",
            ], []),
        ],
        "steps_title": "เริ่มจดโน้ตแรกใน 1 นาที",
        "steps": [
            "เปิด 100 Notes Studio แล้วสร้างสมุดใหม่",
            "เลือกสไตล์สมุดและขนาดหน้า",
            "เลือกปากกาที่ชอบแล้วเริ่มเขียน",
            "นำเข้า PDF ชีทเรียนเพื่อขีดเน้น หรืออัดเสียงไว้ในหน้านั้น",
            "ก่อนสอบ เปิดโหมดทบทวนด้วยแฟลชการ์ด",
        ],
        "cards": [
            ("notesstudio100", "จดโน้ตด้วยลายมือได้ฟีลเหมือนปากกาบนกระดาษ ด้วยปากกาและพู่กัน 29 แบบ แล้วยังค้นหาลายมือของคุณได้ภายหลัง ทำเครื่องหมายบน PDF ชีทเรียน อัดเสียงไว้ในหน้าที่กำลังเขียน แล้วทบทวนด้วยแฟลชการ์ดและการทบทวนแบบเว้นระยะ เลือกสไตล์สมุดได้ 100 แบบ ใช้ออฟไลน์ได้ ไม่ต้องมีบัญชี ไม่มีโฆษณา"),
        ],
        "faqs": [
            ("ค้นหาสิ่งที่เขียนด้วยลายมือได้ไหม?", "ได้ ค้นหาชื่อเรื่อง ข้อความ ลายมือ และไฟล์แนบด้วยการประมวลผลภายในอุปกรณ์"),
            ("เขียนบน PDF ชีทเรียนได้ไหม?", "ได้ นำเข้า PDF เพื่อไฮไลท์ ขีดเส้นใต้ ขีดทับ ใส่ข้อความ เขียน และส่งออกผลลัพธ์"),
            ("ไม่มีอินเทอร์เน็ตใช้ได้ไหม?", "ได้ ฟังก์ชันแก้ไขหลักใช้งานได้แบบออฟไลน์ ข้อมูลเก็บในอุปกรณ์"),
            ("ต้องสร้างบัญชีไหม?", "ไม่ต้องสร้างบัญชี ไม่มีโฆษณา และไม่มีตัวติดตามของบุคคลที่สาม"),
        ],
        "related": [("th/hubs/notesstudio100.html", "100 Notes Studio: คำถามที่พบบ่อย")],
        "legal": "แอปที่แนะนำในหน้านี้พัฒนาโดยอิสระ ผลการค้นหาใน App Store มาจากการค้นหาจริงในปี 2026 และลำดับอาจเปลี่ยนแปลงได้",
    },
    # 6 PhotoCream × 泰國「ฟิลเตอร์ฟิล์ม」（第 8）
    {
        "key": "photocream", "lang": "th",
        "slug": "app-filter-film-klong-film-vintage-iphone",
        "terms": ["ฟิลเตอร์ฟิล์ม", "กล้องฟิล์ม", "ฟิลเตอร์วินเทจ"],
        "title": "แอปฟิลเตอร์ฟิล์ม: แต่งรูปให้ฟีลกล้องฟิล์ม เกรน แสงรั่ว และตราวันที่แบบยุคก่อน",
        "desc": "อยากได้รูปโทนกล้องฟิล์มแบบที่เห็นในฟีด แต่ไม่รู้จะปรับสีอย่างไร? วิธีเลือกแอปฟิลเตอร์ฟิล์ม และวิธีใช้ PhotoCream Pro ขโมยลุคจากรูปที่ชอบมาใช้กับรูปของคุณ พร้อมลิงก์ App Store ประเทศไทย",
        "h1": "ฟิลเตอร์ฟิล์ม: ได้ฟีลกล้องฟิล์มโดยไม่ต้องปรับสีเองทีละค่า",
        "lead": "คนที่ค้นหา “ฟิลเตอร์ฟิล์ม” ใน App Store ส่วนใหญ่เพิ่งเห็นรูปโทนฟิล์มสวยๆ ในฟีด แล้วอยากให้รูปของตัวเองออกมาฟีลเดียวกัน ทั้งเกรน สีซีดนิดๆ และแสงรั่วแบบกล้องฟิล์มยุคก่อน",
        "intro": [
            "ปัญหาคือฟิลเตอร์สำเร็จรูปส่วนใหญ่ใช้ได้ดีกับบางรูปเท่านั้น พอเปลี่ยนแสงหรือสถานที่ โทนก็เพี้ยน ผิวดูหมองหรือแดงเกินไป ครั้นจะปรับเคิร์ฟและสีเองก็ต้องรู้ว่าแต่ละค่าทำอะไร",
            "เราค้นหาใน App Store ประเทศไทยจริงในปี 2026 คำว่า “ฟิลเตอร์ฟิล์ม” มีแอปกล้องฟิล์มหลายตัวขึ้นมา ด้านล่างคือสิ่งที่ควรดูตอนเลือก และวิธีใช้ PhotoCream Pro ให้ได้โทนที่ชอบ",
        ],
        "sections": [
            ("เลือกแอปฟิลเตอร์ฟิล์ม ดู 5 ข้อนี้", [], [
                "ขโมยลุคได้: เลือกรูปที่ชอบสักรูป แอปจะวิเคราะห์โทนสีของรูปนั้นในเครื่อง และแปลงเป็นโทนสีฟิล์มที่ปรับแต่งได้ เพื่อนำไปใช้กับรูปของคุณเอง",
                "ลุคฟิล์มให้เลือกเยอะ: มีลุคฟิล์มกว่า 100 แบบ ทั้งเกรน ฮาเลชัน แสงรั่ว และขอบมืด",
                "ดูก่อนถ่าย: ดูแบบสดได้ก่อนกดชัตเตอร์ ไม่ต้องถ่ายแล้วค่อยลุ้น",
                "ปรับละเอียดได้: เก็บรายละเอียดด้วยเคิร์ฟ HSL และสปลิตโทน",
                "รูปไม่ออกจากเครื่อง: ทุกอย่างประมวลผลในเครื่องของคุณ รูปไม่ถูกอัปโหลดไปไหน",
            ]),
            ("แต่งรูปแบบไหนได้บ้าง", [
                "รูปเที่ยวและอัลบั้มส่งท้ายปี: ใช้ลุคฟิล์มเดียวกันทั้งชุด แล้วเติมเกรนฟิล์มให้รูปดูเป็นเรื่องเดียวกัน",
                "รูปคนและเซลฟี่: ทำผิวเนียนโดยที่ดวงตาและเส้นผมยังคมชัด ยังมีปรับตาโต และยืดสัดส่วนให้ดูสูงเพรียวอย่างเป็นธรรมชาติ",
                "รูปฟีลยุคก่อน: เพิ่มข้อความ กรอบ เกรน ฝุ่น หรือตราวันที่แบบรูปฟิล์มยุคก่อน ให้เหมือนรูปที่เพิ่งล้างจากร้าน",
            ], []),
            ("ทำไมโทนถึงออกมาเป็นธรรมชาติ", [
                "เพราะเริ่มจากรูปที่คุณชอบจริง แล้วแปลงเป็นโทนสีฟิล์มที่ยังปรับต่อได้ จึงไม่ต้องเริ่มจากศูนย์ และไม่ต้องจำค่าสีเอง ถ้าโทนยังไม่ตรงใจ ก็ปรับแสง สี และเคิร์ฟอย่างละเอียดต่อได้",
                "ไม่มีโฆษณา และรูปของคุณไม่ถูกอัปโหลดไปไหน ทุกอย่างประมวลผลในเครื่อง",
            ], []),
        ],
        "steps_title": "ได้โทนฟิล์มใน 5 ขั้นตอน",
        "steps": [
            "เปิด PhotoCream Pro แล้วเลือกรูปที่ชอบโทนสี",
            "ใช้ขโมยลุคเพื่อแปลงเป็นโทนสีฟิล์ม",
            "นำโทนนั้นไปใช้กับรูปของคุณ",
            "ปรับเกรน แสงรั่ว หรือขอบมืดเพิ่มตามชอบ",
            "เติมตราวันที่หรือกรอบแบบรูปฟิล์มยุคก่อน",
        ],
        "cards": [
            ("photocream", "ขโมยลุค: เลือกรูปที่ชอบสักรูป แอปจะวิเคราะห์โทนสีของรูปนั้นในเครื่อง และแปลงเป็นโทนสีฟิล์มที่ปรับแต่งได้ เพื่อนำไปใช้กับรูปของคุณเอง มีลุคฟิล์มกว่า 100 แบบ ทั้งเกรน ฮาเลชัน แสงรั่ว และขอบมืด ดูแบบสดได้ก่อนกดชัตเตอร์ ทำผิวเนียนโดยที่ดวงตาและเส้นผมยังคมชัด ไม่มีโฆษณา รูปไม่ถูกอัปโหลด"),
        ],
        "faqs": [
            ("ใช้โทนจากรูปที่ชอบได้ไหม?", "ได้ เลือกรูปที่ชอบสักรูป แอปจะวิเคราะห์โทนสีในเครื่องและแปลงเป็นโทนสีฟิล์มที่ปรับแต่งได้"),
            ("ดูฟิลเตอร์ก่อนถ่ายได้ไหม?", "ได้ ดูลุคฟิล์มแบบสดได้ก่อนกดชัตเตอร์"),
            ("รูปจะถูกอัปโหลดไหม?", "ไม่ ทุกอย่างประมวลผลในเครื่องของคุณ รูปไม่ถูกอัปโหลดไปไหน"),
            ("ใส่ตราวันที่แบบกล้องฟิล์มได้ไหม?", "ได้ เพิ่มข้อความ กรอบ เกรน ฝุ่น หรือตราวันที่แบบรูปฟิล์มยุคก่อนได้"),
        ],
        "related": [("th/hubs/photocream.html", "PhotoCream: คำถามที่พบบ่อย")],
        "legal": "แอปที่แนะนำในหน้านี้พัฒนาโดยอิสระ ผลการค้นหาใน App Store มาจากการค้นหาจริงในปี 2026 และลำดับอาจเปลี่ยนแปลงได้",
    },
    # 7 MoneyTag × 德國「nebenjob einnahmen」（第 6）
    {
        "key": "moneytag", "lang": "de-DE",
        "slug": "nebenjob-einnahmen-ausgaben-app-projekte-iphone",
        "terms": ["nebenjob einnahmen", "nebenjob ausgaben", "einnahmen ausgaben app"],
        "title": "Nebenjob-Einnahmen im Blick: Was nach Abzug der Ausgaben wirklich bleibt",
        "desc": "Neben dem Hauptjob noch Nachhilfe, Etsy-Shop oder Fotoaufträge – und am Monatsende keine Ahnung, was davon übrig bleibt? Worauf es bei einer App für Nebenjob-Einnahmen ankommt und wie MoneyTag jedes Projekt als eigenes Buch führt. Mit Link zum deutschen App Store.",
        "h1": "Nebenjob-Einnahmen: jedes Projekt mit eigenem Ergebnis",
        "lead": "Wer im App Store nach „Nebenjob Einnahmen“ sucht, hat meistens mehr als eine Geldquelle: einen Hauptjob und daneben Nachhilfe, einen kleinen Onlineshop, Fotoaufträge oder Vermietung.",
        "intro": [
            "Die meisten Haushaltsbuch-Apps werfen alles in einen Topf. Dann sieht man zwar, wie viel insgesamt ausgegeben wurde, aber nicht, ob sich der Nebenjob überhaupt lohnt. Kamera, Material, Fahrtkosten und Gebühren verschwinden zwischen Miete und Lebensmitteln, und am Ende des Jahres sucht man alles aus Kontoauszügen zusammen.",
            "Im Oktober 2026 haben wir im deutschen App Store nachgesehen: „Nebenjob“ schlägt bereits Suchbegriffe rund um Einnahmen vor, und die vorderen Apps haben zusammen nur wenige Bewertungen. Unten steht, worauf du achten solltest und wie MoneyTag das löst.",
        ],
        "sections": [
            ("Fünf Dinge, die eine Nebenjob-App können sollte", [], [
                "Getrennte Bücher: Bei MoneyTag ist ein Projekt ein in sich geschlossenes Buch mit eigenen Buchungen, eigener Währung und eigenem Ergebnis.",
                "Nettoergebnis für jedes Projekt: MoneyTag addiert die Einnahmen, zieht die Ausgaben ab und zeigt das Nettoergebnis allein für dieses Projekt.",
                "Tags über Projekte hinweg: Im Bereich Tags summiert MoneyTag denselben Tag über alle Projekte hinweg, zum Beispiel alle Fahrtkosten: Einnahmen, Ausgaben und das Netto für diesen Tag.",
                "Andere Währungen: Jedes Projekt hat eine eigene Basiswährung; öffentliche Wechselkurse werden etwa alle 6 Stunden aktualisiert, oder du legst einen manuellen Kurs fest.",
                "Export: Aufzeichnungen lassen sich als CSV, als PDF oder als Bild ausgeben und sichern und wiederherstellen.",
            ]),
            ("Drei typische Nebenjobs", [
                "Nachhilfe oder Kurse: Lege ein Projekt „Nachhilfe“ an und erfasse jede Stunde als Einnahme, Bücher und Fahrten als Ausgaben. Das Nettoergebnis zeigt, was im Monat wirklich bleibt.",
                "Kleiner Onlineshop: Material, Versand und Verkäufe landen im Projekt „Shop“, getrennt vom Haushalt. Mit Tags wie „Versand“ siehst du die Summe auch dann, wenn du mehrere Projekte hast.",
                "Aufträge aus dem Ausland: Zahlt ein Kunde in einer anderen Währung, wählst du auf dem Startbildschirm die Eingabewährung direkt aus. Der umgerechnete Betrag wird in der Basiswährung des Projekts gespeichert, und gespeicherte Kurse bleiben offline verfügbar.",
            ], []),
            ("Immer dabei, auch am Handgelenk", [
                "Dasselbe Buch läuft auf iPhone und iPad. In der Apple-Watch-App erfasst du eine Buchung direkt am Handgelenk und siehst Einnahmen, Ausgaben und Netto des aktuellen Projekts; Widgets zeigen denselben Stand auf dem Home- und dem Sperrbildschirm.",
                "Projekte, Buchungen, Beträge, Notizen und Tags bleiben im Gerätespeicher von MoneyTag. Bei aktivierter iCloud-Synchronisierung liegt zusätzlich eine Kopie in deiner eigenen iCloud. MoneyTag ersetzt keine Steuerberatung, macht aber die Zahlen für das Gespräch übersichtlich.",
            ], []),
        ],
        "steps_title": "In fünf Schritten zum ersten Nettoergebnis",
        "steps": [
            "MoneyTag öffnen und ein Projekt für den Nebenjob anlegen.",
            "Die Basiswährung des Projekts wählen.",
            "Jede Einnahme und Ausgabe erfassen und bei Bedarf mit einem Tag versehen.",
            "Das Nettoergebnis des Projekts ansehen.",
            "Am Monatsende als CSV oder PDF exportieren.",
        ],
        "cards": [
            ("moneytag", "Jedes Projekt führt seine eigenen Bücher: Einnahmen minus Ausgaben ergeben sein Nettoergebnis. Tags summieren denselben Posten über Projekte hinweg, jedes Projekt hat eine eigene Währung mit Live- oder manuellen Kursen. Dasselbe Buch auf iPhone und iPad, dazu eine App für die Apple Watch und Widgets für Home- und Sperrbildschirm. Export als CSV, PDF oder Bild."),
        ],
        "faqs": [
            ("Kann ich Nebenjob und Haushalt getrennt führen?", "Ja. Jedes Projekt ist ein in sich geschlossenes Buch mit eigenen Buchungen, eigener Währung und eigenem Nettoergebnis."),
            ("Wie sehe ich eine Ausgabenart über alle Projekte?", "Versieh die Buchungen mit einem Tag. Im Bereich Tags summiert MoneyTag denselben Tag über alle Projekte hinweg."),
            ("Kann ich die Zahlen exportieren?", "Ja, als CSV, als PDF oder als Bild; außerdem gibt es Sichern und Wiederherstellen."),
            ("Wo werden meine Daten gespeichert?", "Im Gerätespeicher von MoneyTag; bei aktivierter iCloud-Synchronisierung zusätzlich als Kopie in deiner eigenen iCloud."),
        ],
        "related": [("de-DE/hubs/moneytag.html", "MoneyTag: häufige Fragen")],
        "legal": "Die vorgestellte App ist eine unabhängige Entwicklung. Die App-Store-Suchergebnisse stammen aus einer eigenen Abfrage im Oktober 2026; die Reihenfolge kann sich ändern. Diese Seite ist keine Steuerberatung.",
    },
    # 8 OnePage PPT × 泰國「สรุปหน้าเดียว」（第 1，守住）
    {
        "key": "onepageppt", "lang": "th",
        "slug": "app-sarup-na-diao-slide-16-9-pptx",
        "terms": ["สรุปหน้าเดียว", "ทำสไลด์", "สไลด์ AI"],
        "title": "สรุปหน้าเดียว: เปลี่ยนโน้ต PDF หรือตารางให้เป็นสไลด์ 16:9 แผ่นเดียวที่คนอ่านจนจบ",
        "desc": "ต้องสรุปรายงาน ผลงานประจำเดือน หรือบทเรียนให้เหลือหน้าเดียวแต่ไม่มีเวลาจัดสไลด์? วิธีเลือกแอปสรุปหน้าเดียว และวิธีใช้ OnePage PPT ส่งออกเป็น pptx PDF หรือ PNG พร้อมลิงก์ App Store ประเทศไทย",
        "h1": "สรุปหน้าเดียว: ใส่เนื้อหาไป ได้สไลด์แผ่นเดียวที่พร้อมพรีเซนต์",
        "lead": "คนที่ค้นหา “สรุปหน้าเดียว” ใน App Store ส่วนใหญ่มีเนื้อหายาวอยู่ในมือ ทั้งรายงาน ตารางตัวเลข หรือโน้ตประชุม และต้องส่งหัวหน้าหรืออาจารย์เป็นสไลด์แผ่นเดียวภายในวันนี้",
        "intro": [
            "การสรุปให้เหลือหน้าเดียวยากกว่าที่คิด ต้องเลือกว่าประเด็นไหนสำคัญ ตัวเลขไหนควรเป็นกราฟ แล้วยังต้องเลือกเทมเพลตและลากกล่องข้อความให้ลงตัว พอทำเสร็จก็หมดเวลาไปครึ่งวัน",
            "เราค้นหาใน App Store ประเทศไทยจริงในปี 2026 คำว่า “สรุปหน้าเดียว” แอป OnePage PPT ขึ้นเป็นอันดับแรก ด้านล่างคือสิ่งที่ควรดูตอนเลือกแอปสรุป และวิธีใช้ให้ได้สไลด์ที่คนอ่านจนจบ",
        ],
        "sections": [
            ("เลือกแอปสรุปหน้าเดียว ดู 5 ข้อนี้", [], [
                "ใส่อะไรก็ได้: OnePage PPT อ่านทั้งข้อความที่พิมพ์ ข้อความที่วาง ภาพหน้าจอ รูปถ่าย ไฟล์ PDF และตาราง CSV",
                "ไม่ต้องจัดเอง: ดึงประเด็นสำคัญมาจัดเป็นสไลด์ 16:9 แผ่นเดียวที่พร้อมพรีเซนต์ทันที ไม่ต้องเลือกเทมเพลต ไม่ต้องลากกล่องข้อความ",
                "ภาพตรงกับข้อมูล: ตัวเลขกลายเป็นกราฟแท่ง เส้น โดนัท หรือกรวย ขั้นตอนกลายเป็นผังกระบวนการ วันที่กลายเป็นไทม์ไลน์",
                "ไม่แต่งตัวเลข: แอปวาดกราฟเฉพาะเมื่อข้อมูลรองรับจริง และไม่แต่งตัวเลขขึ้นเองเด็ดขาด",
                "ส่งต่อได้ทุกที่: ส่งออกไฟล์ .pptx แก้ไขต่อได้ใน PowerPoint, Keynote และ Google Slides หรือเป็น PDF และ PNG ความละเอียดสูง",
            ]),
            ("ใช้ในงานจริงอย่างไร", [
                "สรุปผลงานประจำเดือน: วางตาราง CSV ยอดขายหรือ KPI แล้วได้แถวตัวเลข KPI และกราฟที่เหมาะกับข้อมูล ส่งหัวหน้าเป็น PDF ได้ทันที",
                "สรุปการประชุม: วางโน้ตประชุมยาวๆ แล้วได้หัวข้อสำคัญ ถ้ามีสองตัวเลือกให้ตัดสินใจ แอปจะจัดเป็นคอลัมน์เปรียบเทียบ",
                "สรุปบทเรียนหรือรายงาน: ถ่ายรูปหรือนำเข้า PDF แล้วได้สไลด์แผ่นเดียว ข้อค้นพบกลายเป็นเมทริกซ์สี่ช่องหรือผังลำดับชั้น",
            ], []),
            ("ปรับจนกว่าจะถูกใจ", [
                "มีหกรูปแบบแค่กดครั้งเดียว ทั้งเรียบขึ้น เน้นภาพขึ้น มืออาชีพขึ้น เด่นขึ้น กระชับขึ้น และสไตล์นิตยสาร แต่ละแบบจัดสไลด์ใหม่จริง ชิ้นไหนถูกใจให้ล็อกไว้ แล้วปรับเฉพาะส่วนที่เหลือ แตะชิ้นไหนก็แก้ข้อความได้ และมีประวัติเวอร์ชันให้ย้อนกลับ",
                "ทุกอย่างทำงานในเครื่องของคุณ ไม่ต้องสมัครบัญชี ไม่มีการติดตาม และใช้ได้แม้ไม่มีเน็ต ไฟล์ที่ส่งออกจะออกจากเครื่องก็ต่อเมื่อคุณแชร์เองเท่านั้น",
            ], []),
        ],
        "steps_title": "สรุปหน้าเดียวใน 3 ขั้นตอน",
        "steps": [
            "ใส่อะไรก็ได้ พิมพ์ วาง ถ่ายรูป หรือนำเข้า PDF และสเปรดชีต",
            "แตะ “สร้างสไลด์” เนื้อหาจะถูกสรุปเป็นหัวข้อสำคัญและแปลงเป็นภาพที่เหมาะสม",
            "พรีเซนต์ได้เลย หรือส่งออกเป็นไฟล์ pptx PDF หรือ PNG",
        ],
        "cards": [
            ("onepageppt", "เปลี่ยนข้อความยาวเหยียดให้เหลือสไลด์แผ่นเดียวที่คนอ่านจนจบ OnePage PPT อ่านข้อความ ภาพหน้าจอ รูปถ่าย PDF และตาราง CSV แล้วดึงประเด็นสำคัญมาจัดเป็นสไลด์ 16:9 แผ่นเดียว ตัวเลขเป็นกราฟ ขั้นตอนเป็นผังกระบวนการ ส่งออกเป็น pptx PDF หรือ PNG ทำงานในเครื่อง ไม่ต้องสมัครบัญชี"),
        ],
        "faqs": [
            ("ไฟล์ที่ได้แก้ไขต่อได้ไหม?", "ได้ ไฟล์ .pptx แก้ไขต่อได้ใน PowerPoint, Keynote และ Google Slides"),
            ("แอปจะแต่งตัวเลขขึ้นเองไหม?", "ไม่ แอปวาดกราฟเฉพาะเมื่อข้อมูลรองรับจริง และไม่แต่งตัวเลขขึ้นเองเด็ดขาด"),
            ("ใส่ไฟล์อะไรได้บ้าง?", "ข้อความที่พิมพ์ ข้อความที่วาง ภาพหน้าจอ รูปถ่าย ไฟล์ PDF และตาราง CSV"),
            ("ไม่มีเน็ตใช้ได้ไหม?", "ได้ ทุกอย่างทำงานในเครื่องของคุณ และใช้ได้แม้ไม่มีเน็ต"),
        ],
        "related": [("th/hubs/onepageppt.html", "OnePage PPT: คำถามที่พบบ่อย")],
        "legal": "แอปที่แนะนำในหน้านี้พัฒนาโดยอิสระ ผลการค้นหาใน App Store มาจากการค้นหาจริงในปี 2026 และลำดับอาจเปลี่ยนแปลงได้",
    },
]


def _install() -> None:
    """把本批的語系表、App、頁面與檢查換進第 3 組產生器（其餘版面與檢查原樣沿用）。"""
    g3.LANGS = LANGS
    g3.APP_IDS = APP_IDS
    g3.PAGE_SPECS = PAGE_SPECS
    g3.BANNED = BANNED
    g3.dedicated_size = dedicated_size


def main(argv=None) -> int:
    _install()
    return g3.main(argv)


if __name__ == "__main__":
    sys.exit(main())
