#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web mini-tools that do the exact job of one app (owner-approved 2026-10-14).

Each spec plugs into demand_tools.SPEC_BUILDERS, so pages share its chrome,
hreflang, FAQ/WebApplication JSON-LD, related-tool links, tools index cards
and the tools sitemap.  Everything runs client-side; nothing is uploaded or
stored.  App cards only name the app (facts checked against the live App
Store listing on 2026-10-14) and defer to the listing for features and price.

Demand: every locale carries at least one query that Google Suggest
completes from a truncated prefix (geo/search_demand_audit.py probe,
2026-10-14; D2 = 1 word withheld, D3 = 2, D4 = 3+).
"""
from __future__ import annotations

# ------------------------------------------------ days between dates (CountDaysNow)

DAYS_CSS = """
.days-block{border-top:1px solid var(--line);margin-top:22px;padding-top:6px}
.days-block h3{font-family:ui-serif,Georgia,serif;font-size:21px;margin:12px 0 0}
.big{font-size:clamp(26px,5vw,40px);font-weight:850;color:var(--brand);margin:14px 0 0}
@media (max-width:720px){.controls,.results{grid-template-columns:1fr 1fr}}
"""

DAYS_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="d1">{ui[l_start]}</label><input type="date" id="d1"></div>
<div class="field"><label for="d2">{ui[l_end]}</label><input type="date" id="d2"></div>
<div class="field"><label for="incl">{ui[l_incl]}</label><select id="incl"><option value="0">{ui[no]}</option><option value="1">{ui[yes]}</option></select></div>
</div>
<div class="results">
<div class="result ok"><strong>{ui[r_days]}</strong><span id="rd">—</span></div>
<div class="result"><strong>{ui[r_weeks]}</strong><span id="rw">—</span></div>
<div class="result"><strong>{ui[r_ymd]}</strong><span id="ry">—</span></div>
<div class="result"><strong>{ui[r_work]}</strong><span id="rk">—</span></div>
</div>
<div class="days-block">
<h3>{ui[h_count]}</h3>
<div class="controls">
<div class="field"><label for="ev">{ui[l_event]}</label><input type="text" id="ev" maxlength="60"></div>
<div class="field"><label for="ed">{ui[l_edate]}</label><input type="date" id="ed"></div>
<div class="field" style="align-self:end"><button class="button ghost" id="today">{ui[b_today]}</button></div>
</div>
<p class="big" id="cd" aria-live="polite">—</p>
</div>
<div class="days-block">
<h3>{ui[h_add]}</h3>
<div class="controls">
<div class="field"><label for="ab">{ui[l_base]}</label><input type="date" id="ab"></div>
<div class="field"><label for="an">{ui[l_n]}</label><input type="number" id="an" value="100" step="1" min="-36500" max="36500"></div>
<div class="field"><label>{ui[r_result]}</label><input type="text" id="ar" readonly></div>
</div>
</div>
<p class="note">{ui[note]}</p>
"""

DAYS_JS = r"""
var $=function(i){return document.getElementById(i);};
function pad(n){return (n<10?'0':'')+n;}
function iso(d){return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());}
function parse(v){var p=(v||'').split('-');if(p.length!==3)return null;
  var d=new Date(+p[0],+p[1]-1,+p[2]);return isNaN(d.getTime())?null:d;}
function utc(d){return Date.UTC(d.getFullYear(),d.getMonth(),d.getDate());}
function diff(a,b){return Math.round((utc(b)-utc(a))/86400000);}
function addMonths(a,n){var y=a.getFullYear(),m=a.getMonth()+n,last=new Date(y,m+1,0).getDate();
  return new Date(y,m,Math.min(a.getDate(),last));}
function ymd(a,b){var n=(b.getFullYear()-a.getFullYear())*12+b.getMonth()-a.getMonth();
  if(addMonths(a,n)>b)n--;return [Math.floor(n/12),n%12,diff(addMonths(a,n),b)];}
function work(a,b){var n=0,d=new Date(a.getTime());var guard=0;
  while(d<b&&guard<40000){var w=d.getDay();if(w!==0&&w!==6)n++;d.setDate(d.getDate()+1);guard++;}return n;}
function fmt(t,o){return t.replace(/\{(\w+)\}/g,function(_,k){return o[k];});}
function nice(d){try{return d.toLocaleDateString(L.locale,{weekday:'long',year:'numeric',month:'long',day:'numeric'});}
  catch(e){return iso(d);}}
function between(){var a=parse($('d1').value),b=parse($('d2').value);
  if(!a||!b){['rd','rw','ry','rk'].forEach(function(i){$(i).textContent='—';});return;}
  var sign=1;if(b<a){var t=a;a=b;b=t;sign=-1;}
  var incl=$('incl').value==='1'?1:0,end=new Date(b.getTime());end.setDate(end.getDate()+incl);
  var n=diff(a,end),p=ymd(a,end);
  $('rd').textContent=(sign<0?'−':'')+n.toLocaleString(L.locale);
  $('rw').textContent=fmt(L.w_fmt,{w:Math.floor(n/7),d:n%7});
  $('ry').textContent=fmt(L.ymd_fmt,{y:p[0],m:p[1],d:p[2]});
  $('rk').textContent=work(a,end).toLocaleString(L.locale);
  window.__days={days:sign*n,weeks:Math.floor(n/7),ymd:p,workdays:work(a,end)};}
function countdown(){var d=parse($('ed').value),name=$('ev').value.trim()||L.ev_default;
  if(!d){$('cd').textContent='—';return;}
  var n=diff(new Date(),d),out;
  if(n>0)out=fmt(L.until,{n:n.toLocaleString(L.locale),e:name});
  else if(n<0)out=fmt(L.since,{n:(-n).toLocaleString(L.locale),e:name});
  else out=fmt(L.today_is,{e:name});
  $('cd').textContent=out;window.__countdown=n;}
function add(){var b=parse($('ab').value),n=parseInt($('an').value,10);
  if(!b||isNaN(n)){$('ar').value='';return;}
  var r=new Date(b.getTime());r.setDate(r.getDate()+n);$('ar').value=nice(r);window.__added=iso(r);}
(function init(){var t=new Date(),e=new Date();e.setDate(e.getDate()+100);
  $('d1').value=iso(t);$('d2').value=iso(e);$('ed').value=iso(e);$('ab').value=iso(t);
  $('ev').placeholder=L.ev_default;})();
['d1','d2','incl'].forEach(function(i){$(i).addEventListener('input',between);$(i).addEventListener('change',between);});
['ev','ed'].forEach(function(i){$(i).addEventListener('input',countdown);$(i).addEventListener('change',countdown);});
['ab','an'].forEach(function(i){$(i).addEventListener('input',add);$(i).addEventListener('change',add);});
$('today').addEventListener('click',function(){$('ed').value=iso(new Date());countdown();});
between();countdown();add();
"""

_COUNTDAYS_APP = {"app_key": "countdaysnow", "app_id": "6807079789",
                  "app_name": "CountDaysNow", "category": "UtilitiesApplication"}


