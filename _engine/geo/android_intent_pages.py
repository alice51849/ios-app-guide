#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android intent pages: "<Android> <task> app" pages in 7 locales -> pages/<locale>/best-for/android-*.html

People on Android search the web with the platform in the query ("android 記帳 app 推薦",
"안드로이드 가계부 앱", "android white noise app"). These pages answer exactly that query with
our apps that are verified live on Google Play (geo/data/android_live_snapshot.json): the Google
Play button is the primary call to action (install referrer utm_source=geo_android), the App
Store link stays as the secondary one. A topic whose apps are not all on Google Play is skipped,
so a page never promotes an app that is not downloadable on Android.

Copy rule: every card quotes the app's own Google Play short description in that language
(store copy, already reviewed); intros and answers only restate those facts. No price, no
"free", no ranking words.

Writes only pages/<locale>/best-for/android-*.html and pages/sitemap_android.xml.

    python3 android_intent_pages.py            # write
    python3 android_intent_pages.py --check    # fail if the written tree differs
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from site_config import PUBLIC_SITE  # noqa: E402
import android_play  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
SITE = os.getenv("GEO_SITE", PUBLIC_SITE)
CT = "geo_android"
APP_STORE_CT = "geo_pick"   # gen_store_attribution owns ?ct= on App Store links; best-for pages are geo_pick
LASTMOD = "2026-10-23"

UI = {
    "zh-Hant": dict(back="← App指南", play="在 Google Play 下載", ios="也有 iPhone 版：App Store",
                    faq="常見問題", paid="在 Google Play 付費下載，沒有訂閱。",
                    iap="先下載使用，完整功能用 App 內購買解鎖。",
                    q_ios="有 iPhone 版嗎？", a_ios="有，{name} 也在 App Store 上架，連結在上方。",
                    q_pay="要怎麼付費？",
                    banner="本站由這些 App 的開發者 Lumi Studio 營運，介紹的是我們自己的 App。"),
    "ja": dict(back="← アプリガイド", play="Google Play でダウンロード", ios="iPhone 版もあります：App Store",
               faq="よくある質問", paid="Google Play での買い切りダウンロードです。サブスクリプションはありません。",
               iap="まずダウンロードして使い、すべての機能はアプリ内購入で解放します。",
               q_ios="iPhone 版はありますか？", a_ios="あります。{name} は App Store にもあります（上のリンク）。",
               q_pay="料金のしくみは？",
               banner="当サイトは掲載アプリの開発者であるLumi Studioが運営し、自社アプリを紹介しています。"),
    "ko": dict(back="← 앱 가이드", play="Google Play에서 다운로드", ios="iPhone 버전도 있어요: App Store",
               faq="자주 묻는 질문", paid="Google Play 유료 다운로드이며 구독이 없습니다.",
               iap="먼저 내려받아 쓰고, 전체 기능은 앱 내 구매로 엽니다.",
               q_ios="iPhone 버전도 있나요?", a_ios="네, {name} iPhone 버전은 App Store에서 받을 수 있어요(위 링크).",
               q_pay="결제는 어떻게 하나요?",
               banner="이 사이트는 소개된 앱의 개발사인 Lumi Studio가 운영하며, 여기서 추천하는 앱은 모두 자사 앱입니다."),
    "en": dict(back="← App Guide", play="Get it on Google Play", ios="Also on iPhone: App Store",
               faq="FAQ", paid="A paid download on Google Play, with no subscription.",
               iap="Download it first; the full version is unlocked with an in-app purchase.",
               q_ios="Is there an iPhone version?", a_ios="Yes, {name} is also on the App Store (link above).",
               q_pay="How does pricing work?",
               banner="This site is run by Lumi Studio, the developer of the featured apps. The apps recommended here are our own."),
    "de-DE": dict(back="← App-Ratgeber", play="Bei Google Play laden", ios="Auch fürs iPhone: App Store",
                  faq="Häufige Fragen", paid="Ein einmaliger Kauf bei Google Play, ohne Abo.",
                  iap="Zuerst laden und nutzen; die Vollversion wird per In-App-Kauf freigeschaltet.",
                  q_ios="Gibt es eine iPhone-Version?", a_ios="Ja, {name} gibt es auch im App Store (Link oben).",
                  q_pay="Wie funktioniert die Bezahlung?",
                  banner="Diese Website wird von Lumi Studio betrieben, dem Entwickler der vorgestellten Apps. Die hier empfohlenen Apps sind unsere eigenen."),
    "pt-BR": dict(back="← Guia de Apps", play="Baixar no Google Play", ios="Também para iPhone: App Store",
                  faq="Perguntas frequentes", paid="Download pago no Google Play, sem assinatura.",
                  iap="Baixe e use primeiro; a versão completa é liberada com uma compra no app.",
                  q_ios="Tem versão para iPhone?", a_ios="Sim, o {name} também está na App Store (link acima).",
                  q_pay="Como funciona o pagamento?",
                  banner="Este site é mantido pela Lumi Studio, desenvolvedora dos apps apresentados. Os apps recomendados aqui são nossos."),
    "id": dict(back="← Panduan Aplikasi", play="Unduh di Google Play", ios="Juga ada untuk iPhone: App Store",
               faq="Pertanyaan umum", paid="Unduhan berbayar di Google Play, tanpa langganan.",
               iap="Unduh dan pakai dulu; versi lengkap dibuka dengan pembelian dalam aplikasi.",
               q_ios="Apakah ada versi iPhone?", a_ios="Ada, {name} juga tersedia di App Store (tautan di atas).",
               q_pay="Bagaimana cara pembayarannya?",
               banner="Situs ini dikelola oleh Lumi Studio, pengembang aplikasi yang ditampilkan. Aplikasi yang kami rekomendasikan di sini adalah aplikasi kami sendiri."),
}
HTML_LANG = {"zh-Hant": "zh-Hant", "ja": "ja", "ko": "ko", "en": "en", "de-DE": "de-DE", "pt-BR": "pt-BR", "id": "id"}

