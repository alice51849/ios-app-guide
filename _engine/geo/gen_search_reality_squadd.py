#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜尋實況母語意圖頁：千萬作戰小組 D（第一批 8 頁德／日／泰＋第二批 10 頁日／英）→ <Guide>/<lang>/seasonal/<slug>.html。

背景（aso/search_reality/<key>.json 與 reports/per_app/cards/<key>.md 的實測名次）：
- 遮個資（maskmyfile）德國「pdf schwärzen」第 49，前 10 一半以上是弱對手。
- PicClear（picclear）日本「容量を軽くするアプリ」搜尋建議第 1，前 10 一半以上是弱對手。
- QR Code Halo（qrcodehalo）德國「qr code prüfen」第 32。
- 麻糬打卡（mochidonestamp）泰國「บันทึกครั้งล่าสุด」第 3。
- 100 Notes Studio（notesstudio100）泰國「จดโน้ตด้วยลายมือ」第 16。
- PhotoCream（photocream）泰國「ฟิลเตอร์ฟิล์ม」第 8。
- MoneyTag（moneytag）德國「nebenjob einnahmen」第 6（日文頁已在 g3，不重做）。
- OnePage PPT（onepageppt）泰國「สรุปหน้าเดียว」第 1（簡中頁已在 g3，這頁守住泰國第 1）。

第二批（2026-11-07，每款換第二個市場，10 頁；日文 6、英文 4）：
- Mochi（mochi）日本「todoリスト」搜尋建議第 1（「todoリスト かわいい」第 7～9）；名稱詞照品牌描述，不談改名。
- Metro Time Helper（metrotimehelper）美國「taipei mrt」第 14（來台旅客；部門 12 只做了繁中頁）。
- 遮個資 日本「pdf 黒塗り」第 83；PicClear 美國「photo cleaner」大詞；QR Code Halo 美國「safe qr scanner」前 10 全弱。
- 麻糬打卡 日本「いつやった」（名稱詞，前 10 有 8 個弱對手）；MoneyTag 美國「side hustle tracker」（前 10 有 9 個弱對手）。
- 100 Notes Studio 日本「手書きノート」（建議第 1、名稱已含；美國 digital notebook 同在 12 名外，日文較近）。
- OnePage PPT 美國「one page summary」（推論，無量測；同類實測詞 presentation maker 第 90）。
- PhotoCream 日本「フィルムカメラ 加工」（「フィルムカメラ」建議第 4，副標已命中）。

沿用第 3 組產生器（gen_search_reality_g3.py）的版面、檢查、Google Play 補連結與 sitemap 合併，只換頁面內容
（德文語系表照 gen_search_reality_easyam.py，泰文語系表照同格式新增）。規則：
- 功能句只取 data/<key>_full.json 該語系商店文案；不寫價格、免費、Free、Pro、試用、訂閱。
  商店名本身含「Pro」的兩款（PicClear Pro、PhotoCream Pro）只在品牌名裡出現，其餘 Pro 一律擋。