def spec_days_between_dates():
    spec = dict(_COUNTDAYS_APP)
    spec.update({
        "slug": "days-between-dates-calculator",
        "body": DAYS_BODY,
        "script": DAYS_JS,
        "extra_css": DAYS_CSS,
        "i18n": {
            "en": {
                "q": [("days between dates calculator", "D4"), ("days between dates", "D3"), ("how many days until", "D3")],
                "title": "Days Between Dates Calculator — Countdown & Add Days, Free",
                "description": "Count the days between two dates, with weeks, years-months-days and Monday–Friday days, run a countdown to any event, or add and subtract days from a date. Runs in your browser.",
                "h1": "Days between dates calculator",
                "eyebrow": "Days · countdown · add days · free",
                "lead": "Pick two dates for the exact gap, name an event for a live countdown, or jump forward or back a number of days — three calculators on one page.",
                "badges": ["Exact day count", "Weeks & months", "Countdown", "Add or subtract days"],
                "features": ["Days between two dates, with an option to count the end date", "The same gap in weeks and in years, months and days", "Monday–Friday day count for the same range", "Event countdown and date plus or minus N days"],
                "how": [
                    "Dates are compared at local midnight in UTC terms, so daylight-saving changes never add or lose a day.",
                    "“Count the end date” adds one day, the way a hotel stay or a course that includes both dates is counted.",
                    "Months are counted one calendar month at a time; when a month is shorter the step lands on its last day, so 31 January to 1 March is 1 month and 1 day in a non-leap year.",
                    "The Monday–Friday figure simply skips Saturdays and Sundays; it does not know your public holidays.",
                ],
                "never": [
                    "It does not know public holidays or school calendars, so treat the Monday–Friday count as a ceiling.",
                    "It does not send reminders or save your events — close the tab and they are gone.",
                    "No account, no tracking, nothing uploaded.",
                ],
                "faq": [
                    ("Does it count the start date?", "The plain count is the number of midnights between the two dates. Choose “Count the end date: yes” when both the first and the last day should be counted, for example for a 1–7 March holiday."),
                    ("Why is the Monday–Friday number different from my working days?", "Because it does not remove public holidays or your own days off. Subtract those yourself."),
                    ("Can I count backwards?", "Yes. If the end date is earlier than the start date the result is shown with a minus sign, and the add-days box accepts negative numbers."),
                ],
                "app_heading": "Want countdowns on your Home Screen?",
                "card": "Exact days between two dates, an event countdown and add-or-subtract days, in one page.",
                "ui": {
                    "h2": "Days between two dates", "intro": "Both dates are your local calendar dates.",
                    "l_start": "Start date", "l_end": "End date", "l_incl": "Count the end date",
                    "no": "No", "yes": "Yes",
                    "r_days": "Days", "r_weeks": "Weeks", "r_ymd": "Years · months · days", "r_work": "Mon–Fri days",
                    "h_count": "Countdown to an event", "l_event": "Event name", "l_edate": "Event date", "b_today": "Today",
                    "h_add": "Add or subtract days", "l_base": "From", "l_n": "Days (+ or −)", "r_result": "Result",
                    "w_fmt": "{w} weeks {d} days", "ymd_fmt": "{y} y {m} m {d} d",
                    "until": "{n} days until {e}", "since": "{n} days since {e}", "today_is": "{e} is today",
                    "ev_default": "the big day", "locale": "en-US",
                    "note": "Holidays are not removed from the Monday–Friday count. Nothing you type is stored.",
                },
            },
            "ja": {
                "q": [("日数計算", "D3"), ("日付計算", "D3"), ("カウントダウン", "D4")],
                "title": "日数計算ツール — 日付の間の日数・カウントダウン・○日後を無料で",
                "description": "2つの日付の間の日数を、週・年月日・平日（月〜金）の日数とあわせて計算。イベントまでのカウントダウンや「○日後・○日前」もブラウザだけで計算できます。",
                "h1": "日数計算・日付計算ツール",
                "eyebrow": "日数 · カウントダウン · ○日後 · 無料",
                "lead": "2つの日付を選べば正確な日数、イベント名を入れればカウントダウン、日数を入れれば○日後の日付。3つの計算を1ページで。",
                "badges": ["正確な日数", "週・年月日", "カウントダウン", "○日後・○日前"],
                "features": ["2つの日付の間の日数（終了日を含めるか選択可）", "同じ期間を週と年・月・日で表示", "同じ期間の平日（月〜金）の日数", "イベントまでのカウントダウンと○日後・○日前の日付"],
                "how": [
                    "日付はUTC基準の0時同士で比べるので、夏時間の切り替えで1日ずれることはありません。",
                    "「終了日を含める」を選ぶと1日足します。開始日と最終日の両方を数える旅行や講座の日数はこちらです。",
                    "月は暦どおり1か月ずつ数え、短い月では月末日に合わせます。そのため平年の1月31日〜3月1日は「1か月1日」になります。",
                    "平日の日数は土日を除くだけで、祝日は考慮しません。",
                ],
                "never": [
                    "祝日や学校の行事予定は知りません。平日の日数は上限の目安として使ってください。",
                    "通知を送ったりイベントを保存したりしません。タブを閉じると消えます。",
                    "アカウント不要、トラッキングなし、アップロードなし。",
                ],
                "faq": [
                    ("開始日は数えますか？", "基本の日数は2つの日付の間の「夜の数」です。3月1日〜7日の旅行のように初日と最終日の両方を数えたいときは「終了日を含める：はい」を選んでください。"),
                    ("平日の日数が実際の勤務日数と違うのはなぜ？", "祝日や個人の休みを差し引いていないためです。その分はご自身で引いてください。"),
                    ("過去にさかのぼって数えられますか？", "はい。終了日が開始日より前ならマイナス付きで表示し、○日後の欄にはマイナスの数も入力できます。"),
                ],
                "app_heading": "ホーム画面でもカウントダウンしたい方へ",
                "card": "2つの日付の間の日数、イベントまでのカウントダウン、○日後の日付を1ページで計算。",
                "ui": {
                    "h2": "2つの日付の間の日数", "intro": "どちらもお使いの地域の日付です。",
                    "l_start": "開始日", "l_end": "終了日", "l_incl": "終了日を含める",
                    "no": "いいえ", "yes": "はい",
                    "r_days": "日数", "r_weeks": "週", "r_ymd": "年・月・日", "r_work": "平日（月〜金）",
                    "h_count": "イベントまでのカウントダウン", "l_event": "イベント名", "l_edate": "日付", "b_today": "今日",
                    "h_add": "○日後・○日前", "l_base": "基準日", "l_n": "日数（＋/−）", "r_result": "結果",
                    "w_fmt": "{w}週{d}日", "ymd_fmt": "{y}年{m}か月{d}日",
                    "until": "{e}まであと{n}日", "since": "{e}から{n}日", "today_is": "今日は{e}",
                    "ev_default": "その日", "locale": "ja-JP",
                    "note": "平日の日数から祝日は除いていません。入力内容は保存されません。",
                },
            },
            "ko": {
                "q": [("디데이 계산기", "D2"), ("디데이", "D2")],
                "title": "디데이 계산기 — 날짜 사이 일수·D-day·며칠 후 계산 (무료)",
                "description": "두 날짜 사이의 일수를 주·년월일·평일(월~금) 일수와 함께 계산하고, 행사까지 D-day를 세거나 며칠 후·며칠 전 날짜를 브라우저에서 바로 구합니다.",
                "h1": "디데이 · 날짜 계산기",
                "eyebrow": "일수 · D-day · 며칠 후 · 무료",
                "lead": "두 날짜를 고르면 정확한 일수, 행사 이름을 넣으면 D-day, 일수를 넣으면 며칠 후 날짜. 계산기 세 개를 한 페이지에.",
                "badges": ["정확한 일수", "주·년월일", "D-day", "며칠 후·며칠 전"],
                "features": ["두 날짜 사이 일수(종료일 포함 여부 선택)", "같은 기간을 주와 년·월·일로 표시", "같은 기간의 평일(월~금) 일수", "행사 D-day와 며칠 후·며칠 전 날짜"],
                "how": [
                    "날짜는 UTC 기준 자정끼리 비교하므로 서머타임 때문에 하루가 늘거나 줄지 않습니다.",
                    "‘종료일 포함’을 선택하면 하루를 더합니다. 첫날과 마지막 날을 모두 세는 여행·강좌 일수에 쓰세요.",
                    "월은 달력대로 한 달씩 세고 짧은 달에서는 말일에 맞춥니다. 그래서 평년 1월 31일~3월 1일은 ‘1개월 1일’입니다.",
                    "평일 일수는 토·일만 빼며 공휴일은 고려하지 않습니다.",
                ],
                "never": [
                    "공휴일이나 학사 일정은 모릅니다. 평일 일수는 최대치로 보세요.",
                    "알림을 보내거나 행사를 저장하지 않습니다. 탭을 닫으면 사라집니다.",
                    "계정 없음, 추적 없음, 업로드 없음.",
                ],
                "faq": [
                    ("시작일도 세나요?", "기본 일수는 두 날짜 사이의 ‘밤’의 수입니다. 3월 1일~7일 여행처럼 첫날과 마지막 날을 모두 세려면 ‘종료일 포함: 예’를 고르세요."),
                    ("평일 일수가 실제 근무일과 다른 이유는?", "공휴일과 개인 휴무를 빼지 않았기 때문입니다. 그만큼 직접 빼 주세요."),
                    ("거꾸로도 셀 수 있나요?", "네. 종료일이 시작일보다 이르면 마이너스로 표시하고, 며칠 후 칸에는 음수도 입력할 수 있습니다."),
                ],
                "app_heading": "홈 화면에서도 D-day를 보고 싶다면",
                "card": "두 날짜 사이 일수, 행사 D-day, 며칠 후 날짜를 한 페이지에서 계산.",
                "ui": {
                    "h2": "두 날짜 사이의 일수", "intro": "두 날짜 모두 현지 달력 기준입니다.",
                    "l_start": "시작일", "l_end": "종료일", "l_incl": "종료일 포함",
                    "no": "아니요", "yes": "예",
                    "r_days": "일수", "r_weeks": "주", "r_ymd": "년·월·일", "r_work": "평일(월~금)",
                    "h_count": "행사까지 D-day", "l_event": "행사 이름", "l_edate": "날짜", "b_today": "오늘",
                    "h_add": "며칠 후 · 며칠 전", "l_base": "기준일", "l_n": "일수(+/−)", "r_result": "결과",
                    "w_fmt": "{w}주 {d}일", "ymd_fmt": "{y}년 {m}개월 {d}일",
                    "until": "{e}까지 D-{n}", "since": "{e} 이후 {n}일", "today_is": "오늘이 {e}",
                    "ev_default": "그날", "locale": "ko-KR",
                    "note": "평일 일수에서 공휴일은 빼지 않습니다. 입력한 내용은 저장되지 않습니다.",
                },
            },
            "de-DE": {
                "q": [("tage zwischen zwei daten", "D3"), ("countdown", "D4")],
                "title": "Tage zwischen zwei Daten berechnen — Countdown & Tage addieren, kostenlos",
                "description": "Tage zwischen zwei Daten zählen, mit Wochen, Jahren-Monaten-Tagen und Montag-bis-Freitag-Tagen, einen Countdown zu jedem Termin starten oder Tage zu einem Datum addieren. Läuft im Browser.",
                "h1": "Tage zwischen zwei Daten",
                "eyebrow": "Tage · Countdown · Tage addieren · kostenlos",
                "lead": "Zwei Daten wählen für den genauen Abstand, einen Termin benennen für den Countdown oder eine Anzahl Tage vor- oder zurückspringen — drei Rechner auf einer Seite.",
                "badges": ["Genaue Tageszahl", "Wochen & Monate", "Countdown", "Tage addieren/abziehen"],
                "features": ["Tage zwischen zwei Daten, Enddatum wahlweise mitgezählt", "Derselbe Abstand in Wochen sowie Jahren, Monaten und Tagen", "Anzahl Montag–Freitag im selben Zeitraum", "Countdown zu einem Termin und Datum plus/minus N Tage"],
                "how": [
                    "Verglichen wird Mitternacht mit Mitternacht in UTC, daher kostet oder bringt die Zeitumstellung keinen Tag.",
                    "„Enddatum mitzählen“ addiert einen Tag — so zählt man Urlaube oder Kurse, bei denen erster und letzter Tag dazugehören.",
                    "Monate werden Kalendermonat für Kalendermonat gezählt; ist ein Monat kürzer, landet der Schritt auf seinem letzten Tag — 31. Januar bis 1. März ist im Nicht-Schaltjahr 1 Monat und 1 Tag.",
                    "Die Montag-bis-Freitag-Zahl lässt nur Samstage und Sonntage weg; Feiertage kennt sie nicht.",
                ],
                "never": [
                    "Es kennt keine Feiertage oder Schulferien — die Werktagszahl ist eine Obergrenze.",
                    "Es verschickt keine Erinnerungen und speichert keine Termine; mit dem Tab sind sie weg.",
                    "Kein Konto, kein Tracking, kein Upload.",
                ],
                "faq": [
                    ("Wird der Starttag mitgezählt?", "Die einfache Zahl ist die Anzahl der Mitternächte zwischen beiden Daten. Wählen Sie „Enddatum mitzählen: Ja“, wenn erster und letzter Tag zählen sollen, etwa bei einem Urlaub vom 1. bis 7. März."),
                    ("Warum weicht die Montag–Freitag-Zahl von meinen Arbeitstagen ab?", "Weil Feiertage und eigene freie Tage nicht abgezogen werden. Ziehen Sie diese selbst ab."),
                    ("Kann ich rückwärts rechnen?", "Ja. Liegt das Enddatum vor dem Startdatum, erscheint das Ergebnis mit Minuszeichen, und das Feld für Tage akzeptiert negative Zahlen."),
                ],
                "app_heading": "Countdowns auch auf dem Home-Bildschirm?",
                "card": "Genaue Tage zwischen zwei Daten, Countdown zu einem Termin und Tage addieren — auf einer Seite.",
                "ui": {
                    "h2": "Tage zwischen zwei Daten", "intro": "Beide Daten sind Ihre lokalen Kalenderdaten.",
                    "l_start": "Startdatum", "l_end": "Enddatum", "l_incl": "Enddatum mitzählen",
                    "no": "Nein", "yes": "Ja",
                    "r_days": "Tage", "r_weeks": "Wochen", "r_ymd": "Jahre · Monate · Tage", "r_work": "Mo–Fr-Tage",
                    "h_count": "Countdown zu einem Termin", "l_event": "Termin", "l_edate": "Datum", "b_today": "Heute",
                    "h_add": "Tage addieren oder abziehen", "l_base": "Ab", "l_n": "Tage (+ oder −)", "r_result": "Ergebnis",
                    "w_fmt": "{w} Wochen {d} Tage", "ymd_fmt": "{y} J. {m} M. {d} T.",
                    "until": "Noch {n} Tage bis {e}", "since": "{n} Tage seit {e}", "today_is": "{e} ist heute",
                    "ev_default": "zum großen Tag", "locale": "de-DE",
                    "note": "Feiertage werden bei Mo–Fr nicht abgezogen. Eingaben werden nicht gespeichert.",
                },
            },
            "zh-Hant": {
                "q": [("天數計算", "D3"), ("日期計算", "D3"), ("倒數計時", "D3")],
                "title": "天數計算機 — 兩個日期相差幾天、倒數幾天、幾天後是幾號（免費）",
                "description": "計算兩個日期相差幾天，同時顯示週數、年月日與週一到週五的天數；也能倒數到任何日子，或算出幾天後、幾天前是哪一天。全部在瀏覽器裡完成。",
                "h1": "天數計算機・日期計算",
                "eyebrow": "相差天數 · 倒數 · 幾天後 · 免費",
                "lead": "選兩個日期看相差幾天，輸入活動名稱就倒數，輸入天數就算出幾天後——三個計算器放在同一頁。",
                "badges": ["精確天數", "週數與年月日", "倒數", "幾天後／幾天前"],
                "features": ["兩個日期相差的天數（可選擇是否含結束日）", "同一段期間換算成週數與年、月、日", "同一段期間的週一到週五天數", "活動倒數，以及某日加減 N 天"],
                "how": [
                    "日期以 UTC 的午夜互相比較，所以日光節約時間切換不會多算或少算一天。",
                    "選「含結束日」會多加一天，適合把第一天和最後一天都算進去的旅行或課程。",
                    "月份按日曆一個月一個月算，遇到較短的月份就落在月底，所以平年 1 月 31 日到 3 月 1 日是「1 個月 1 天」。",
                    "週一到週五的天數只扣掉週六、週日，不知道國定假日。",
                ],
                "never": [
                    "不知道國定假日或學校行事曆，週一到週五的天數請當作上限。",
                    "不會發提醒，也不會儲存活動；關掉分頁就沒了。",
                    "不用帳號、不追蹤、不上傳。",
                ],
                "faq": [
                    ("開始那天有算進去嗎？", "基本天數是兩個日期之間經過幾個午夜。如果像 3 月 1 日到 7 日的旅行，第一天和最後一天都要算，請選「含結束日：是」。"),
                    ("週一到週五的天數為什麼和我的上班天數不同？", "因為沒有扣掉國定假日和你自己的休假，請自行再扣。"),
                    ("可以往回算嗎？", "可以。結束日早於開始日時會以負號顯示，「幾天後」也可以輸入負數。"),
                ],
                "app_heading": "想在主畫面也看到倒數？",
                "card": "兩個日期相差幾天、活動倒數、幾天後是幾號，一頁算完。",
                "ui": {
                    "h2": "兩個日期相差幾天", "intro": "兩個日期都以你所在地的日曆為準。",
                    "l_start": "開始日期", "l_end": "結束日期", "l_incl": "含結束日",
                    "no": "否", "yes": "是",
                    "r_days": "天數", "r_weeks": "週數", "r_ymd": "年・月・日", "r_work": "週一至週五天數",
                    "h_count": "活動倒數", "l_event": "活動名稱", "l_edate": "日期", "b_today": "今天",
                    "h_add": "幾天後・幾天前", "l_base": "從", "l_n": "天數（＋／−）", "r_result": "結果",
                    "w_fmt": "{w} 週 {d} 天", "ymd_fmt": "{y} 年 {m} 個月 {d} 天",
                    "until": "距離{e}還有 {n} 天", "since": "{e}已過 {n} 天", "today_is": "今天就是{e}",
                    "ev_default": "那一天", "locale": "zh-TW",
                    "note": "週一至週五天數沒有扣除國定假日。輸入的內容不會被儲存。",
                },
            },
        },
    })
    return spec


