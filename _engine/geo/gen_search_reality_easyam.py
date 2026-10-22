#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜尋實況意圖頁：假日鬧鐘（easyam）新上架 6 頁 → <Guide>/<lang>/seasonal/<slug>.html。

背景：業主 2026-10-23「easyAM是近期新上架有沒有確保加到每一條宣傳線再推一波」。aso/search_reality/easyam.md
依 App Store 搜尋建議（clientApplication=Software）與搜尋結果前 12 名，替輪班族、上班族挑出各國最該搶的詞；
這支替主力 5 國（台、日、韓、德、巴西）各寫一頁母語手寫內容，外加英文（美、英）一頁，標題與網址用使用者真的會打的字。

沿用第 3 組產生器（gen_search_reality_g3.py）的版面、檢查、Google Play 補連結與 sitemap 合併，只換頁面內容、
語系表與禁用字（加韓、德、葡的免費／價格字）。規則同第 3 組：
- 功能句只取 data/easyam_full.json 該語系商店文案；不寫價格、免費、Free、Pro。
- 每頁一張主卡，附該國 App Store 直連（pt＋ct＋mt）；ct＝ln_easyam_sr_<國碼>_gw_1023。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 每頁專屬內容：中日文 ≥450 字、韓文 ≥450 個韓文字、英德葡 ≥450 個詞。
- 只寫這些頁與各語系 sitemap_seasonal_<lang>.xml 的這幾列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_easyam.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_easyam.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gen_search_reality_g3 as g3  # noqa: E402

LANGS = dict(g3.LANGS)
LANGS.update({
    "ko": {"store": "ko", "dir": "ko", "cc": "kr", "og": "ko_KR", "html": "ko",
           "home": "iOS 앱 가이드", "answers": "답변", "about": "소개", "crumb": "추천",
           "updated": "업데이트", "cta": "App Store에서 다운로드 →", "more": "앱 자세히 보기",
           "faq": "자주 묻는 질문", "related": "관련 페이지", "toc": "이 페이지", "home_label": "홈"},
    "de-DE": {"store": "de-DE", "dir": "de-DE", "cc": "de", "og": "de_DE", "html": "de-DE",
              "home": "iOS-App-Guide", "answers": "Antworten", "about": "Über uns", "crumb": "Empfehlungen",
              "updated": "Aktualisiert", "cta": "Im App Store laden →", "more": "Zur ausführlichen App-Seite",
              "faq": "Häufige Fragen", "related": "Verwandte Seiten", "toc": "Auf dieser Seite", "home_label": "Start"},
    "pt-BR": {"store": "pt-BR", "dir": "pt-BR", "cc": "br", "og": "pt_BR", "html": "pt-BR",
              "home": "Guia de Apps iOS", "answers": "Respostas", "about": "Sobre", "crumb": "Recomendações",
              "updated": "Atualizado", "cta": "Baixar na App Store →", "more": "Ver o app completo",
              "faq": "Perguntas frequentes", "related": "Páginas relacionadas", "toc": "Nesta página",
              "home_label": "Início"},
})
APP_IDS = {"easyam": "6821790092"}
BANNED = re.compile(
    r"免費|免费|無料|무료|\bfree\b|\bpro\b|kostenlos|gratis|grátis|gratuito|NT\$|US\$|R\$|\$\s?\d|€\s?\d|\d\s?€|"
    r"¥\s?\d|￥|\d\s?円|\d\s?元|\d\s?원",
    re.IGNORECASE,
)
HANGUL = re.compile(r"[가-힣]")
LATIN_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")


def dedicated_size(lang: str, text: str) -> int:
    if lang in ("zh-Hant", "zh-Hans", "ja"):
        return len(g3.CJK.findall(text))
    if lang == "ko":
        return len(HANGUL.findall(text))
    return len(LATIN_WORD.findall(text))