- 不寫摺疊、Duo 相關宣稱。
- 每頁一張主卡，附該國 App Store 直連（pt＋ct＋mt）；ct＝gw 階梯碼（gw_campaign.py，款 × 國家 × 詞群 sr）。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 專屬內容：日文 ≥450 字、德文與英文 ≥450 詞、泰文 ≥450 個泰文字。只寫這些頁與各語系 sitemap_seasonal_<lang>.xml
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
    "mochi": "6785004775", "metrotimehelper": "6819061896",
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
    # ── 第二批（2026-11-07）：每款換第二個市場 ──
    # 9 Mochi × 日本「todoリスト」（搜尋建議第 1；「todoリスト かわいい」第 7～9）
    {
        "key": "mochi", "lang": "ja",
        "slug": "todo-list-app-kawaii-tsuzukeru-erabikata",
        "terms": ["todoリスト", "todoリスト かわいい", "やることリスト"],
        "title": "todoリストアプリの選び方：かわいくて続けられるToDoリストに必要な5つのこと",
        "desc": "やることリストを作っても三日で開かなくなる。そんな人のためのtodoリストアプリの選び方と、絵文字とテーマで毎日開きたくなるMochiの使い方をまとめました。日本の App Store へのリンク付き。",
        "h1": "todoリスト：毎日開きたくなるかわいいToDoリストの選び方",
        "lead": "App Store で「todoリスト」と検索する人の多くは、やることが頭の中であふれていて、とりあえず書き出したいと思っています。勉強、仕事、買い物、家のこと。でも、これまでのアプリは数日で開かなくなってしまった。",
        "intro": [
            "ToDoリストが続かない理由は、たいてい機能の多さではありません。開くたびに義務のように感じたり、画面が事務的で気分が上がらなかったり、どこに何を書いたか分からなくなったりするからです。毎日使う道具だからこそ、見た目のかわいさと、チェックしたときの小さな達成感が大切です。",
            "2026年に日本の App Store で調べると、「todoリスト」は検索候補の1番目に出てくる言葉で、続けて「かわいい」「毎日」「ウィジェット」が候補に並びます。ここでは、続けられるToDoリストを選ぶときに見るべきポイントと、Mochi の実際の使い方をまとめます。",
        ],
        "sections": [
            ("続けられるtodoリスト、まずこの5点を確認", [], [
                "チェックが気持ちいいか：Mochi では終わったら小さな丸をタップ。チェックするたびに、気持ちがふわっと軽くなります。",
                "ひと目で分かるか：タスクごとに小さな絵文字を添えられるので、文字を読まなくても何のタスクかすぐ分かります。",
                "気分で着せ替えられるか：テーマで気分に合わせて着せ替えでき、毎日開くのが楽しみになります。",
                "アプリを開かなくても見えるか：ホーム画面のウィジェットや Apple Watch で、やることをいつでも確認できます。",
                "忘れないか：忘れ物を防ぐリマインダーで、大事なことを思い出させてくれます。",
            ]),
            ("こんな使い方ができます", [
                "勉強：テスト範囲や課題を教科ごとに書き出し、終わった単元から丸をタップ。進み具合が目で見えるので、次に何をやればいいか迷いません。",
                "仕事：その日のタスクをデイリープランナーとして並べ、予定管理にも使えます。ウィジェットに出しておけば、パソコンを開く前に今日やることを確認できます。",
                "買い物と家のこと：買い物リスト、習慣、毎日のルーティンまで、ひとつのアプリでかわいく整理できます。年末の大掃除のように、やることが一気に増える時期にも便利です。",
            ], []),
            ("かわいいだけじゃない、毎日の道具として", [
                "直感的で使いやすいチェックリストなので、初めてでも迷わず使えます。習慣やルーティンの記録、メモにも対応しているので、手帳や付箋を何枚も持ち歩く必要がありません。",
                "Mochi は、がんばる毎日に小さな癒やしと可愛さを届けるために作られた、かわいくてやさしいToDoリストです。",
            ], []),
        ],
        "steps_title": "はじめてのリスト、5ステップ",
        "steps": [
            "Mochi を開いて、新しいリストを作ります。",
            "やることを書き出し、タスクごとに絵文字を添えます。",
            "好きなテーマを選んで着せ替えます。",
            "ホーム画面にウィジェットを置いて、いつでも確認できるようにします。",
            "終わったら小さな丸をタップしてチェックします。",
        ],
        "cards": [
            ("mochi", "Mochi は、タスクごとに小さな絵文字を添えられる、かわいくてやさしいToDoリストです。終わったら小さな丸をタップ。テーマで気分に合わせて着せ替えでき、ホーム画面のウィジェットや Apple Watch で、やることをいつでも確認できます。勉強、仕事、買い物リスト、習慣、毎日のルーティンまで、ひとつのアプリでかわいく整理。忘れ物を防ぐリマインダーも。"),
        ],
        "faqs": [
            ("ホーム画面でやることを確認できますか？", "できます。ホーム画面のウィジェットや Apple Watch で、やることをいつでも確認できます。"),
            ("買い物リストにも使えますか？", "使えます。勉強、仕事、買い物リスト、習慣、毎日のルーティンまで、ひとつのアプリで整理できます。"),
            ("リマインダーはありますか？", "あります。忘れ物を防ぐリマインダーで、大事なことを知らせます。"),
            ("見た目を変えられますか？", "テーマで気分に合わせて着せ替えでき、タスクごとに小さな絵文字も添えられます。"),
        ],
        "related": [("ja/hubs/mochi.html", "Mochi のよくある質問")],
        "legal": "本ページで紹介するアプリは独立開発です。App Store の検索結果は2026年に実際に検索したもので、順位は変わることがあります。",
    },
    # 10 Metro Time Helper × 美國「taipei mrt」（第 14；來台旅客）
    {
        "key": "metrotimehelper", "lang": "en",
        "slug": "taipei-mrt-app-for-visitors-latest-time-to-leave",
        "terms": ["taipei mrt", "taipei mrt app", "taipei metro app"],
        "title": "Taipei MRT app for visitors: know the latest time to leave, in your own language",
        "desc": "Visiting Taipei and riding the MRT for the first time? What to look for in a Taipei MRT app, and how Metro Time Helper works backward from your arrival time to the latest time to enter the station, in 50 languages. With a link to the US App Store.",
        "h1": "Taipei MRT app for visitors: when do I need to leave?",
        "lead": "Most people who search the App Store for “Taipei MRT” are planning a trip to Taiwan or have just landed: a hotel in Ximending, dinner in Xinyi, a day trip to the Xinbeitou hot springs, and a metro map full of names they cannot read yet.",
        "intro": [
            "The Taipei MRT is easy to ride, but planning around it as a visitor is harder than it looks. Station names change between Chinese and English depending on where you look, transfers between lines can take longer than expected, and the question that matters before a dinner reservation or the last train of the night is not when you will arrive. It is when you need to walk out of the door.",
            "We searched the US App Store in 2026: for “taipei mrt” the top results have only a few hundred ratings each, and most of them answer the arrival question. Below is what to look for in a Taipei MRT app as a visitor, and how Metro Time Helper answers the leaving question instead.",
        ],
        "sections": [
            ("Five things a Taipei MRT app should do for visitors", [], [
                "Work backward from your arrival time: tell Metro Time Helper when you need to be there, and it tells you the latest time to walk into the station, transfers included.",
                "Speak your language: Metro Time Helper comes in 50 languages you can switch inside the app, so travelers from around the world can ride the Taipei MRT for the first time in a language they know.",
                "Show every leg: you get a step-by-step timeline for every leg and transfer, plus first and last train warnings.",
                "Let you pick stations on a map: tap any station on the built-in zoomable MRT map to set it as your start or destination, and your route is drawn right on the map.",
                "Remind you to go: once you set Remind me, a Live Activity counts down to your time to leave on the Lock Screen and in the Dynamic Island on iPhone.",
            ]),
            ("Three typical visitor trips", [
                "Dinner reservation: choose your starting station, your destination and the time you need to arrive. Pick Cautious estimates for a full headway of waiting if you would rather be early, and adjust your station entry buffer if you walk slowly with luggage.",
                "Last train of the night: after a night market or a concert, first and last train warnings tell you whether the route still works. Would rather leave right now? Switch to Leave now and see when you will get there.",
                "Hot springs day trip: the short Beitou to Xinbeitou branch has its own countdown to the next train, full timetables, departure reminders and the official timetable PDF, so you do not have to wait around on the platform.",
            ], []),
            ("What it covers, and what it does not", [
                "Lines covered: Wenhu, Tamsui-Xinyi including the Xinbeitou branch, Songshan-Xindian including the Xiaobitan branch, Zhonghe-Xinlu, Bannan, phase one of the Circular line, and the New Taipei Metro Sanying line. Airport MRT and light rail are not included, so check your airport transfer separately.",
                "Times are estimates based on official published headways and travel times between stations; they are not live train arrivals. There is no sign-up, no ads and no third-party analytics, and everything is calculated on your device. Metro Time Helper is an independent app and is not affiliated with or endorsed by Taipei Rapid Transit Corporation.",
            ], []),
        ],
        "steps_title": "Plan your first MRT trip in five steps",
        "steps": [
            "Open Metro Time Helper and switch to the language you know.",
            "Tap your starting station and your destination on the MRT map.",
            "Enter the time you need to arrive.",
            "Read the latest time to enter the station and the timeline for each transfer.",
            "Tap Remind me so a countdown appears on your Lock Screen.",
        ],
        "cards": [
            ("metrotimehelper", "Built for the Taipei MRT in Taiwan: tell Metro Time Helper when you need to be there, and it tells you the latest time to walk into the station. It works backward from your arrival time, transfers included, with a step-by-step timeline, first and last train warnings and a reminder when it is time to go. 50 languages, a zoomable MRT map, widgets, Live Activities and an Apple Watch app. No sign-up and no ads."),
        ],
        "faqs": [
            ("Does it work in English and other languages?", "Yes. Metro Time Helper has 50 languages you can switch inside the app."),
            ("Does it show live train arrivals?", "No. Times are estimates based on official published headways and travel times between stations; they are not live train arrivals."),
            ("Is the Airport MRT included?", "No. Airport MRT and light rail are not included."),
            ("Do I need an account?", "No. There is no sign-up, no personal data collection and no ads; everything is calculated on your device."),
        ],
        "related": [("en-US/hubs/metrotimehelper.html", "Metro Time Helper: common questions")],
        "legal": "The app featured on this page is independently developed and is not affiliated with Taipei Rapid Transit Corporation. App Store search results come from our own search in 2026; the order can change.",
    },
    # 11 Mask My File × 日本「pdf 黒塗り」（第 83）
    {
        "key": "maskmyfile", "lang": "ja",
        "slug": "pdf-kuronuri-iphone-kojin-joho-sosin-mae",
        "terms": ["pdf 黒塗り", "黒塗り", "個人情報 マスク"],
        "title": "PDFを黒塗りする方法（iPhone）：見た目だけでなく本当に消すための5つのチェック",
        "desc": "賃貸の申込書や給与明細、身分証のコピーを送る前に、氏名や口座番号を黒塗りしたい。PDFの黒塗りが本当に消えているかの見分け方と、Mask My File で端末内で黒塗りする手順をまとめました。日本の App Store へのリンク付き。",
        "h1": "PDFの黒塗り：送る前に、見た目だけでなく本当に消す",
        "lead": "App Store で「pdf 黒塗り」と検索する人の多くは、いままさに送らなければいけない書類を手にしています。賃貸の申込書、給与明細、顧客ファイル、身分証のコピー。",
        "intro": [
            "気をつけたいのは、画像編集アプリやPDFアプリで上から黒い四角を描いただけでは、下の文字が残っている場合があることです。ファイルによっては文字を選択したりコピーしたり検索できたりしますし、メタデータに名前や作成日時が残っていることもあります。安心して送るには、該当部分を完全に塗りつぶし、できあがったファイルをもう一度確かめられる道具が必要です。",
            "2026年に日本の App Store を検索したところ、「黒塗り」は検索候補にあり、上位は評価の少ない小さなアプリが中心でした。ここでは、黒塗りアプリを選ぶときに見るべき点と、Mask My File の実際の手順をまとめます。",
        ],
        "sections": [
            ("黒塗りアプリ、まずこの5点を確認", [], [
                "見つけてくれるか：Mask My File は氏名・電話番号・メールアドレス・住所・口座や支払い情報を見つけ出し、選んだ部分だけを完全に塗りつぶします。",
                "完全に塗りつぶすか：画像などの視覚ファイルは、恒久的な塗りつぶし（黒塗り）または削除のみです。",
                "メタデータまで考えているか：形式が対応していれば、メタデータも削除します。",
                "元のファイルを守るか：元のファイルは上書きせず、開き直して確認した新しいコピーを作ります。",
                "外に出さないか：すべては端末内で処理され、アカウント、広告、トラッキング、分析、コンテンツのアップロードは一切ありません。",
            ]),
            ("よくある3つの場面", [
                "賃貸の申込書や給与明細：見せる必要のない番号や口座情報を検出結果から選び、ページ単位で確認しながら黒塗りします。全幅プレビューと最大5倍ズームで、小さな文字も見落としにくくなります。",
                "身分証のコピー：顔とバーコードの検出は、確認用の領域を示すだけです。何を塗りつぶすかは自分で決め、手動での正確な範囲選択で必要な部分だけを隠せます。",
                "仕事の顧客ファイル：同じ名前が複数のファイルにあるときは、バッチで最大100ファイルまで対応し、個別プレビュー・ファイル横断検索・ファイルごとの手動選択ができます。テキストやCSVでは、全体マスク・部分マスク・プレースホルダー・仮名化・削除を選べます。",
            ], []),
            ("データの扱い", [
                "Apple Vision と組み込みの Tesseract OCR はローカルで動作します。顔検出は領域を作るだけで、個人を特定せず、テンプレートも作らず、顔データを共有も保持もしません。",
                "プライベートセッション、プロジェクトワークスペース、プレースホルダー保管庫で作業を整理でき、一時作業ファイルやプロジェクトは削除するまで端末内に残ります。",
            ], []),
        ],
        "steps_title": "PDFを黒塗りする5ステップ",
        "steps": [
            "Mask My File を開いて、PDF・写真・スクリーンショットを選びます。",
            "見つかった氏名・番号・住所を確認します。",
            "塗りつぶす部分を選び、必要なら手動で範囲を追加します。",
            "新しいコピーを作ります。開き直して確認されます。",
            "確認できてから、そのコピーを送ります。元のファイルはそのままです。",
        ],
        "cards": [
            ("maskmyfile", "共有する前に個人情報を黒塗り。Mask My File が氏名・電話番号・メールアドレス・住所・口座や支払い情報を見つけ出し、選んだ部分だけを完全に塗りつぶします。PDF、写真、スクリーンショット、テキストファイルに対応し、形式が対応していればメタデータも削除。元のファイルは上書きせず、開き直して確認した新しいコピーを作ります。すべて端末内で処理、アカウント不要。"),
        ],
        "faqs": [
            ("書類がどこかにアップロードされませんか？", "されません。すべては端末内で処理され、コンテンツのアップロードは一切ありません。"),
            ("黒塗りした部分はあとから読めませんか？", "画像などの視覚ファイルは恒久的な塗りつぶし（黒塗り）または削除のみです。新しいコピーは開き直して確認されます。"),
            ("元のPDFは変わってしまいますか？", "元のファイルは上書きされません。黒塗りした新しいコピーが作られます。"),
            ("スクリーンショットや写真も黒塗りできますか？", "できます。PDF、写真、スクリーンショット、テキストファイルに対応しています。"),
        ],
        "related": [("ja/hubs/maskmyfile.html", "Mask My File のよくある質問")],
        "legal": "本ページで紹介するアプリは独立開発です。App Store の検索結果は2026年に実際に検索したもので、順位は変わることがあります。",
    },
    # 12 PicClear × 美國「photo cleaner」（搜尋建議大詞，前 10 有 3 個弱對手）
    {
        "key": "picclear", "lang": "en",
        "slug": "photo-cleaner-iphone-storage-full-review-before-delete",
        "terms": ["photo cleaner", "photo cleaner app", "delete duplicate photos"],
        "title": "Photo cleaner for iPhone: how to clear storage without losing the photos you love",
        "desc": "“iPhone Storage Full” and no room for one more photo? What a photo cleaner app should find, how it should let you review before deleting, and how PicClear Pro does it on your device. With a link to the US App Store.",
        "h1": "Photo cleaner for iPhone: clear the clutter, keep the memories",
        "lead": "Most people who search the App Store for “photo cleaner” have just seen the “iPhone Storage Full” warning. The camera will not take another shot, an update will not install, and the photo library has grown to tens of thousands of pictures.",
        "intro": [
            "Photos and videos are usually what fill an iPhone. The same picture saved twice, a burst of thirty nearly identical shots, screenshots of receipts and maps you needed for one afternoon, a few long videos that take up gigabytes on their own. Going through them one by one takes hours, and deleting in a hurry risks losing the one picture you actually wanted to keep.",
            "We searched the US App Store in 2026: “photo cleaner” is one of the biggest search terms in the category, and the results are full of cleaner apps that look alike. Below is what a photo cleaner should actually do, and how PicClear Pro handles each step.",
        ],
        "sections": [
            ("Five things a photo cleaner app should do", [], [
                "Find the right things: duplicate photos, similar photos and bursts, old screenshots, blurry photos, large videos and large photos.",
                "Suggest what to keep: similar shots and bursts are grouped with a suggested best photo to keep in each group.",
                "Let you review first: you see exactly what will be removed, with thumbnail previews, and nothing is deleted until you confirm.",
                "Protect your Favorites: Favorites are never selected automatically.",
                "Keep photos on your phone: everything is analyzed on your device, your photos are never uploaded, and there is no account, ever.",
            ]),
            ("Three common clean-ups", [
                "After a trip: bursts and near-identical shots pile up fast. Go through each group of similar photos, keep the suggested best shot, and the memory stays while the clutter goes.",
                "Screenshots: receipts, boarding passes, directions and chat captures you only needed once. Review all of your old screenshots together and remove the ones you no longer need.",
                "Kids and pets on video: a few minutes of video can take more space than hundreds of photos. Start with the large videos, the biggest space hogs in your library, and you often recover the most storage in the least time.",
            ], []),
            ("If you change your mind", [
                "Deleted items go to Recently Deleted in Photos, so you can still recover them for a limited time. If you realize later that you needed a picture, it is easy to bring back.",
                "PicClear Pro works fully offline, with no ads, no tracking and no third-party analytics. Scanning is quick even for large libraries, and you can start a Smart Scan from Siri, Spotlight, Shortcuts or the Action Button. It is available in 45 languages.",
            ], []),
        ],
        "steps_title": "Your first clean-up in five steps",
        "steps": [
            "Open PicClear Pro and allow access to your photos.",
            "Run a Smart Scan for duplicates, similar shots, screenshots, blurry photos and large videos.",
            "Preview each group and check the suggested best photo to keep.",
            "Select only what you are sure about and confirm.",
            "If needed, recover items from Recently Deleted in Photos for a limited time.",
        ],
        "cards": [
            ("picclear", "Clear gigabytes of storage by cleaning out the photos you do not need: duplicates, screenshots, blurry shots and space-hungry videos. Similar shots and bursts are grouped with a suggested best photo to keep, and you preview everything before anything is deleted. Favorites are never auto-selected. Deleted items go to Recently Deleted in Photos. Everything is analyzed on your iPhone, with no account and no ads."),
        ],
        "faqs": [
            ("Are my photos uploaded anywhere?", "No. Everything is analyzed on your device, your photos are never uploaded, and it works fully offline."),
            ("What if I delete something by mistake?", "Deleted items go to Recently Deleted in Photos, so you can still recover them for a limited time."),
            ("Will it select my favorite photos?", "No. Favorites are protected and never selected automatically, and nothing is deleted until you confirm."),
            ("What does it look for?", "Duplicate photos, similar photos, screenshots, blurry photos, large videos and large photos."),
        ],
        "related": [("en-US/hubs/picclear.html", "PicClear Pro: common questions")],
        "legal": "The app featured on this page is independently developed. App Store search results come from our own search in 2026; the order can change.",
    },
    # 13 QR Code Halo × 美國「safe qr scanner」（搜尋建議有、前 10 全是弱對手）
    {
        "key": "qrcodehalo", "lang": "en",
        "slug": "safe-qr-scanner-iphone-check-link-before-opening",
        "terms": ["safe qr scanner", "qr code checker", "qr scanner"],
        "title": "Safe QR scanner for iPhone: check where a code leads before it opens",
        "desc": "A QR code on a parking meter, a letter or a restaurant table, and a doubt about whether it is real. What a safe QR scanner should check, and how QR Code Halo rates every code as Safe, Caution or Blocked on your device. With a link to the US App Store.",
        "h1": "Safe QR scanner: look first, open second",
        "lead": "Most people who search the App Store for “safe QR scanner” have a code in front of them that they do not fully trust: a sticker on a parking meter, a code in a letter about a package, or a payment request on a flyer.",
        "intro": [
            "The iPhone camera shows a short address when it reads a code, and one tap opens the page. Fake codes rely on exactly that. A sticker placed over the real code leads to a page that looks almost like the right one, and on a small screen it is hard to tell whether an address is genuine, especially when a domain mixes letters from different alphabets.",
            "We searched the US App Store in 2026: “safe qr scanner” appears as a search suggestion, yet almost none of the top results are built around checking a code before it opens. Below is what a safe QR scanner should do, and how QR Code Halo handles it.",
        ],
        "sections": [
            ("Five things a safe QR scanner should do", [], [
                "Not open automatically: turn off “Run action after scanning” in QR Code Halo and you can check every code first.",
                "Break the link apart: on your device, QR Code Halo parses the complete payload into scheme, host, path, query and fragment, so you see where the code really leads.",
                "Give a clear rating: suspicious URLs, non-HTTPS links and hosts that mix alphabets are flagged as Safe, Caution or Blocked.",
                "Never open risky types: javascript:, data: and file: codes never open, and parsing uncertainty fails closed instead of enabling an action.",
                "Show its reasons: deterministic rules return transparent findings, with no network reputation lookup and no fuzzy score.",
            ]),
            ("Three everyday situations", [
                "Parking meter or charging station: scan the code, open it in History and tap Security Check. If the host does not match the operator or the rating says Caution, pay through the route you already know.",
                "Letters and package notices: QR Code Halo recognizes codes in photos, even several codes in one frame, so you can check a code from a letter without opening it with the camera first.",
                "Your own codes at a shop or club: save a result as a local reference. QR Verification then compares a later scan by its complete SHA-256 fingerprint, QR format, content type and URL components, so a swapped sticker stands out.",
            ], []),
            ("More than a checker", [
                "QR Code Halo scans QR codes and barcodes in 20 formats from the camera or a photo, and Wi-Fi codes bring up the Join prompt. You can create nine kinds of QR codes too, including Wi-Fi, contacts and events.",
                "Every scan outside batch mode is saved on this device unless “Skip saving to history” is on, and History offers favorites, search, filters and sorting. A privacy mode with automatic clearing is built in.",
            ], []),
        ],
        "steps_title": "Check a code in five steps",
        "steps": [
            "In QR Code Halo, turn off “Run action after scanning”.",
            "Scan the code with the camera or recognize it from a photo.",
            "Open the scan in History.",
            "Tap Security Check and read the Safe, Caution or Blocked rating.",
            "Open the link only when the host and the rating make sense.",
        ],
        "cards": [
            ("qrcodehalo", "Scan QR codes and barcodes in 20 formats, from the camera or a photo. Worried a code was a scam? Open it in History and tap Security Check. On your device, QR Code Halo breaks the link into parts and flags suspicious URLs, non-HTTPS links and hosts that mix alphabets as Safe, Caution or Blocked. javascript:, data: and file: codes never open. Create nine kinds of QR codes too, including Wi-Fi, contacts and events."),
        ],
        "faqs": [
            ("Does the app send my codes to a server?", "No. Security Check parses the payload on your device with deterministic rules; no network reputation lookup is used."),
            ("Can I stop a link from opening right away?", "Yes. Turn off “Run action after scanning” and you can check every code first."),
            ("How does it spot a suspicious link?", "It flags suspicious URLs, non-HTTPS links and hosts that mix alphabets, and javascript:, data: and file: codes never open."),
            ("Can I check a code from a photo?", "Yes. QR Code Halo recognizes codes in photos, even several codes in one frame."),
        ],
        "related": [("en-US/hubs/qrcodehalo.html", "QR Code Halo: common questions")],
        "legal": "The app featured on this page is independently developed. App Store search results come from our own search in 2026; the order can change.",
    },
    # 14 Mochi DoneStamp × 日本「いつやった」（名稱詞；前 10 有 8 個弱對手）
    {
        "key": "mochidonestamp", "lang": "ja",
        "slug": "itsu-yatta-app-zenkai-no-hizuke-kaji-kiroku",
        "terms": ["いつやった", "家事 記録", "経過日数"],
        "title": "「いつやった？」を記録するアプリ：前回の日付がすぐわかって、次の時期に知らせてくれる",
        "desc": "シーツを替えたのは？エアコンのフィルター掃除は前回いつ？「いつやった」を記録するアプリの選び方と、ワンタップで日時を残せる Mochi DoneStamp の使い方をまとめました。日本の App Store へのリンク付き。",
        "h1": "いつやった？：ワンタップで記録して、もう思い出そうとしない",
        "lead": "App Store で「いつやった」と検索する人の多くは、また同じ疑問にぶつかったところです。シーツを替えたのはいつだっけ、エアコンのフィルター掃除は前回いつ、植物に水をやったのはいつ。",
        "intro": [
            "家のことの多くは毎日ではなく、一定の間隔でやるものです。しばらくたつと、前回いつやったのか思い出せなくなります。カレンダーに書くのは手間がかかり、毎月同じ日に鳴る通知は実際にやった日とずれていきます。本当に欲しいのは、終わったときにひと押しで記録して、あとはアプリが前回から何日たったかを教えてくれることです。",
            "2026年に日本の App Store を検索したところ、「いつやった」は検索候補にあり、上位10件のうち8件は評価の少ない小さなアプリでした。ここでは、選ぶときに見るべき点と、Mochi DoneStamp の使い方を順番にまとめます。",
        ],
        "sections": [
            ("「いつやった」アプリ、まずこの5点を確認", [], [
                "ワンタップで記録できるか：終わったらワンタップ。Mochi DoneStamp が正確な日時を記録し、間違えても取り消せます。",
                "経過がひと目で分かるか：前回から何日たったかがいつでもわかります。",
                "次の予定日が実際の日から数え直されるか：周期を設定すれば期限が来たときにお知らせ。次の予定日は実際に済ませた日から数え直すので、過ぎた期限に縛られません。",
                "周期が柔軟か：分から年までの柔軟または正確な周期を選べ、過去の日時を追加・編集・削除できます。",
                "通知からすぐ操作できるか：完了・スヌーズ操作付きの端末内通知で、その場で済ませられます。",
            ]),
            ("こんなことの記録に", [
                "定期的な家事：シーツの交換、エアコンのフィルター掃除、浄水器のカートリッジ交換。終わったらスタンプを押せば、Mochi が覚えて次の時期に知らせます。",
                "車と消耗品：車のオイル交換の日を記録し、任意のメモと写真を添えておけば、次に整備に行くときに見返せます。",
                "植物や家族との連絡：水やりや、離れて暮らす家族への電話も。間隔分析で、平均して何日おきにやっているかも確認できます。",
            ], []),
            ("どこからでも使える", [
                "ホーム画面とロック画面のインタラクティブウィジェット、Siriとショートカット、そして Apple Watch では前回の日時を確認して手首からワンタップで記録できます。ダークモード、iPad、VoiceOver、Dynamic Type にも対応しています。",
                "アカウント・広告・解析・追跡はありません。主要データは端末内に保存され、完全バックアップとJSON書き出しもできます。",
            ], []),
        ],
        "steps_title": "1分ではじめる5ステップ",
        "steps": [
            "Mochi DoneStamp を開いて、シーツ交換などのイベントを追加します。",
            "すでにやったことがあれば、過去の日時をさかのぼって入れます。",
            "2週間ごとなど、周期を設定して通知を受け取れるようにします。",
            "終わったらワンタップで記録します。",
            "ホーム画面にウィジェットを置いて、前回からの日数を確認します。",
        ],
        "cards": [
            ("mochidonestamp", "シーツを替えたのは？エアコンのフィルター掃除や車のオイル交換は、前回いつでしたか？終わったらワンタップ。Mochi DoneStamp が正確な日時を記録し、前回から何日たったかがいつでもわかります。周期を設定すれば期限が来たときにお知らせ。次の予定日は実際に済ませた日から数え直します。ウィジェット、Siri、Apple Watch に対応。アカウント・広告なし。"),
        ],
        "faqs": [
            ("記録し忘れたときは？", "過去の日時を追加・編集・削除できるので、あとから実際にやった日を入れられます。"),
            ("通知はいつから数えますか？", "次の予定日は、最初に決めた日ではなく、実際に済ませた日から数え直します。"),
            ("アカウント登録は必要ですか？", "不要です。アカウント・広告・解析・追跡はなく、主要データは端末内に保存されます。"),
            ("Apple Watch でも使えますか？", "使えます。前回の日時を確認して、手首からワンタップで記録できます。"),
        ],
        "related": [("ja/hubs/mochidonestamp.html", "Mochi DoneStamp のよくある質問")],
        "legal": "本ページで紹介するアプリは独立開発です。App Store の検索結果は2026年に実際に検索したもので、順位は変わることがあります。",
    },
    # 15 MoneyTag × 美國「side hustle tracker」（搜尋建議有、前 10 名 9 個弱對手）
    {
        "key": "moneytag", "lang": "en",
        "slug": "side-hustle-tracker-income-expenses-per-project",
        "terms": ["side hustle tracker", "side hustle income tracker", "freelance income tracker"],
        "title": "Side hustle tracker: see what each side project really earns after expenses",
        "desc": "A day job plus tutoring, an online shop or photo gigs, and no idea what is left at the end of the month? What a side hustle tracker should do, and how MoneyTag keeps every project in its own books. With a link to the US App Store.",
        "h1": "Side hustle tracker: one project, one net result",
        "lead": "Most people who search the App Store for “side hustle tracker” have more than one source of income: a main job, and next to it tutoring, a small online shop, freelance design, photo gigs or a room they rent out.",
        "intro": [
            "Most budgeting apps put everything in one pot. You can see how much you spent in total, but not whether the side hustle is actually worth the evenings. Equipment, materials, mileage and platform fees disappear between rent and groceries, and at the end of the year you are digging through bank statements to piece it all together.",
            "We searched the US App Store in 2026: “side hustle” already suggests income tracking terms, and nine of the top ten results have very few ratings. Below is what a side hustle tracker should do, and how MoneyTag handles it.",
        ],
        "sections": [
            ("Five things a side hustle tracker should do", [], [
                "Separate books: in MoneyTag, a project is a self-contained ledger with its own transactions, its own currency and its own bottom line.",
                "A net result for each project: MoneyTag adds up the income, subtracts the expenses and shows the net result for that project alone.",
                "Tags across projects: tag any income or expense, and the Tags screen totals that same tag across all of your projects at once, with income, expenses and the net for the tag.",
                "Other currencies: each project has its own base currency, with public exchange rates refreshed about every 6 hours or a manual rate you set.",
                "Export: get your records out as CSV, PDF or a photo, and back up and restore your ledger.",
            ]),
            ("Three typical side hustles", [
                "Tutoring or lessons: create a project called Tutoring and log each session as income, books and travel as expenses. The net result shows what the month really earned.",
                "A small online shop: materials, shipping and sales go into a Shop project, kept apart from your household money. With a tag such as Shipping you can see the total even when you run several projects.",
                "Clients abroad: when a client pays in another currency, choose the input currency directly on the Home screen. The converted amount is saved in the project’s base currency, and saved rates remain available offline.",
            ], []),
            ("Always with you", [
                "The same ledger works on iPhone and iPad. The Apple Watch app lets you add a transaction from your wrist and see the current project’s income, expenses and net, and the widgets show that same status on the Home Screen and the Lock Screen.",
                "Projects, transactions, amounts, notes, tags, categories and settings stay in MoneyTag’s on-device storage. With iCloud Sync on, one copy also lives in your own iCloud. MoneyTag is not tax advice, but it makes the numbers easy to bring to your accountant.",
            ], []),
        ],
        "steps_title": "Your first net result in five steps",
        "steps": [
            "Open MoneyTag and create a project for your side hustle.",
            "Choose the project’s base currency.",
            "Log each income and expense, and add a tag where it helps.",
            "Check the project’s net result.",
            "At the end of the month, export it as CSV or PDF.",
        ],
        "cards": [
            ("moneytag", "Every project keeps its own books: income minus expenses is its net result. Tags add up the same item across projects, and each project has its own currency with live or manual rates. The same ledger on iPhone and iPad, an Apple Watch app, and widgets for the Home and Lock Screen. Export as CSV, PDF or a photo, with backup and restore."),
        ],
        "faqs": [
            ("Can I keep my side hustle apart from household money?", "Yes. Each project is a self-contained ledger with its own transactions, its own currency and its own net result."),
            ("How do I see one kind of expense across all projects?", "Tag the transactions. The Tags screen totals that same tag across all of your projects at once."),
            ("Can I export my numbers?", "Yes, as CSV, PDF or a photo, with backup and restore."),
            ("Where is my data stored?", "In MoneyTag’s on-device storage; with iCloud Sync on, one copy also lives in your own iCloud."),
        ],
        "related": [("en-US/hubs/moneytag.html", "MoneyTag: common questions")],
        "legal": "The app featured on this page is independently developed. App Store search results come from our own search in 2026; the order can change. This page is not tax advice.",
    },
    # 16 100 Notes Studio × 日本「手書きノート」（搜尋建議第 1、名稱已含；美國 digital notebook 同在 12 名外，日文名稱命中較近）
    {
        "key": "notesstudio100", "lang": "ja",
        "slug": "tegaki-note-app-pdf-kakikomi-kogi-rokuon",
        "terms": ["手書きノート", "メモ 手書き", "pdf 書き込み"],
        "title": "手書きノートアプリの選び方：紙のような書き心地、PDFへの書き込み、講義の録音まで",
        "desc": "iPad や iPhone で、紙にペンで書くように手書きノートを取りたい。講義のPDFに書き込み、録音も同じページに残したい。手書きノートアプリの選び方と、100 Notes Studio の使い方をまとめました。日本の App Store へのリンク付き。",
        "h1": "手書きノート：書く、書き込む、録音する、復習するをひとつに",
        "lead": "App Store で「手書きノート」と検索する人の多くは、学生や社会人で、何冊ものノートを持ち歩くのはやめたいけれど、手で書く感覚は手放したくないと思っています。",
        "intro": [
            "手で書くと覚えやすい一方で、紙のノートはあとから探すのが大変です。講義の資料がPDFなら、印刷しないと書き込めません。授業の録音は別のアプリにあり、試験前には何か所も開いて見比べることになります。",
            "2026年に日本の App Store を検索したところ、「手書きノート」は検索候補の1番目に出てくる言葉で、上位には大きなアプリと小さなアプリが混ざっていました。ここでは、手書きノートアプリを選ぶときに見るべき点と、100 Notes Studio の使い方をまとめます。",
        ],
        "sections": [
            ("手書きノートアプリ、まずこの5点を確認", [], [
                "書き心地：万年筆や鉛筆から筆ペン、水彩まで29種類のペンとブラシがあり、それぞれが独自の質感を持っています。",
                "スタイラス対応：対応するスタイラスでは筆圧、傾き、パームリジェクション、利用できるショートジェスチャーを使えます。",
                "手書きを検索できるか：端末内で手書きとPDFの文字を認識し、タイトル、本文、手書き、添付ファイルを横断検索できます。",
                "PDFに書き込めるか：PDFの読み込みと注釈はハイライト、下線、取り消し線、テキストメモ、手書き、回転、トリミング、挿入、抽出、結合、書き出しに対応しています。",
                "オフラインで使えるか：主な編集機能はオフラインでも使え、アカウント登録もありません。",
            ]),
            ("授業と試験前の使い方", [
                "講義中：講義のPDFを開いてそのまま書き込みます。書きながら録音でき、録音は作成したページに残るので、あとでそのページの内容と一緒に聞き返せます。",
                "まとめノート：固定ページと無限キャンバス、A4、A5、レター、画面サイズから選べます。定規、8種類の図形ツール、投げ縄ツールで、見やすいまとめを作れます。",
                "試験前：ページと連動する暗記カード、穴埋めカード、FSRSによる間隔反復で、忘れかけたところから復習できます。",
            ], []),
            ("自分だけのノートに", [
                "ノートのスタイルは100種類。ミニマル、リネン、方眼、学習用レイアウト、ドット方眼の手帳、五線譜、会議、レシピなど、表紙や用紙構造まで、それぞれに合わせて設計されています。階層フォルダ、タグ、ピン留め、復元できるゴミ箱で整理できます。",
                "広告や第三者のトラッキングや解析はありません。内容は外部の人工知能へ送信されず、オフラインで端末内に保存されます。アプリ全体またはノートごとに、端末の生体認証でロックできます。",
            ], []),
        ],
        "steps_title": "最初のノートを1分で",
        "steps": [
            "100 Notes Studio を開いて、新しいノートを作ります。",
            "ノートのスタイルとページサイズを選びます。",
            "好きなペンを選んで書き始めます。",
            "講義のPDFを読み込んで書き込むか、そのページで録音します。",
            "試験前は暗記カードで復習します。",
        ],
        "cards": [
            ("notesstudio100", "紙にペンで書くような手書きノート。万年筆や鉛筆から筆ペン、水彩まで29種類のペンとブラシがあり、手書きの文字もあとから検索できます。講義のPDFに直接書き込み、書いているページにそのまま録音を残して、単語カードと間隔反復で復習できます。ノートのスタイルは100種類。主な編集機能はオフラインでも使え、アカウント登録・広告なし。"),
        ],
        "faqs": [
            ("手書きの文字を検索できますか？", "できます。端末内で手書きとPDFの文字を認識し、タイトル、本文、手書き、添付ファイルを横断検索できます。"),
            ("講義のPDFに書き込めますか？", "できます。ハイライト、下線、取り消し線、テキストメモ、手書きなどで注釈し、書き出せます。"),
            ("ネットがなくても使えますか？", "主な編集機能はオフラインでも使え、内容は端末内に保存されます。"),
            ("アカウント登録は必要ですか？", "不要です。広告や第三者のトラッキングもありません。"),
        ],
        "related": [("ja/hubs/notesstudio100.html", "100 Notes Studio のよくある質問")],
        "legal": "本ページで紹介するアプリは独立開発です。App Store の検索結果は2026年に実際に検索したもので、順位は変わることがあります。",
    },
    # 17 OnePage PPT × 美國「one page summary」（推論：無量測；同類實測詞 presentation maker 第 90）
    {
        "key": "onepageppt", "lang": "en",
        "slug": "one-page-summary-slide-from-notes-pdf-iphone",
        "terms": ["one page summary", "presentation maker", "one slide summary"],
        "title": "One-page summary: turn notes, PDFs or a spreadsheet into one slide people read",
        "desc": "A long report, a table of numbers or meeting notes, and a one-page summary due tomorrow? What to look for in a one-page summary app, and how OnePage PPT turns your content into a single 16:9 slide you can export as pptx, PDF or PNG. With a link to the US App Store.",
        "h1": "One-page summary: put your content in, get one slide out",
        "lead": "Most people looking for a one-page summary have a lot of material and very little time: a long report, a spreadsheet of results or a page of meeting notes, and a manager, client or teacher who wants it on one page by tomorrow.",
        "intro": [
            "Summarizing to a single page is harder than it sounds. You have to decide which points matter, which numbers deserve a chart, and then pick a template and drag text boxes around until everything fits. By the time it looks right, half the day is gone.",
            "In the US App Store, “presentation maker” is the term people type, and the first results are the big presentation suites built for full decks. Below is what to look for when you only need one clear page, and how OnePage PPT handles it.",
        ],
        "sections": [
            ("Five things a one-page summary app should do", [], [
                "Take whatever you have: OnePage PPT reads typed notes, pasted text, screenshots, photos, PDFs and CSV tables.",
                "Do the layout for you: it finds the key points and lays them out as a single, presentation-ready 16:9 slide, with no template picking and no dragging boxes around.",
                "Pick the right visual: numbers become column, bar, line, donut or funnel charts, steps become a process flow, and dates become a timeline.",
                "Stay honest with numbers: it only draws a chart the data can honestly support, and it never invents figures.",
                "Export anywhere: an editable .pptx for PowerPoint, Keynote and Google Slides, a PDF for sharing and printing, or a high-resolution PNG for docs, email and chat.",
            ]),
            ("How people use it at work and school", [
                "Monthly results: paste a CSV of sales or KPIs and get the right chart for the data, then send it to your manager as a PDF.",
                "Meeting notes: paste a long page of notes and get the headlines. When two options are on the table, they become a side-by-side comparison.",
                "Reports and lessons: snap a photo or import a PDF and get one slide. Findings become a matrix or a hierarchy, so the structure is clear at a glance.",
            ], []),
            ("Redesign until it is right", [
                "Six one-tap redesigns, Cleaner, More Visual, More Professional, More Bold, More Compact and More Editorial, each genuinely rebuild the slide with different chart forms, typography and layout. Lock any element you like and redesign around it. Tap any element to rewrite it, and full version history lets you go back to any earlier draft.",
                "Everything runs on your device. Your projects and images stay on your iPhone or iPad, exported files leave it only when you share them yourself, and there is no account, no sign-in and no tracking. It works with no network at all.",
            ], []),
        ],
        "steps_title": "A one-page summary in three steps",
        "steps": [
            "Add anything: type, paste, snap a photo, or import a PDF or spreadsheet.",
            "Tap Make My Slide. Your content is summarised into headlines and turned into the right visual.",
            "Present it, or export it as pptx, PDF or PNG.",
        ],
        "cards": [
            ("onepageppt", "Turn a wall of text into one slide people actually read. OnePage PPT reads typed notes, pasted text, screenshots, photos, PDFs and CSV tables, finds the key points, and lays them out as a single, presentation-ready 16:9 slide. Numbers become charts, steps become a process flow, dates become a timeline. Export an editable .pptx, a PDF or a PNG. Everything runs on your device, with no account."),
        ],
        "faqs": [
            ("Can I edit the slide afterwards?", "Yes. The .pptx is editable in PowerPoint, Keynote and Google Slides, and you can tap any element in the app to rewrite it."),
            ("Will it make up numbers?", "No. It only draws a chart the data can honestly support, and it never invents figures."),
            ("What can I put in?", "Typed notes, pasted text, screenshots, photos, PDFs and CSV tables."),
            ("Does it work offline?", "Yes. Everything runs on your device and it works with no network at all."),
        ],
        "related": [("en-US/hubs/onepageppt.html", "OnePage PPT: common questions")],
        "legal": "The app featured on this page is independently developed. App Store search results come from our own search in 2026; the order can change.",
    },
    # 18 PhotoCream × 日本「フィルムカメラ 加工」（「フィルムカメラ」搜尋建議第 4；副標已命中）
    {
        "key": "photocream", "lang": "ja",
        "slug": "film-camera-kakou-app-emoi-shashin-iphone",
        "terms": ["フィルムカメラ 加工", "フィルム加工", "写ルンです 加工"],
        "title": "フィルムカメラ風の加工アプリ：粒子・光漏れ・日付スタンプで、エモい写真に仕上げる",
        "desc": "SNSで見かけるフィルムカメラ風のエモい写真。自分の写真も同じ雰囲気にしたいけれど、色の調整は難しい。フィルムカメラ加工アプリの選び方と、PhotoCream Pro で好きな写真の色を盗む方法をまとめました。日本の App Store へのリンク付き。",
        "h1": "フィルムカメラ加工：色をひとつずつ調整しなくても、あの雰囲気に",
        "lead": "App Store で「フィルムカメラ 加工」と検索する人の多くは、SNSでフィルムカメラで撮ったような写真を見て、自分の写真も同じ雰囲気にしたいと思ったところです。粒子感、少しくすんだ色、昔のカメラのような光漏れ。",
        "intro": [
            "むずかしいのは、出来合いのフィルターがうまくはまる写真が限られることです。光や場所が変わると色がずれ、肌がくすんだり赤くなりすぎたりします。自分でカーブや色を調整しようとすると、それぞれの値が何をするのか分かっていないといけません。",
            "2026年に日本の App Store を検索したところ、「フィルムカメラ」の検索候補には「加工」が並び、上位にはフィルムカメラ風のアプリが多く出てきます。ここでは選ぶときに見るべき点と、PhotoCream Pro で好きな色に仕上げる方法をまとめます。",
        ],
        "sections": [
            ("フィルムカメラ加工アプリ、まずこの5点を確認", [], [
                "ルックを盗めるか：お気に入りの写真を1枚選ぶと、PhotoCream Pro が端末内でその色を分析し、自分の写真に適用できる調整可能なフィルムカラーに変換します。",
                "フィルム調の種類：100種類以上のフィルム調ルックがあり、粒子・ハレーション・光漏れ・周辺減光を選べます。",
                "撮る前に見られるか：シャッターを切る前からライブプレビューで確認できます。",
                "細かく仕上げられるか：カーブ・HSL・スプリットトーンで細かく仕上げられます。",
                "写真が外に出ないか：処理はすべて端末内で完結し、写真がアップロードされることもありません。",
            ]),
            ("こんな写真に", [
                "旅行や年末のアルバム：同じフィルム調ルックを1セットの写真すべてに使い、粒子を足せば、ひとつの物語のようにまとまります。",
                "人物とセルフィー：目や髪のシャープさを保ったまま肌をなめらかに。目を大きく、全身をすらりと自然に伸ばす補正もできます。",
                "昔の写真の雰囲気に：テキスト・フレーム・粒子・ダスト、昔のフィルム写真のような日付スタンプを加えれば、現像から戻ってきたばかりの一枚のようになります。",
            ], []),
            ("自然な色に仕上がる理由", [
                "自分が本当に好きな写真から始めて、まだ調整できるフィルムカラーに変換するので、ゼロから作る必要も、色の値を覚える必要もありません。もう少し好みに近づけたいときは、カーブやHSLで細かく調整を続けられます。",
                "広告はなく、写真がアップロードされることもありません。処理はすべて端末内で完結します。",
            ], []),
        ],
        "steps_title": "フィルムの色に仕上げる5ステップ",
        "steps": [
            "PhotoCream Pro を開いて、色が好きな写真を1枚選びます。",
            "ルックを盗むで、フィルムカラーに変換します。",
            "その色を自分の写真に適用します。",
            "粒子、光漏れ、周辺減光をお好みで足します。",
            "日付スタンプやフレームで、昔のフィルム写真のように仕上げます。",
        ],
        "cards": [
            ("photocream", "ルックを盗む：お気に入りの写真を1枚選ぶと、PhotoCream Pro が端末内でその色を分析し、自分の写真に適用できる調整可能なフィルムカラーに変換します。100種類以上のフィルム調ルック。粒子・ハレーション・光漏れ・周辺減光を、シャッターを切る前からライブプレビューで確認できます。日付スタンプも。広告なし、写真はアップロードされません。"),
        ],
        "faqs": [
            ("好きな写真の色をまねできますか？", "できます。お気に入りの写真を1枚選ぶと、端末内でその色を分析し、調整可能なフィルムカラーに変換します。"),
            ("撮る前にフィルターを確認できますか？", "できます。シャッターを切る前からライブプレビューで確認できます。"),
            ("写真はアップロードされますか？", "されません。処理はすべて端末内で完結します。"),
            ("日付スタンプは入れられますか？", "入れられます。テキスト・フレーム・粒子・ダスト、昔のフィルム写真のような日付スタンプも加えられます。"),
        ],
        "related": [("ja/hubs/photocream.html", "PhotoCream のよくある質問"),
                    ("ja/answers/film-filter-app-for-iphone.html", "フィルム風フィルターアプリ")],
        "legal": "本ページで紹介するアプリは独立開発です。App Store の検索結果は2026年に実際に検索したもので、順位は変わることがあります。",
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