# ------------------------------------------------ Wi-Fi QR code (QR Code Halo)

# Byte-mode QR encoder, ECC level M, versions 1–40.  Verified module-for-module
# against the qrcodegen reference implementation (same version and mask).
QR_JS = r"""
var QR=(function(){
var ECW=[-1,10,16,26,18,24,16,18,22,22,26,30,22,22,24,24,28,28,26,26,26,26,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28];
var NB=[-1,1,1,1,2,2,4,4,4,5,5,5,8,9,9,10,10,11,13,14,16,17,17,18,20,21,23,25,26,28,29,31,33,35,37,38,40,43,45,47,49];
function rawModules(v){var r=(16*v+128)*v+64;if(v>=2){var a=Math.floor(v/7)+2;r-=(25*a-10)*a-55;if(v>=7)r-=36;}return r;}
function dataCw(v){return Math.floor(rawModules(v)/8)-ECW[v]*NB[v];}
function gmul(x,y){var z=0;for(var i=7;i>=0;i--){z=(z<<1)^((z>>>7)*0x11D);z^=((y>>>i)&1)*x;}return z&255;}
function rsDiv(deg){var r=[];for(var i=0;i<deg-1;i++)r.push(0);r.push(1);var root=1;
  for(i=0;i<deg;i++){for(var j=0;j<r.length;j++){r[j]=gmul(r[j],root);if(j+1<r.length)r[j]^=r[j+1];}root=gmul(root,2);}return r;}
function rsRem(data,div){var r=div.map(function(){return 0;});
  data.forEach(function(b){var f=b^r.shift();r.push(0);div.forEach(function(c,i){r[i]^=gmul(c,f);});});return r;}
function utf8(s){var out=[],e=unescape(encodeURIComponent(s));for(var i=0;i<e.length;i++)out.push(e.charCodeAt(i));return out;}
function encode(text){
  var bytes=utf8(text),v,cap;
  for(v=1;v<=40;v++){cap=dataCw(v)*8;if(4+(v<10?8:16)+bytes.length*8<=cap)break;}
  if(v>40)throw new Error('too long');
  var bits=[];function put(val,len){for(var i=len-1;i>=0;i--)bits.push((val>>>i)&1);}
  put(4,4);put(bytes.length,v<10?8:16);bytes.forEach(function(b){put(b,8);});
  put(0,Math.min(4,cap-bits.length));put(0,(8-bits.length%8)%8);
  for(var pad=0xEC;bits.length<cap;pad^=0xEC^0x11)put(pad,8);
  var data=[];for(var i=0;i<bits.length;i+=8){var b=0;for(var k=0;k<8;k++)b=(b<<1)|bits[i+k];data.push(b);}
  var nb=NB[v],ec=ECW[v],raw=Math.floor(rawModules(v)/8),nshort=nb-raw%nb,shortLen=Math.floor(raw/nb);
  var div=rsDiv(ec),blocks=[],off=0;
  for(i=0;i<nb;i++){var len=shortLen-ec+(i<nshort?0:1);var dat=data.slice(off,off+len);off+=len;
    var e=rsRem(dat,div);if(i<nshort)dat.push(0);blocks.push(dat.concat(e));}
  var all=[];for(i=0;i<blocks[0].length;i++)blocks.forEach(function(bl,j){if(i!==shortLen-ec||j>=nshort)all.push(bl[i]);});
  var size=v*4+17,M=[],F=[];for(i=0;i<size;i++){M.push(new Array(size).fill(false));F.push(new Array(size).fill(false));}
  function set(x,y,d){M[y][x]=d;F[y][x]=true;}
  for(i=0;i<size;i++){set(6,i,i%2===0);set(i,6,i%2===0);}
  function finder(x,y){for(var dy=-4;dy<=4;dy++)for(var dx=-4;dx<=4;dx++){var d=Math.max(Math.abs(dx),Math.abs(dy)),xx=x+dx,yy=y+dy;
    if(xx>=0&&xx<size&&yy>=0&&yy<size)set(xx,yy,d!==2&&d!==4);}}
  finder(3,3);finder(size-4,3);finder(3,size-4);
  var pos=[];if(v>1){var n=Math.floor(v/7)+2,step=(v===32)?26:Math.ceil((v*4+4)/(n*2-2))*2;
    pos=[6];for(var p=size-7;pos.length<n;p-=step)pos.splice(1,0,p);}
  pos.forEach(function(a,ai){pos.forEach(function(b,bi){if((ai===0&&bi===0)||(ai===0&&bi===pos.length-1)||(ai===pos.length-1&&bi===0))return;
    for(var dy=-2;dy<=2;dy++)for(var dx=-2;dx<=2;dx++)set(a+dx,b+dy,Math.max(Math.abs(dx),Math.abs(dy))!==1);});});
  function format(mask){var d=mask,r=d;for(var i=0;i<10;i++)r=(r<<1)^((r>>>9)*0x537);var bits=((d<<10)|r)^0x5412;
    for(i=0;i<=5;i++)set(8,i,((bits>>>i)&1)!==0);set(8,7,((bits>>>6)&1)!==0);set(8,8,((bits>>>7)&1)!==0);set(7,8,((bits>>>8)&1)!==0);
    for(i=9;i<15;i++)set(14-i,8,((bits>>>i)&1)!==0);
    for(i=0;i<8;i++)set(size-1-i,8,((bits>>>i)&1)!==0);for(i=8;i<15;i++)set(8,size-15+i,((bits>>>i)&1)!==0);set(8,size-8,true);}
  format(0);
  if(v>=7){var r=v;for(i=0;i<12;i++)r=(r<<1)^((r>>>11)*0x1F25);var vb=(v<<12)|r;
    for(i=0;i<18;i++){var bt=((vb>>>i)&1)!==0,a2=size-11+i%3,b2=Math.floor(i/3);set(a2,b2,bt);set(b2,a2,bt);}}
  var bi2=0;for(var right=size-1;right>=1;right-=2){if(right===6)right=5;
    for(var vert=0;vert<size;vert++)for(var j2=0;j2<2;j2++){var x=right-j2,up=((right+1)&2)===0,y=up?size-1-vert:vert;
      if(!F[y][x]&&bi2<all.length*8){M[y][x]=((all[bi2>>>3]>>>(7-(bi2&7)))&1)!==0;bi2++;}}}
  function maskFn(m,x,y){switch(m){case 0:return(x+y)%2===0;case 1:return y%2===0;case 2:return x%3===0;case 3:return(x+y)%3===0;
    case 4:return(Math.floor(x/3)+Math.floor(y/2))%2===0;case 5:return x*y%2+x*y%3===0;case 6:return(x*y%2+x*y%3)%2===0;default:return((x+y)%2+x*y%3)%2===0;}}
  function applyMask(m){for(var y=0;y<size;y++)for(var x=0;x<size;x++)if(!F[y][x]&&maskFn(m,x,y))M[y][x]=!M[y][x];}
  function penalty(){var s=0,x,y,run,c;
    for(y=0;y<size;y++){run=1;for(x=1;x<=size;x++){if(x<size&&M[y][x]===M[y][x-1])run++;else{if(run>=5)s+=run-2;run=1;}}}
    for(x=0;x<size;x++){run=1;for(y=1;y<=size;y++){if(y<size&&M[y][x]===M[y-1][x])run++;else{if(run>=5)s+=run-2;run=1;}}}
    for(y=0;y<size-1;y++)for(x=0;x<size-1;x++){c=M[y][x];if(c===M[y][x+1]&&c===M[y+1][x]&&c===M[y+1][x+1])s+=3;}
    var P1=[1,0,1,1,1,0,1,0,0,0,0],P2=[0,0,0,0,1,0,1,1,1,0,1];
    function scan(get){var t=0;for(var a=0;a<size;a++)for(var b=0;b+11<=size;b++){var m1=true,m2=true;
      for(var k=0;k<11;k++){var val=get(a,b+k)?1:0;if(val!==P1[k])m1=false;if(val!==P2[k])m2=false;}if(m1)t+=40;if(m2)t+=40;}return t;}
    s+=scan(function(a,b){return M[a][b];});s+=scan(function(a,b){return M[b][a];});
    var dark=0;for(y=0;y<size;y++)for(x=0;x<size;x++)if(M[y][x])dark++;
    s+=Math.floor(Math.abs(dark*20-size*size*10)/(size*size))*10;return s;}
  var best=0,bestP=Infinity;
  for(var m=0;m<8;m++){applyMask(m);format(m);var pp=penalty();if(pp<bestP){bestP=pp;best=m;}applyMask(m);}
  applyMask(best);format(best);
  return {size:size,version:v,mask:best,get:function(x,y){return M[y][x];}};}
return {encode:encode};})();
"""