# Google Play titles and short descriptions, copied from the live listings on 2026-10-23 (store copy).
CARDS = {
    "zh-Hant": {
        "gmoney": ("G+Money：旅遊記帳", "出國旅遊與日常記帳，搭配 50 種貨幣匯率換算，依旅程記錄花費、設每日預算", "paid"),
        "moneytag": ("MoneyTag: 收入與支出記帳", "專案制收支記帳：每個專案各算淨額，標籤跨專案合計，接案、副業、小店都好用", "iap"),
        "hourstaglite": ("HoursTag Lite", "買東西前先換算要工作幾小時，標記必要、想要或衝動，花得清楚，存錢也更有方向", "iap"),
        "mochi": ("Mochi: 可愛待辦清單", "可愛又療癒的待辦清單，寫下待辦事項輕點打勾，100 款主題外觀與重複提醒", "iap"),
        "mochidonestamp": ("Mochi DoneStamp：上次何時", "上次是什麼時候做的？一鍵記下家事與保養的完成時間，顯示經過天數，到期自動循環提醒", "iap"),
        "sereno": ("Sereno: 睡眠音效・白噪音", "白噪音、褐噪音與雨聲即時生成不循環，陪你入睡、專注與放鬆", "iap"),
        "zipbox": ("Zipbox 解壓縮：RAR ZIP 7z", "解壓縮前先預覽壓縮檔內容，只取出需要的檔案；支援 13 種格式，也能開啟密碼保護的壓縮檔", "paid"),
        "lumibopomofo": ("Lumi注音星球", "幼兒學注音好幫手：餵食小夥伴、描寫筆順、聲調與拼音遊戲，輕鬆認讀 37 個符號", "iap"),
        "lumibopomofopro": ("Lumi注音星球 Pro", "用遊戲學注音：ㄅㄆㄇ發音、拼讀、聲調與筆順，幼兒到小一都適用", "paid"),
        "easyam": ("EasyAM: 國定假日、連假不響的智慧鬧鐘", "上班日、補班日照響，國定假日與休假不響；主畫面小工具，101 款時鐘主題可先預覽", "iap"),
    },
    "ja": {
        "gmoney": ("G+Money：旅行家計簿・通貨換算", "海外旅行の支出をすぐ記録。50通貨の為替換算と1日の予算管理ができる旅行家計簿", "paid"),
        "gmoneylite": ("G+Money Lite", "海外旅行の支出を現地通貨で記録して、すぐ自国通貨に換算。1日の予算管理にも", "iap"),
        "mochi": ("Mochi：かわいいToDoリスト", "かわいく整うToDoリスト＆チェックリスト。100種類のスキンと、くり返しリマインダー", "iap"),
        "sereno": ("Sereno：睡眠用サウンド・ホワイトノイズ", "眠るときや集中したいときに。ループしないホワイトノイズ・ブラウンノイズ・雨の音", "iap"),
        "zipbox": ("Zipbox：ZIP・RAR・7z 解凍", "ZIP・RAR・7zを解凍。展開前に中身をプレビューして、必要なファイルだけ取り出せます", "paid"),
        "qrcodehalo": ("QR Code Halo：QRコード読み取り・作成", "QRコードリーダー＆バーコード読み取り。QRコード作成と端末内のリンク安全チェック", "iap"),
    },
    "ko": {
        "gmoney": ("G+Money: 여행 가계부·지출 관리", "해외여행 지출을 바로 기록하고 50개 통화 환율 변환과 하루 예산까지 챙기는 여행 가계부", "paid"),
        "mochi": ("Mochi: 귀여운 할 일 목록", "100가지 포근한 스킨과 반복 알림이 있는 귀여운 할 일 목록·체크리스트", "iap"),
        "ledmovingtext": ("LED Moving Text: 핸드폰 전광판", "흐르는 글자 LED 전광판: 콘서트 응원, 공항 마중, 픽업, 행사에서 휴대폰을 들어요", "iap"),
        "countdaysnow": ("CountDaysNow: 디데이 카운트다운", "생일·기념일·여행 디데이 위젯: 며칠 남았는지, 며칠 지났는지 한눈에 세어 봐요", "iap"),
        "studydown": ("Studydown: 엎어 두는 집중 타이머", "휴대폰을 엎어 두면 시간이 쌓이는 공부 타이머이자 집중 시간 기록 앱", "iap"),
    },
    "en": {
        "sereno": ("Sereno: Sleep Sounds", "White noise, brown noise and rain sounds that never loop, for sleep and focus", "iap"),
        "cyca": ("Cyca: Period & Cycle Tracker", "Private period and cycle tracker with a daily body forecast and calm calendar", "iap"),
        "picclear": ("PicClear Pro: Photo Cleaner", "Duplicate photo remover: clear screenshots and blurry shots to reclaim storage", "iap"),
        "unblurry": ("Unblurry Pro: Unblur Photo HD", "Restore old photos offline, sharpen blurry shots and upscale them with AI", "iap"),
        "zipbox": ("Zipbox: Unzip RAR, ZIP & 7z", "Unzip, unrar and 7z file extractor: preview inside, take out only what you need", "paid"),
        "lockhour": ("LockHour Pro: App Blocker", "App blocker for focus and digital detox: lock distracting apps, less phone time", "iap"),
        "studydown": ("Studydown: Face-Down Timer", "Face-down study timer and focus tracker: put the phone down, see hours add up", "iap"),
        "snapport": ("Snapport: Passport & ID Photos", "Passport photo maker for visa and ID photos, with templates and print sheets", "paid"),
        "snapportlite": ("Snapport Lite: Passport Photo", "Passport, visa and ID photo maker: 2x2 sizing, white background, print sheets", "iap"),
        "ledmovingtext": ("LED Moving Text: Banner Sign", "Scrolling text LED banner: hold up your phone at concerts, pickups and events", "iap"),
    },
    "de-DE": {
        "sereno": ("Sereno: Schlafklänge", "Weißes Rauschen, braunes Rauschen und Regengeräusche ohne Schleife", "iap"),
        "cyca": ("Cyca: Periode & Zyklus-Tracker", "Privater Perioden- und Zyklustracker mit täglicher Körpervorhersage & Kalender", "iap"),
        "scanto": ("ScanTo Pro: PDF Scanner & OCR", "Dokumentenscanner mit OCR-Textsuche auf dem Gerät – offline und privat", "iap"),
    },
    "pt-BR": {
        "sereno": ("Sereno: Sons para Dormir", "Ruído branco, ruído marrom e sons de chuva que nunca se repetem, para dormir", "iap"),
        "cyca": ("Cyca: Calendário Menstrual", "Rastreador privado de ciclo com previsão corporal diária e calendário calmo", "iap"),
        "picclear": ("PicClear Pro: Limpar Fotos", "Remova fotos duplicadas, prints e fotos borradas e libere espaço no celular", "iap"),
    },
    "id": {
        "cyca": ("Cyca: Kalender Menstruasi", "Pelacak siklus pribadi dengan prakiraan tubuh harian dan kalender yang tenang", "iap"),
        "picclear": ("PicClear Pro", "Hapus tangkapan layar dan foto duplikat, bebaskan penyimpanan tanpa internet", "iap"),
    },
}