PAGE_SPECS: list[dict] = [
    # 1 台灣：「國定假日 鬧鐘」「輪班鬧鐘」「假日鬧鐘」
    {
        "key": "easyam", "lang": "zh-Hant",
        "slug": "guoding-jiari-naozhong-buban-zhaoxiang-lunban-zhhant",
        "terms": ["國定假日 鬧鐘", "輪班鬧鐘", "假日鬧鐘", "上班日 鬧鐘"],
        "title": "國定假日鬧鐘怎麼選？連假不響、補班日照響、輪班也適用的 5 個重點",
        "desc": "連假前一晚不想再一個個關鬧鐘、收假又怕忘了打開？國定假日鬧鐘要看假日資料、補班日、請假與輪班、只跳過一次、iOS 系統鬧鐘。附 EasyAM 的實際設定步驟與台灣 App Store 直連。",
        "h1": "國定假日鬧鐘怎麼選：連假不響、補班日照響的 5 個重點",
        "lead": "在 App Store 搜「國定假日 鬧鐘」「輪班鬧鐘」的人，多半剛經歷過一次連假：前一晚把鬧鐘一個個關掉，收假那天早上卻忘了打開，差點遲到。",
        "intro": [
            "台灣一年有好幾次連假，還有補班日、颱風假、自己排的特休。內建的「時鐘」App 只會照星期幾重複，它不知道今天是國定假日，也不知道這個星期六要補班。所以大家才會去找「國定假日不響、上班日才響」的鬧鐘。",
            "我們在 2026 年 10 月實際查了台灣 App Store：打「國定假日」時跳出的建議裡，就有好幾款專門做假日鬧鐘的 App；打「輪班」時，「輪班鬧鐘」是前幾個建議詞。代表這不是少數人的需求，而是每逢連假就會有人重新找一次。挑之前，先確認下面幾件事，才不會裝了之後還是要自己手動關。",
        ],
        "sections": [
            ("國定假日鬧鐘真正要做到的 5 件事", [], [
                "假日資料要內建、而且離線也能用：國定假日自動跳過，不必每年自己輸入；沒有網路時照樣判斷。",
                "補班日要照響：週六補班是台灣特有的情況，鬧鐘要知道那天是上班日。",
                "自己的休假也要能設：請假、特休、出國旅遊，設成休假就安靜不響，收假那天自動恢復。",
                "臨時狀況一鍵處理：颱風假前一晚宣布、明天想晚點起床，只跳過「下一次」，原本的規則不要被改掉。",
                "響不響要看得到：最好能一眼看到接下來七天哪幾天會響、幾點響，睡前不用再猜。",
            ]),
            ("三種最常見的情況，各自怎麼設", [
                "一般上班族：週一到週五設一個起床鬧鐘就好。國定假日與連假的早上安安靜靜，前一晚什麼都不用動；遇到補班的星期六，鬧鐘照常叫你起床。年底想排特休接元旦連假，把那幾天設成休假，整段日期一次設好，也能一次刪掉。",
                "輪班、排班的護理師、工廠、保全、餐飲：班表不是週一到週五，透過 App 內購買使用輪班與隔週模式，設定一次就照著班別響。夜班、值班、加班這類額外上班日，可以加上標籤與圖示，月曆一看就知道哪天要上班。",
                "學生與老師：上課日照常起床，寒暑假整段設成休假；開學那天早上，鬧鐘自己會回來。",
            ], []),
            ("為什麼「資料不明就照響」很重要", [
                "鬧鐘最怕的不是多響一次，而是該響的時候不響。EasyAM 的做法是：假日資料不明或過舊的日子，一律算作上班日，鬧鐘照常響。內建 67 個國家與地區 2026 至 2028 年的假日資料，可以離線使用，也能下載較新的資料檔。",
                "另外，它使用 iOS 系統鬧鐘排程，iOS 確認後才顯示鬧鐘已就緒，並可查看排程狀態；響鈴或貪睡時，會以即時動態顯示在鎖定畫面與動態島。",
            ], []),
        ],
        "steps_title": "連假前 3 分鐘設定好",
        "steps": [
            "打開 EasyAM，國家或地區選台灣（之後外派、出國也能隨時更換）。",
            "設定一個每週重複的起床鬧鐘，例如週一到週五 7:00，加上標籤與想要的貪睡時間。",
            "打開「接下來七天」確認：國定假日那幾天不響、補班日照響。",
            "有排特休或出國，就在行事曆把那幾天設成休假，可以單日也可以整段日期。",
            "臨時放颱風假或想晚點起床，用一鍵「只跳過下一次」，原本的規則不變。",
        ],
        "cards": [
            ("easyam", "EasyAM 每天幫你判斷鬧鐘要不要響：上班日照響，國定假日和你的休假安靜不響，補班日也照常叫你起床。接下來七天哪幾天會響、幾點響一眼看清楚（iPad 可看 14 天），主畫面、鎖定畫面與 Apple Watch 都看得到下一次鬧鐘。不需要帳號、沒有廣告、不追蹤。不限鬧鐘數量、輪班與隔週模式、每個鬧鐘各自的假日曆與另外 100 款時鐘主題，以一次性 App 內購買解鎖。"),
        ],
        "faqs": [
            ("國定假日鬧鐘遇到補班日會響嗎？", "會。EasyAM 遇到補班日照常響鈴，週六要上班也不用另外設鬧鐘。"),
            ("颱風假臨時宣布，要怎麼讓明天不響？", "一鍵只跳過下一次。只有明天早上那一次不響，原本每週的規則不變。"),
            ("輪班、排班的人可以用嗎？", "可以。透過 App 內購買使用輪班與隔週模式，設定一次就照著班別響；夜班、值班、加班等額外上班日也能加上標籤與圖示。"),
            ("沒有網路還能判斷假日嗎？", "可以。內建 67 個國家與地區 2026 至 2028 年的假日資料，可離線使用；假日資料不明或過舊的日子一律算作上班日，鬧鐘照常響。"),
        ],
        "related": [("zh-Hant/easyam.html", "EasyAM 完整介紹"),
                    ("zh-Hant/seasonal/lianjia-dasaochu-zhengli-daiban-qingdan-app-zhhant.html", "連假大掃除與待辦清單 App")],
    },
    # 2 日本：「アラーム 祝日」「祝日は鳴らないアラーム」「シフト アラーム」
    {
        "key": "easyam", "lang": "ja",
        "slug": "shukujitsu-naranai-alarm-iphone-shift-kinmu",
        "terms": ["アラーム 祝日", "祝日は鳴らないアラーム", "シフト アラーム", "交代勤務 アラーム"],
        "title": "祝日に鳴らないアラームの選び方：iPhoneで「平日だけ鳴る」を自動にする5つのポイント",
        "desc": "三連休の前にアラームを切って、休み明けに戻し忘れる…をなくすには。祝日データ、有給の登録、シフト・隔週、次の1回だけスキップで比べるポイントと、EasyAMの設定手順。",
        "h1": "祝日に鳴らないアラームの選び方：平日だけ鳴るiPhoneアラーム",
        "lead": "App Storeで「アラーム 祝日」「祝日は鳴らないアラーム」と検索する人の多くは、連休明けの朝にアラームが鳴らず、ひやっとした経験がある人です。",
        "intro": [
            "iPhone標準の時計アプリは、曜日でしか繰り返しを設定できません。祝日も平日として鳴り、三連休の前に一つずつ切って、休み明けに戻し忘れる。この繰り返しが嫌で、Androidのころは「祝日に鳴らない目覚まし」を使っていたのに、iPhoneに替えたら見つからない、という声も多く見かけます。",
            "2026年10月に日本のApp Storeで実際に「祝日」と入力すると、検索候補の上位に「アラーム 祝日」や「祝日は鳴らないアラームアプリ」が出てきます。それだけ多くの人が探しているということです。選ぶ前に、次のポイントを確認しておくと失敗しません。",
        ],
        "sections": [
            ("祝日に鳴らないアラームに必要な5つのこと", [], [
                "祝日データを内蔵していて、オフラインでも判断できること。毎年手で入力する必要がないこと。",
                "有給や夏休み、年末年始の会社の休みを「休み」として登録でき、その朝は鳴らないこと。",
                "シフト勤務や隔週の休みにも合わせられること。",
                "明日だけゆっくり起きたいときに、次の1回だけをスキップできること。いつものルールはそのまま残ること。",
                "この先何日分、どの日の何時に鳴るのかが、ひと目でわかること。",
            ]),
            ("こんな人は、こう使う", [
                "会社員：平日の起床アラームを1つ作るだけ。文化の日（11月3日）の朝も、勤労感謝の日（11月23日）までの三連休の朝も静かなままで、前の晩に何もしなくて大丈夫です。休み明けの朝は、いつも通り鳴ります。",
                "シフト勤務・交代勤務（看護・介護・工場・警備・飲食など）：App内課金でシフトや隔週のパターンを一度設定すれば、あとはおまかせ。残業、出張、夜勤、オンコールなどの追加の出勤日も、ラベルとアイコンを付けて登録できます。",
                "お盆や年末年始に休む人：会社の休みを休暇として登録しておけば、その日の朝は鳴りません。期間でまとめて登録・編集・削除できます。",
            ], []),
            ("「わからない日は鳴らす」という安心", [
                "アラームで一番困るのは、鳴るべき日に鳴らないことです。EasyAMは、祝日データが不明または古い日を出勤日とみなし、アラームを鳴らします。67の国と地域の祝日データ（2026年から2028年）を内蔵し、オフラインで使え、新しいデータのダウンロードにも対応しています。",
                "予約はiOSのシステムアラームで行い、iOSの確認が取れてから準備完了を表示します。鳴っている間やスヌーズ中は、ライブアクティビティとDynamic Islandに表示されます。",
            ], []),
        ],
        "steps_title": "連休の前に3分で設定",
        "steps": [
            "EasyAMを開き、国・地域を日本に設定する（海外勤務になってもいつでも変更できます）。",
            "平日の起床アラームを1つ作る。曜日ごとの繰り返し、ラベル、スヌーズの長さを決める。",
            "この先7日間の表示で、祝日の朝が「鳴らない」になっているか確認する。",
            "有給や会社の休みがあれば、カレンダーで休暇として登録する（1日でも期間でも可）。",
            "明日だけゆっくり起きたい日は、次の1回だけをワンタップでスキップする。",
        ],
        "cards": [
            ("easyam", "EasyAMが毎日判断して、出勤日は鳴らし、祝日や自分の休みの日は鳴らしません。この先7日間（iPadでは14日間）のどの日に何時に鳴るかがひと目でわかり、次のアラームはウィジェット、ロック画面、Apple Watchでも確認できます。アカウント登録は不要で、広告・分析・トラッキングはありません。アラーム数の制限なし、シフト・隔週パターン、アラームごとの祝日カレンダー、さらに100種類の時計テーマは、1回限りのApp内課金で利用できるようになります。"),
        ],
        "faqs": [
            ("祝日は自分で入力する必要がありますか？", "必要ありません。67の国と地域の祝日データ（2026年から2028年）を内蔵しており、新しいデータのダウンロードにも対応しています。"),
            ("シフト勤務でも使えますか？", "使えます。App内課金でシフトや隔週のパターンを一度設定すれば、その通りに鳴ります。夜勤やオンコールなどの追加の出勤日も登録できます。"),
            ("明日だけ鳴らしたくないときは？", "次の1回だけをワンタップでスキップできます。いつものルールはそのままです。"),
            ("祝日データがない日はどうなりますか？", "祝日データが不明または古い日は出勤日とみなし、アラームは鳴ります。"),
        ],
        "related": [("ja/easyam.html", "EasyAMの詳しい紹介")],
    },
    # 3 韓國：「공휴일 알람」「교대근무 알람」「평일 알람」
    {
        "key": "easyam", "lang": "ko",
        "slug": "gonghyuil-allam-iphone-gyodae-geunmu",
        "terms": ["공휴일 알람", "교대근무 알람", "평일 알람", "빨간날 알람"],
        "title": "공휴일 알람 고르는 법: 빨간날엔 안 울리고 출근날엔 울리는 아이폰 알람 5가지 기준",
        "desc": "연휴 전날 알람 끄고, 연휴 끝나고 다시 켜는 걸 깜빡한 적 있다면. 공휴일 데이터, 연차 등록, 교대근무·격주, 다음 알람 한 번만 건너뛰기로 비교하는 법과 EasyAM 설정 순서.",
        "h1": "공휴일 알람 고르는 법: 빨간날엔 조용히, 출근날엔 정확히",
        "lead": "App Store에서 '공휴일 알람'이나 '교대근무 알람'을 검색하는 분들은 대부분 한 번쯤 연휴가 끝난 아침에 알람을 다시 켜는 걸 깜빡해 본 분들이에요.",
        "intro": [
            "아이폰 기본 시계 앱은 요일로만 반복을 정할 수 있어요. 빨간날도 평일처럼 울리니까, 연휴 전날 밤에 알람을 하나씩 끄고 연휴가 끝나면 다시 켜야 하죠. 설날이나 추석처럼 긴 연휴라면 더 번거롭고, 깜빡하면 바로 지각이에요.",
            "2026년 10월에 한국 App Store에서 '공휴일'을 입력해 보면 검색어 추천 위쪽에 '공휴일 알람'이 나오고, '교대근무 알람'을 입력하면 교대근무 알람 앱들이 줄줄이 나와요. 그만큼 많은 사람이 찾고 있다는 뜻이에요. 고르기 전에 아래 기준을 먼저 확인해 보세요.",
        ],
        "sections": [
            ("공휴일 알람이 꼭 해야 하는 다섯 가지", [], [
                "공휴일 데이터가 앱 안에 들어 있어서 인터넷이 없어도 판단할 수 있을 것. 해마다 직접 입력하지 않아도 될 것.",
                "연차, 여행, 병가처럼 내가 쉬는 날을 휴가로 등록하면 그날 아침엔 울리지 않을 것.",
                "교대근무나 격주 근무 패턴에도 맞출 수 있을 것.",
                "내일만 늦잠 자고 싶을 때 다음 알람 한 번만 건너뛰고, 원래 규칙은 그대로 둘 수 있을 것.",
                "앞으로 며칠 동안 어느 날 몇 시에 울리는지 한눈에 볼 수 있을 것.",
            ]),
            ("이런 분은 이렇게 쓰세요", [
                "직장인: 평일 기상 알람 하나만 만들면 끝이에요. 연휴 아침에도 전날 밤 알람을 만질 필요가 없고, 연휴가 끝난 출근날 아침엔 평소처럼 울려요. 징검다리 연휴에 연차를 붙인다면 그날을 휴가로 등록해 두면 돼요.",
                "교대근무자(간호사, 생산직, 경비, 요식업 등): 앱 내 구입으로 교대근무·격주 패턴을 한 번만 설정해 두면 알아서 울려요. 야근, 출장, 야간근무, 당직 같은 추가 근무일도 이름과 아이콘을 붙여 등록할 수 있어요.",
                "학생과 선생님: 수업 있는 날에 맞춰 일어나고, 방학은 기간으로 한 번에 휴가 등록하면 돼요.",
            ], []),
            ("모를 때는 울리는 쪽으로", [
                "알람에서 가장 무서운 건 울려야 할 날 안 울리는 거예요. EasyAM은 공휴일 정보가 없거나 오래된 날을 근무일로 간주해서 알람을 울려요. 67개 국가·지역의 공휴일 데이터(2026년부터 2028년까지)가 들어 있고, 오프라인으로 쓸 수 있으며 새 데이터 파일도 받을 수 있어요.",
                "예약은 iOS 시스템 알람으로 하고, iOS가 확인한 뒤에만 준비 완료로 표시해요. 알람이 울리거나 스누즈 중일 때는 실시간 현황과 Dynamic Island에 표시돼요.",
            ], []),
        ],
        "steps_title": "연휴 전에 3분이면 끝",
        "steps": [
            "EasyAM을 열고 국가를 대한민국으로 설정해요(해외 근무 때도 언제든 바꿀 수 있어요).",
            "평일 기상 알람을 하나 만들어요. 요일 반복, 레이블, 스누즈 시간을 정해요.",
            "앞으로 7일 화면에서 공휴일 아침이 울리지 않는지 확인해요.",
            "연차나 여행이 있으면 캘린더에서 휴가로 등록해요. 하루도, 기간도 돼요.",
            "내일만 늦잠 자고 싶으면 다음 알람 한 번만 탭 한 번으로 건너뛰어요.",
        ],
        "cards": [
            ("easyam", "EasyAM이 날마다 알아서 정해요. 출근하는 날엔 울리고, 공휴일과 내가 등록한 휴가엔 조용히 쉬어요. 앞으로 7일(iPad는 14일) 동안 어느 날 몇 시에 울리는지 한눈에 보이고, 다음 알람은 위젯, 잠금 화면, Apple Watch에서도 확인할 수 있어요. 계정이 필요 없고 광고, 분석, 추적이 없어요. 알람 개수 제한 해제, 교대근무·격주 패턴, 알람별 공휴일 달력, 시계 테마 100종 추가는 한 번의 앱 내 구입으로 잠금 해제돼요."),
        ],
        "faqs": [
            ("공휴일을 직접 입력해야 하나요?", "아니요. 67개 국가·지역의 공휴일 데이터(2026년부터 2028년까지)가 들어 있고, 새 데이터 파일도 받을 수 있어요."),
            ("교대근무자도 쓸 수 있나요?", "네. 앱 내 구입으로 교대근무·격주 패턴을 한 번만 설정해 두면 알아서 울려요. 야간근무나 당직 같은 추가 근무일도 등록할 수 있어요."),
            ("내일 하루만 안 울리게 하려면요?", "탭 한 번으로 다음 알람만 건너뛰면 돼요. 원래 규칙은 그대로예요."),
            ("공휴일 정보가 없는 날은 어떻게 되나요?", "공휴일 정보가 없거나 오래된 날은 근무일로 간주해 알람이 울려요."),
        ],
        "related": [("ko/easyam.html", "EasyAM 자세히 보기")],
    },
    # 4 德國：「Wecker Feiertage」「Wecker ohne Feiertage」「Schichtwecker」
    {
        "key": "easyam", "lang": "de-DE",
        "slug": "wecker-feiertage-ueberspringen-iphone-schichtdienst",
        "terms": ["Wecker Feiertage", "Wecker ohne Feiertage", "Schichtwecker", "Schicht Wecker"],
        "title": "Wecker, der an Feiertagen nicht klingelt: So findest du den richtigen fürs iPhone (auch im Schichtdienst)",
        "desc": "Vor jedem Feiertag den Wecker aus, danach wieder an – und einmal vergessen? Worauf es bei einem Feiertags-Wecker ankommt: Feiertagsdaten, Urlaub, Brückentage, Schichtmuster, nur den nächsten Wecker auslassen. Mit Anleitung für EasyAM.",
        "h1": "Wecker ohne Feiertage: woran du einen guten Feiertags-Wecker fürs iPhone erkennst",
        "lead": "Wer im App Store nach „Wecker Feiertage“ oder einem Schichtwecker sucht, hat meistens schon einmal nach einem langen Wochenende verschlafen, weil der Wecker noch aus war.",
        "intro": [
            "Die Uhr-App des iPhone kennt nur Wochentage. Sie weiß nicht, dass heute Feiertag ist, und sie weiß auch nichts von deinem Urlaub oder deinem Brückentag. Also schaltet man vor jedem Feiertag den Wecker ab und muss danach daran denken, ihn wieder einzuschalten. Genau dieser zweite Schritt geht irgendwann schief.",
            "Im Oktober 2026 haben wir im deutschen App Store nachgesehen: Wer „Feiertag“ eintippt, bekommt neben Feiertagskalendern bereits einen Wecker vorgeschlagen, der Feiertage auslässt, und bei „Schicht“ tauchen Schichtplan- und Schichtkalender-Apps ganz oben auf. Das Bedürfnis ist also groß. Bevor du dich entscheidest, lohnt sich ein Blick auf die folgenden Punkte.",
        ],
        "sections": [
            ("Fünf Dinge, die ein Feiertags-Wecker können muss", [], [
                "Feiertagsdaten in der App, die auch offline funktionieren, damit du sie nicht jedes Jahr selbst eintragen musst.",
                "Urlaub, Brückentage und freie Tage einmal eintragen können, damit der Wecker an diesen Tagen still bleibt.",
                "Schichtmuster oder Wechselwochen abbilden können, wenn du nicht Montag bis Freitag arbeitest.",
                "Morgen ausschlafen, ohne die Regel zu ändern: nur den nächsten Wecker auslassen.",
                "Auf einen Blick zeigen, an welchen Tagen und um wie viel Uhr der Wecker in den nächsten Tagen klingelt.",
            ]),
            ("So nutzen es Büro, Schichtdienst und Schule", [
                "Im Büro: Ein Wecker für Montag bis Freitag genügt. An Feiertagen und Brückentagen schläfst du aus, ohne abends etwas umzustellen, und am ersten Arbeitstag danach klingelt er wie gewohnt. Wer zwischen den Jahren frei hat, trägt den ganzen Zeitraum einmal als Urlaub ein und kann ihn genauso in einem Schritt wieder ändern oder löschen.",
                "Im Schichtdienst, etwa in Pflege, Produktion, Sicherheitsdienst oder Gastronomie: Schichtmuster oder Wechselwochen legst du per In-App-Kauf einmal fest, EasyAM plant die passenden Tage. Zusätzliche Arbeitstage wie Überstunden, Dienstreisen, Nachtschichten oder Bereitschaft trägst du mit eigenem Namen und Symbol ein.",
                "Lehrkräfte und Studierende: Ferien als freie Tage eintragen, der Wecker richtet sich danach und meldet sich am ersten Schultag von selbst zurück.",
            ], []),
            ("Gesetzliche und regionale Feiertage: lieber vorher nachsehen", [
                "In Deutschland unterscheiden sich viele Feiertage von Bundesland zu Bundesland. EasyAM bringt Feiertage für 67 Länder und Regionen für 2026 bis 2028 mit, nutzbar ohne Internet und mit neueren Dateien zum Herunterladen. Im Monatskalender siehst du vorab, welche Feiertage und freien Tage eingetragen sind. Fehlt ein regionaler Feiertag, den du frei hast, trägst du ihn einfach als freien Tag ein.",
                "Wichtig für die Sicherheit: Fehlen Feiertagsdaten oder sind sie veraltet, zählt der Tag als Arbeitstag und der Wecker klingelt. Geplant wird über echte iOS-Systemwecker, die erst als bereit angezeigt werden, wenn iOS die Planung bestätigt hat. Beim Klingeln und Schlummern erscheint der Wecker als Live-Aktivität und in der Dynamic Island.",
            ], []),
        ],
        "steps_title": "In drei Minuten vor dem nächsten Feiertag eingerichtet",
        "steps": [
            "EasyAM öffnen und Deutschland als Land wählen; bei einem Umzug ins Ausland lässt sich das Land jederzeit wechseln.",
            "Einen Wecker für die Arbeitstage anlegen, mit Bezeichnung und Schlummerzeit zwischen 1 und 60 Minuten.",
            "In der 7-Tage-Vorschau prüfen, dass der nächste Feiertag still bleibt.",
            "Urlaub und Brückentage im Kalender als freie Tage eintragen, einzeln oder als Zeitraum.",
            "Morgen ausschlafen? Mit einem Tippen nur den nächsten Wecker auslassen; deine Regel bleibt.",
        ],
        "cards": [
            ("easyam", "EasyAM entscheidet Tag für Tag, ob dein Wecker klingelt: am Arbeitstag ja, an Feiertagen und im Urlaub nein. Die 7-Tage-Vorschau zeigt, an welchen Tagen und um wie viel Uhr es klingelt. Feiertage für 67 Länder und Regionen (2026 bis 2028), offline nutzbar. Schichtmuster und Wechselwochen gibt es per In-App-Kauf. Widgets für Home-Bildschirm und Sperrbildschirm sowie eine App für die Apple Watch."),
        ],
        "faqs": [
            ("Muss ich die Feiertage selbst eintragen?", "Nein. EasyAM bringt Feiertage für 67 Länder und Regionen für 2026 bis 2028 mit, offline nutzbar, und neuere Dateien lassen sich laden."),
            ("Funktioniert das auch im Schichtdienst?", "Ja. Schichtmuster oder Wechselwochen legst du per In-App-Kauf einmal fest; zusätzliche Arbeitstage wie Nachtschichten oder Bereitschaft trägst du mit Namen und Symbol ein."),
            ("Wie lasse ich nur morgen aus?", "Ein Tippen lässt nur den nächsten Wecker aus. Deine Regel bleibt, wie sie ist."),
            ("Was passiert, wenn Feiertagsdaten fehlen?", "Dann zählt der Tag als Arbeitstag und der Wecker klingelt. Im Zweifel wird geweckt."),
        ],
        "related": [("de-DE/easyam.html", "EasyAM ausführlich")],
    },
    # 5 巴西：「despertador feriado」「despertador escala」「despertador dia útil」
    {
        "key": "easyam", "lang": "pt-BR",
        "slug": "despertador-nao-toca-feriado-escala-iphone",
        "terms": ["despertador feriado", "despertador escala", "despertador dia útil", "despertador que não toca no feriado"],
        "title": "Despertador que não toca no feriado: como escolher no iPhone (e funcionar até na escala de trabalho)",
        "desc": "Cansou de desligar o alarme na véspera do feriado e esquecer de ligar de novo? O que conferir num despertador para feriados: dados de feriados, folgas e emendas, escala, pular só o próximo alarme. Com o passo a passo do EasyAM.",
        "h1": "Despertador que não toca no feriado: o que conferir antes de escolher",
        "lead": "Quem procura “despertador feriado” ou “despertador escala” na App Store quase sempre já perdeu a hora depois de um feriadão, porque o alarme ainda estava desligado.",
        "intro": [
            "O app Relógio do iPhone só entende dias da semana. Ele não sabe que hoje é feriado, não sabe da sua folga e muito menos da sua escala. Por isso a rotina é sempre a mesma: desligar o alarme na véspera e torcer para lembrar de ligar de novo depois. É justamente essa segunda parte que falha um dia.",
            "Em outubro de 2026 conferimos a App Store do Brasil: quem digita “feriado” já recebe sugestões de calendários de feriados e de um despertador que pula feriados, e quem digita “escala” vê apps de escala de trabalho e de plantão logo no topo. A procura é grande. Antes de escolher, vale conferir os pontos abaixo.",
        ],
        "sections": [
            ("Cinco coisas que um despertador para feriados precisa fazer", [], [
                "Ter os dados de feriados dentro do app, funcionando até sem internet, para você não precisar cadastrar tudo todo ano.",
                "Deixar marcar férias, folgas e emendas uma vez só, para o alarme ficar em silêncio nesses dias.",
                "Acompanhar a escala ou as semanas alternadas de quem não trabalha de segunda a sexta.",
                "Pular só o próximo alarme quando você quer dormir mais amanhã, sem mudar a regra.",
                "Mostrar de uma vez em quais dias e em que horário o alarme vai tocar nos próximos dias.",
            ]),
            ("Escritório, escala e plantão: como cada um usa", [
                "No escritório: um alarme de segunda a sexta resolve. Nos feriados e emendas você descansa sem mexer em nada na noite anterior, e no primeiro dia útil depois ele toca no horário de sempre. Em novembro há vários feriados nacionais próximos, como Finados, Proclamação da República e Consciência Negra; antes de cada um, abra a prévia dos próximos 7 dias e confira em quais manhãs o alarme vai tocar.",
                "Escala ou plantão, como enfermagem, indústria, segurança e restaurantes: defina uma vez o padrão de turnos ou de semanas alternadas (compra dentro do app) e o EasyAM calcula os dias certos. Dias extras de trabalho, como hora extra, viagem, turno da noite ou sobreaviso, entram com nome e ícone do seu jeito.",
                "Professores e estudantes: marque as férias como folga e o alarme se adapta, voltando sozinho no primeiro dia de aula.",
            ], []),
            ("Na dúvida, toca", [
                "O pior que um despertador pode fazer é ficar quieto no dia em que você precisa acordar. Por isso, no EasyAM, se faltar dado de feriado ou ele estiver desatualizado, o dia conta como dia útil e o alarme toca. São feriados de 67 países e regiões, de 2026 a 2028, em 15 países também os estaduais ou provinciais; funciona offline e permite baixar arquivos mais recentes. No calendário mensal você vê com antecedência os feriados e as suas folgas.",
                "Os alarmes são alarmes reais do sistema iOS, mostrados como prontos só depois que o iOS confirma o agendamento. Enquanto toca ou está na soneca, o alarme aparece como Atividade ao Vivo e na Dynamic Island.",
            ], []),
        ],
        "steps_title": "Pronto em três minutos antes do próximo feriado",
        "steps": [
            "Abra o EasyAM e escolha o Brasil como país; se você se mudar, dá para trocar de país quando quiser.",
            "Crie um alarme para os dias úteis, com nome e soneca ajustável de 1 a 60 minutos.",
            "Na prévia dos próximos 7 dias, confira que a manhã do próximo feriado fica em silêncio.",
            "Marque férias, folgas e emendas no calendário, um dia só ou um período inteiro.",
            "Quer dormir mais amanhã? Um toque pula só o próximo alarme, sem mudar a regra.",
        ],
        "cards": [
            ("easyam", "O EasyAM decide, dia a dia, se o alarme deve tocar: dia útil toca, feriado ou folga não toca. A prévia dos próximos 7 dias mostra em quais dias ele toca e em que horário. Feriados de 67 países e regiões (2026 a 2028), funciona offline. Padrão de turnos e semanas alternadas com compra dentro do app. Widgets da Tela de Início e da Tela Bloqueada e app para o Apple Watch."),
        ],
        "faqs": [
            ("Preciso cadastrar os feriados sozinho?", "Não. O EasyAM traz feriados de 67 países e regiões de 2026 a 2028, funciona offline e permite baixar arquivos mais recentes."),
            ("Funciona para quem trabalha em escala?", "Sim. Defina uma vez o padrão de turnos ou de semanas alternadas (compra dentro do app); dias extras como turno da noite ou sobreaviso também podem ser marcados."),
            ("Como faço para não tocar só amanhã?", "Um toque pula só o próximo alarme. A regra continua igual."),
            ("E se faltar o dado de algum feriado?", "Nesse caso o dia conta como dia útil e o alarme toca. Na dúvida, toca."),
        ],
        "related": [("pt-BR/easyam.html", "EasyAM completo")],
    },
    # 6 英文（美、英）：「shift work alarm」「alarm skip holidays」「holiday alarm clock」
    {
        "key": "easyam", "lang": "en",
        "slug": "shift-work-alarm-skip-public-holidays-iphone",
        "terms": ["shift work alarm", "alarm skip holidays", "holiday alarm clock", "workday alarm clock"],
        "title": "Shift work alarm that skips public holidays: how to pick one for iPhone",
        "desc": "Tired of switching your alarm off before every long weekend and forgetting to turn it back on? What to check in a holiday alarm clock: built-in holiday data, time off, shift patterns, skip-once, real iOS alarms. With setup steps for EasyAM.",
        "h1": "Shift work alarm that skips public holidays: what to check before you choose",
        "lead": "People who search the App Store for \"shift work alarm\" or \"alarm skip holidays\" have usually overslept once after a long weekend, because the alarm they switched off on Friday was still off on Tuesday.",
        "intro": [
            "The built-in Clock app on iPhone repeats by weekday and nothing else. It does not know that Monday is a public holiday, it does not know about your vacation, and it certainly does not know your rotating schedule. So the routine becomes: turn the alarm off before the holiday, then remember to turn it back on. The second half is the part that eventually fails, and it fails on the one morning that matters.",
            "We looked at the US and UK App Store in October 2026. Typing \"shift\" or \"shift alarm\" brings up a whole row of shift work alarm apps, and typing \"holiday alarm\" surfaces holiday alarm clocks right away, so plenty of people are looking. Before you pick one, it is worth checking the points below.",
        ],
        "sections": [
            ("Five things a holiday-aware alarm has to get right", [], [
                "Built-in public holiday data that works offline, so you do not have to type the holidays in every year.",
                "Time off you can add once, such as vacations, sick days and trips, so those mornings stay quiet.",
                "Shift or alternating-week patterns for anyone who does not work Monday to Friday.",
                "A way to sleep in tomorrow without touching your routine: skip only the next ring.",
                "A clear view of which mornings will ring and at what time over the next few days.",
            ]),
            ("Office hours, rotating shifts and school terms", [
                "Office workers: one weekday alarm is enough. Long weekends take care of themselves, with nothing to switch off the night before, and the first workday back rings as usual. Thanksgiving, Christmas and New Year's Day are the obvious test.",
                "Shift workers in nursing, manufacturing, security, hospitality or emergency services: set a shift or alternating-week pattern once, available with the in-app purchase, and let the app work out the right mornings. Extra working days such as overtime, business trips, night shifts or on-call days can carry their own label and icon, so the calendar shows them at a glance.",
                "Students and teachers: ring on class days and add school breaks as time off; the alarm returns by itself on the first day of school.",
            ], []),
            ("When in doubt, it rings", [
                "The worst thing an alarm can do is stay quiet on a morning you need it. EasyAM treats days with unknown or outdated holiday data as workdays, so the alarm rings. It carries holiday data for 67 countries and regions for 2026 to 2028, usable offline, with newer data files to download, and the calendar tab shows public holidays, make-up working days and your days off by month.",
                "Alarms are real iOS system alarms, marked ready only after iOS confirms the schedule, and there is a schedule health screen if you want to check. While an alarm rings or snoozes, it shows as a Live Activity and in the Dynamic Island.",
            ], []),
        ],
        "steps_title": "Three minutes before the next long weekend",
        "steps": [
            "Open EasyAM and choose your country or region; you can change it anytime if you move or work abroad.",
            "Create one alarm for your workdays, with a label and a snooze length from 1 to 60 minutes.",
            "Check the seven-day preview: the next public holiday should show as a quiet morning.",
            "Add vacations and other days off in the calendar, as a single day or a date range.",
            "Want a slow start tomorrow? One tap skips only the next ring and keeps your routine.",
        ],
        "cards": [
            ("easyam", "EasyAM decides day by day whether your alarm should ring: it rings on workdays and stays quiet on public holidays and your days off. The seven-day preview shows which mornings ring and at what time (14 days on iPad), and your next alarm is on your widgets, Lock Screen and Apple Watch. No account, no ads, no tracking. Unlimited alarms, shift and alternating-week patterns, a holiday calendar per alarm and 100 more clock themes unlock with a one-time in-app purchase."),
        ],
        "faqs": [
            ("Do I have to enter public holidays myself?", "No. EasyAM includes holiday data for 67 countries and regions for 2026 to 2028, works offline and can download newer data files."),
            ("Does it work for rotating shifts?", "Yes. Set a shift or alternating-week pattern once with the in-app purchase; extra working days such as night shifts or on-call days can be added with a label and icon."),
            ("How do I skip just tomorrow?", "One tap skips only the next ring. Your weekly routine stays as it is."),
            ("What if holiday data is missing for a day?", "Days with unknown or outdated holiday data count as workdays, so the alarm rings."),
        ],
        "related": [("en-US/easyam.html", "EasyAM full overview"),
                    ("answers/alarm-skip-holidays-app-for-iphone.html", "Alarm that skips holidays on iPhone")],
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