WIFI_CSS = """
.qr-out{display:grid;grid-template-columns:minmax(0,300px) 1fr;gap:22px;align-items:center;margin-top:20px}
.qr-out canvas{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:16px;image-rendering:pixelated}
.qr-card{border:2px dashed #dcc9a4;border-radius:18px;padding:16px 18px;background:#fff}
.qr-card p{margin:4px 0;word-break:break-all}.qr-card strong{color:var(--brand)}
.pw{display:flex;gap:8px}.pw input{flex:1}
@media (max-width:720px){.controls{grid-template-columns:1fr}.qr-out{grid-template-columns:1fr}}
"""

WIFI_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="ssid">{ui[l_ssid]}</label><input type="text" id="ssid" maxlength="32" autocomplete="off" spellcheck="false"></div>
<div class="field"><label for="pass">{ui[l_pass]}</label><div class="pw"><input type="password" id="pass" maxlength="63" autocomplete="off" spellcheck="false"><button class="button ghost" id="show" type="button">{ui[b_show]}</button></div></div>
<div class="field"><label for="sec">{ui[l_sec]}</label><select id="sec">
<option value="WPA" selected>WPA / WPA2 / WPA3</option><option value="WEP">WEP</option><option value="nopass">{ui[o_open]}</option></select></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="hid">{ui[l_hidden]}</label><select id="hid"><option value="0">{ui[no]}</option><option value="1">{ui[yes]}</option></select></div>
<div class="field" style="align-self:end"><a class="button" id="dl" download="wifi-qr.png">{ui[b_png]}</a></div>
<div class="field" style="align-self:end"><button class="button ghost" id="print" type="button">{ui[b_print]}</button></div>
</div>
<div class="qr-out">
<canvas id="qr" width="330" height="330" aria-label="QR"></canvas>
<div class="qr-card"><p><strong>{ui[c_net]}</strong> <span id="cs">—</span></p><p><strong>{ui[c_pass]}</strong> <span id="cp">—</span></p><p class="small">{ui[c_scan]}</p></div>
</div>
<p class="note" id="msg">{ui[note]}</p>
"""

WIFI_JS = QR_JS + r"""
var $=function(i){return document.getElementById(i);};
function esc(s){return s.replace(/([\\;,:"])/g,'\\$1');}
function payload(){var sec=$('sec').value,s=$('ssid').value,p=$('pass').value;
  var out='WIFI:T:'+sec+';S:'+esc(s)+';';
  if(sec!=='nopass')out+='P:'+esc(p)+';';
  if($('hid').value==='1')out+='H:true;';
  return out+';';}
function draw(){var c=$('qr'),x=c.getContext('2d'),s=$('ssid').value,p=$('pass').value,sec=$('sec').value;
  $('cs').textContent=s||'—';$('cp').textContent=sec==='nopass'?L.c_none:(p||'—');
  x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);
  if(!s){$('msg').textContent=L.need_ssid;$('dl').removeAttribute('href');window.__wifi=null;return;}
  if(sec==='WPA'&&p&&p.length<8){$('msg').textContent=L.short_pw;}
  else{$('msg').textContent=L.note;}
  var data=payload(),q=QR.encode(data),quiet=4,n=q.size+quiet*2,scale=Math.floor(330/n);
  c.width=c.height=n*scale;x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.fillStyle='#111';
  for(var yy=0;yy<q.size;yy++)for(var xx=0;xx<q.size;xx++)if(q.get(xx,yy))x.fillRect((xx+quiet)*scale,(yy+quiet)*scale,scale,scale);
  $('dl').href=c.toDataURL('image/png');
  window.__wifi={payload:data,version:q.version,size:q.size};}
['ssid','pass','sec','hid'].forEach(function(i){$(i).addEventListener('input',draw);$(i).addEventListener('change',draw);});
$('show').addEventListener('click',function(){var t=$('pass').type==='password';$('pass').type=t?'text':'password';
  $('show').textContent=t?L.b_hide:L.b_show;});
$('print').addEventListener('click',function(){window.print();});
draw();
"""

_QR_APP = {"app_key": "qrcodehalo", "app_id": "6806779853",
           "app_name": "QR Code Halo", "category": "UtilitiesApplication"}


def spec_wifi_qr():
    spec = dict(_QR_APP)
    spec.update({
        "slug": "wifi-qr-code-generator",
        "body": WIFI_BODY,
        "script": WIFI_JS,
        "extra_css": WIFI_CSS,
        "print_css": ".top,.hero,.app-card,.footer,.faq,.grid,.controls,.note,.intro,#tool>h2{display:none!important}body{background:#fff}.tool{box-shadow:none;border:0;padding:0}",
        "i18n": {
            "en": {
                "q": [("wifi qr code generator", "D3"), ("wifi qr code", "D2")],
                "title": "Wi-Fi QR Code Generator — Free, Made in Your Browser",
                "description": "Turn your Wi-Fi name and password into a QR code guests can scan to join. WPA/WPA2/WPA3, WEP, open and hidden networks; download a PNG or print a card. Nothing is uploaded.",
                "h1": "Wi-Fi QR code generator",
                "eyebrow": "Scan to join · PNG or print · free",
                "lead": "Type the network name and password once; guests point their phone camera at the code and join without spelling out a long password.",
                "badges": ["WPA / WEP / open", "Hidden networks", "PNG download", "Printable card"],
                "features": ["Standard WIFI: QR payload with special characters escaped", "WPA/WPA2/WPA3, WEP and open networks, plus hidden SSIDs", "PNG download with a proper quiet zone", "Printable card that shows the network name and password"],
                "how": [
                    "The page builds the same WIFI:T:…;S:…;P:…;; text that phone cameras recognise, escaping backslashes, semicolons, commas, colons and quotes in the name and password.",
                    "That text is encoded as a QR code (error-correction level M) by a small encoder that runs on this page — no image is fetched from a server.",
                    "WPA covers WPA2 and WPA3 personal networks; enterprise logins with a user name are not supported by the format.",
                    "Download keeps a four-module white border so the code scans reliably once printed.",
                ],
                "never": [
                    "It never sends your password anywhere — the code is drawn on your device.",
                    "It cannot change your router’s settings or check that the password is right; test the code with your own phone before printing.",
                    "No account, no tracking, no watermark.",
                ],
                "faq": [
                    ("Which phones can scan it?", "Recent iPhone and Android camera apps recognise Wi-Fi QR codes and offer to join the network. Older phones may need a QR reader app."),
                    ("Is it safe to put my password in a QR code?", "Anyone who can see the code can read the password, exactly as if it were written on the card. Use it for a guest network where possible."),
                    ("What if my network is hidden?", "Choose “Hidden network: yes”. The code then tells the phone to look for a network that does not broadcast its name."),
                ],
                "app_heading": "Scanning and making codes on iPhone?",
                "card": "Make a scan-to-join Wi-Fi QR code from your network name and password, without uploading either.",
                "ui": {
                    "h2": "Your network", "intro": "Exactly as it appears in your router or phone settings — names are case-sensitive.",
                    "l_ssid": "Network name (SSID)", "l_pass": "Password", "b_show": "Show", "b_hide": "Hide",
                    "l_sec": "Security", "o_open": "None (open)", "l_hidden": "Hidden network", "no": "No", "yes": "Yes",
                    "b_png": "Download PNG", "b_print": "Print card",
                    "c_net": "Wi-Fi:", "c_pass": "Password:", "c_none": "(no password)", "c_scan": "Point your phone camera at the code to join.",
                    "need_ssid": "Type the network name to make a code.",
                    "short_pw": "WPA passwords are at least 8 characters — check it before printing.",
                    "note": "Test the code with your own phone before you print or share it.",
                },
            },
            "ja": {
                "q": [("wifi qrコード 作成", "D2")],
                "title": "Wi-Fi QRコード作成 — ブラウザだけで無料作成",
                "description": "Wi-Fiのネットワーク名とパスワードから、読み取るだけで接続できるQRコードを作成。WPA/WPA2/WPA3・WEP・パスワードなし・非公開ネットワーク対応。PNG保存や印刷も。アップロードなし。",
                "h1": "Wi-Fi QRコード作成",
                "eyebrow": "読み取って接続 · PNG・印刷 · 無料",
                "lead": "ネットワーク名とパスワードを一度入れるだけ。来客はカメラをかざすだけで、長いパスワードを読み上げずに接続できます。",
                "badges": ["WPA・WEP・なし", "非公開ネットワーク", "PNG保存", "印刷用カード"],
                "features": ["特殊文字をエスケープした標準のWIFI:形式", "WPA/WPA2/WPA3・WEP・パスワードなし、非公開SSIDにも対応", "余白（クワイエットゾーン）付きPNGを保存", "ネットワーク名とパスワードを載せた印刷用カード"],
                "how": [
                    "スマホのカメラが認識する WIFI:T:…;S:…;P:…;; 形式の文字列を作り、名前とパスワード内の \\ ; , : \" をエスケープします。",
                    "その文字列をこのページ内の小さなエンコーダーでQRコード（誤り訂正レベルM）にします。サーバーから画像を取得しません。",
                    "WPAはWPA2・WPA3のパーソナルを含みます。ユーザー名が必要な企業向けの認証はこの形式では扱えません。",
                    "保存画像には4モジュール分の白い余白を残し、印刷しても読み取りやすくしています。",
                ],
                "never": [
                    "パスワードをどこにも送信しません。QRコードは端末内で描画します。",
                    "ルーターの設定を変えたり、パスワードが正しいか確かめたりはできません。印刷前にご自身のスマホで試してください。",
                    "アカウント不要、トラッキングなし、透かしなし。",
                ],
                "faq": [
                    ("どのスマホで読み取れますか？", "最近のiPhoneやAndroidの標準カメラはWi-Fi用QRコードを認識し、接続を提案します。古い機種ではQRリーダーアプリが必要な場合があります。"),
                    ("パスワードをQRコードにして大丈夫？", "コードが見える人は誰でもパスワードを読めます。カードに書いておくのと同じです。できればゲスト用ネットワークで使ってください。"),
                    ("ネットワークを非公開（ステルス）にしている場合は？", "「非公開ネットワーク：はい」を選ぶと、名前を発信していないネットワークを探すようスマホに伝えます。"),
                ],
                "app_heading": "iPhoneでQRコードを読み取り・作成するなら",
                "card": "ネットワーク名とパスワードから、読み取るだけで接続できるWi-Fi QRコードを作成。どちらも送信しません。",
                "ui": {
                    "h2": "ネットワーク情報", "intro": "ルーターや設定アプリの表示どおりに入力してください（大文字・小文字を区別します）。",
                    "l_ssid": "ネットワーク名（SSID）", "l_pass": "パスワード", "b_show": "表示", "b_hide": "隠す",
                    "l_sec": "セキュリティ", "o_open": "なし（オープン）", "l_hidden": "非公開ネットワーク", "no": "いいえ", "yes": "はい",
                    "b_png": "PNGを保存", "b_print": "カードを印刷",
                    "c_net": "Wi-Fi：", "c_pass": "パスワード：", "c_none": "（パスワードなし）", "c_scan": "カメラをかざすと接続できます。",
                    "need_ssid": "ネットワーク名を入力するとコードができます。",
                    "short_pw": "WPAのパスワードは8文字以上です。印刷前に確認してください。",
                    "note": "印刷・共有の前に、ご自身のスマホで読み取れるか試してください。",
                },
            },
            "ko": {
                "q": [("qr코드 만들기", "D2")],
                "title": "와이파이 QR코드 만들기 — 브라우저에서 무료로",
                "description": "와이파이 이름과 비밀번호로 스캔만 하면 접속되는 QR코드를 만듭니다. WPA/WPA2/WPA3·WEP·비밀번호 없음·숨김 네트워크 지원, PNG 저장과 인쇄 가능. 업로드 없음.",
                "h1": "와이파이 QR코드 만들기",
                "eyebrow": "스캔해서 접속 · PNG·인쇄 · 무료",
                "lead": "네트워크 이름과 비밀번호를 한 번만 입력하세요. 손님은 카메라만 대면 긴 비밀번호를 불러 주지 않아도 접속합니다.",
                "badges": ["WPA·WEP·없음", "숨김 네트워크", "PNG 저장", "인쇄용 카드"],
                "features": ["특수문자를 이스케이프한 표준 WIFI: 형식", "WPA/WPA2/WPA3·WEP·비밀번호 없음, 숨김 SSID 지원", "여백(quiet zone)을 둔 PNG 저장", "네트워크 이름과 비밀번호가 적힌 인쇄용 카드"],
                "how": [
                    "휴대폰 카메라가 인식하는 WIFI:T:…;S:…;P:…;; 문자열을 만들고, 이름과 비밀번호 속 \\ ; , : \" 를 이스케이프합니다.",
                    "이 문자열을 페이지 안의 작은 인코더가 QR코드(오류 정정 레벨 M)로 바꿉니다. 서버에서 이미지를 받아오지 않습니다.",
                    "WPA는 WPA2·WPA3 개인용을 포함합니다. 사용자 이름이 필요한 기업용 인증은 이 형식이 지원하지 않습니다.",
                    "저장 이미지에는 4모듈 흰 여백을 남겨 인쇄해도 잘 읽히게 했습니다.",
                ],
                "never": [
                    "비밀번호를 어디에도 보내지 않습니다. QR코드는 기기에서 그립니다.",
                    "공유기 설정을 바꾸거나 비밀번호가 맞는지 확인할 수 없습니다. 인쇄 전에 직접 휴대폰으로 시험해 보세요.",
                    "계정 없음, 추적 없음, 워터마크 없음.",
                ],
                "faq": [
                    ("어떤 휴대폰으로 읽을 수 있나요?", "최신 iPhone과 Android 기본 카메라는 와이파이 QR코드를 인식해 접속을 제안합니다. 오래된 기기는 QR 리더 앱이 필요할 수 있습니다."),
                    ("비밀번호를 QR코드로 만들어도 안전한가요?", "코드를 볼 수 있는 사람은 누구나 비밀번호를 읽을 수 있습니다. 카드에 적어 두는 것과 같으니 가능하면 게스트 네트워크에 쓰세요."),
                    ("숨김 네트워크라면?", "‘숨김 네트워크: 예’를 고르면 이름을 알리지 않는 네트워크를 찾으라고 휴대폰에 알려 줍니다."),
                ],
                "app_heading": "iPhone에서 QR코드를 스캔하고 만든다면",
                "card": "네트워크 이름과 비밀번호로 스캔해서 접속하는 와이파이 QR코드를 만듭니다. 둘 다 전송하지 않습니다.",
                "ui": {
                    "h2": "네트워크 정보", "intro": "공유기나 설정 앱에 표시된 그대로 입력하세요(대소문자 구분).",
                    "l_ssid": "네트워크 이름(SSID)", "l_pass": "비밀번호", "b_show": "보기", "b_hide": "숨기기",
                    "l_sec": "보안", "o_open": "없음(개방형)", "l_hidden": "숨김 네트워크", "no": "아니요", "yes": "예",
                    "b_png": "PNG 저장", "b_print": "카드 인쇄",
                    "c_net": "와이파이:", "c_pass": "비밀번호:", "c_none": "(비밀번호 없음)", "c_scan": "카메라를 대면 접속할 수 있어요.",
                    "need_ssid": "네트워크 이름을 입력하면 코드가 만들어집니다.",
                    "short_pw": "WPA 비밀번호는 8자 이상입니다. 인쇄 전에 확인하세요.",
                    "note": "인쇄하거나 공유하기 전에 직접 휴대폰으로 읽어 보세요.",
                },
            },
            "de-DE": {
                "q": [("wlan qr code", "D2"), ("qr code generator", "D2")],
                "title": "WLAN-QR-Code erstellen — kostenlos im Browser",
                "description": "Aus WLAN-Name und Passwort einen QR-Code machen, mit dem Gäste per Scan ins Netz kommen. WPA/WPA2/WPA3, WEP, offen und versteckt; als PNG speichern oder als Karte drucken. Kein Upload.",
                "h1": "WLAN-QR-Code-Generator",
                "eyebrow": "Scannen & verbinden · PNG oder Druck · kostenlos",
                "lead": "Netzwerkname und Passwort einmal eintippen — Gäste halten die Kamera darauf und sind verbunden, ohne ein langes Passwort abzutippen.",
                "badges": ["WPA / WEP / offen", "Versteckte Netze", "PNG-Download", "Druckbare Karte"],
                "features": ["Standard-WIFI:-Inhalt mit maskierten Sonderzeichen", "WPA/WPA2/WPA3, WEP und offene Netze, auch versteckte SSIDs", "PNG mit korrekter Ruhezone", "Druckkarte mit Netzwerkname und Passwort"],
                "how": [
                    "Die Seite baut denselben Text WIFI:T:…;S:…;P:…;; den Handykameras erkennen, und maskiert dabei \\ ; , : \" in Name und Passwort.",
                    "Der Text wird von einem kleinen Encoder direkt auf dieser Seite als QR-Code (Fehlerkorrektur M) gezeichnet — kein Bild kommt von einem Server.",
                    "WPA umfasst WPA2- und WPA3-Personal; Firmen-Logins mit Benutzername unterstützt das Format nicht.",
                    "Der Download behält einen weißen Rand von vier Modulen, damit der Code auch gedruckt sicher scannt.",
                ],
                "never": [
                    "Ihr Passwort wird nirgendwohin gesendet — der Code entsteht auf Ihrem Gerät.",
                    "Es ändert keine Router-Einstellungen und prüft das Passwort nicht; testen Sie den Code vor dem Druck mit dem eigenen Handy.",
                    "Kein Konto, kein Tracking, kein Wasserzeichen.",
                ],
                "faq": [
                    ("Welche Handys können ihn scannen?", "Aktuelle Kamera-Apps von iPhone und Android erkennen WLAN-QR-Codes und bieten das Verbinden an. Ältere Geräte brauchen eventuell eine QR-App."),
                    ("Ist mein Passwort im QR-Code sicher?", "Wer den Code sieht, kann das Passwort lesen — genau wie bei einer beschrifteten Karte. Nutzen Sie nach Möglichkeit ein Gastnetz."),
                    ("Und wenn mein Netz versteckt ist?", "Wählen Sie „Verstecktes Netz: Ja“. Dann sucht das Handy nach einem Netz, das seinen Namen nicht aussendet."),
                ],
                "app_heading": "Codes auch auf dem iPhone scannen und erstellen?",
                "card": "WLAN-QR-Code zum Scannen und Verbinden aus Netzwerkname und Passwort — ohne Upload.",
                "ui": {
                    "h2": "Ihr Netzwerk", "intro": "Genau wie im Router oder in den Einstellungen — Groß- und Kleinschreibung zählt.",
                    "l_ssid": "Netzwerkname (SSID)", "l_pass": "Passwort", "b_show": "Zeigen", "b_hide": "Verbergen",
                    "l_sec": "Sicherheit", "o_open": "Keine (offen)", "l_hidden": "Verstecktes Netz", "no": "Nein", "yes": "Ja",
                    "b_png": "PNG speichern", "b_print": "Karte drucken",
                    "c_net": "WLAN:", "c_pass": "Passwort:", "c_none": "(kein Passwort)", "c_scan": "Kamera auf den Code halten, um zu verbinden.",
                    "need_ssid": "Netzwerknamen eingeben, um einen Code zu erstellen.",
                    "short_pw": "WPA-Passwörter haben mindestens 8 Zeichen — bitte vor dem Druck prüfen.",
                    "note": "Testen Sie den Code vor dem Drucken oder Teilen mit dem eigenen Handy.",
                },
            },
            "zh-Hant": {
                "q": [("qr code 產生器", "D2")],
                "title": "Wi-Fi QR Code 產生器 — 在瀏覽器裡免費製作",
                "description": "把 Wi-Fi 名稱和密碼做成 QR Code，客人掃一下就能連線。支援 WPA/WPA2/WPA3、WEP、無密碼與隱藏網路，可下載 PNG 或列印小卡，不上傳任何資料。",
                "h1": "Wi-Fi QR Code 產生器",
                "eyebrow": "掃描即連線 · PNG 或列印 · 免費",
                "lead": "網路名稱和密碼只要輸入一次；客人用手機相機對準就能連上，不必再一個字一個字念長密碼。",
                "badges": ["WPA／WEP／無密碼", "隱藏網路", "下載 PNG", "可列印小卡"],
                "features": ["標準 WIFI: 格式，特殊字元自動跳脫", "支援 WPA/WPA2/WPA3、WEP、無密碼與隱藏 SSID", "下載含留白（quiet zone）的 PNG", "印出含網路名稱與密碼的小卡"],
                "how": [
                    "頁面會組出手機相機認得的 WIFI:T:…;S:…;P:…;; 文字，並把名稱與密碼中的 \\ ; , : \" 跳脫。",
                    "再由這一頁內建的小型編碼器把文字畫成 QR Code（容錯等級 M），不會向伺服器索取圖片。",
                    "WPA 已包含 WPA2、WPA3 個人版；需要帳號的企業級登入不在這個格式支援範圍內。",
                    "下載的圖片保留 4 格白邊，印出來也比較好掃。",
                ],
                "never": [
                    "不會把密碼送到任何地方——QR Code 在你的裝置上畫出來。",
                    "不能修改路由器設定，也不會檢查密碼對不對；列印前請先用自己的手機掃掃看。",
                    "不用帳號、不追蹤、沒有浮水印。",
                ],
                "faq": [
                    ("哪些手機掃得到？", "近年的 iPhone 和 Android 內建相機都認得 Wi-Fi QR Code，會跳出加入網路的提示；較舊的手機可能需要掃碼 App。"),
                    ("把密碼做成 QR Code 安全嗎？", "看得到這個碼的人都能讀出密碼，就跟把密碼寫在卡片上一樣。可以的話，請用訪客網路。"),
                    ("我的網路是隱藏的怎麼辦？", "選「隱藏網路：是」，QR Code 會告訴手機去找不廣播名稱的網路。"),
                ],
                "app_heading": "也想在 iPhone 上掃描和製作條碼？",
                "card": "用網路名稱與密碼做出掃描即連線的 Wi-Fi QR Code，兩者都不會上傳。",
                "ui": {
                    "h2": "你的網路", "intro": "請照路由器或設定 App 顯示的輸入，大小寫有差別。",
                    "l_ssid": "網路名稱（SSID）", "l_pass": "密碼", "b_show": "顯示", "b_hide": "隱藏",
                    "l_sec": "加密方式", "o_open": "無（開放）", "l_hidden": "隱藏網路", "no": "否", "yes": "是",
                    "b_png": "下載 PNG", "b_print": "列印小卡",
                    "c_net": "Wi-Fi：", "c_pass": "密碼：", "c_none": "（無密碼）", "c_scan": "用手機相機對準就能連線。",
                    "need_ssid": "輸入網路名稱就會產生 QR Code。",
                    "short_pw": "WPA 密碼至少 8 個字元，列印前請再確認。",
                    "note": "列印或分享前，請先用自己的手機掃描測試。",
                },
            },
        },
    })
    return spec


# ------------------------------------------------ LED scrolling text (LED Moving Text)

LED_CSS = """
.led-wrap{background:#050505;border-radius:18px;padding:10px;margin-top:18px;overflow:hidden}
.led-wrap canvas{display:block;width:100%;height:auto}
.led-wrap:fullscreen{display:flex;align-items:center;justify-content:center;border-radius:0;padding:0}
.swatches{display:flex;gap:8px;flex-wrap:wrap}.swatches button{width:34px;height:34px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px var(--line);cursor:pointer}
.swatches button[aria-pressed=true]{box-shadow:0 0 0 3px var(--brand)}
@media (max-width:720px){.controls{grid-template-columns:1fr 1fr}}
"""

LED_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field" style="grid-column:1/-1"><label for="txt">{ui[l_text]}</label><input type="text" id="txt" maxlength="120" value="{ui[sample]}"></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="spd">{ui[l_speed]}</label><input type="range" id="spd" min="0" max="10" value="4"></div>
<div class="field"><label for="dir">{ui[l_dir]}</label><select id="dir"><option value="-1">{ui[d_left]}</option><option value="1">{ui[d_right]}</option><option value="0">{ui[d_still]}</option></select></div>
<div class="field"><label for="blink">{ui[l_blink]}</label><select id="blink"><option value="0">{ui[off]}</option><option value="1">{ui[on]}</option></select></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label>{ui[l_color]}</label><div class="swatches" id="sw"></div></div>
<div class="field"><label for="mir">{ui[l_mirror]}</label><select id="mir"><option value="0">{ui[off]}</option><option value="1">{ui[on]}</option></select></div>
<div class="field" style="align-self:end"><button class="button" id="fs" type="button">{ui[b_full]}</button></div>
</div>
<div class="led-wrap" id="wrap"><canvas id="led" width="960" height="200"></canvas></div>
<p class="note">{ui[note]}</p>
"""

LED_JS = r"""
var $=function(i){return document.getElementById(i);};
var COLORS=['#ff3b30','#ff9500','#ffd60a','#34c759','#00c7be','#0a84ff','#bf5af2','#ffffff'];
var color=COLORS[0],off=0,last=0,ROWS=16,cols=0,bitmap=null,textW=0;
var sw=$('sw');COLORS.forEach(function(c,i){var b=document.createElement('button');b.type='button';b.style.background=c;
  b.setAttribute('aria-label',c);b.setAttribute('aria-pressed',i===0?'true':'false');
  b.addEventListener('click',function(){color=c;[].forEach.call(sw.children,function(x){x.setAttribute('aria-pressed','false');});
    b.setAttribute('aria-pressed','true');});sw.appendChild(b);});
function rasterize(){var t=$('txt').value||' ',c=document.createElement('canvas'),x=c.getContext('2d');
  var font='bold '+(ROWS-2)+'px "Helvetica Neue",Arial,"PingFang TC","Hiragino Sans","Noto Sans CJK TC",sans-serif';
  x.font=font;textW=Math.ceil(x.measureText(t).width)+4;c.width=textW;c.height=ROWS;x.font=font;
  x.fillStyle='#000';x.fillRect(0,0,c.width,c.height);x.fillStyle='#fff';x.textBaseline='middle';x.fillText(t,2,ROWS/2+1);
  var d=x.getImageData(0,0,c.width,c.height).data;bitmap=new Uint8Array(c.width*ROWS);
  for(var i=0;i<c.width*ROWS;i++)bitmap[i]=d[i*4]>110?1:0;window.__led={text:t,width:textW};}
function frame(ts){var cv=$('led'),x=cv.getContext('2d'),W=cv.width,H=cv.height,cell=H/ROWS;cols=Math.floor(W/cell);
  var dt=last?Math.min(100,ts-last):16;last=ts;var dir=parseInt($('dir').value,10),speed=parseInt($('spd').value,10);
  off+=dir*speed*dt*0.004;var span=textW+cols;if(off<-span)off+=span;if(off>span)off-=span;
  var lit=!($('blink').value==='1'&&Math.floor(ts/450)%2===1),mir=$('mir').value==='1';
  x.fillStyle='#050505';x.fillRect(0,0,W,H);
  var start=dir===0?Math.floor((cols-textW)/2):Math.round(off)+(dir<0?cols:-textW);
  if(dir===0)start=Math.floor((cols-textW)/2);
  for(var cx=0;cx<cols;cx++){var tx=(mir?cols-1-cx:cx)-start;
    if(dir!==0){tx=((tx%span)+span)%span;}
    for(var cy=0;cy<ROWS;cy++){var on=lit&&tx>=0&&tx<textW&&bitmap[cy*textW+tx];
      x.beginPath();x.arc(cx*cell+cell/2,cy*cell+cell/2,cell*0.38,0,6.2832);
      x.fillStyle=on?color:'#1b1b1b';x.fill();}}
  requestAnimationFrame(frame);}
$('txt').addEventListener('input',rasterize);
$('fs').addEventListener('click',function(){var w=$('wrap');
  if(document.fullscreenElement){document.exitFullscreen();return;}
  if(w.requestFullscreen)w.requestFullscreen().catch(function(){});});
rasterize();requestAnimationFrame(frame);
"""

_LED_APP = {"app_key": "ledmovingtext", "app_id": "6806639602",
            "app_name": "LED Moving Text", "category": "UtilitiesApplication"}


def spec_led_scrolling_text():
    spec = dict(_LED_APP)
    spec.update({
        "slug": "led-scrolling-text-preview",
        "body": LED_BODY,
        "script": LED_JS,
        "extra_css": LED_CSS,
        "i18n": {
            "en": {
                "q": [("led scrolling text", "D2"), ("scrolling text", "D2"), ("led banner", "D2")],
                "title": "LED Scrolling Text Online — Free Dot-Matrix Banner Preview",
                "description": "Type a message and watch it scroll across a dot-matrix LED board in your browser: eight colours, speed, left or right, still, blink, mirrored text and full screen. Nothing is uploaded.",
                "h1": "LED scrolling text preview",
                "eyebrow": "Dot-matrix board · full screen · free",
                "lead": "Try a message the way it will look on an LED sign before a concert, an airport pickup or a counter notice — then go full screen on a laptop or tablet.",
                "badges": ["Dot-matrix look", "8 colours", "Left, right or still", "Full screen"],
                "features": ["Any text, including Chinese, Japanese and Korean", "Scroll left, right or hold still, with adjustable speed", "Eight LED colours, blink and mirrored text", "Full-screen board in the browser"],
                "how": [
                    "Your text is drawn once into a 16-pixel-high image, and every lit pixel becomes one round LED on the board.",
                    "Scrolling moves that bitmap one LED column at a time, timed by the browser’s animation clock so speed stays steady on fast and slow screens.",
                    "Mirror flips the board left to right so the message reads correctly from outside a window or in a rear-view mirror.",
                    "Full screen uses the browser’s own full-screen mode; press Esc or the button again to leave.",
                ],
                "never": [
                    "It is a browser preview, not a phone app: there are no saved boards, fonts or effect packs.",
                    "It does not keep the screen awake on every device — check your display settings for long use.",
                    "No account, no tracking, nothing uploaded.",
                ],
                "faq": [
                    ("Can I use emoji or Chinese characters?", "Yes. Any character your browser can draw is rasterised onto the board; very detailed characters are simplified by the 16-LED height."),
                    ("How do I make it bigger?", "Use Full screen, or turn a phone sideways in full screen to give the letters more height."),
                    ("Why does my message look mirrored?", "The Mirror option is on. Turn it off unless you are showing the board through a window."),
                ],
                "app_heading": "Want a full-screen LED board on your iPhone?",
                "card": "Preview a scrolling LED message in eight colours, then show it full screen in the browser.",
                "ui": {
                    "h2": "Your message", "intro": "Type it, pick a colour and speed, then go full screen.",
                    "l_text": "Text", "sample": "WELCOME HOME!",
                    "l_speed": "Speed", "l_dir": "Direction", "d_left": "Scroll left", "d_right": "Scroll right", "d_still": "Still",
                    "l_blink": "Blink", "l_color": "Colour", "l_mirror": "Mirror", "on": "On", "off": "Off",
                    "b_full": "Full screen",
                    "note": "Browser preview only. Brightness depends on your screen; nothing you type is stored.",
                },
            },
            "ja": {
                "q": [("電光掲示板", "D4"), ("電光掲示板 アプリ", "D2")],
                "title": "電光掲示板メーカー — 流れる文字をブラウザで無料プレビュー",
                "description": "文字を入れるとドットマトリクスの電光掲示板に流れて表示。8色・速度・左右・停止・点滅・左右反転・全画面に対応。ブラウザだけで動き、何もアップロードしません。",
                "h1": "電光掲示板（流れる文字）プレビュー",
                "eyebrow": "ドット表示 · 全画面 · 無料",
                "lead": "ライブの応援、空港のお出迎え、店先のお知らせ。掲示板でどう見えるかを試して、パソコンやタブレットでそのまま全画面表示できます。",
                "badges": ["ドット風表示", "8色", "左・右・停止", "全画面"],
                "features": ["日本語・中国語・韓国語を含む好きな文字", "左右へのスクロールや停止、速度調整", "8色のLED、点滅、左右反転", "ブラウザで全画面表示"],
                "how": [
                    "文字を高さ16ピクセルの画像に一度描き、点灯したピクセルを1つずつ丸いLEDにします。",
                    "スクロールはLED1列ずつ動かし、ブラウザのアニメーション時計に合わせるので、画面の速さが違っても速度は一定です。",
                    "左右反転は、窓の外やバックミラー越しに正しく読めるように表示を反転します。",
                    "全画面はブラウザの全画面モードを使います。Escキーかもう一度ボタンで戻ります。",
                ],
                "never": [
                    "ブラウザ用のプレビューで、スマホアプリではありません。ボードの保存やフォント・エフェクトはありません。",
                    "端末によっては画面の自動ロックを止められません。長時間使うときは画面設定を確認してください。",
                    "アカウント不要、トラッキングなし、アップロードなし。",
                ],
                "faq": [
                    ("絵文字や漢字も使えますか？", "はい。ブラウザで表示できる文字ならボードに描けます。画数の多い漢字は高さ16個のLEDで簡略化されます。"),
                    ("もっと大きく表示するには？", "全画面を使うか、全画面のままスマホを横にすると文字が大きくなります。"),
                    ("文字が反転して見えるのはなぜ？", "「左右反転」がオンです。窓越しに見せるとき以外はオフにしてください。"),
                ],
                "app_heading": "iPhoneでも全画面の電光掲示板を使うなら",
                "card": "流れる電光掲示板の文字を8色でプレビューして、ブラウザで全画面表示。",
                "ui": {
                    "h2": "表示する文字", "intro": "文字を入れて色と速度を選び、全画面にどうぞ。",
                    "l_text": "文字", "sample": "おかえりなさい！",
                    "l_speed": "速度", "l_dir": "方向", "d_left": "左へ流す", "d_right": "右へ流す", "d_still": "停止",
                    "l_blink": "点滅", "l_color": "色", "l_mirror": "左右反転", "on": "オン", "off": "オフ",
                    "b_full": "全画面",
                    "note": "ブラウザでのプレビューです。明るさは画面によります。入力内容は保存されません。",
                },
            },
            "ko": {
                "q": [("전광판", "D2"), ("전광판 앱", "D2")],
                "title": "전광판 만들기 — 흐르는 글자를 브라우저에서 무료 미리보기",
                "description": "문구를 입력하면 도트 매트릭스 LED 전광판에 흐르듯 표시됩니다. 8가지 색, 속도, 왼쪽·오른쪽·정지, 깜빡임, 좌우 반전, 전체 화면 지원. 업로드 없음.",
                "h1": "LED 전광판 문구 미리보기",
                "eyebrow": "도트 전광판 · 전체 화면 · 무료",
                "lead": "콘서트 응원, 공항 마중, 가게 안내. 전광판에서 어떻게 보일지 미리 보고 노트북이나 태블릿에서 바로 전체 화면으로 띄우세요.",
                "badges": ["도트 느낌", "8가지 색", "왼쪽·오른쪽·정지", "전체 화면"],
                "features": ["한글·한자·일본어를 포함한 어떤 문구든", "왼쪽·오른쪽 스크롤 또는 정지, 속도 조절", "LED 8색, 깜빡임, 좌우 반전", "브라우저 전체 화면 전광판"],
                "how": [
                    "문구를 높이 16픽셀 이미지로 한 번 그리고, 켜진 픽셀 하나하나를 둥근 LED로 표시합니다.",
                    "스크롤은 LED 한 칸씩 움직이며 브라우저 애니메이션 시계에 맞추므로 화면 성능과 상관없이 속도가 일정합니다.",
                    "좌우 반전은 창밖이나 백미러로 볼 때 바르게 읽히도록 화면을 뒤집습니다.",
                    "전체 화면은 브라우저 전체 화면 모드를 씁니다. Esc 키나 버튼을 다시 누르면 나옵니다.",
                ],
                "never": [
                    "브라우저 미리보기일 뿐 휴대폰 앱이 아닙니다. 보드 저장, 글꼴, 효과 팩은 없습니다.",
                    "기기에 따라 화면 자동 잠금을 막지 못합니다. 오래 쓸 때는 화면 설정을 확인하세요.",
                    "계정 없음, 추적 없음, 업로드 없음.",
                ],
                "faq": [
                    ("이모지나 한자도 되나요?", "네. 브라우저가 그릴 수 있는 글자는 전광판에 표시됩니다. 획이 많은 글자는 16칸 높이에 맞게 단순해집니다."),
                    ("더 크게 보려면?", "전체 화면을 쓰거나, 전체 화면에서 휴대폰을 가로로 돌리면 글자가 커집니다."),
                    ("글자가 거꾸로 보여요.", "‘좌우 반전’이 켜져 있습니다. 창 너머로 보여 줄 때가 아니면 끄세요."),
                ],
                "app_heading": "iPhone에서도 전체 화면 전광판을 쓰려면",
                "card": "흐르는 LED 전광판 문구를 8가지 색으로 미리 보고 브라우저 전체 화면으로 띄우기.",
                "ui": {
                    "h2": "표시할 문구", "intro": "문구를 입력하고 색과 속도를 고른 뒤 전체 화면으로 띄우세요.",
                    "l_text": "문구", "sample": "환영합니다!",
                    "l_speed": "속도", "l_dir": "방향", "d_left": "왼쪽으로", "d_right": "오른쪽으로", "d_still": "정지",
                    "l_blink": "깜빡임", "l_color": "색", "l_mirror": "좌우 반전", "on": "켜기", "off": "끄기",
                    "b_full": "전체 화면",
                    "note": "브라우저 미리보기입니다. 밝기는 화면에 따라 다릅니다. 입력한 내용은 저장되지 않습니다.",
                },
            },
            "de-DE": {
                "q": [("laufschrift", "D4")],
                "title": "LED-Laufschrift online — kostenlose Punktmatrix-Vorschau",
                "description": "Text eintippen und als Laufschrift auf einer LED-Punktmatrix im Browser ansehen: acht Farben, Tempo, links, rechts oder stehend, Blinken, Spiegelschrift und Vollbild. Kein Upload.",
                "h1": "LED-Laufschrift-Vorschau",
                "eyebrow": "Punktmatrix · Vollbild · kostenlos",
                "lead": "Testen Sie eine Nachricht so, wie sie auf einem LED-Schild aussieht — fürs Konzert, die Abholung am Flughafen oder den Hinweis an der Theke — und zeigen Sie sie im Vollbild auf Laptop oder Tablet.",
                "badges": ["Punktmatrix-Look", "8 Farben", "Links, rechts, stehend", "Vollbild"],
                "features": ["Beliebiger Text, auch Chinesisch, Japanisch und Koreanisch", "Lauf nach links, rechts oder stehend, Tempo einstellbar", "Acht LED-Farben, Blinken und Spiegelschrift", "Vollbild-Anzeige im Browser"],
                "how": [
                    "Der Text wird einmal in ein 16 Pixel hohes Bild gezeichnet; jedes leuchtende Pixel wird zu einer runden LED.",
                    "Die Laufschrift verschiebt dieses Bild LED-Spalte für LED-Spalte im Takt der Browser-Animation, damit das Tempo auf jedem Bildschirm gleich bleibt.",
                    "Spiegeln dreht die Anzeige seitenverkehrt, damit die Nachricht durch ein Fenster oder im Rückspiegel richtig lesbar ist.",
                    "Vollbild nutzt den Vollbildmodus des Browsers; Esc oder der Knopf beendet ihn.",
                ],
                "never": [
                    "Es ist eine Browser-Vorschau, keine Handy-App: keine gespeicherten Tafeln, Schriften oder Effektpakete.",
                    "Es hält nicht auf jedem Gerät den Bildschirm wach — prüfen Sie für längere Nutzung die Anzeigeeinstellungen.",
                    "Kein Konto, kein Tracking, kein Upload.",
                ],
                "faq": [
                    ("Gehen Emojis oder chinesische Zeichen?", "Ja. Jedes Zeichen, das der Browser darstellen kann, landet auf der Tafel; sehr detailreiche Zeichen werden durch die 16 LED Höhe vereinfacht."),
                    ("Wie wird es größer?", "Vollbild nutzen oder das Handy im Vollbild quer halten — dann bekommen die Buchstaben mehr Höhe."),
                    ("Warum ist meine Nachricht spiegelverkehrt?", "Die Option Spiegeln ist an. Schalten Sie sie aus, außer Sie zeigen die Tafel durch ein Fenster."),
                ],
                "app_heading": "Eine Vollbild-LED-Tafel auch auf dem iPhone?",
                "card": "LED-Laufschrift in acht Farben ausprobieren und im Browser als Vollbild zeigen.",
                "ui": {
                    "h2": "Ihre Nachricht", "intro": "Eintippen, Farbe und Tempo wählen, dann Vollbild.",
                    "l_text": "Text", "sample": "WILLKOMMEN ZUHAUSE!",
                    "l_speed": "Tempo", "l_dir": "Richtung", "d_left": "Nach links", "d_right": "Nach rechts", "d_still": "Stehend",
                    "l_blink": "Blinken", "l_color": "Farbe", "l_mirror": "Spiegeln", "on": "An", "off": "Aus",
                    "b_full": "Vollbild",
                    "note": "Nur eine Browser-Vorschau. Die Helligkeit hängt vom Bildschirm ab; Eingaben werden nicht gespeichert.",
                },
            },
            "zh-Hant": {
                "q": [("跑馬燈", "D2"), ("跑馬燈 app", "D2")],
                "title": "LED 跑馬燈產生器 — 在瀏覽器免費預覽字幕跑馬燈",
                "description": "輸入文字就能在點陣 LED 看板上跑起來：8 種顏色、速度、向左向右或靜止、閃爍、鏡像與全螢幕，全部在瀏覽器完成，不上傳任何內容。",
                "h1": "LED 跑馬燈預覽",
                "eyebrow": "點陣看板 · 全螢幕 · 免費",
                "lead": "演唱會應援、機場接機、店門口告示——先看看在 LED 看板上的樣子，再用筆電或平板直接全螢幕播放。",
                "badges": ["點陣效果", "8 種顏色", "向左、向右、靜止", "全螢幕"],
                "features": ["任何文字，中文、日文、韓文都可以", "向左、向右捲動或靜止，速度可調", "8 種 LED 顏色、閃爍與鏡像文字", "瀏覽器全螢幕看板"],
                "how": [
                    "文字先畫成 16 像素高的小圖，每個亮起的像素就變成一顆圓形 LED。",
                    "捲動時一次移動一欄 LED，並跟著瀏覽器的動畫時鐘走，所以快慢螢幕上的速度都一樣。",
                    "鏡像會把看板左右翻轉，從車窗外或後照鏡看也是正的。",
                    "全螢幕使用瀏覽器內建的全螢幕模式，按 Esc 或再按一次按鈕即可離開。",
                ],
                "never": [
                    "這只是瀏覽器預覽，不是手機 App：沒有儲存看板、字型或特效包。",
                    "不是每台裝置都能讓螢幕保持常亮，長時間使用請先檢查螢幕設定。",
                    "不用帳號、不追蹤、不上傳。",
                ],
                "faq": [
                    ("可以打表情符號或中文嗎？", "可以。瀏覽器能顯示的字都能畫到看板上；筆畫很多的字會因為只有 16 顆 LED 高而被簡化。"),
                    ("怎麼讓字更大？", "按全螢幕，或在全螢幕時把手機橫過來，字就有更多高度。"),
                    ("為什麼字是反的？", "「鏡像」開著。除非要隔著窗戶給人看，否則請關掉。"),
                ],
                "app_heading": "想在 iPhone 上也有全螢幕 LED 看板？",
                "card": "用 8 種顏色預覽 LED 跑馬燈文字，再在瀏覽器全螢幕播放。",
                "ui": {
                    "h2": "要顯示的文字", "intro": "輸入文字，選好顏色和速度，再按全螢幕。",
                    "l_text": "文字", "sample": "歡迎回家！",
                    "l_speed": "速度", "l_dir": "方向", "d_left": "向左捲動", "d_right": "向右捲動", "d_still": "靜止",
                    "l_blink": "閃爍", "l_color": "顏色", "l_mirror": "鏡像", "on": "開", "off": "關",
                    "b_full": "全螢幕",
                    "note": "僅為瀏覽器預覽，亮度取決於你的螢幕；輸入的內容不會被儲存。",
                },
            },
        },
    })
    return spec


APP_JOB_SPEC_BUILDERS = [
    spec_days_between_dates,
    spec_wifi_qr,
    spec_led_scrolling_text,
]