# (locale, slug, title / h1, meta description, intro, app keys)
TOPICS = [
    ("zh-Hant", "android-jizhang-app-tuijian", "Android 記帳 App 推薦（2026）：旅遊記帳、副業收支、先想再買",
     "在 Google Play 找 Android 記帳 App？依你要記的東西挑：出國旅遊記帳換算台幣、接案副業分專案算收支、買東西前先換算工時。",
     "在 Google Play 搜「記帳」會跳出一大堆功能很多的 App。先想清楚你要記的是什麼：出國旅遊要用當地貨幣記帳、換算回台幣，選 G+Money；接案、副業、小店要分專案看收支淨額，選 MoneyTag；想在下單前先停一下，選 HoursTag Lite。",
     ["gmoney", "moneytag", "hourstaglite"]),
    ("zh-Hant", "android-keai-daiban-qingdan-app", "Android 可愛待辦清單 App 推薦（2026）",
     "想找可愛的 Android 待辦事項 App？Mochi 待辦清單有 100 款主題外觀與重複提醒；Mochi DoneStamp 記下家事上次是哪天做的。",
     "待辦清單要每天打開才有用。如果你想要可愛、療癒、打開就想用的 Android 待辦事項 App，Mochi 把待辦寫成清單、完成時輕點打勾；家事和保養這種「上次是哪天做的？」的事，交給 Mochi DoneStamp。",
     ["mochi", "mochidonestamp"]),
    ("zh-Hant", "android-baizaoyin-zhumian-app", "Android 白噪音 App：助眠、專注都好用（2026）",
     "Android 白噪音 App 推薦：Sereno 的白噪音、褐噪音與雨聲即時生成、不循環，陪你入睡與專注。",
     "很多白噪音 App 是一段錄音一直重播，安靜的夜裡聽得出接縫。Sereno 在手機上即時生成白噪音、褐噪音與雨聲，聲音不循環，適合睡前或讀書、工作時開著。",
     ["sereno"]),
    ("zh-Hant", "android-jieyasuo-rar-zip-app", "Android 解壓縮 App：RAR、ZIP、7z 怎麼開（2026）",
     "Android 手機打不開 RAR、7z？Zipbox 解壓縮前先預覽內容、只取出需要的檔案，支援 13 種格式與密碼保護壓縮檔。",
     "收到 RAR、ZIP、7z 壓縮檔，手機卻打不開？Zipbox 可以先預覽壓縮檔裡有什麼，再只取出你要的那一個檔案；支援 13 種格式，也能開啟密碼保護的壓縮檔。",
     ["zipbox"]),
    ("zh-Hant", "android-zhuyin-app", "Android 注音 App：孩子學ㄅㄆㄇ（2026）",
     "Android 注音 App 推薦：Lumi注音星球用餵食、描寫、聲調與拼音遊戲帶孩子認讀 37 個注音符號。",
     "孩子要上小一、要學ㄅㄆㄇ了？Lumi注音星球用遊戲帶孩子認讀 37 個注音符號；想要發音、拼讀、聲調、筆順一次到位，選 Lumi注音星球 Pro。",
     ["lumibopomofo", "lumibopomofopro"]),
    ("zh-Hant", "android-guoding-jiari-buxiang-naozhong", "Android 鬧鐘：國定假日、連假不響，補班日照響（2026）",
     "連假前不想手動關鬧鐘？EasyAM 上班日、補班日照響，國定假日與休假不響，主畫面小工具一眼看到明天會不會響。",
     "每到連假前一晚都要記得關鬧鐘，收假又要記得打開？EasyAM 幫你判斷：上班日、補班日照響，國定假日與你的休假不響。",
     ["easyam"]),
    ("ja", "android-ryokou-kakeibo-app", "Android の旅行家計簿アプリ：為替計算もひとつで（2026）",
     "Android で使える旅行家計簿アプリ。G+Money は50通貨の為替換算と1日の予算管理、G+Money Lite は現地通貨の支出をすぐ自国通貨に換算。",
     "海外旅行の支出を現地通貨で記録して、合計は円で見たい。そんなときの Android 向け旅行家計簿です。旅行ごとに予算まで管理するなら G+Money、まず記録と換算だけなら G+Money Lite。",
     ["gmoney", "gmoneylite"]),
    ("ja", "android-kawaii-todo-list-app", "Android のかわいいToDoリストアプリ（2026）",
     "かわいいToDoリストを Android で。Mochi は100種類のスキンとくり返しリマインダー付きのチェックリストアプリ。",
     "やることリストは、毎日開きたくなる見た目がいちばん大事。Mochi はかわいいスキンでToDoリストとチェックリストを整え、くり返すタスクはリマインダーでお知らせします。",
     ["mochi"]),
    ("ja", "android-white-noise-app", "Android のホワイトノイズ・雨音アプリ（2026）",
     "Android で使えるホワイトノイズアプリ。Sereno はループしないホワイトノイズ・ブラウンノイズ・雨の音を端末内で生成。",
     "録音をくり返すタイプのアプリだと、静かな夜に切れ目が気になることがあります。Sereno はホワイトノイズや雨の音を端末の中でリアルタイムに生成するので、ループの切れ目がありません。",
     ["sereno"]),
    ("ja", "android-kaitou-app-zip-rar", "Android の解凍アプリ：ZIP・RAR・7z（2026）",
     "Android で ZIP・RAR・7z を解凍。Zipbox は展開前に中身をプレビューして、必要なファイルだけ取り出せます。",
     "メールで届いた ZIP や、ダウンロードした RAR・7z を Android で開きたいときに。Zipbox は展開する前に中身を確認して、必要なファイルだけ取り出せます。",
     ["zipbox"]),
    ("ja", "android-qr-code-reader-app", "Android のQRコードリーダー：読み取りと作成（2026）",
     "Android のQRコードリーダー＆バーコード読み取り。QR Code Halo はQRコード作成と端末内のリンク安全チェックにも対応。",
     "QRコードやバーコードを読み取って、そのまま開く。QR Code Halo はQRコードの作成もでき、保存したコードは端末内でリンクの安全チェックができます。",
     ["qrcodehalo"]),
    ("ko", "android-yeohaeng-gagyebu-app", "안드로이드 여행 가계부 앱 (환율 계산 포함, 2026)",
     "안드로이드 여행 가계부 앱: G+Money는 해외여행 지출을 바로 기록하고 50개 통화 환율 변환과 하루 예산까지 챙겨요.",
     "해외여행에서 현지 통화로 쓴 돈, 원화로 얼마인지 바로 알고 싶다면. G+Money는 지출을 기록하면 50개 통화 환율로 바로 변환하고 하루 예산까지 챙겨 주는 안드로이드 여행 가계부예요.",
     ["gmoney"]),
    ("ko", "android-gwiyeoun-todolist-app", "안드로이드 귀여운 투두리스트 앱 (2026)",
     "안드로이드 귀여운 투두리스트: Mochi는 100가지 포근한 스킨과 반복 알림이 있는 할 일 목록·체크리스트 앱이에요.",
     "투두리스트는 매일 열고 싶어야 계속 쓰게 돼요. Mochi는 귀여운 스킨으로 할 일 목록과 체크리스트를 정리하고, 반복되는 일은 알림으로 챙겨 줘요.",
     ["mochi"]),
    ("ko", "android-led-jeongwangpan-app", "안드로이드 LED 전광판 앱: 콘서트 응원, 공항 마중 (2026)",
     "안드로이드 핸드폰 전광판 앱: LED Moving Text로 흐르는 글자를 띄워 콘서트 응원, 공항 마중, 픽업에 써요.",
     "콘서트 응원, 공항 마중, 픽업할 때 목소리 대신 휴대폰을 들어요. LED Moving Text는 입력한 문구를 흐르는 LED 전광판으로 보여 줘요.",
     ["ledmovingtext"]),
    ("ko", "android-dday-widget-app", "안드로이드 디데이 위젯 앱 (2026)",
     "안드로이드 디데이 위젯: CountDaysNow로 생일·기념일·여행까지 며칠 남았는지, 며칠 지났는지 한눈에.",
     "생일, 기념일, 여행, 시험까지 며칠 남았는지 홈 화면에서 바로 보고 싶다면. CountDaysNow는 남은 날과 지난 날을 위젯으로 세어 줘요.",
     ["countdaysnow"]),
    ("ko", "android-gongbu-timer-app", "안드로이드 공부 타이머 앱: 폰 엎어 두기 (2026)",
     "안드로이드 공부 타이머: Studydown은 휴대폰을 엎어 두면 시간이 쌓이는 집중 타이머이자 공부 시간 기록 앱이에요.",
     "공부할 때 폰을 엎어 두는 것만으로 집중 시간이 쌓여요. Studydown은 엎어 둔 시간을 기록해 오늘 얼마나 공부했는지 보여 줘요.",
     ["studydown"]),
    ("en", "android-white-noise-app", "White Noise App for Android: Sleep and Focus (2026)",
     "A white noise app for Android: Sereno plays white noise, brown noise and rain sounds that never loop, for sleep and focus.",
     "Many white noise apps replay a short recording, and on a quiet night you can hear the seam. Sereno generates white noise, brown noise and rain sounds live on your Android phone, so they never loop.",
     ["sereno"]),
    ("en", "android-private-period-tracker", "Private Period Tracker for Android (2026)",
     "A private period tracker for Android: Cyca keeps your cycle on your phone, with a daily body forecast and a calm calendar.",
     "If you want a period tracker that keeps your data on your phone, start with what it stores and where. Cyca is a private period and cycle tracker for Android with a daily body forecast and a calm calendar.",
     ["cyca"]),
    ("en", "android-duplicate-photo-remover", "Duplicate Photo Remover for Android (2026)",
     "Reclaim storage on Android: PicClear Pro finds duplicate photos, old screenshots and blurry shots to clear.",
     "When your Android phone says storage is full, photos are usually the reason. PicClear Pro finds duplicate photos, screenshots and blurry shots so you can review them and reclaim space.",
     ["picclear"]),
    ("en", "android-unblur-photo-app", "Unblur Photo App for Android (2026)",
     "Unblur photos on Android: Unblurry Pro sharpens blurry shots, restores old photos and upscales them on your device.",
     "A shaky hand or a missed focus point can spoil a photo you cannot retake. Unblurry Pro sharpens blurry shots, restores old photos and upscales them right on your Android phone.",
     ["unblurry"]),
    ("en", "android-rar-zip-7z-extractor", "RAR, ZIP and 7z Extractor for Android (2026)",
     "Open RAR, ZIP and 7z files on Android: Zipbox lets you preview inside an archive and take out only what you need.",
     "Got a RAR or 7z file your Android phone will not open? Zipbox unzips, unrars and opens 7z files, and lets you preview what is inside before you extract only the file you need.",
     ["zipbox"]),
    ("en", "android-app-blocker-for-focus", "App Blocker and Study Timer for Android (2026)",
     "Stay off your phone on Android: LockHour Pro locks distracting apps; Studydown is a face-down study timer.",
     "Two ways to spend less time on your phone: lock the apps that pull you in with LockHour Pro, or put the phone face down and let Studydown count your focus hours.",
     ["lockhour", "studydown"]),
    ("en", "android-passport-photo-maker", "Passport Photo Maker for Android (2026)",
     "Make passport, visa and ID photos on Android with templates and print sheets: Snapport and Snapport Lite.",
     "Need a passport or visa photo before an appointment? Snapport and Snapport Lite make passport, visa and ID photos on your Android phone, with size templates and print sheets. Always check the official requirements before you submit.",
     ["snapport", "snapportlite"]),
    ("en", "android-led-banner-app", "LED Banner App for Android: Scrolling Text (2026)",
     "Turn your Android phone into a scrolling LED banner for concerts, airport pickups and events: LED Moving Text.",
     "At a concert, an arrivals hall or a pickup curb, a bright scrolling message works better than shouting. LED Moving Text turns your Android phone into a scrolling text LED banner.",
     ["ledmovingtext"]),
    ("de-DE", "android-einschlafgeraeusche-app", "Einschlafgeräusche-App für Android (2026)",
     "Einschlafgeräusche für Android: Sereno erzeugt weißes Rauschen, braunes Rauschen und Regengeräusche ohne Schleife.",
     "Viele Einschlaf-Apps spielen eine kurze Aufnahme in Schleife, und nachts hört man die Naht. Sereno erzeugt weißes und braunes Rauschen sowie Regengeräusche direkt auf deinem Android-Handy, ohne Schleife.",
     ["sereno"]),
    ("de-DE", "android-periodenkalender-privat", "Privater Periodenkalender für Android (2026)",
     "Privater Periodenkalender für Android: Cyca mit täglicher Körpervorhersage und ruhigem Kalender.",
     "Wenn dein Periodenkalender privat bleiben soll, zählt, wo die Daten liegen. Cyca ist ein privater Perioden- und Zyklustracker für Android mit täglicher Körpervorhersage und Kalender.",
     ["cyca"]),
    ("de-DE", "android-dokumente-scannen-offline", "Dokumente offline scannen mit Android (2026)",
     "Dokumentenscanner für Android mit OCR-Textsuche auf dem Gerät – offline und privat: ScanTo Pro.",
     "Verträge, Belege und Formulare als PDF scannen, ohne sie in eine Cloud hochzuladen: ScanTo Pro ist ein Dokumentenscanner für Android mit OCR-Textsuche direkt auf dem Gerät.",
     ["scanto"]),
    ("pt-BR", "android-sons-para-dormir-app", "App de sons para dormir no Android (2026)",
     "Sons para dormir no Android: o Sereno toca ruído branco, ruído marrom e sons de chuva que nunca se repetem.",
     "Muitos apps de sons para dormir repetem uma gravação curta, e no silêncio da noite dá para ouvir o corte. O Sereno gera ruído branco, ruído marrom e sons de chuva no próprio celular Android, sem repetição.",
     ["sereno"]),
    ("pt-BR", "android-calendario-menstrual-privado", "Calendário menstrual privado para Android (2026)",
     "Calendário menstrual privado para Android: o Cyca acompanha o ciclo com previsão corporal diária e calendário calmo.",
     "Se você quer um calendário menstrual que mantenha seus dados no celular, o Cyca é um rastreador privado de ciclo para Android, com previsão corporal diária e calendário calmo.",
     ["cyca"]),
    ("pt-BR", "android-apagar-fotos-duplicadas", "App para apagar fotos duplicadas no Android (2026)",
     "Libere espaço no Android: o PicClear Pro encontra fotos duplicadas, prints e fotos borradas para remover.",
     "Quando o celular avisa que o armazenamento está cheio, as fotos costumam ser o motivo. O PicClear Pro encontra fotos duplicadas, prints e fotos borradas para você revisar e liberar espaço.",
     ["picclear"]),
    ("id", "android-kalender-menstruasi-pribadi", "Aplikasi kalender menstruasi pribadi untuk Android (2026)",
     "Kalender menstruasi untuk Android: Cyca adalah pelacak siklus pribadi dengan prakiraan tubuh harian dan kalender yang tenang.",
     "Kalau kamu ingin kalender menstruasi yang datanya tetap di ponsel, Cyca adalah pelacak siklus pribadi untuk Android dengan prakiraan tubuh harian dan kalender yang tenang.",
     ["cyca"]),
    ("id", "android-hapus-foto-duplikat", "Aplikasi hapus foto duplikat untuk Android (2026)",
     "Memori penuh? PicClear Pro menghapus tangkapan layar dan foto duplikat untuk membebaskan penyimpanan Android.",
     "Saat memori ponsel Android penuh, biasanya foto penyebabnya. PicClear Pro menemukan foto duplikat dan tangkapan layar supaya kamu bisa memeriksa lalu menghapusnya.",
     ["picclear"]),
]


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def page_path(locale: str, slug: str) -> Path:
    return PAGES / locale / "best-for" / f"{slug}.html"


def page_url(locale: str, slug: str) -> str:
    return f"{SITE}/{locale}/best-for/{slug}.html"


def render(locale: str, slug: str, title: str, desc: str, intro: str, keys: list[str], apps: dict) -> str:
    ui = UI[locale]
    url = page_url(locale, slug)
    cards, items, faqs = [], [], []
    for pos, key in enumerate(keys, 1):
        name, short, model = CARDS[locale][key]
        entry = apps[key]
        play = android_play.tracked_play_url(entry["play_url"], CT, key)
        store = f"https://apps.apple.com/app/id{entry['ios_app_id']}?pt=118326163&ct={APP_STORE_CT}&mt=8"
        items.append({"@type": "ListItem", "position": pos, "name": name, "url": play})
        cards.append(
            f'<div class="app"><strong>{esc(name)}</strong><p>{esc(short)}</p>'
            f'<p><em>{esc(ui[model])}</em></p>'
            f'<a href="{esc(play)}" class="dl" rel="noopener">{esc(ui["play"])} →</a> '
            f'<a href="{esc(store)}" class="ios" rel="noopener">{esc(ui["ios"])}</a></div>')
        faqs.append((ui["q_ios"] if len(keys) == 1 else f'{name}: {ui["q_ios"]}', ui["a_ios"].format(name=name)))
    model_lines = " ".join(f'{CARDS[locale][k][0]}: {ui[CARDS[locale][k][2]]}' if len(keys) > 1
                           else ui[CARDS[locale][k][2]] for k in keys)
    faqs.append((ui["q_pay"], model_lines))
    ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": title, "description": desc,
           "itemListElement": items},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}]
    faq_html = "".join(f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faqs)
    return f"""<!DOCTYPE html>
<html lang="{HTML_LANG[locale]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{url}">
<style>
body{{font-family:system-ui,sans-serif;max-width:700px;margin:2rem auto;padding:0 1rem;color:#222}}
h1{{font-size:1.4rem;line-height:1.3}}
h2{{font-size:1.1rem;margin-top:2rem}}
.app{{border:1px solid #e8e8e8;border-radius:10px;padding:1.2rem;margin:1.5rem 0}}
.app strong{{display:block;font-size:1.1rem;margin:.3rem 0}}
.app p{{margin:.4rem 0;color:#444;font-size:.9rem}}
.dl{{display:inline-block;background:#01875f;color:#fff;padding:.6rem 1.2rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.9rem;margin-top:.7rem}}
.ios{{display:inline-block;color:#007aff;font-size:.85rem;margin:.7rem 0 0 .6rem}}
.faq{{border:1px solid #e8e8e8;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0}}
.faq summary{{cursor:pointer;font-size:.95rem}}
.faq p{{margin:.5rem 0 0;color:#444;font-size:.9rem}}
</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body><p class="first-party-disclosure" data-first-party-disclosure="banner" role="note" style="margin:0;padding:8px 16px;background:#f3f4f6;color:#1f2937;border-bottom:1px solid #d1d5db;font-size:13px;line-height:1.5;text-align:center">{esc(ui["banner"])}</p>

<p><a href="{SITE}/{locale}/">{esc(ui["back"])}</a></p>
<h1>{esc(title)}</h1>
<p>{esc(intro)}</p>
{chr(10).join(cards)}
<h2>{esc(ui["faq"])}</h2>
{faq_html}
</body>
</html>
"""


def build(apps: dict | None = None) -> dict[Path, str]:
    apps = android_play.load_snapshot() if apps is None else apps
    out: dict[Path, str] = {}
    urls = []
    for locale, slug, title, desc, intro, keys in TOPICS:
        if not all(k in apps for k in keys):
            print(f"skip {locale}/{slug}: not every app is on Google Play", file=sys.stderr)
            continue
        out[page_path(locale, slug)] = render(locale, slug, title, desc, intro, keys, apps)
        urls.append(page_url(locale, slug))
    body = "".join(f"  <url><loc>{u}</loc><lastmod>{LASTMOD}</lastmod></url>\n" for u in urls)
    out[PAGES / "sitemap_android.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    files = build()
    stale = []
    for path, text in files.items():
        cur = path.read_text(encoding="utf-8") if path.exists() else None
        if cur == text:
            continue
        stale.append(path)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    print(f"android intent pages: {len(files) - 1} pages, {'stale' if args.check else 'written'}={len(stale)}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
