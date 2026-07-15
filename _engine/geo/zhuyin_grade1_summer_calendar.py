#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a nine-locale, print-ready 14-day Grade 1 Zhuyin warm-up calendar."""
from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from bopomofo_flashcards import (  # noqa: E402
    ALT_LOCALES,
    APP_ID,
    APP_KEY,
    write_text_if_changed,
)
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-grade1-14-day-summer-calendar"
CONTENT_DATE = "2026-07-15"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/"
    "html_ch/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=0"
SOURCES = (MOE_HANDBOOK, MOE_PRACTICE)

RELATED_SLUGS = (
    "zhuyin-practice-sheet",
    "zhuyin-flashcards",
    "zhuyin-bingo",
    "private-bopomofo-matching-pair-cards",
    "private-bopomofo-symbol-contrast-cards",
)

DAY_MIN = 1
DAY_MAX = 14
LANE_VALUES = ("base", "stretch")

TARGET_ANSWER_SLUGS = (
    "how-can-my-child-prepare-for-grade-1-bopomofo-over-the-summer-before-"
    "school-starts.html",
    "my-child-starts-grade-1-in-september-and-doesn-t-know-any-bopomofo-yet-"
    "will-they-fall-behind.html",
)
INBOUND_LINK_CLASS = "zhuyin-grade1-summer-calendar-inline-link"
_APP_STORE_ANCHOR = re.compile(
    r'<a\b(?=[^>]*\bhref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id'
    + APP_ID
    + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)

DAYS = {
    "en": (
        {
            "day": "Day 1",
            "focus": "Choose a gentle starting lane",
            "base": "If Zhuyin is completely new, open the official chart and choose only two or three symbols. The adult models once; listening counts.",
            "stretch": "If the child has seen Zhuyin before, use the free 3-minute observation guide once to choose a lane\u2014not to produce a score.",
        },
        {
            "day": "Day 2",
            "focus": "Hear, then point",
            "base": "Say or play three selected symbol sounds one at a time. The child may point, look, copy a gesture or simply listen.",
            "stretch": "Mix four to six familiar symbols and let the child choose which one the adult models next.",
        },
        {
            "day": "Day 3",
            "focus": "Match shapes without speed",
            "base": "Write two copies of each selected symbol on scrap paper. Turn them face up and pair matching shapes together.",
            "stretch": "Add one similar-looking pair and talk about one visible difference without calling either answer wrong.",
        },
        {
            "day": "Day 4",
            "focus": "Trace one official form",
            "base": "Check the Ministry of Education stroke reference. Model one or two symbols in the air; the child may air-trace, finger-trace or watch.",
            "stretch": "Trace the same familiar symbols once on paper, stopping before neatness becomes the goal.",
        },
        {
            "day": "Day 5",
            "focus": "Connect one sound to family life",
            "base": "Choose one familiar spoken Mandarin word and use an authorized reference to notice one Zhuyin symbol in it.",
            "stretch": "Find a second family word with the same selected sound; conversation matters more than recall.",
        },
        {
            "day": "Day 6",
            "focus": "Move with one tone contrast",
            "base": "Use one familiar spoken syllable. The adult models two tones with a hand path; the child may move, listen or imitate.",
            "stretch": "Try the same base syllable with up to four tones only if the child remains comfortable.",
        },
        {
            "day": "Day 7",
            "focus": "Repeat by child choice",
            "base": "Offer the activities from Days 2\u20136 and let the child choose one. Add no new symbol today.",
            "stretch": "Let the child become the caller, card chooser or movement leader without correcting publicly.",
        },
        {
            "day": "Day 8",
            "focus": "Meet a second small set",
            "base": "Choose two or three different symbols from the official chart. Model, point and move exactly as on Day 2.",
            "stretch": "Mix the new set with two familiar symbols and sort them into 'seen before' and 'new today.'",
        },
        {
            "day": "Day 9",
            "focus": "Notice a look-alike pair",
            "base": "Place one similar-looking pair side by side. Name or trace the feature that makes their shapes different.",
            "stretch": "Add each symbol to a tiny matching or pointing game; avoid timed rounds.",
        },
        {
            "day": "Day 10",
            "focus": "Return to stroke order",
            "base": "Use the official stroke reference for one selected symbol. Model slowly, then invite one air or paper trace.",
            "stretch": "Compare the child's own two attempts only to notice movement\u2014not to grade neatness.",
        },
        {
            "day": "Day 11",
            "focus": "Listen to a two-part blend",
            "base": "With two familiar symbols from an authorized model, say the parts slowly and then join them. The child may only listen.",
            "stretch": "If ready, let the child slide two paper cards together while joining the sounds without a timer.",
        },
        {
            "day": "Day 12",
            "focus": "Add a tone only when ready",
            "base": "Reuse yesterday's familiar base syllable and model one tone with a hand path. Keep symbol blending and tone listening separate.",
            "stretch": "Compare two tones on the same syllable; stop if the two tasks begin to overload attention.",
        },
        {
            "day": "Day 13",
            "focus": "Notice Zhuyin in real reading",
            "base": "Use one legally owned, borrowed or authorized annotated book. Let the child choose one page and notice one familiar symbol.",
            "stretch": "Read for meaning, then point to one short annotation only if the child wants to revisit it.",
        },
        {
            "day": "Day 14",
            "focus": "Let the child lead the ending",
            "base": "The child chooses a favorite activity from the calendar. Repeat it and end while the interaction is still comfortable.",
            "stretch": "Choose one neutral next step\u2014repeat, pause, ask the school or explore another small set\u2014without assigning a level.",
        },
    ),
    "zh-Hant": (
        {
            "day": "第 1 天",
            "focus": "選一條溫和起點",
            "base": "完全沒接觸過注音時，打開教育部官方符號表，只選兩至三個符號。大人示範一次，孩子只聽也算參與。",
            "stretch": "孩子以前看過注音時，可使用一次免費 3 分鐘觀察指南，只用來選起點，不產生分數。",
        },
        {
            "day": "第 2 天",
            "focus": "先聽，再指",
            "base": "一次說出或播放一個選定符號的聲音，共三個。孩子可以指、看、模仿手勢或只聽。",
            "stretch": "混合四至六個熟悉符號，讓孩子選下一個由大人示範的符號。",
        },
        {
            "day": "第 3 天",
            "focus": "不計時配對形狀",
            "base": "在廢紙上把每個選定符號各寫兩張，全部翻開，將相同形狀配在一起。",
            "stretch": "加入一組外形相近的符號，只談一個看得見的差異，不說哪個答案錯了。",
        },
        {
            "day": "第 4 天",
            "focus": "描一個官方字形",
            "base": "查看教育部官方筆順，示範一至兩個符號的空中筆畫；孩子可空寫、手指描或觀看。",
            "stretch": "把同一個熟悉符號在紙上描一次；整齊還沒變成目標前就停止。",
        },
        {
            "day": "第 5 天",
            "focus": "把一個聲音連到家庭生活",
            "base": "選一個熟悉的華語口語詞，搭配合法授權的參考資料，注意其中一個注音。",
            "stretch": "再找一個含相同聲音的家庭詞語；對話比記住答案重要。",
        },
        {
            "day": "第 6 天",
            "focus": "用動作感受一組聲調",
            "base": "使用一個熟悉的口語音節，大人用手勢路徑示範兩個聲調；孩子可動作、聆聽或模仿。",
            "stretch": "只有孩子仍感到自在時，才把同一個音節試到最多四個聲調。",
        },
        {
            "day": "第 7 天",
            "focus": "由孩子選擇重複",
            "base": "把第 2 至 6 天的活動列出來，讓孩子選一個；今天不增加新符號。",
            "stretch": "讓孩子擔任出題、選卡或動作帶領者，不公開糾正。",
        },
        {
            "day": "第 8 天",
            "focus": "認識第二小組符號",
            "base": "從官方符號表另選兩至三個符號，像第 2 天一樣示範、指認與動作。",
            "stretch": "把新符號與兩個熟悉符號混合，分成「以前看過」與「今天新看見」。",
        },
        {
            "day": "第 9 天",
            "focus": "注意一組相近字形",
            "base": "把一組外形相近的符號並排，說出或描出讓兩個形狀不同的特徵。",
            "stretch": "把兩個符號放進小型配對或指認遊戲，不做計時回合。",
        },
        {
            "day": "第 10 天",
            "focus": "再次查看筆順",
            "base": "使用官方筆順參考一個選定符號；慢慢示範，再邀請孩子空寫或紙上描一次。",
            "stretch": "只比較孩子自己的兩次動作來觀察路徑，不評分整齊度。",
        },
        {
            "day": "第 11 天",
            "focus": "聽一組二拼",
            "base": "依合法授權的示範，使用兩個熟悉符號，先慢慢分開說，再連起來；孩子只聽也可以。",
            "stretch": "準備好時，讓孩子把兩張紙卡滑近並連音，不使用計時器。",
        },
        {
            "day": "第 12 天",
            "focus": "準備好才加聲調",
            "base": "沿用昨天熟悉的基本音節，以手勢路徑示範一個聲調；先把拼讀與聽聲調分開。",
            "stretch": "在同一音節比較兩個聲調；兩項任務開始讓注意力過載就停止。",
        },
        {
            "day": "第 13 天",
            "focus": "在真實閱讀中看見注音",
            "base": "使用家中合法購買、借閱或授權取得的注音讀物，讓孩子選一頁，只注意一個熟悉符號。",
            "stretch": "以理解內容為主；孩子想再看時，才指一個短短的注音標示。",
        },
        {
            "day": "第 14 天",
            "focus": "讓孩子帶領收尾",
            "base": "孩子從日曆選一個最喜歡的活動，重複一次，在互動仍自在時結束。",
            "stretch": "選一個中性的下一步：重複、休息、詢問學校或再探索一小組，不替孩子分級。",
        },
    ),
    "zh-Hans": (
        {
            "day": "第 1 天",
            "focus": "选一条温和起点",
            "base": "完全没接触过注音时，打开教育部官方符号表，只选两至三个符号。大人示范一次，孩子只听也算参与。",
            "stretch": "孩子以前见过注音时，可使用一次免费 3 分钟观察指南，只用来选起点，不产生分数。",
        },
        {
            "day": "第 2 天",
            "focus": "先听，再指",
            "base": "一次说出或播放一个选定符号的声音，共三个。孩子可以指、看、模仿手势或只听。",
            "stretch": "混合四至六个熟悉符号，让孩子选下一个由大人示范的符号。",
        },
        {
            "day": "第 3 天",
            "focus": "不计时配对形状",
            "base": "在废纸上把每个选定符号各写两张，全部翻开，将相同形状配在一起。",
            "stretch": "加入一组外形相近的符号，只谈一个看得见的差异，不说哪个答案错了。",
        },
        {
            "day": "第 4 天",
            "focus": "描一个官方字形",
            "base": "查看教育部官方笔顺，示范一至两个符号的空中笔画；孩子可空写、手指描或观看。",
            "stretch": "把同一个熟悉符号在纸上描一次；整齐还没变成目标前就停止。",
        },
        {
            "day": "第 5 天",
            "focus": "把一个声音连到家庭生活",
            "base": "选一个熟悉的华语口语词，搭配合法授权的参考资料，注意其中一个注音。",
            "stretch": "再找一个含相同声音的家庭词语；对话比记住答案重要。",
        },
        {
            "day": "第 6 天",
            "focus": "用动作感受一组声调",
            "base": "使用一个熟悉的口语音节，大人用手势路径示范两个声调；孩子可动作、聆听或模仿。",
            "stretch": "只有孩子仍感到自在时，才把同一个音节试到最多四个声调。",
        },
        {
            "day": "第 7 天",
            "focus": "由孩子选择重复",
            "base": "把第 2 至 6 天的活动列出来，让孩子选一个；今天不增加新符号。",
            "stretch": "让孩子担任出题、选卡或动作带领者，不公开纠正。",
        },
        {
            "day": "第 8 天",
            "focus": "认识第二小组符号",
            "base": "从官方符号表另选两至三个符号，像第 2 天一样示范、指认与动作。",
            "stretch": "把新符号与两个熟悉符号混合，分成「以前见过」与「今天新见」。",
        },
        {
            "day": "第 9 天",
            "focus": "注意一组相近字形",
            "base": "把一组外形相近的符号并排，说出或描出让两个形状不同的特征。",
            "stretch": "把两个符号放进小型配对或指认游戏，不做计时回合。",
        },
        {
            "day": "第 10 天",
            "focus": "再次查看笔顺",
            "base": "使用官方笔顺参考一个选定符号；慢慢示范，再邀请孩子空写或纸上描一次。",
            "stretch": "只比较孩子自己的两次动作来观察路径，不评分整齐度。",
        },
        {
            "day": "第 11 天",
            "focus": "听一组二拼",
            "base": "依合法授权的示范，使用两个熟悉符号，先慢慢分开说，再连起来；孩子只听也可以。",
            "stretch": "准备好时，让孩子把两张纸卡滑近并连音，不使用计时器。",
        },
        {
            "day": "第 12 天",
            "focus": "准备好才加声调",
            "base": "沿用昨天熟悉的基本音节，以手势路径示范一个声调；先把拼读与听声调分开。",
            "stretch": "在同一音节比较两个声调；两项任务开始让注意力过载就停止。",
        },
        {
            "day": "第 13 天",
            "focus": "在真实阅读中看见注音",
            "base": "使用家中合法购买、借阅或授权取得的注音读物，让孩子选一页，只注意一个熟悉符号。",
            "stretch": "以理解内容为主；孩子想再看时，才指一个短短的注音标示。",
        },
        {
            "day": "第 14 天",
            "focus": "让孩子带领收尾",
            "base": "孩子从日历选一个最喜欢的活动，重复一次，在互动仍自在时结束。",
            "stretch": "选一个中性的下一步：重复、休息、询问学校或再探索一小组，不替孩子分级。",
        },
    ),
    "ja": (
        {
            "day": "1日目",
            "focus": "やさしいスタートを選ぶ",
            "base": "注音符号にまったく触れたことがない場合は、公式の符号表を開いて2〜3個だけ選びましょう。大人が一度お手本を見せるだけでよく、聞くだけでも参加になります。",
            "stretch": "注音符号に触れたことがある場合は、無料の3分観察ガイドを一度使って、点数をつけるためではなく、始めるレーンを選ぶために活用しましょう。",
        },
        {
            "day": "2日目",
            "focus": "聞いてから指さす",
            "base": "選んだ符号の音を1つずつ、合計3つ言うか再生します。子どもは指さす、見る、身振りをまねる、あるいはただ聞くだけでも構いません。",
            "stretch": "すでに慣れている符号を4〜6個混ぜて、次に大人がお手本を見せる符号を子どもに選ばせましょう。",
        },
        {
            "day": "3日目",
            "focus": "急がずに形を合わせる",
            "base": "選んだ符号をそれぞれ2枚ずつ、いらない紙に書きます。すべて表向きにして、同じ形同士を合わせましょう。",
            "stretch": "形が似ているペアを1組加え、見た目の違いを1つだけ話します。どちらが正解かは言わないようにしましょう。",
        },
        {
            "day": "4日目",
            "focus": "公式の字形を1つなぞる",
            "base": "教育部の筆順資料を確認し、1〜2個の符号を空中でお手本として示します。子どもは空書き、指なぞり、または見るだけでも構いません。",
            "stretch": "同じ慣れた符号を紙に1回なぞります。きれいに書くことが目的にならないうちにやめましょう。",
        },
        {
            "day": "5日目",
            "focus": "音を家庭生活とつなげる",
            "base": "よく使う話し言葉の単語を1つ選び、正規の資料を使ってその中の注音符号を1つ見つけます。",
            "stretch": "同じ音を含む家庭の言葉をもう1つ見つけましょう。答えを覚えることより会話が大切です。",
        },
        {
            "day": "6日目",
            "focus": "声調の違いを動きで感じる",
            "base": "慣れている話し言葉の音節を1つ使い、大人が手の動きで2つの声調を示します。子どもは動く、聞く、まねるだけでも構いません。",
            "stretch": "子どもが心地よく感じている場合のみ、同じ音節で声調を最大4つまで試してみましょう。",
        },
        {
            "day": "7日目",
            "focus": "子どもが選んで繰り返す",
            "base": "2日目から6日目までの活動を並べて、子どもに1つ選ばせます。今日は新しい符号を増やしません。",
            "stretch": "子どもに出題係、カード選び係、動きのリーダー役を任せ、人前で訂正しないようにしましょう。",
        },
        {
            "day": "8日目",
            "focus": "2つ目の小さなセットに出会う",
            "base": "公式の符号表から別の2〜3個の符号を選び、2日目と同じようにお手本を示し、指さし、動きを行います。",
            "stretch": "新しい符号を慣れた符号2個と混ぜ、「前に見たもの」と「今日初めて見たもの」に分けましょう。",
        },
        {
            "day": "9日目",
            "focus": "似ている符号のペアに気づく",
            "base": "形が似ている符号のペアを1組並べ、2つの形の違いとなる部分を言葉にするか、なぞって示します。",
            "stretch": "それぞれの符号を小さな神経衰弱や指さしゲームに加えましょう。時間を計るラウンドは避けます。",
        },
        {
            "day": "10日目",
            "focus": "もう一度筆順を見る",
            "base": "選んだ符号1つの公式筆順資料を使います。ゆっくりお手本を示し、そのあと空書きか紙へのなぞり書きに誘いましょう。",
            "stretch": "子ども自身の2回の書き方だけを比べて動きに気づき、きれいさを評価しないようにしましょう。",
        },
        {
            "day": "11日目",
            "focus": "2つの音の組み合わせを聞く",
            "base": "正規のお手本にならい、慣れた符号2つを使って、ゆっくり分けて言ってからつなげます。子どもは聞くだけでも構いません。",
            "stretch": "準備ができていれば、紙のカード2枚を近づけながら音をつなげてみましょう。タイマーは使いません。",
        },
        {
            "day": "12日目",
            "focus": "準備ができてから声調を加える",
            "base": "昨日使った慣れた基本音節をそのまま使い、手の動きで声調を1つ示します。まずは音をつなげる練習と声調を聞く練習を分けましょう。",
            "stretch": "同じ音節で2つの声調を比べます。2つの課題で注意が散漫になり始めたらやめましょう。",
        },
        {
            "day": "13日目",
            "focus": "実際の読書の中で注音に気づく",
            "base": "家庭で合法的に購入・借用・許諾された注音付きの本を1冊使い、子どもに1ページ選ばせ、慣れた符号を1つだけ見つけます。",
            "stretch": "内容を理解することを中心にし、子どもがもう一度見たいと言ったときだけ、短い注音の表記を1つ指し示しましょう。",
        },
        {
            "day": "14日目",
            "focus": "子どもに締めくくりを任せる",
            "base": "子どもがカレンダーの中から一番好きな活動を選び、もう一度行い、まだ心地よいうちに終わりにします。",
            "stretch": "次に取る中立的な一歩を1つ選びましょう：繰り返す、休む、学校に相談する、または別の小さなセットを試す。子どもにレベルをつけないようにします。",
        },
    ),
    "ko": (
        {
            "day": "1일차",
            "focus": "부드러운 시작 방법 고르기",
            "base": "주음부호를 처음 접한다면 공식 기호표를 열어 두세 개만 골라 보세요. 어른이 한 번 시범을 보이면 되고, 아이는 듣기만 해도 참여한 것입니다.",
            "stretch": "아이가 주음부호를 전에 본 적이 있다면, 무료 3분 관찰 가이드를 한 번 사용해 점수를 매기기 위해서가 아니라 시작 단계를 정하기 위해 활용하세요.",
        },
        {
            "day": "2일차",
            "focus": "듣고 나서 가리키기",
            "base": "선택한 기호의 소리를 한 번에 하나씩, 총 세 개를 말하거나 재생하세요. 아이는 가리키거나, 보거나, 몸짓을 따라 하거나, 그냥 듣기만 해도 됩니다.",
            "stretch": "이미 익숙한 기호 네댓 개를 섞어서, 어른이 다음으로 시범을 보일 기호를 아이가 고르게 하세요.",
        },
        {
            "day": "3일차",
            "focus": "속도 없이 모양 맞추기",
            "base": "이면지에 선택한 기호를 각각 두 장씩 씁니다. 모두 뒤집어 놓고 같은 모양끼리 짝을 맞추세요.",
            "stretch": "모양이 비슷한 한 쌍을 추가하고, 눈에 보이는 차이 한 가지만 이야기하세요. 어느 쪽이 틀렸는지는 말하지 않습니다.",
        },
        {
            "day": "4일차",
            "focus": "공식 글자 모양 따라 쓰기",
            "base": "교육부 공식 필순 자료를 확인하고, 기호 한두 개를 허공에 시범으로 보여 주세요. 아이는 허공 쓰기, 손가락 따라 쓰기, 혹은 지켜보기만 해도 됩니다.",
            "stretch": "같은 익숙한 기호를 종이에 한 번 따라 써 보세요. 글씨가 반듯한 것이 목표가 되기 전에 멈추세요.",
        },
        {
            "day": "5일차",
            "focus": "소리 하나를 가정생활과 연결하기",
            "base": "익숙한 구어 단어를 하나 고르고, 공인된 자료를 사용해 그 안의 주음부호 하나를 찾아보세요.",
            "stretch": "같은 소리가 들어간 가족 단어를 하나 더 찾아보세요. 정답을 외우는 것보다 대화가 더 중요합니다.",
        },
        {
            "day": "6일차",
            "focus": "성조 대비를 동작으로 느끼기",
            "base": "익숙한 구어 음절 하나를 사용해 어른이 손동작으로 두 가지 성조를 시범 보이세요. 아이는 움직이거나, 듣거나, 따라 해도 됩니다.",
            "stretch": "아이가 여전히 편안해할 때만, 같은 음절로 성조를 최대 네 가지까지 시도해 보세요.",
        },
        {
            "day": "7일차",
            "focus": "아이가 골라서 반복하기",
            "base": "2일차부터 6일차까지의 활동을 늘어놓고 아이가 하나를 고르게 하세요. 오늘은 새 기호를 추가하지 않습니다.",
            "stretch": "아이에게 문제 내는 역할, 카드 고르는 역할, 동작 이끄는 역할을 맡기고 공개적으로 고쳐 주지 마세요.",
        },
        {
            "day": "8일차",
            "focus": "두 번째 작은 세트 만나기",
            "base": "공식 기호표에서 다른 두세 개 기호를 골라, 2일차와 같은 방식으로 시범, 가리키기, 동작을 진행하세요.",
            "stretch": "새 기호를 익숙한 기호 두 개와 섞어서 '전에 본 것'과 '오늘 새로 본 것'으로 나눠 보세요.",
        },
        {
            "day": "9일차",
            "focus": "비슷하게 생긴 한 쌍 알아차리기",
            "base": "모양이 비슷한 기호 한 쌍을 나란히 놓고, 두 모양을 다르게 만드는 특징을 말하거나 따라 그리세요.",
            "stretch": "각 기호를 작은 짝맞추기나 가리키기 게임에 넣어 보세요. 시간을 재는 라운드는 피하세요.",
        },
        {
            "day": "10일차",
            "focus": "필순을 다시 살펴보기",
            "base": "선택한 기호 하나의 공식 필순 자료를 사용하세요. 천천히 시범을 보인 뒤, 허공 쓰기나 종이 따라 쓰기를 한 번 권해 보세요.",
            "stretch": "아이 자신의 두 번 시도만 비교해 움직임을 살펴보고, 반듯함을 채점하지 마세요.",
        },
        {
            "day": "11일차",
            "focus": "두 부분으로 된 결합음 듣기",
            "base": "공인된 시범을 따라 익숙한 기호 두 개를 사용해, 천천히 나눠 말한 뒤 합쳐 보세요. 아이는 듣기만 해도 됩니다.",
            "stretch": "준비가 되었다면, 종이 카드 두 장을 가까이 밀며 소리를 합쳐 보세요. 타이머는 사용하지 않습니다.",
        },
        {
            "day": "12일차",
            "focus": "준비되었을 때만 성조 추가하기",
            "base": "어제 익숙해진 기본 음절을 그대로 사용해 손동작으로 성조 하나를 시범 보이세요. 결합 연습과 성조 듣기를 따로 유지하세요.",
            "stretch": "같은 음절로 성조 두 가지를 비교해 보세요. 두 가지 과제로 주의가 과부하되기 시작하면 멈추세요.",
        },
        {
            "day": "13일차",
            "focus": "실제 읽기 속에서 주음부호 알아차리기",
            "base": "집에 합법적으로 구매, 대여 또는 인가받은 주음 표기 도서 한 권을 사용해, 아이가 한 페이지를 고르게 하고 익숙한 기호 하나만 알아차리게 하세요.",
            "stretch": "내용을 이해하는 데 집중하고, 아이가 다시 보고 싶어 할 때만 짧은 주음 표기 하나를 가리키세요.",
        },
        {
            "day": "14일차",
            "focus": "마무리를 아이가 이끌게 하기",
            "base": "아이가 달력에서 가장 좋아하는 활동을 하나 골라 다시 해 보고, 아직 편안할 때 마무리하세요.",
            "stretch": "다음에 취할 중립적인 한 걸음을 고르세요: 반복하기, 쉬어 가기, 학교에 물어보기, 또는 다른 작은 세트 탐색하기. 아이에게 등급을 매기지 않습니다.",
        },
    ),
    "es-ES": (
        {
            "day": "Día 1",
            "focus": "Elige un comienzo suave",
            "base": "Si el Zhuyin es totalmente nuevo, abre la tabla oficial y elige solo dos o tres símbolos. El adulto hace de modelo una vez; escuchar ya cuenta como participar.",
            "stretch": "Si el niño ya ha visto el Zhuyin antes, usa una vez la guía gratuita de observación de 3 minutos para elegir el nivel de partida, no para obtener una puntuación.",
        },
        {
            "day": "Día 2",
            "focus": "Escuchar y luego señalar",
            "base": "Di o reproduce el sonido de tres símbolos elegidos, uno a la vez. El niño puede señalar, mirar, imitar un gesto o simplemente escuchar.",
            "stretch": "Mezcla de cuatro a seis símbolos ya conocidos y deja que el niño elija cuál modela el adulto a continuación.",
        },
        {
            "day": "Día 3",
            "focus": "Emparejar formas sin prisa",
            "base": "Escribe dos copias de cada símbolo elegido en papel de borrador. Vuélvelas boca arriba y empareja las formas iguales.",
            "stretch": "Añade un par de símbolos parecidos y comenta solo una diferencia visible, sin decir cuál es la respuesta incorrecta.",
        },
        {
            "day": "Día 4",
            "focus": "Trazar una forma oficial",
            "base": "Consulta la referencia oficial de trazos. Haz de modelo con uno o dos símbolos en el aire; el niño puede trazar en el aire, con el dedo o solo observar.",
            "stretch": "Traza los mismos símbolos conocidos una vez en papel, deteniéndote antes de que la pulcritud se convierta en el objetivo.",
        },
        {
            "day": "Día 5",
            "focus": "Conectar un sonido con la vida familiar",
            "base": "Elige una palabra hablada familiar y usa una referencia autorizada para identificar un símbolo Zhuyin dentro de ella.",
            "stretch": "Busca una segunda palabra familiar con el mismo sonido; la conversación importa más que memorizar.",
        },
        {
            "day": "Día 6",
            "focus": "Sentir un contraste de tonos con movimiento",
            "base": "Usa una sílaba hablada familiar. El adulto modela dos tonos con un gesto de la mano; el niño puede moverse, escuchar o imitar.",
            "stretch": "Prueba la misma sílaba base con hasta cuatro tonos solo si el niño sigue cómodo.",
        },
        {
            "day": "Día 7",
            "focus": "Repetir según elija el niño",
            "base": "Ofrece las actividades de los días 2 a 6 y deja que el niño elija una. No añadas ningún símbolo nuevo hoy.",
            "stretch": "Deja que el niño sea quien dicta, elige tarjetas o dirige el movimiento, sin corregirlo en público.",
        },
        {
            "day": "Día 8",
            "focus": "Conocer un segundo grupo pequeño",
            "base": "Elige dos o tres símbolos distintos de la tabla oficial. Modela, señala y muévete igual que el día 2.",
            "stretch": "Mezcla el nuevo grupo con dos símbolos conocidos y clasifícalos en «visto antes» y «nuevo hoy».",
        },
        {
            "day": "Día 9",
            "focus": "Notar un par parecido",
            "base": "Coloca un par de símbolos parecidos uno junto al otro. Nombra o traza el rasgo que hace diferentes sus formas.",
            "stretch": "Añade cada símbolo a un pequeño juego de memoria o de señalar; evita las rondas cronometradas.",
        },
        {
            "day": "Día 10",
            "focus": "Volver al orden de los trazos",
            "base": "Usa la referencia oficial de trazos para un símbolo elegido. Modela despacio y luego invita a un trazo en el aire o en papel.",
            "stretch": "Compara solo los dos intentos propios del niño para observar el movimiento, sin calificar la pulcritud.",
        },
        {
            "day": "Día 11",
            "focus": "Escuchar una combinación de dos partes",
            "base": "Con dos símbolos familiares siguiendo un modelo autorizado, di las partes despacio y luego únelas. El niño puede solo escuchar.",
            "stretch": "Si está listo, deja que el niño deslice dos tarjetas de papel mientras une los sonidos, sin cronómetro.",
        },
        {
            "day": "Día 12",
            "focus": "Añadir un tono solo cuando esté listo",
            "base": "Reutiliza la sílaba base familiar de ayer y modela un tono con un gesto de la mano. Mantén separada la combinación de símbolos de la escucha de tonos.",
            "stretch": "Compara dos tonos en la misma sílaba; detente si las dos tareas empiezan a saturar la atención.",
        },
        {
            "day": "Día 13",
            "focus": "Notar el Zhuyin en una lectura real",
            "base": "Usa un libro anotado adquirido, prestado o autorizado legalmente. Deja que el niño elija una página y note un símbolo conocido.",
            "stretch": "Lee para comprender el significado y señala una anotación breve solo si el niño quiere volver a verla.",
        },
        {
            "day": "Día 14",
            "focus": "Dejar que el niño dirija el cierre",
            "base": "El niño elige su actividad favorita del calendario. Repítela y termina mientras la interacción siga siendo cómoda.",
            "stretch": "Elige un siguiente paso neutral: repetir, hacer una pausa, preguntar al colegio o explorar otro grupo pequeño, sin asignar un nivel.",
        },
    ),
    "pt-BR": (
        {
            "day": "Dia 1",
            "focus": "Escolha um começo tranquilo",
            "base": "Se o Zhuyin for totalmente novo, abra a tabela oficial e escolha só dois ou três símbolos. O adulto demonstra uma vez; ouvir já conta como participação.",
            "stretch": "Se a criança já viu o Zhuyin antes, use uma vez o guia gratuito de observação de 3 minutos apenas para escolher o ponto de partida, não para gerar uma nota.",
        },
        {
            "day": "Dia 2",
            "focus": "Ouvir e depois apontar",
            "base": "Diga ou reproduza o som de três símbolos escolhidos, um de cada vez. A criança pode apontar, olhar, imitar um gesto ou simplesmente ouvir.",
            "stretch": "Misture de quatro a seis símbolos já conhecidos e deixe a criança escolher qual o adulto demonstra em seguida.",
        },
        {
            "day": "Dia 3",
            "focus": "Combinar formas sem pressa",
            "base": "Escreva duas cópias de cada símbolo escolhido em papel de rascunho. Vire todas para cima e junte as formas iguais.",
            "stretch": "Acrescente um par de símbolos parecidos e converse sobre apenas uma diferença visível, sem dizer qual resposta está errada.",
        },
        {
            "day": "Dia 4",
            "focus": "Traçar uma forma oficial",
            "base": "Consulte a referência oficial de traços. Demonstre um ou dois símbolos no ar; a criança pode traçar no ar, com o dedo ou apenas observar.",
            "stretch": "Trace os mesmos símbolos conhecidos uma vez no papel, parando antes que a letra bonita vire o objetivo.",
        },
        {
            "day": "Dia 5",
            "focus": "Conectar um som à vida em família",
            "base": "Escolha uma palavra falada familiar e use uma referência autorizada para notar um símbolo Zhuyin dentro dela.",
            "stretch": "Encontre uma segunda palavra da família com o mesmo som; a conversa importa mais do que decorar a resposta.",
        },
        {
            "day": "Dia 6",
            "focus": "Sentir um contraste de tons com movimento",
            "base": "Use uma sílaba falada familiar. O adulto demonstra dois tons com um gesto da mão; a criança pode se mover, ouvir ou imitar.",
            "stretch": "Experimente a mesma sílaba base com até quatro tons, só se a criança continuar confortável.",
        },
        {
            "day": "Dia 7",
            "focus": "Repetir por escolha da criança",
            "base": "Ofereça as atividades dos dias 2 a 6 e deixe a criança escolher uma. Não acrescente nenhum símbolo novo hoje.",
            "stretch": "Deixe a criança ser quem chama, escolhe as cartas ou lidera o movimento, sem corrigir em público.",
        },
        {
            "day": "Dia 8",
            "focus": "Conhecer um segundo grupo pequeno",
            "base": "Escolha dois ou três símbolos diferentes da tabela oficial. Demonstre, aponte e se mova exatamente como no dia 2.",
            "stretch": "Misture o novo grupo com dois símbolos conhecidos e separe em «já visto» e «novo hoje».",
        },
        {
            "day": "Dia 9",
            "focus": "Notar um par parecido",
            "base": "Coloque um par de símbolos parecidos lado a lado. Nomeie ou trace o traço que torna as formas diferentes.",
            "stretch": "Acrescente cada símbolo a um pequeno jogo de memória ou de apontar; evite rodadas cronometradas.",
        },
        {
            "day": "Dia 10",
            "focus": "Voltar à ordem dos traços",
            "base": "Use a referência oficial de traços para um símbolo escolhido. Demonstre devagar e depois convide para um traço no ar ou no papel.",
            "stretch": "Compare apenas as duas tentativas da própria criança para notar o movimento, sem avaliar a letra bonita.",
        },
        {
            "day": "Dia 11",
            "focus": "Ouvir uma combinação de duas partes",
            "base": "Com dois símbolos familiares seguindo um modelo autorizado, diga as partes devagar e depois junte-as. A criança pode apenas ouvir.",
            "stretch": "Se estiver pronta, deixe a criança deslizar duas cartas de papel juntando os sons, sem cronômetro.",
        },
        {
            "day": "Dia 12",
            "focus": "Acrescentar um tom só quando estiver pronto",
            "base": "Reaproveite a sílaba base familiar de ontem e demonstre um tom com um gesto da mão. Mantenha separadas a combinação de símbolos e a escuta de tons.",
            "stretch": "Compare dois tons na mesma sílaba; pare se as duas tarefas começarem a sobrecarregar a atenção.",
        },
        {
            "day": "Dia 13",
            "focus": "Notar o Zhuyin numa leitura real",
            "base": "Use um livro anotado comprado, emprestado ou autorizado legalmente. Deixe a criança escolher uma página e notar um símbolo conhecido.",
            "stretch": "Leia focando no significado e aponte uma anotação curta só se a criança quiser revê-la.",
        },
        {
            "day": "Dia 14",
            "focus": "Deixar a criança conduzir o encerramento",
            "base": "A criança escolhe sua atividade favorita do calendário. Repita-a e termine enquanto a interação ainda estiver confortável.",
            "stretch": "Escolha um próximo passo neutro: repetir, pausar, perguntar à escola ou explorar outro grupo pequeno, sem atribuir um nível.",
        },
    ),
    "de-DE": (
        {
            "day": "Tag 1",
            "focus": "Einen sanften Einstieg wählen",
            "base": "Wenn Zhuyin völlig neu ist, öffnen Sie die offizielle Zeichentabelle und wählen Sie nur zwei bis drei Zeichen aus. Der Erwachsene macht es einmal vor; Zuhören zählt bereits als Mitmachen.",
            "stretch": "Wenn das Kind Zhuyin schon einmal gesehen hat, nutzen Sie einmal den kostenlosen 3-Minuten-Beobachtungsleitfaden, um eine Einstiegsspur zu wählen \u2013 nicht, um eine Note zu erhalten.",
        },
        {
            "day": "Tag 2",
            "focus": "Erst hören, dann zeigen",
            "base": "Sprechen oder spielen Sie die Laute von drei ausgewählten Zeichen nacheinander ab. Das Kind darf zeigen, zusehen, eine Geste nachahmen oder einfach nur zuhören.",
            "stretch": "Mischen Sie vier bis sechs bereits vertraute Zeichen und lassen Sie das Kind wählen, welches der Erwachsene als Nächstes vorführt.",
        },
        {
            "day": "Tag 3",
            "focus": "Formen ohne Zeitdruck zuordnen",
            "base": "Schreiben Sie jedes ausgewählte Zeichen zweimal auf Schmierpapier. Drehen Sie alle nach oben und legen Sie gleiche Formen zusammen.",
            "stretch": "Fügen Sie ein Paar ähnlich aussehender Zeichen hinzu und sprechen Sie nur über einen sichtbaren Unterschied, ohne zu sagen, welche Antwort falsch ist.",
        },
        {
            "day": "Tag 4",
            "focus": "Eine offizielle Form nachzeichnen",
            "base": "Sehen Sie in der offiziellen Strichfolge-Referenz nach. Führen Sie ein oder zwei Zeichen in der Luft vor; das Kind darf in der Luft nachzeichnen, mit dem Finger nachfahren oder nur zusehen.",
            "stretch": "Zeichnen Sie dieselben vertrauten Zeichen einmal auf Papier nach und hören Sie auf, bevor Ordentlichkeit zum Ziel wird.",
        },
        {
            "day": "Tag 5",
            "focus": "Einen Laut mit dem Familienalltag verbinden",
            "base": "Wählen Sie ein vertrautes gesprochenes Mandarin-Wort und nutzen Sie eine autorisierte Referenz, um ein Zhuyin-Zeichen darin zu entdecken.",
            "stretch": "Finden Sie ein zweites Familienwort mit demselben Laut; das Gespräch zählt mehr als das Erinnern der Antwort.",
        },
        {
            "day": "Tag 6",
            "focus": "Einen Tonkontrast mit Bewegung erleben",
            "base": "Verwenden Sie eine vertraute gesprochene Silbe. Der Erwachsene führt zwei Töne mit einer Handbewegung vor; das Kind darf sich bewegen, zuhören oder nachahmen.",
            "stretch": "Probieren Sie dieselbe Grundsilbe mit bis zu vier Tönen aus, aber nur, solange das Kind sich wohlfühlt.",
        },
        {
            "day": "Tag 7",
            "focus": "Nach Wahl des Kindes wiederholen",
            "base": "Bieten Sie die Aktivitäten der Tage 2 bis 6 an und lassen Sie das Kind eine auswählen. Fügen Sie heute kein neues Zeichen hinzu.",
            "stretch": "Lassen Sie das Kind Ansager, Kartenwähler oder Bewegungsleiter sein, ohne es öffentlich zu korrigieren.",
        },
        {
            "day": "Tag 8",
            "focus": "Eine zweite kleine Gruppe kennenlernen",
            "base": "Wählen Sie zwei oder drei andere Zeichen aus der offiziellen Tabelle. Führen Sie vor, zeigen Sie und bewegen Sie sich genau wie an Tag 2.",
            "stretch": "Mischen Sie die neue Gruppe mit zwei vertrauten Zeichen und sortieren Sie sie in „schon gesehen“ und „heute neu“.",
        },
        {
            "day": "Tag 9",
            "focus": "Ein ähnlich aussehendes Paar bemerken",
            "base": "Legen Sie ein Paar ähnlich aussehender Zeichen nebeneinander. Benennen oder zeichnen Sie das Merkmal nach, das die Formen unterscheidet.",
            "stretch": "Nehmen Sie jedes Zeichen in ein kleines Zuordnungs- oder Zeigespiel auf; vermeiden Sie zeitgemessene Runden.",
        },
        {
            "day": "Tag 10",
            "focus": "Zur Strichfolge zurückkehren",
            "base": "Nutzen Sie die offizielle Strichfolge-Referenz für ein ausgewähltes Zeichen. Führen Sie es langsam vor und laden Sie dann zu einem Nachzeichnen in der Luft oder auf Papier ein.",
            "stretch": "Vergleichen Sie nur die beiden eigenen Versuche des Kindes, um die Bewegung zu beobachten \u2013 nicht, um die Ordentlichkeit zu bewerten.",
        },
        {
            "day": "Tag 11",
            "focus": "Eine zweiteilige Lautverbindung hören",
            "base": "Sprechen Sie mit zwei vertrauten Zeichen nach einer autorisierten Vorlage die Teile langsam aus und verbinden Sie sie dann. Das Kind darf nur zuhören.",
            "stretch": "Wenn es so weit ist, lassen Sie das Kind zwei Papierkarten zusammenschieben, während die Laute verbunden werden \u2013 ohne Timer.",
        },
        {
            "day": "Tag 12",
            "focus": "Einen Ton erst hinzufügen, wenn das Kind bereit ist",
            "base": "Verwenden Sie erneut die vertraute Grundsilbe von gestern und führen Sie einen Ton mit einer Handbewegung vor. Halten Sie das Verbinden der Laute und das Hören der Töne getrennt.",
            "stretch": "Vergleichen Sie zwei Töne auf derselben Silbe; hören Sie auf, wenn die beiden Aufgaben die Aufmerksamkeit zu überfordern beginnen.",
        },
        {
            "day": "Tag 13",
            "focus": "Zhuyin beim echten Lesen bemerken",
            "base": "Nutzen Sie ein legal gekauftes, ausgeliehenes oder autorisiertes Buch mit Zhuyin-Anmerkungen. Lassen Sie das Kind eine Seite wählen und ein vertrautes Zeichen bemerken.",
            "stretch": "Lesen Sie auf das Verständnis ausgerichtet und zeigen Sie nur dann auf eine kurze Anmerkung, wenn das Kind sie noch einmal sehen möchte.",
        },
        {
            "day": "Tag 14",
            "focus": "Das Kind den Abschluss gestalten lassen",
            "base": "Das Kind wählt seine Lieblingsaktivität aus dem Kalender. Wiederholen Sie sie und beenden Sie die Interaktion, solange sie noch angenehm ist.",
            "stretch": "Wählen Sie einen neutralen nächsten Schritt: wiederholen, pausieren, die Schule fragen oder eine weitere kleine Gruppe erkunden \u2013 ohne dem Kind ein Niveau zuzuweisen.",
        },
    ),
    "fr-FR": (
        {
            "day": "Jour 1",
            "focus": "Choisir un départ en douceur",
            "base": "Si le zhuyin est totalement nouveau, ouvrez le tableau officiel et ne choisissez que deux ou trois symboles. L'adulte montre une seule fois ; écouter compte déjà comme participer.",
            "stretch": "Si l'enfant a déjà vu le zhuyin, utilisez une fois le guide d'observation gratuit de 3 minutes pour choisir un niveau de départ, pas pour obtenir une note.",
        },
        {
            "day": "Jour 2",
            "focus": "Écouter, puis montrer du doigt",
            "base": "Dites ou faites entendre le son de trois symboles choisis, un par un. L'enfant peut montrer du doigt, regarder, imiter un geste ou simplement écouter.",
            "stretch": "Mélangez quatre à six symboles déjà familiers et laissez l'enfant choisir lequel l'adulte montrera ensuite.",
        },
        {
            "day": "Jour 3",
            "focus": "Associer les formes sans chronomètre",
            "base": "Écrivez deux copies de chaque symbole choisi sur du papier brouillon. Retournez-les face visible et associez les formes identiques.",
            "stretch": "Ajoutez une paire de symboles qui se ressemblent et ne parlez que d'une seule différence visible, sans dire laquelle est la mauvaise réponse.",
        },
        {
            "day": "Jour 4",
            "focus": "Tracer une forme officielle",
            "base": "Consultez la référence officielle de l'ordre des traits. Montrez un ou deux symboles en l'air ; l'enfant peut tracer en l'air, suivre du doigt ou simplement regarder.",
            "stretch": "Tracez les mêmes symboles familiers une fois sur papier, en s'arrêtant avant que la netteté ne devienne l'objectif.",
        },
        {
            "day": "Jour 5",
            "focus": "Relier un son à la vie de famille",
            "base": "Choisissez un mot parlé familier et utilisez une référence autorisée pour repérer un symbole zhuyin qu'il contient.",
            "stretch": "Trouvez un deuxième mot de la famille avec le même son ; la conversation compte plus que de retenir la réponse.",
        },
        {
            "day": "Jour 6",
            "focus": "Ressentir un contraste de tons par le mouvement",
            "base": "Utilisez une syllabe parlée familière. L'adulte montre deux tons avec un geste de la main ; l'enfant peut bouger, écouter ou imiter.",
            "stretch": "Essayez la même syllabe de base avec jusqu'à quatre tons, mais seulement si l'enfant reste à l'aise.",
        },
        {
            "day": "Jour 7",
            "focus": "Répéter selon le choix de l'enfant",
            "base": "Proposez les activités des jours 2 à 6 et laissez l'enfant en choisir une. N'ajoutez aucun nouveau symbole aujourd'hui.",
            "stretch": "Laissez l'enfant être celui qui appelle, choisit les cartes ou mène le mouvement, sans le corriger en public.",
        },
        {
            "day": "Jour 8",
            "focus": "Découvrir un deuxième petit groupe",
            "base": "Choisissez deux ou trois symboles différents du tableau officiel. Montrez, désignez et bougez exactement comme au jour 2.",
            "stretch": "Mélangez le nouveau groupe avec deux symboles familiers et triez-les en « déjà vus » et « nouveaux aujourd'hui ».",
        },
        {
            "day": "Jour 9",
            "focus": "Remarquer une paire qui se ressemble",
            "base": "Placez côte à côte une paire de symboles qui se ressemblent. Nommez ou tracez le trait qui rend leurs formes différentes.",
            "stretch": "Ajoutez chaque symbole à un petit jeu de mémoire ou de pointage ; évitez les manches chronométrées.",
        },
        {
            "day": "Jour 10",
            "focus": "Revenir à l'ordre des traits",
            "base": "Utilisez la référence officielle de l'ordre des traits pour un symbole choisi. Montrez lentement, puis invitez à un tracé en l'air ou sur papier.",
            "stretch": "Comparez seulement les deux essais de l'enfant lui-même pour observer le mouvement, sans noter la netteté.",
        },
        {
            "day": "Jour 11",
            "focus": "Écouter une combinaison en deux parties",
            "base": "Avec deux symboles familiers suivant un modèle autorisé, dites les parties lentement puis assemblez-les. L'enfant peut se contenter d'écouter.",
            "stretch": "Si l'enfant est prêt, laissez-le faire glisser deux cartes en papier l'une vers l'autre en assemblant les sons, sans chronomètre.",
        },
        {
            "day": "Jour 12",
            "focus": "Ajouter un ton seulement quand l'enfant est prêt",
            "base": "Réutilisez la syllabe de base familière d'hier et montrez un ton avec un geste de la main. Gardez séparés l'assemblage des sons et l'écoute des tons.",
            "stretch": "Comparez deux tons sur la même syllabe ; arrêtez si les deux tâches commencent à surcharger l'attention.",
        },
        {
            "day": "Jour 13",
            "focus": "Remarquer le zhuyin dans une vraie lecture",
            "base": "Utilisez un livre annoté acheté, emprunté ou autorisé légalement. Laissez l'enfant choisir une page et remarquer un symbole familier.",
            "stretch": "Lisez pour le sens, puis montrez une courte annotation seulement si l'enfant veut y revenir.",
        },
        {
            "day": "Jour 14",
            "focus": "Laisser l'enfant mener la conclusion",
            "base": "L'enfant choisit son activité préférée du calendrier. Refaites-la et arrêtez pendant que l'échange reste agréable.",
            "stretch": "Choisissez une prochaine étape neutre : répéter, faire une pause, demander à l'école ou explorer un autre petit groupe, sans attribuer de niveau à l'enfant.",
        },
    ),
}


def validate_days() -> None:
    if set(DAYS) != set(ALT_LOCALES):
        raise ValueError("DAYS locales must match ALT_LOCALES exactly")
    for locale, entries in DAYS.items():
        if len(entries) != DAY_MAX:
            raise ValueError(f"{locale} must define exactly {DAY_MAX} days")
        for index, entry in enumerate(entries, 1):
            for key in ("day", "focus", "base", "stretch"):
                if not entry.get(key):
                    raise ValueError(f"{locale} day {index} is missing '{key}'")


validate_days()


def build_day_plan(locale: str, day: int, lane: str) -> dict[str, object]:
    """Return the fixed, deterministic day plan for locale/day/lane.

    Only integer day (1..14) and lane ('base'|'stretch') select already
    embedded static content; there is no randomness and booleans are
    rejected as invalid integers.
    """
    if not isinstance(locale, str):
        raise TypeError("locale must be a string")
    if locale not in DAYS:
        raise ValueError(f"unsupported locale: {locale}")
    if not isinstance(day, int) or isinstance(day, bool):
        raise TypeError("day must be an integer")
    if not isinstance(lane, str):
        raise TypeError("lane must be a string")
    if day < DAY_MIN or day > DAY_MAX:
        raise ValueError("unsupported day")
    if lane not in LANE_VALUES:
        raise ValueError("unsupported lane")
    entry = DAYS[locale][day - 1]
    return {
        "selected_inputs": {"day": day, "lane": lane},
        "day_label": entry["day"],
        "focus": entry["focus"],
        "instruction": entry[lane],
    }


RELATED_LABELS = {
    "en": (
        "Printable Bopomofo Practice Sheets",
        "Printable Bopomofo Flashcards",
        "Printable Bopomofo Bingo Cards",
        "Private Bopomofo Matching-Pair Cut Cards",
        "Private Bopomofo Symbol Contrast Cards",
    ),
    "zh-Hant": (
        "可列印注音符號描寫練習表",
        "可列印注音符號字卡",
        "可列印注音賓果卡",
        "私人注音配對卡產生器",
        "私人注音符號對比練習卡",
    ),
    "zh-Hans": (
        "可打印注音符号描写练习表",
        "可打印注音符号卡片",
        "可打印注音符号宾果卡",
        "私人注音配对卡生成器",
        "私人注音符号对比练习卡",
    ),
    "ja": (
        "印刷用・注音符号なぞり書き練習シート",
        "印刷用・注音符号フラッシュカード",
        "注音符号ビンゴカード作成・印刷",
        "非公開ボポモフォ神経衰弱カード生成",
        "プライベートな注音記号対比カード",
    ),
    "ko": (
        "인쇄용 주음부호 따라 쓰기 연습지",
        "인쇄용 주음부호 플래시카드",
        "인쇄용 주음부호 빙고 카드",
        "비공개 주음부호 짝맞추기 카드 생성기",
        "개인용 주음부호 대비 카드",
    ),
    "es-ES": (
        "Fichas Bopomofo para imprimir",
        "Tarjetas Bopomofo para imprimir",
        "Cartones de bingo Bopomofo para imprimir",
        "Tarjetas privadas de parejas Bopomofo para recortar",
        "Tarjetas privadas de contraste de símbolos Bopomofo",
    ),
    "pt-BR": (
        "Folhas Bopomofo para imprimir",
        "Cartões Bopomofo para imprimir",
        "Cartelas de bingo Bopomofo para imprimir",
        "Cartas privadas de pares Bopomofo para recortar",
        "Cartões privados de contraste de símbolos Bopomofo",
    ),
    "de-DE": (
        "Bopomofo-Übungsblätter zum Ausdrucken",
        "Bopomofo-Lernkarten zum Ausdrucken",
        "Bopomofo-Bingokarten zum Ausdrucken",
        "Private Bopomofo Karten für Paarzuordnung zum Ausschneiden",
        "Private Bopomofo-Symbolkontrast-Karten",
    ),
    "fr-FR": (
        "Fiches Bopomofo à imprimer",
        "Cartes mémo Bopomofo à imprimer",
        "Grilles de bingo Bopomofo à imprimer",
        "Cartes privées de paires Bopomofo à découper",
        "Cartes privées de contraste de symboles Bopomofo",
    ),
}


COPY = {
    "en": {
        "title": "Free 14-Day Grade 1 Zhuyin Summer Warm-Up Calendar",
        "description": (
            "A free, print-ready 14-day Zhuyin summer warm-up with 8-10 minute "
            "family activities. No score, no login, no readiness claim."
        ),
        "eyebrow": "Free summer family calendar · no login",
        "lead": (
            "Build familiarity before school without turning summer into a test. "
            "Choose a starting lane, keep each day under ten minutes and stop early when needed."
        ),
        "badges": (
            "14 days · 8-10 minutes each",
            "No score, diagnosis or saved child data",
            "Original family activity, not an official curriculum",
        ),
        "start": "Open the 14-day calendar",
        "switch": "繁體中文",
        "boundary": "Warm-up, not an entrance requirement",
        "boundary_text": (
            "This optional calendar does not set a Grade 1 prerequisite. It does not "
            "teach or assess all 37 symbols, assign a level or predict school performance. "
            "Schools differ; ask the child's school about its actual first-term plan."
        ),
        "lanes": "Choose one starting lane",
        "lane_intro": (
            "Use the lightest lane that fits today. Move between lanes freely; no child "
            "needs to complete a lane or catch up to the calendar."
        ),
        "lane_items": (
            (
                "Completely new",
                "Use two or three symbols. The adult models; listening, watching or stopping all count.",
            ),
            (
                "Recognises some",
                "Use four to six symbols the child has already seen for pointing, matching and movement.",
            ),
            (
                "Ready to combine",
                "Use two familiar two-part blends without speed, ranking or handwriting pressure.",
            ),
        ),
        "routine": "The same 8-10 minute rhythm",
        "routine_items": (
            "1 minute · child chooses the lane or material",
            "2 minutes · adult models once; do not quiz first",
            "3 minutes · point, match, move or listen",
            "2 minutes · connect to paper, a family word or an authorized book",
            "1-2 minutes · name one effort and stop",
        ),
        "calendar": "Fourteen-day printable calendar",
        "base_label": "Gentle route",
        "stretch_label": "Only if already comfortable",
        "print": "Print the calendar",
        "share": "Share tool",
        "share_title": "Free 14-day Grade 1 Zhuyin summer warm-up calendar",
        "shared": "Tool link copied.",
        "cancelled": "Sharing was cancelled.",
        "copied": "Tool link copied.",
        "copy_failed": "Copy was unavailable. Use this link:",
        "lookup": "Look up any single day",
        "day_field_label": "Day",
        "lane_field_label": "Lane",
        "show_day": "Show this day",
        "invalid_input": "Choose a day from 1-14 and a lane.",
        "privacy": "No completion tracking",
        "privacy_text": (
            "There is no child-name field, date field, checkbox tracker, account, "
            "form submission, camera, microphone, upload, analytics input, local "
            "storage or saved profile. The page receives no answers or activity history."
        ),
        "evidence": "What the official sources do-and do not-show",
        "evidence_text": (
            "Taiwan Ministry of Education references establish standard Zhuyin forms, "
            "notation and stroke order. They do not prescribe or endorse this calendar. "
            "This original 14-day sequence has not been evaluated in a study and cannot "
            "show that a child is ready for school, will learn faster or will earn a "
            "particular result. Fourteen days is a bounded family routine, not a mastery timeline."
        ),
        "sources": "Official references",
        "source_labels": (
            "Taiwan Ministry of Education Bopomofo Handbook",
            "Taiwan Ministry of Education Zhuyin Stroke Order",
        ),
        "reuse": "Reuse the original calendar",
        "reuse_text": (
            "Families, libraries and heritage schools may print or adapt this original "
            "calendar under CC BY 4.0 with credit to iOS App Guide and a link to this page. "
            "The license does not cover Ministry materials, books or other external sources."
        ),
        "app_title": "Optional practice inside a chosen day",
        "app_text": (
            "The complete calendar works with paper, official references and an authorized "
            "book. If a family wants guided listening, tracing, tone or blending practice, "
            "Lumi Bopomofo covers all 37 symbols. It uses a one-time lifetime unlock with no "
            "ads, subscription or account."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "related": "Related free resources",
        "faq": "Parent FAQ",
        "faq_items": (
            (
                "Must a child know Zhuyin before Grade 1?",
                "This calendar sets no entrance requirement. Ask the child's school about its teaching plan and use this only as an optional familiarity routine.",
            ),
            (
                "Will fourteen days teach all 37 symbols?",
                "No. It samples listening, shape, stroke, tone, blending and reading interactions. Repeat, pause or continue later without assigning a level.",
            ),
            (
                "What if the child uses little spoken Mandarin?",
                "Treat oral language as a separate need. Pair Zhuyin with conversation and fluent speech; do not interpret slow symbol work as a diagnosis.",
            ),
            (
                "Is an app required?",
                "No. Paper, official references, adult modeling and a legally available annotated book are enough for the complete calendar.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": (
            "Independent family resource; not an official curriculum, entrance "
            "requirement, assessment, diagnosis or promise of school results."
        ),
        "index_title": "14-Day Grade 1 Zhuyin Summer Warm-Up Calendar",
        "index_description": (
            "A free, print-ready 14-day family calendar with no score, diagnosis or saved child data."
        ),
        "inline_link": "Open the free 14-day Grade 1 Zhuyin summer warm-up calendar",
        "webmcp_description": (
            "Return one fixed, already-published day's focus and instruction from the "
            "14-day Grade 1 Zhuyin summer warm-up calendar, selected only by day (1-14) "
            "and lane (base or stretch). Deterministic and read-only: accepts no child "
            "name, free text, file, recording, answer, score, or progress; is not an "
            "assessment, diagnosis, readiness check or learning-outcome claim."
        ),
    },
    "zh-Hant": {
        "title": "小一入學前 14 天注音暖身日曆｜免費可列印",
        "description": "免費、可列印的 14 天注音暑假暖身日曆：每天 8-10 分鐘、免登入、不評分、不診斷，也不把注音設為入學門檻。",
        "eyebrow": "免費暑假家庭日曆 · 免登入",
        "lead": "入學前先降低陌生感，不把暑假變成測驗。選一條適合今天的起點，每天不超過 10 分鐘，需要時提早停止。",
        "badges": ("14 天 · 每天 8-10 分鐘", "不評分、不診斷、不儲存孩子資料", "原創家庭活動，非官方課程"),
        "start": "開啟 14 天日曆",
        "switch": "English",
        "boundary": "只是暖身，不是入學門檻",
        "boundary_text": "這份選用日曆不替小一設定先備條件；它不教完或評量全部 37 個符號、不替孩子分級，也不預測學校表現。各校安排不同，請向孩子的學校確認實際開學教學計畫。",
        "lanes": "選一條起點",
        "lane_intro": "今天適合多輕就從多輕開始，可自由更換路線；孩子不需要完成某條路線，也不需要追趕日曆。",
        "lane_items": (
            ("完全沒接觸過", "只用兩至三個符號。大人示範；聆聽、觀看或停止都算參與。"),
            ("已認得一些", "使用孩子看過的四至六個符號，進行指認、配對與動作。"),
            ("準備開始組合", "使用兩組熟悉的二拼，不計速度、不排名，也不要求書寫整齊。"),
        ),
        "routine": "每天相同的 8-10 分鐘節奏",
        "routine_items": (
            "1 分鐘 · 孩子選路線或材料",
            "2 分鐘 · 大人示範一次，不先考問",
            "3 分鐘 · 指認、配對、動作或聆聽",
            "2 分鐘 · 連到紙張、家庭詞語或合法取得的書",
            "1-2 分鐘 · 說出一項努力並停止",
        ),
        "calendar": "14 天可列印日曆",
        "base_label": "溫和路線",
        "stretch_label": "已經自在才延伸",
        "print": "列印日曆",
        "share": "分享工具",
        "share_title": "免費小一入學前 14 天注音暖身日曆",
        "shared": "已複製工具連結。",
        "cancelled": "已取消分享。",
        "copied": "已複製工具連結。",
        "copy_failed": "無法複製，請使用此連結：",
        "lookup": "查詢單一天內容",
        "day_field_label": "天數",
        "lane_field_label": "路線",
        "show_day": "顯示這一天",
        "invalid_input": "請選擇 1-14 的天數與一條路線。",
        "privacy": "沒有完成度追蹤",
        "privacy_text": "沒有孩子姓名欄、日期欄、打卡追蹤、帳號、表單送出、相機、麥克風、上傳、分析輸入、local storage 或儲存檔案。本頁不接收答案或活動紀錄。",
        "evidence": "官方來源能說明什麼，不能說明什麼",
        "evidence_text": "台灣教育部資料提供標準注音字形、標示方式與筆順；並未制定或背書本日曆。這份原創 14 天流程尚未經研究評估，不能判定孩子是否準備好上學、能否學得更快或取得特定成果。14 天只是有邊界的家庭流程，不是精熟時程。",
        "sources": "官方參考",
        "source_labels": ("台灣教育部《國語注音符號手冊》", "台灣教育部注音符號筆順"),
        "reuse": "自由使用原創日曆",
        "reuse_text": "家庭、圖書館與海外中文學校可依 CC BY 4.0 列印或改編本原創日曆；請標註 iOS App Guide 並連回本頁。此授權不涵蓋教育部資料、書籍或其他外部來源。",
        "app_title": "選定活動中的選用練習",
        "app_text": "只用紙張、官方參考與合法取得的書，就能完整使用日曆。家庭若想在某一天加入有引導的聽音、描寫、聲調或拼讀練習，Lumi 注音星球涵蓋全部 37 個符號；採一次性永久解鎖，無廣告、免訂閱、免帳號。",
        "app_cta": "試用 Lumi 注音星球",
        "related": "相關免費資源",
        "faq": "家長常見問題",
        "faq_items": (
            ("孩子上小一前一定要會注音嗎？", "本日曆不設定入學門檻。請向孩子的學校確認教學安排，並只把這份日曆當成選用的熟悉流程。"),
            ("14 天能學完全部 37 個符號嗎？", "不能。它只取樣聽音、字形、筆順、聲調、拼讀與閱讀互動；可重複、暫停或日後延續，不替孩子分級。"),
            ("孩子平常很少說華語怎麼辦？", "把口語視為另一項需要；注音要搭配對話與流暢口語，不把符號學得慢解讀成診斷。"),
            ("一定要使用 App 嗎？", "不用。紙張、官方參考、大人示範與合法取得的注音讀物，就能完成整份日曆。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立家庭資源；不是官方課程、入學門檻、評量、診斷或學校成果保證。",
        "index_title": "小一入學前 14 天注音暖身日曆",
        "index_description": "免費、可列印的 14 天家庭日曆：不評分、不診斷、不儲存孩子資料。",
        "inline_link": "開啟免費小一入學前 14 天注音暖身日曆",
        "webmcp_description": (
            "只依天數（1-14）與路線（溫和或延伸）從小一 14 天注音暖身日曆中，"
            "回傳一則已公開、固定不變的當天重點與說明。具決定性且唯讀：不接收孩子姓名、"
            "自由輸入文字、檔案、錄音、答案、分數或進度；不是測驗、診斷、入學準備度判定"
            "或學習成果保證。"
        ),
    },
    "zh-Hans": {
        "title": "小一入学前 14 天注音暖身日历｜免费可打印",
        "description": "免费、可打印的 14 天注音暑假暖身日历：每天 8-10 分钟、免登录、不评分、不诊断，也不把注音设为入学门槛。",
        "eyebrow": "免费暑假家庭日历 · 免登录",
        "lead": "入学前先降低陌生感，不把暑假变成测验。选一条适合今天的起点，每天不超过 10 分钟，需要时提早停止。",
        "badges": ("14 天 · 每天 8-10 分钟", "不评分、不诊断、不储存孩子资料", "原创家庭活动，非官方课程"),
        "start": "开启 14 天日历",
        "switch": "English",
        "boundary": "只是暖身，不是入学门槛",
        "boundary_text": "这份选用日历不替小一设定先备条件；它不教完或评量全部 37 个符号、不替孩子分级，也不预测学校表现。各校安排不同，请向孩子的学校确认实际开学教学计划。",
        "lanes": "选一条起点",
        "lane_intro": "今天适合多轻就从多轻开始，可自由更换路线；孩子不需要完成某条路线，也不需要追赶日历。",
        "lane_items": (
            ("完全没接触过", "只用两至三个符号。大人示范；聆听、观看或停止都算参与。"),
            ("已认得一些", "使用孩子看过的四至六个符号，进行指认、配对与动作。"),
            ("准备开始组合", "使用两组熟悉的二拼，不计速度、不排名，也不要求书写整齐。"),
        ),
        "routine": "每天相同的 8-10 分钟节奏",
        "routine_items": (
            "1 分钟 · 孩子选路线或材料",
            "2 分钟 · 大人示范一次，不先考问",
            "3 分钟 · 指认、配对、动作或聆听",
            "2 分钟 · 连到纸张、家庭词语或合法取得的书",
            "1-2 分钟 · 说出一项努力并停止",
        ),
        "calendar": "14 天可打印日历",
        "base_label": "温和路线",
        "stretch_label": "已经自在才延伸",
        "print": "打印日历",
        "share": "分享工具",
        "share_title": "免费小一入学前 14 天注音暖身日历",
        "shared": "已复制工具链接。",
        "cancelled": "已取消分享。",
        "copied": "已复制工具链接。",
        "copy_failed": "无法复制，请使用此链接：",
        "lookup": "查询单一天内容",
        "day_field_label": "天数",
        "lane_field_label": "路线",
        "show_day": "显示这一天",
        "invalid_input": "请选择 1-14 的天数与一条路线。",
        "privacy": "没有完成度追踪",
        "privacy_text": "没有孩子姓名栏、日期栏、打卡追踪、账号、表单提交、相机、麦克风、上传、分析输入、local storage 或储存档案。本页不接收答案或活动记录。",
        "evidence": "官方来源能说明什么，不能说明什么",
        "evidence_text": "台湾教育部资料提供标准注音字形、标示方式与笔顺；并未制定或背书本日历。这份原创 14 天流程尚未经研究评估，不能判定孩子是否准备好上学、能否学得更快或取得特定成果。14 天只是有边界的家庭流程，不是精熟时程。",
        "sources": "官方参考",
        "source_labels": ("台湾教育部《国语注音符号手册》", "台湾教育部注音符号笔顺"),
        "reuse": "自由使用原创日历",
        "reuse_text": "家庭、图书馆与海外中文学校可依 CC BY 4.0 打印或改编本原创日历；请标注 iOS App Guide 并连回本页。此授权不涵盖教育部资料、书籍或其他外部来源。",
        "app_title": "选定活动中的选用练习",
        "app_text": "只用纸张、官方参考与合法取得的书，就能完整使用日历。家庭若想在某一天加入有引导的听音、描写、声调或拼读练习，Lumi 注音星球涵盖全部 37 个符号；采一次性永久解锁，无广告、免订阅、免账号。",
        "app_cta": "试用 Lumi 注音星球",
        "related": "相关免费资源",
        "faq": "家长常见问题",
        "faq_items": (
            ("孩子上小一前一定要会注音吗？", "本日历不设定入学门槛。请向孩子的学校确认教学安排，并只把这份日历当成选用的熟悉流程。"),
            ("14 天能学完全部 37 个符号吗？", "不能。它只取样听音、字形、笔顺、声调、拼读与阅读互动；可重复、暂停或日后延续，不替孩子分级。"),
            ("孩子平常很少说华语怎么办？", "把口语视为另一项需要；注音要搭配对话与流畅口语，不把符号学得慢解读成诊断。"),
            ("一定要使用 App 吗？", "不用。纸张、官方参考、大人示范与合法取得的注音读物，就能完成整份日历。"),
        ),
        "home": "首页",
        "tools": "免费工具",
        "footer": "独立家庭资源；不是官方课程、入学门槛、评量、诊断或学校成果保证。",
        "index_title": "小一入学前 14 天注音暖身日历",
        "index_description": "免费、可打印的 14 天家庭日历：不评分、不诊断、不储存孩子资料。",
        "inline_link": "开启免费小一入学前 14 天注音暖身日历",
        "webmcp_description": (
            "只依天数（1-14）与路线（温和或延伸）从小一 14 天注音暖身日历中，"
            "回传一则已公开、固定不变的当天重点与说明。具决定性且只读：不接收孩子姓名、"
            "自由输入文字、档案、录音、答案、分数或进度；不是测验、诊断、入学准备度判定"
            "或学习成果保证。"
        ),
    },
    "ja": {
        "title": "小学校入学前 14日間 注音符号サマー・ウォームアップカレンダー｜無料印刷用",
        "description": "無料で印刷できる14日間の注音符号サマー・ウォームアップカレンダー。1日8〜10分、ログイン不要、採点や診断は行いません。",
        "eyebrow": "無料の夏休み家族カレンダー・ログイン不要",
        "lead": "夏休みをテストに変えず、入学前に注音符号への親しみを育てましょう。今日に合ったレーンを選び、1日10分以内にとどめ、必要ならいつでも早めに切り上げてください。",
        "badges": ("14日間・1日8〜10分", "採点・診断・保存される子どものデータなし", "独自の家庭活動であり、公式カリキュラムではありません"),
        "start": "14日間カレンダーを開く",
        "switch": "繁體中文",
        "boundary": "ウォームアップであり、入学条件ではありません",
        "boundary_text": "この任意のカレンダーは小学校入学の前提条件を定めるものではありません。37個すべての符号を教えたり評価したりせず、レベル分けや学校での成績予測も行いません。学校ごとに方針は異なるため、実際の入学後の指導計画については学校にご確認ください。",
        "lanes": "スタートするレーンを1つ選ぶ",
        "lane_intro": "今日に合った、いちばん軽いレーンを使ってください。レーン間は自由に行き来でき、どのレーンも最後までやり切る必要はなく、カレンダーに追いつく必要もありません。",
        "lane_items": (
            ("まったく初めて", "符号を2〜3個だけ使います。大人がお手本を見せ、聞くだけ、見るだけ、途中でやめることもすべて参加として数えます。"),
            ("いくつか認識できる", "子どもがすでに見たことのある符号を4〜6個使い、指さし・マッチング・動きを行います。"),
            ("組み合わせる準備ができている", "慣れている二拼を2組使い、速さや順位、きれいな文字を求めません。"),
        ),
        "routine": "毎日同じ8〜10分のリズム",
        "routine_items": (
            "1分・子どもがレーンや教材を選ぶ",
            "2分・大人が一度お手本を示す（先にテストしない）",
            "3分・指さす、合わせる、動く、または聞く",
            "2分・紙、家庭の言葉、または正規の本とつなげる",
            "1〜2分・がんばったことを一つ言葉にして終える",
        ),
        "calendar": "14日間の印刷用カレンダー",
        "base_label": "やさしいルート",
        "stretch_label": "すでに慣れている場合のみ",
        "print": "カレンダーを印刷",
        "share": "ツールを共有",
        "share_title": "無料 小学校入学前 14日間 注音符号サマー・ウォームアップカレンダー",
        "shared": "ツールのリンクをコピーしました。",
        "cancelled": "共有はキャンセルされました。",
        "copied": "ツールのリンクをコピーしました。",
        "copy_failed": "コピーできませんでした。こちらのリンクをご利用ください：",
        "lookup": "1日分だけ確認する",
        "day_field_label": "日",
        "lane_field_label": "レーン",
        "show_day": "この日を表示",
        "invalid_input": "1〜14の日とレーンを選択してください。",
        "privacy": "達成度の記録はありません",
        "privacy_text": "子どもの氏名欄、日付欄、チェック式の進捗トラッカー、アカウント、フォーム送信、カメラ、マイク、アップロード、アナリティクス入力、ローカルストレージ、保存されるプロフィールは一切ありません。このページは回答も活動履歴も受け取りません。",
        "evidence": "公式情報源が示すこと・示さないこと",
        "evidence_text": "台湾教育部の資料は標準的な注音符号の字形、表記、筆順を定めるものであり、このカレンダーを規定したり推奨したりするものではありません。この独自の14日間の流れは研究による評価を受けておらず、子どもが入学準備できているか、より速く学べるか、特定の成果を得られるかを示すものではありません。14日間は熟達までの道のりではなく、範囲を区切った家庭の習慣です。",
        "sources": "公式参考資料",
        "source_labels": ("台湾教育部『国語注音符号手冊』", "台湾教育部 注音符号筆順"),
        "reuse": "この独自カレンダーを自由に活用する",
        "reuse_text": "ご家庭、図書館、継承語学校は、iOS App Guideのクレジット表記とこのページへのリンクを添えることで、CC BY 4.0のもとにこの独自カレンダーを印刷・改変できます。このライセンスは教育部の資料、書籍、その他の外部情報源には適用されません。",
        "app_title": "選んだ1日の中での任意の練習",
        "app_text": "紙、公式参考資料、正規に入手した本があれば、このカレンダーは完結します。ある1日にガイド付きの聞き取り・なぞり書き・声調・拼読練習を加えたいご家庭には、Lumi Bopomofoが全37符号をカバーします。買い切り型の永久アンロックで、広告・サブスクリプション・アカウントは不要です。",
        "app_cta": "Lumi Bopomofoを試す",
        "related": "関連する無料リソース",
        "faq": "保護者向けFAQ",
        "faq_items": (
            ("小学校入学前に注音符号を覚えていなければいけませんか？", "このカレンダーは入学条件を定めるものではありません。実際の指導計画については学校に確認し、これはあくまで任意の親しみづくりの習慣としてご利用ください。"),
            ("14日間で37個すべての符号を学べますか？", "いいえ。聞き取り、字形、筆順、声調、拼読、読書に関わる活動のごく一部を体験するものです。繰り返す、休む、後日続けるなど、レベル分けせずに進めてください。"),
            ("子どもが話し言葉の中国語をあまり話さない場合はどうすればよいですか？", "話し言葉は別の課題として扱ってください。注音符号は会話や流暢な発話と組み合わせ、符号の習得がゆっくりであることを診断だと解釈しないでください。"),
            ("アプリは必須ですか？", "いいえ。紙、公式参考資料、大人によるお手本、合法的に入手した注音付きの本があれば、このカレンダーは完結します。"),
        ),
        "home": "ホーム",
        "tools": "無料ツール",
        "footer": "独立した家庭向けリソースであり、公式カリキュラム、入学条件、評価、診断、学校での成果を保証するものではありません。",
        "index_title": "小学校入学前 14日間 注音符号サマー・ウォームアップカレンダー",
        "index_description": "無料で印刷できる14日間の家族カレンダー。採点・診断・保存される子どものデータはありません。",
        "inline_link": "無料の小学校入学前14日間 注音符号サマー・ウォームアップカレンダーを開く",
        "webmcp_description": (
            "日（1〜14）とレーン（base または stretch）のみで選択し、小学校入学前14日間"
            "注音符号サマー・ウォームアップカレンダーからすでに公開・固定された1日分の"
            "重点と説明を返します。決定的かつ読み取り専用で、子どもの氏名、自由入力、"
            "ファイル、録音、回答、点数、進捗は一切受け取りません。評価、診断、"
            "入学準備度チェック、学習成果の保証ではありません。"
        ),
    },
    "ko": {
        "title": "초등학교 입학 전 14일 주음부호 여름 준비 달력｜무료 인쇄용",
        "description": "무료로 인쇄할 수 있는 14일 주음부호 여름 준비 달력입니다. 하루 8-10분, 로그인 불필요, 점수나 진단이 없습니다.",
        "eyebrow": "무료 여름 가족 달력 · 로그인 불필요",
        "lead": "여름방학을 시험으로 만들지 않고 입학 전에 친숙함을 쌓아 보세요. 오늘에 맞는 시작 방법을 고르고, 하루 10분을 넘기지 말고, 필요하면 언제든 일찍 마무리하세요.",
        "badges": ("14일 · 하루 8-10분", "점수, 진단, 저장되는 아이 데이터 없음", "독창적인 가정 활동이며 공식 교육과정이 아님"),
        "start": "14일 달력 열기",
        "switch": "繁體中文",
        "boundary": "준비 운동이지 입학 조건이 아닙니다",
        "boundary_text": "이 선택형 달력은 초등학교 입학을 위한 필수 조건을 정하지 않습니다. 37개 기호를 전부 가르치거나 평가하지 않으며, 등급을 매기거나 학교 성적을 예측하지 않습니다. 학교마다 방침이 다르므로 실제 1학기 계획은 아이의 학교에 문의하세요.",
        "lanes": "시작 방법 하나 고르기",
        "lane_intro": "오늘에 맞는 가장 가벼운 방법을 사용하세요. 방법은 자유롭게 바꿀 수 있으며, 아이는 어떤 방법도 끝까지 마치거나 달력 진도를 따라잡을 필요가 없습니다.",
        "lane_items": (
            ("처음 접함", "기호 두세 개만 사용하세요. 어른이 시범을 보이며, 듣기만 하거나 보기만 하거나 멈추는 것도 모두 참여로 인정됩니다."),
            ("일부를 인식함", "아이가 이미 본 적 있는 기호 네다섯 개로 가리키기, 짝맞추기, 동작 활동을 하세요."),
            ("결합할 준비가 됨", "익숙한 이합 결합 두 개를 속도, 순위, 필기 압박 없이 사용하세요."),
        ),
        "routine": "매일 같은 8-10분 리듬",
        "routine_items": (
            "1분 · 아이가 방법이나 재료를 고름",
            "2분 · 어른이 한 번 시범을 보임(먼저 시험하지 않기)",
            "3분 · 가리키기, 짝맞추기, 움직이기 또는 듣기",
            "2분 · 종이, 가족 단어, 또는 정식으로 구한 책과 연결",
            "1-2분 · 노력한 점 한 가지를 말하고 마무리",
        ),
        "calendar": "14일 인쇄용 달력",
        "base_label": "부드러운 경로",
        "stretch_label": "이미 편안할 때만",
        "print": "달력 인쇄",
        "share": "도구 공유",
        "share_title": "무료 초등학교 입학 전 14일 주음부호 여름 준비 달력",
        "shared": "도구 링크가 복사되었습니다.",
        "cancelled": "공유가 취소되었습니다.",
        "copied": "도구 링크가 복사되었습니다.",
        "copy_failed": "복사할 수 없습니다. 이 링크를 사용하세요:",
        "lookup": "하루만 확인하기",
        "day_field_label": "일차",
        "lane_field_label": "방법",
        "show_day": "이 날 보기",
        "invalid_input": "1-14 사이의 일차와 방법을 선택하세요.",
        "privacy": "완료 추적이 없습니다",
        "privacy_text": "아이 이름 입력란, 날짜 입력란, 체크 추적기, 계정, 양식 제출, 카메라, 마이크, 업로드, 분석 입력, 로컬 저장소 또는 저장된 프로필이 전혀 없습니다. 이 페이지는 답변이나 활동 기록을 받지 않습니다.",
        "evidence": "공식 자료가 보여주는 것과 보여주지 않는 것",
        "evidence_text": "대만 교육부 자료는 표준 주음부호 글꼴, 표기법, 필순을 정합니다. 이 달력을 규정하거나 보증하지 않습니다. 이 독창적인 14일 과정은 연구로 평가된 적이 없으며, 아이가 학교 갈 준비가 되었는지, 더 빨리 배우는지, 특정 결과를 얻는지를 보여줄 수 없습니다. 14일은 숙달 일정이 아니라 범위가 정해진 가정 루틴입니다.",
        "sources": "공식 참고 자료",
        "source_labels": ("대만 교육부 《국어 주음부호 手冊》", "대만 교육부 주음부호 필순"),
        "reuse": "독창적인 달력 자유롭게 활용하기",
        "reuse_text": "가정, 도서관, 교포 학교는 iOS App Guide를 출처로 표기하고 이 페이지로 링크를 걸면 CC BY 4.0에 따라 이 독창적인 달력을 인쇄하거나 각색할 수 있습니다. 이 라이선스는 교육부 자료, 도서 또는 기타 외부 출처에는 적용되지 않습니다.",
        "app_title": "선택한 하루 안에서의 선택적 연습",
        "app_text": "종이, 공식 참고 자료, 정식으로 구한 책만으로 이 달력을 완전히 사용할 수 있습니다. 어느 하루에 안내가 있는 듣기, 따라 쓰기, 성조, 결합 연습을 더하고 싶은 가정을 위해 Lumi Bopomofo는 37개 기호를 모두 다룹니다. 일회성 평생 잠금 해제 방식이며 광고, 구독, 계정이 필요 없습니다.",
        "app_cta": "Lumi Bopomofo 사용해 보기",
        "related": "관련 무료 자료",
        "faq": "학부모 자주 묻는 질문",
        "faq_items": (
            ("초등학교 입학 전에 아이가 주음부호를 꼭 알아야 하나요?", "이 달력은 입학 조건을 정하지 않습니다. 실제 교육 계획은 아이의 학교에 확인하고, 이 달력은 선택적인 친숙화 루틴으로만 사용하세요."),
            ("14일 만에 37개 기호를 모두 배울 수 있나요?", "아니요. 듣기, 모양, 필순, 성조, 결합, 읽기 활동을 조금씩 맛보는 것입니다. 등급을 매기지 않고 반복하거나 쉬거나 나중에 이어가도 됩니다."),
            ("아이가 구어 중국어를 거의 사용하지 않으면 어떻게 하나요?", "구어를 별도의 필요로 다루세요. 주음부호는 대화 및 유창한 말하기와 함께 사용하고, 기호 학습이 느린 것을 진단으로 해석하지 마세요."),
            ("앱이 꼭 필요한가요?", "아니요. 종이, 공식 참고 자료, 어른의 시범, 합법적으로 구한 주음 표기 도서만으로 이 달력을 완전히 마칠 수 있습니다."),
        ),
        "home": "홈",
        "tools": "무료 도구",
        "footer": "독립적인 가정용 자료이며, 공식 교육과정, 입학 조건, 평가, 진단 또는 학교 성과 보장이 아닙니다.",
        "index_title": "초등학교 입학 전 14일 주음부호 여름 준비 달력",
        "index_description": "무료로 인쇄할 수 있는 14일 가족 달력. 점수, 진단, 저장되는 아이 데이터가 없습니다.",
        "inline_link": "무료 초등학교 입학 전 14일 주음부호 여름 준비 달력 열기",
        "webmcp_description": (
            "일차(1-14)와 방법(base 또는 stretch)만으로 초등학교 입학 전 14일 주음부호 "
            "여름 준비 달력에서 이미 공개된 고정된 하루의 초점과 안내를 반환합니다. "
            "결정적이며 읽기 전용으로, 아이 이름, 자유 텍스트, 파일, 녹음, 답변, 점수, "
            "진행 상황을 전혀 받지 않습니다. 평가, 진단, 준비도 확인 또는 학습 성과 "
            "보장이 아닙니다."
        ),
    },
    "es-ES": {
        "title": "Calendario gratuito de 14 días para preparar el Zhuyin antes de 1.º de Primaria",
        "description": "Un calendario gratuito y listo para imprimir de 14 días de preparación de Zhuyin en verano, con actividades de 8-10 minutos. Sin puntuación, sin inicio de sesión, sin afirmación de preparación escolar.",
        "eyebrow": "Calendario familiar de verano gratuito · sin inicio de sesión",
        "lead": "Genera familiaridad antes del colegio sin convertir el verano en un examen. Elige un nivel de partida, mantén cada día por debajo de diez minutos y termina antes si hace falta.",
        "badges": ("14 días · 8-10 minutos cada uno", "Sin puntuación, diagnóstico ni datos guardados del niño", "Actividad familiar original, no un currículo oficial"),
        "start": "Abrir el calendario de 14 días",
        "switch": "English",
        "boundary": "Es preparación, no un requisito de acceso",
        "boundary_text": "Este calendario opcional no establece un requisito previo para 1.º de Primaria. No enseña ni evalúa los 37 símbolos, no asigna un nivel ni predice el rendimiento escolar. Los colegios varían; consulta al colegio del niño sobre su plan real del primer trimestre.",
        "lanes": "Elige un nivel de partida",
        "lane_intro": "Usa el nivel más ligero que encaje hoy. Cambia de nivel libremente; ningún niño necesita completar un nivel ni ponerse al día con el calendario.",
        "lane_items": (
            ("Completamente nuevo", "Usa dos o tres símbolos. El adulto hace de modelo; escuchar, mirar o parar cuentan igual como participación."),
            ("Reconoce algunos", "Usa de cuatro a seis símbolos que el niño ya ha visto para señalar, emparejar y moverse."),
            ("Listo para combinar", "Usa dos combinaciones de dos partes ya conocidas, sin velocidad, clasificación ni presión por la caligrafía."),
        ),
        "routine": "El mismo ritmo de 8-10 minutos",
        "routine_items": (
            "1 minuto · el niño elige el nivel o el material",
            "2 minutos · el adulto hace de modelo una vez; no preguntes antes",
            "3 minutos · señalar, emparejar, moverse o escuchar",
            "2 minutos · conectar con papel, una palabra familiar o un libro autorizado",
            "1-2 minutos · nombrar un esfuerzo y terminar",
        ),
        "calendar": "Calendario imprimible de catorce días",
        "base_label": "Ruta suave",
        "stretch_label": "Solo si ya está cómodo",
        "print": "Imprimir el calendario",
        "share": "Compartir herramienta",
        "share_title": "Calendario gratuito de 14 días para preparar el Zhuyin antes de 1.º de Primaria",
        "shared": "Enlace de la herramienta copiado.",
        "cancelled": "Se canceló el uso compartido.",
        "copied": "Enlace de la herramienta copiado.",
        "copy_failed": "No se pudo copiar. Usa este enlace:",
        "lookup": "Consultar un solo día",
        "day_field_label": "Día",
        "lane_field_label": "Nivel",
        "show_day": "Mostrar este día",
        "invalid_input": "Elige un día del 1 al 14 y un nivel.",
        "privacy": "Sin seguimiento de finalización",
        "privacy_text": "No hay campo de nombre del niño, campo de fecha, rastreador de casillas, cuenta, envío de formularios, cámara, micrófono, subida de archivos, entrada de análisis, almacenamiento local ni perfil guardado. La página no recibe respuestas ni historial de actividad.",
        "evidence": "Qué muestran las fuentes oficiales, y qué no",
        "evidence_text": "Las referencias del Ministerio de Educación de Taiwán establecen las formas estándar, la notación y el orden de trazos del Zhuyin. No prescriben ni respaldan este calendario. Esta secuencia original de 14 días no ha sido evaluada en ningún estudio y no puede mostrar que un niño esté listo para el colegio, aprenda más rápido u obtenga un resultado concreto. Catorce días es una rutina familiar acotada, no un calendario de dominio.",
        "sources": "Referencias oficiales",
        "source_labels": ("Manual de símbolos fonéticos Bopomofo del Ministerio de Educación de Taiwán", "Orden de trazos del Zhuyin del Ministerio de Educación de Taiwán"),
        "reuse": "Reutiliza el calendario original",
        "reuse_text": "Las familias, bibliotecas y escuelas de herencia cultural pueden imprimir o adaptar este calendario original bajo CC BY 4.0 con crédito a iOS App Guide y un enlace a esta página. La licencia no cubre los materiales del Ministerio, libros u otras fuentes externas.",
        "app_title": "Práctica opcional dentro de un día elegido",
        "app_text": "El calendario completo funciona con papel, referencias oficiales y un libro autorizado. Si una familia quiere práctica guiada de escucha, trazado, tonos o combinación, Lumi Bopomofo cubre los 37 símbolos. Usa un desbloqueo único de por vida, sin anuncios, suscripción ni cuenta.",
        "app_cta": "Probar Lumi Bopomofo",
        "related": "Recursos gratuitos relacionados",
        "faq": "Preguntas frecuentes de padres",
        "faq_items": (
            ("¿Debe un niño saber Zhuyin antes de 1.º de Primaria?", "Este calendario no establece ningún requisito de acceso. Consulta al colegio del niño sobre su plan de enseñanza y usa esto solo como una rutina opcional de familiarización."),
            ("¿Catorce días enseñarán los 37 símbolos?", "No. Muestra interacciones de escucha, forma, trazo, tono, combinación y lectura. Repite, pausa o continúa más adelante sin asignar un nivel."),
            ("¿Y si el niño usa poco mandarín hablado?", "Trata el lenguaje oral como una necesidad aparte. Combina el Zhuyin con la conversación y el habla fluida; no interpretes un trabajo lento con los símbolos como un diagnóstico."),
            ("¿Se necesita una aplicación?", "No. El papel, las referencias oficiales, el modelado por parte de un adulto y un libro anotado obtenido legalmente son suficientes para el calendario completo."),
        ),
        "home": "Inicio",
        "tools": "Herramientas gratuitas",
        "footer": "Recurso familiar independiente; no es un currículo oficial, un requisito de acceso, una evaluación, un diagnóstico ni una promesa de resultados escolares.",
        "index_title": "Calendario de 14 días para preparar el Zhuyin antes de 1.º de Primaria",
        "index_description": "Un calendario familiar gratuito y listo para imprimir de 14 días, sin puntuación, diagnóstico ni datos guardados del niño.",
        "inline_link": "Abrir el calendario gratuito de 14 días para preparar el Zhuyin antes de 1.º de Primaria",
        "webmcp_description": (
            "Devuelve el enfoque e instrucción de un día fijo ya publicado del calendario "
            "de 14 días de preparación de Zhuyin antes de 1.º de Primaria, seleccionado "
            "solo por día (1-14) y nivel (base o stretch). Determinista y de solo lectura: "
            "no acepta nombre del niño, texto libre, archivo, grabación, respuesta, "
            "puntuación ni progreso; no es una evaluación, diagnóstico, comprobación de "
            "preparación ni afirmación de resultado de aprendizaje."
        ),
    },
    "pt-BR": {
        "title": "Calendário gratuito de 14 dias para preparar o Zhuyin antes do 1.º ano",
        "description": "Um calendário gratuito e pronto para imprimir de 14 dias de preparação de Zhuyin no verão, com atividades de 8-10 minutos. Sem nota, sem login, sem promessa de prontidão escolar.",
        "eyebrow": "Calendário familiar de verão gratuito · sem login",
        "lead": "Construa familiaridade antes da escola sem transformar as férias em uma prova. Escolha um ponto de partida, mantenha cada dia com menos de dez minutos e termine mais cedo quando precisar.",
        "badges": ("14 dias · 8-10 minutos cada", "Sem nota, diagnóstico ou dados salvos da criança", "Atividade familiar original, não é um currículo oficial"),
        "start": "Abrir o calendário de 14 dias",
        "switch": "English",
        "boundary": "É aquecimento, não um requisito de entrada",
        "boundary_text": "Este calendário opcional não estabelece um pré-requisito para o 1.º ano. Ele não ensina nem avalia os 37 símbolos, não atribui um nível nem prevê o desempenho escolar. As escolas variam; pergunte à escola da criança sobre o plano real do primeiro semestre.",
        "lanes": "Escolha um ponto de partida",
        "lane_intro": "Use o nível mais leve que encaixar hoje. Mude de nível livremente; nenhuma criança precisa concluir um nível nem alcançar o calendário.",
        "lane_items": (
            ("Totalmente novo", "Use dois ou três símbolos. O adulto demonstra; ouvir, olhar ou parar contam igualmente como participação."),
            ("Reconhece alguns", "Use de quatro a seis símbolos que a criança já viu para apontar, combinar e se mover."),
            ("Pronto para combinar", "Use duas combinações de duas partes já conhecidas, sem velocidade, classificação ou pressão pela caligrafia."),
        ),
        "routine": "O mesmo ritmo de 8-10 minutos",
        "routine_items": (
            "1 minuto · a criança escolhe o nível ou o material",
            "2 minutos · o adulto demonstra uma vez; não pergunte antes",
            "3 minutos · apontar, combinar, mover ou ouvir",
            "2 minutos · conectar com papel, uma palavra da família ou um livro autorizado",
            "1-2 minutos · nomear um esforço e terminar",
        ),
        "calendar": "Calendário imprimível de catorze dias",
        "base_label": "Rota tranquila",
        "stretch_label": "Só se já estiver confortável",
        "print": "Imprimir o calendário",
        "share": "Compartilhar ferramenta",
        "share_title": "Calendário gratuito de 14 dias para preparar o Zhuyin antes do 1.º ano",
        "shared": "Link da ferramenta copiado.",
        "cancelled": "O compartilhamento foi cancelado.",
        "copied": "Link da ferramenta copiado.",
        "copy_failed": "Não foi possível copiar. Use este link:",
        "lookup": "Consultar um único dia",
        "day_field_label": "Dia",
        "lane_field_label": "Nível",
        "show_day": "Mostrar este dia",
        "invalid_input": "Escolha um dia de 1 a 14 e um nível.",
        "privacy": "Sem rastreamento de conclusão",
        "privacy_text": "Não há campo de nome da criança, campo de data, rastreador de marcação, conta, envio de formulário, câmera, microfone, upload, entrada de análise, armazenamento local ou perfil salvo. A página não recebe respostas nem histórico de atividade.",
        "evidence": "O que as fontes oficiais mostram - e não mostram",
        "evidence_text": "As referências do Ministério da Educação de Taiwan estabelecem formas padrão, notação e ordem de traços do Zhuyin. Elas não prescrevem nem endossam este calendário. Esta sequência original de 14 dias não foi avaliada em nenhum estudo e não pode mostrar que uma criança está pronta para a escola, aprenderá mais rápido ou obterá um resultado específico. Catorze dias é uma rotina familiar limitada, não um cronograma de domínio.",
        "sources": "Referências oficiais",
        "source_labels": ("Manual de símbolos fonéticos Bopomofo do Ministério da Educação de Taiwan", "Ordem de traços do Zhuyin do Ministério da Educação de Taiwan"),
        "reuse": "Reutilize o calendário original",
        "reuse_text": "Famílias, bibliotecas e escolas de herança podem imprimir ou adaptar este calendário original sob a CC BY 4.0, com crédito ao iOS App Guide e um link para esta página. A licença não cobre materiais do Ministério, livros ou outras fontes externas.",
        "app_title": "Prática opcional dentro de um dia escolhido",
        "app_text": "O calendário completo funciona com papel, referências oficiais e um livro autorizado. Se uma família quiser prática guiada de escuta, traçado, tom ou combinação, o Lumi Bopomofo cobre todos os 37 símbolos. Ele usa um desbloqueio único vitalício, sem anúncios, assinatura ou conta.",
        "app_cta": "Experimentar o Lumi Bopomofo",
        "related": "Recursos gratuitos relacionados",
        "faq": "Perguntas frequentes dos pais",
        "faq_items": (
            ("A criança precisa saber Zhuyin antes do 1.º ano?", "Este calendário não estabelece nenhum requisito de entrada. Pergunte à escola da criança sobre seu plano de ensino e use isto apenas como uma rotina opcional de familiarização."),
            ("Catorze dias vão ensinar todos os 37 símbolos?", "Não. Ele apresenta interações de escuta, forma, traço, tom, combinação e leitura. Repita, pause ou continue depois sem atribuir um nível."),
            ("E se a criança fala pouco mandarim falado?", "Trate a língua oral como uma necessidade separada. Combine o Zhuyin com conversa e fala fluente; não interprete um trabalho lento com os símbolos como um diagnóstico."),
            ("É necessário um aplicativo?", "Não. Papel, referências oficiais, demonstração de um adulto e um livro anotado obtido legalmente são suficientes para o calendário completo."),
        ),
        "home": "Início",
        "tools": "Ferramentas gratuitas",
        "footer": "Recurso familiar independente; não é um currículo oficial, requisito de entrada, avaliação, diagnóstico ou promessa de resultados escolares.",
        "index_title": "Calendário de 14 dias para preparar o Zhuyin antes do 1.º ano",
        "index_description": "Um calendário familiar gratuito e pronto para imprimir de 14 dias, sem nota, diagnóstico ou dados salvos da criança.",
        "inline_link": "Abrir o calendário gratuito de 14 dias para preparar o Zhuyin antes do 1.º ano",
        "webmcp_description": (
            "Retorna o foco e a instrução de um dia fixo já publicado do calendário de 14 "
            "dias de preparação de Zhuyin antes do 1.º ano, selecionado apenas por dia "
            "(1-14) e nível (base ou stretch). Determinístico e somente leitura: não "
            "aceita nome da criança, texto livre, arquivo, gravação, resposta, nota ou "
            "progresso; não é uma avaliação, diagnóstico, verificação de prontidão nem "
            "promessa de resultado de aprendizagem."
        ),
    },
    "de-DE": {
        "title": "Kostenloser 14-Tage-Sommer-Warm-up-Kalender für Zhuyin vor der 1. Klasse",
        "description": "Ein kostenloser, druckfertiger 14-Tage-Sommer-Warm-up-Kalender für Zhuyin mit 8-10-minütigen Familienaktivitäten. Keine Bewertung, keine Anmeldung, kein Anspruch auf Schulreife.",
        "eyebrow": "Kostenloser Sommer-Familienkalender · keine Anmeldung",
        "lead": "Schaffen Sie Vertrautheit vor der Schule, ohne den Sommer zu einer Prüfung zu machen. Wählen Sie eine Einstiegsspur, halten Sie jeden Tag unter zehn Minuten und hören Sie bei Bedarf früher auf.",
        "badges": ("14 Tage · je 8-10 Minuten", "Keine Bewertung, Diagnose oder gespeicherte Kinddaten", "Originale Familienaktivität, kein offizieller Lehrplan"),
        "start": "14-Tage-Kalender öffnen",
        "switch": "English",
        "boundary": "Aufwärmen, keine Zugangsvoraussetzung",
        "boundary_text": "Dieser optionale Kalender legt keine Voraussetzung für die 1. Klasse fest. Er lehrt oder prüft nicht alle 37 Zeichen, weist kein Niveau zu und sagt keine schulische Leistung voraus. Schulen unterscheiden sich; fragen Sie die Schule des Kindes nach ihrem tatsächlichen Plan fürs erste Halbjahr.",
        "lanes": "Eine Einstiegsspur wählen",
        "lane_intro": "Nutzen Sie die leichteste Spur, die heute passt. Wechseln Sie frei zwischen den Spuren; kein Kind muss eine Spur abschließen oder den Kalender einholen.",
        "lane_items": (
            ("Völlig neu", "Verwenden Sie zwei oder drei Zeichen. Der Erwachsene macht es vor; Zuhören, Zusehen oder Aufhören zählen alle als Mitmachen."),
            ("Erkennt einige", "Verwenden Sie vier bis sechs Zeichen, die das Kind bereits gesehen hat, zum Zeigen, Zuordnen und für Bewegung."),
            ("Bereit zum Kombinieren", "Verwenden Sie zwei bereits vertraute Zweier-Verbindungen ohne Zeitdruck, Rangfolge oder Druck auf die Handschrift."),
        ),
        "routine": "Der gleiche 8-10-Minuten-Rhythmus",
        "routine_items": (
            "1 Minute · das Kind wählt die Spur oder das Material",
            "2 Minuten · der Erwachsene macht es einmal vor; nicht vorher abfragen",
            "3 Minuten · zeigen, zuordnen, bewegen oder zuhören",
            "2 Minuten · mit Papier, einem Familienwort oder einem autorisierten Buch verbinden",
            "1-2 Minuten · eine Anstrengung benennen und aufhören",
        ),
        "calendar": "Vierzehntägiger Kalender zum Ausdrucken",
        "base_label": "Sanfter Weg",
        "stretch_label": "Nur wenn bereits wohlfühlt",
        "print": "Kalender drucken",
        "share": "Tool teilen",
        "share_title": "Kostenloser 14-Tage-Sommer-Warm-up-Kalender für Zhuyin vor der 1. Klasse",
        "shared": "Tool-Link kopiert.",
        "cancelled": "Teilen wurde abgebrochen.",
        "copied": "Tool-Link kopiert.",
        "copy_failed": "Kopieren war nicht möglich. Verwenden Sie diesen Link:",
        "lookup": "Einen einzelnen Tag nachschlagen",
        "day_field_label": "Tag",
        "lane_field_label": "Spur",
        "show_day": "Diesen Tag anzeigen",
        "invalid_input": "Wählen Sie einen Tag von 1-14 und eine Spur.",
        "privacy": "Keine Abschlussverfolgung",
        "privacy_text": "Es gibt kein Namensfeld für das Kind, kein Datumsfeld, keinen Checkbox-Tracker, kein Konto, keine Formularübermittlung, keine Kamera, kein Mikrofon, keinen Upload, keine Analytics-Eingabe, keinen lokalen Speicher und kein gespeichertes Profil. Die Seite erhält keine Antworten oder Aktivitätsverläufe.",
        "evidence": "Was die offiziellen Quellen zeigen - und was nicht",
        "evidence_text": "Referenzen des taiwanesischen Bildungsministeriums legen standardmäßige Zhuyin-Formen, Notation und Strichfolge fest. Sie schreiben diesen Kalender weder vor noch befürworten sie ihn. Diese originale 14-Tage-Abfolge wurde nicht in einer Studie evaluiert und kann nicht zeigen, dass ein Kind schulreif ist, schneller lernt oder ein bestimmtes Ergebnis erzielt. Vierzehn Tage sind eine begrenzte Familienroutine, kein Zeitplan zur Beherrschung.",
        "sources": "Offizielle Referenzen",
        "source_labels": ("Bopomofo-Handbuch des taiwanesischen Bildungsministeriums", "Zhuyin-Strichfolge des taiwanesischen Bildungsministeriums"),
        "reuse": "Den originalen Kalender wiederverwenden",
        "reuse_text": "Familien, Bibliotheken und Herkunftssprachschulen dürfen diesen originalen Kalender unter CC BY 4.0 mit Nennung von iOS App Guide und einem Link zu dieser Seite drucken oder anpassen. Die Lizenz deckt keine Materialien des Ministeriums, Bücher oder andere externe Quellen ab.",
        "app_title": "Optionale Übung innerhalb eines gewählten Tages",
        "app_text": "Der vollständige Kalender funktioniert mit Papier, offiziellen Referenzen und einem autorisierten Buch. Wenn eine Familie geführtes Hören, Nachzeichnen, Ton- oder Verbindungsübungen möchte, deckt Lumi Bopomofo alle 37 Zeichen ab. Es nutzt eine einmalige lebenslange Freischaltung ohne Werbung, Abonnement oder Konto.",
        "app_cta": "Lumi Bopomofo ausprobieren",
        "related": "Verwandte kostenlose Ressourcen",
        "faq": "FAQ für Eltern",
        "faq_items": (
            ("Muss ein Kind vor der 1. Klasse Zhuyin können?", "Dieser Kalender legt keine Zugangsvoraussetzung fest. Fragen Sie die Schule des Kindes nach ihrem Lehrplan und nutzen Sie dies nur als optionale Gewöhnungsroutine."),
            ("Werden in vierzehn Tagen alle 37 Zeichen gelehrt?", "Nein. Er bietet Beispiele für Hör-, Form-, Strich-, Ton-, Verbindungs- und Leseinteraktionen. Wiederholen, pausieren oder später fortsetzen, ohne ein Niveau zuzuweisen."),
            ("Was, wenn das Kind wenig gesprochenes Mandarin verwendet?", "Behandeln Sie die mündliche Sprache als eigenen Bedarf. Kombinieren Sie Zhuyin mit Gesprächen und flüssigem Sprechen; deuten Sie langsame Zeichenarbeit nicht als Diagnose."),
            ("Wird eine App benötigt?", "Nein. Papier, offizielle Referenzen, Vorführung durch einen Erwachsenen und ein legal erhältliches, annotiertes Buch reichen für den vollständigen Kalender aus."),
        ),
        "home": "Startseite",
        "tools": "Kostenlose Tools",
        "footer": "Unabhängige Familienressource; kein offizieller Lehrplan, keine Zugangsvoraussetzung, Bewertung, Diagnose oder Zusage schulischer Ergebnisse.",
        "index_title": "14-Tage-Sommer-Warm-up-Kalender für Zhuyin vor der 1. Klasse",
        "index_description": "Ein kostenloser, druckfertiger 14-Tage-Familienkalender ohne Bewertung, Diagnose oder gespeicherte Kinddaten.",
        "inline_link": "Kostenlosen 14-Tage-Sommer-Warm-up-Kalender für Zhuyin vor der 1. Klasse öffnen",
        "webmcp_description": (
            "Gibt Fokus und Anleitung eines festen, bereits veröffentlichten Tages aus dem "
            "14-Tage-Sommer-Warm-up-Kalender für Zhuyin vor der 1. Klasse zurück, "
            "ausgewählt nur nach Tag (1-14) und Spur (base oder stretch). "
            "Deterministisch und schreibgeschützt: akzeptiert keinen Namen des Kindes, "
            "keinen Freitext, keine Datei, Aufnahme, Antwort, Bewertung oder Fortschritt; "
            "ist keine Bewertung, Diagnose, Schulreifeprüfung oder Zusage eines "
            "Lernergebnisses."
        ),
    },
    "fr-FR": {
        "title": "Calendrier gratuit de 14 jours pour préparer le zhuyin avant le CP",
        "description": "Un calendrier gratuit et prêt à imprimer de 14 jours pour préparer le zhuyin pendant l'été, avec des activités de 8 à 10 minutes. Sans note, sans connexion, sans promesse de préparation scolaire.",
        "eyebrow": "Calendrier familial d'été gratuit · sans connexion",
        "lead": "Construisez de la familiarité avant l'école sans transformer l'été en examen. Choisissez un niveau de départ, gardez chaque jour à moins de dix minutes et arrêtez plus tôt si besoin.",
        "badges": ("14 jours · 8-10 minutes chacun", "Sans note, diagnostic ni données enregistrées sur l'enfant", "Activité familiale originale, pas un programme officiel"),
        "start": "Ouvrir le calendrier de 14 jours",
        "switch": "English",
        "boundary": "C'est un échauffement, pas une condition d'entrée",
        "boundary_text": "Ce calendrier optionnel n'établit pas de prérequis pour le CP. Il n'enseigne ni n'évalue les 37 symboles, n'attribue pas de niveau et ne prédit pas les résultats scolaires. Les écoles diffèrent ; demandez à l'école de l'enfant son plan réel pour le premier trimestre.",
        "lanes": "Choisir un niveau de départ",
        "lane_intro": "Utilisez le niveau le plus léger qui convient aujourd'hui. Changez de niveau librement ; aucun enfant n'a besoin de terminer un niveau ni de rattraper le calendrier.",
        "lane_items": (
            ("Totalement nouveau", "Utilisez deux ou trois symboles. L'adulte montre ; écouter, regarder ou s'arrêter comptent tous comme participer."),
            ("Reconnaît quelques-uns", "Utilisez quatre à six symboles que l'enfant a déjà vus pour montrer du doigt, associer et bouger."),
            ("Prêt à combiner", "Utilisez deux combinaisons en deux parties déjà familières, sans vitesse, classement ni pression sur l'écriture."),
        ),
        "routine": "Le même rythme de 8-10 minutes",
        "routine_items": (
            "1 minute · l'enfant choisit le niveau ou le matériel",
            "2 minutes · l'adulte montre une fois ; ne pas interroger d'abord",
            "3 minutes · montrer du doigt, associer, bouger ou écouter",
            "2 minutes · relier à du papier, un mot familial ou un livre autorisé",
            "1-2 minutes · nommer un effort et s'arrêter",
        ),
        "calendar": "Calendrier imprimable de quatorze jours",
        "base_label": "Parcours en douceur",
        "stretch_label": "Seulement si déjà à l'aise",
        "print": "Imprimer le calendrier",
        "share": "Partager l'outil",
        "share_title": "Calendrier gratuit de 14 jours pour préparer le zhuyin avant le CP",
        "shared": "Lien de l'outil copié.",
        "cancelled": "Le partage a été annulé.",
        "copied": "Lien de l'outil copié.",
        "copy_failed": "La copie n'a pas fonctionné. Utilisez ce lien :",
        "lookup": "Consulter un seul jour",
        "day_field_label": "Jour",
        "lane_field_label": "Niveau",
        "show_day": "Afficher ce jour",
        "invalid_input": "Choisissez un jour de 1 à 14 et un niveau.",
        "privacy": "Aucun suivi d'achèvement",
        "privacy_text": "Il n'y a aucun champ pour le nom de l'enfant, aucun champ de date, aucun suivi par cases à cocher, aucun compte, aucune soumission de formulaire, aucune caméra, aucun microphone, aucun téléversement, aucune saisie analytique, aucun stockage local ni profil enregistré. La page ne reçoit aucune réponse ni historique d'activité.",
        "evidence": "Ce que montrent les sources officielles - et ce qu'elles ne montrent pas",
        "evidence_text": "Les références du ministère de l'Éducation de Taïwan établissent les formes standard, la notation et l'ordre des traits du zhuyin. Elles ne prescrivent ni n'approuvent ce calendrier. Cette séquence originale de 14 jours n'a fait l'objet d'aucune étude et ne peut pas montrer qu'un enfant est prêt pour l'école, apprendra plus vite ou obtiendra un résultat particulier. Quatorze jours sont une routine familiale bornée, pas un calendrier de maîtrise.",
        "sources": "Références officielles",
        "source_labels": ("Manuel des symboles phonétiques Bopomofo du ministère de l'Éducation de Taïwan", "Ordre des traits du zhuyin du ministère de l'Éducation de Taïwan"),
        "reuse": "Réutiliser le calendrier original",
        "reuse_text": "Les familles, bibliothèques et écoles de langue d'origine peuvent imprimer ou adapter ce calendrier original sous licence CC BY 4.0 avec mention d'iOS App Guide et un lien vers cette page. La licence ne couvre pas les documents du ministère, les livres ou d'autres sources externes.",
        "app_title": "Pratique optionnelle au sein d'un jour choisi",
        "app_text": "Le calendrier complet fonctionne avec du papier, des références officielles et un livre autorisé. Si une famille souhaite une pratique guidée d'écoute, de traçage, de tons ou d'assemblage, Lumi Bopomofo couvre les 37 symboles. Il utilise un déverrouillage unique à vie, sans publicité, abonnement ni compte.",
        "app_cta": "Essayer Lumi Bopomofo",
        "related": "Ressources gratuites associées",
        "faq": "FAQ pour les parents",
        "faq_items": (
            ("Un enfant doit-il connaître le zhuyin avant le CP ?", "Ce calendrier ne fixe aucune condition d'entrée. Demandez à l'école de l'enfant son plan d'enseignement et utilisez ceci uniquement comme une routine optionnelle de familiarisation."),
            ("Quatorze jours vont-ils enseigner les 37 symboles ?", "Non. Il propose un échantillon d'interactions d'écoute, de forme, de trait, de ton, d'assemblage et de lecture. Répétez, faites une pause ou continuez plus tard sans attribuer de niveau."),
            ("Que faire si l'enfant parle peu le mandarin oral ?", "Traitez la langue orale comme un besoin distinct. Associez le zhuyin à la conversation et à une expression fluide ; n'interprétez pas un travail lent sur les symboles comme un diagnostic."),
            ("Une application est-elle nécessaire ?", "Non. Du papier, des références officielles, la démonstration d'un adulte et un livre annoté obtenu légalement suffisent pour le calendrier complet."),
        ),
        "home": "Accueil",
        "tools": "Outils gratuits",
        "footer": "Ressource familiale indépendante ; ce n'est pas un programme officiel, une condition d'entrée, une évaluation, un diagnostic ni une promesse de résultats scolaires.",
        "index_title": "Calendrier de 14 jours pour préparer le zhuyin avant le CP",
        "index_description": "Un calendrier familial gratuit et prêt à imprimer de 14 jours, sans note, diagnostic ni données enregistrées sur l'enfant.",
        "inline_link": "Ouvrir le calendrier gratuit de 14 jours pour préparer le zhuyin avant le CP",
        "webmcp_description": (
            "Renvoie le point de focalisation et l'instruction d'un jour fixe déjà publié "
            "du calendrier de 14 jours pour préparer le zhuyin avant le CP, sélectionné "
            "uniquement par jour (1-14) et niveau (base ou stretch). Déterministe et en "
            "lecture seule : n'accepte aucun nom d'enfant, texte libre, fichier, "
            "enregistrement, réponse, note ou progression ; ce n'est pas une évaluation, "
            "un diagnostic, une vérification de préparation ni une promesse de résultat "
            "d'apprentissage."
        ),
    },
}


def validate_copy() -> None:
    if set(COPY) != set(ALT_LOCALES):
        raise ValueError("COPY locales must match ALT_LOCALES exactly")
    if set(RELATED_LABELS) != set(ALT_LOCALES):
        raise ValueError("RELATED_LABELS locales must match ALT_LOCALES exactly")
    reference_keys = set(COPY["en"])
    for locale, entries in COPY.items():
        if set(entries) != reference_keys:
            missing = reference_keys - set(entries)
            extra = set(entries) - reference_keys
            raise ValueError(
                f"{locale} COPY keys mismatch: missing={missing} extra={extra}"
            )
        if len(entries["badges"]) != 3:
            raise ValueError(f"{locale} must define exactly 3 badges")
        if len(entries["lane_items"]) != 3:
            raise ValueError(f"{locale} must define exactly 3 lane_items")
        if len(entries["routine_items"]) != 5:
            raise ValueError(f"{locale} must define exactly 5 routine_items")
        if len(entries["source_labels"]) != len(SOURCES):
            raise ValueError(f"{locale} source_labels must match SOURCES length")
        if len(entries["faq_items"]) != 4:
            raise ValueError(f"{locale} must define exactly 4 faq_items")
        if len(RELATED_LABELS[locale]) != len(RELATED_SLUGS):
            raise ValueError(f"{locale} RELATED_LABELS must match RELATED_SLUGS length")


validate_copy()


STYLE = """
:root{--ink:#283246;--muted:#687287;--paper:#fffef9;--line:#dddcd4;--blue:#486a93;--green:#42806d;--sun:#d99a35;--soft:#eef7f2}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#f4f9ff 0,#f5fbf7 52%,#fff9ea 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}a{color:#315f87}.wrap{width:min(1080px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:4;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px;overflow-x:auto}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.nav-links{display:flex;gap:15px;align-items:center}.hero{padding:58px 0 32px}.eyebrow{color:var(--green);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:940px;margin:.18em 0;font-size:clamp(2rem,5.7vw,4rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:830px;color:var(--muted);font-size:clamp(1.08rem,2.5vw,1.27rem)}.badges,.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.badge{padding:8px 12px;border:1px solid #cde0d9;border-radius:999px;background:#fff;color:#3e665d;font-weight:800;white-space:nowrap}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--green),#579781);color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #34796f28}.button.secondary{background:#fff;color:#315f87!important;border:1px solid #c9d6e2;box-shadow:none}.button:focus-visible{outline:3px solid #e2b858;outline-offset:3px}.card{padding:23px;background:var(--paper);border:1px solid var(--line);border-radius:23px;box-shadow:0 10px 32px #34281a12}.boundary{margin-bottom:24px}.notice{padding:17px 19px;border-left:5px solid var(--sun);border-radius:14px;background:#fff7dc}.section-title{margin:1.6em 0 .55em;font-size:clamp(1.45rem,3vw,2rem);line-height:1.18}.lanes,.info-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.lane{padding:19px;border:1px solid #cadbd5;border-radius:18px;background:#fff}.lane h3{margin:.1em 0}.routine{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:16px}.beat{padding:14px;border-radius:16px;background:var(--soft);font-weight:750}.calendar{margin-top:25px;padding:clamp(20px,4vw,32px);background:#fff;border:1px solid #d8d9d5;border-radius:28px;box-shadow:0 20px 55px #23354b15}.calendar-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}.calendar-head h2{margin:.1em 0}.days{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;margin-top:20px}.day{padding:19px;border:1px solid #d7dcd7;border-radius:19px;background:linear-gradient(160deg,#fff,#fbfdfb);break-inside:avoid}.day-no{color:var(--green);font-size:.82rem;font-weight:900;letter-spacing:.05em}.day h3{margin:.18em 0 .6em;line-height:1.25}.route{margin:.55em 0;padding:11px 13px;border-radius:13px;background:#f0f6fb}.route.stretch{background:#fff8e8}.route strong{display:block;color:#526276;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}.lookup{margin-top:25px;padding:clamp(18px,4vw,28px)}.lookup-controls{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;margin-top:14px}.lookup-field label{display:block;font-size:13px;font-weight:850;color:var(--muted);margin-bottom:6px;white-space:nowrap}.lookup-field select{font:inherit;font-weight:800;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:14px;padding:9px 13px;min-width:100px}.lookup-result{margin-top:16px;min-height:1.4em}.extras{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:24px}.source-list a{overflow-wrap:anywhere}.related ul{padding-left:1.2em}.faq{margin-top:24px}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--green);font-weight:800}
@media(max-width:820px){.lanes,.info-grid,.extras{grid-template-columns:1fr}.routine{grid-template-columns:1fr 1fr}.days{grid-template-columns:1fr}.hero{padding-top:38px}.lookup-controls{flex-direction:column;align-items:stretch}}
@media(max-width:480px){.routine{grid-template-columns:1fr}.badge{font-size:.88rem}.calendar{padding:16px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.extras,.app-card,.related,.faq,.evidence,.footer,.actions,.share-status,.lookup{display:none!important}body{background:#fff;font-size:9.2pt}.wrap{width:100%}.boundary,.calendar,.card{border:0;box-shadow:none;padding:0}.boundary{margin-bottom:4mm}.lanes{grid-template-columns:repeat(3,1fr);gap:3mm}.lane{padding:3mm}.routine{grid-template-columns:repeat(5,1fr);gap:2mm}.beat{padding:2mm}.calendar-head{margin-top:4mm}.days{grid-template-columns:repeat(2,1fr);gap:3mm}.day{padding:3mm}.route{padding:2mm;margin:1.5mm 0}@page{size:A4;margin:8mm}}
"""


def canonical(locale: str) -> str:
    if locale not in ALT_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def webmcp_input_schema(locale: str) -> dict[str, object]:
    t = COPY[locale]
    return {
        "type": "object",
        "properties": {
            "day": {
                "type": "integer",
                "minimum": DAY_MIN,
                "maximum": DAY_MAX,
                "description": t["day_field_label"],
            },
            "lane": {
                "type": "string",
                "enum": list(LANE_VALUES),
                "description": t["lane_field_label"],
            },
        },
        "required": ["day", "lane"],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool = False) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    url = canonical(locale)
    other_locale = "zh-Hant" if locale == "en" else "en"
    alternate = canonical(other_locale)
    prefix = "" if locale == "en" else f"{locale}/"
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    alternate_links = "\n".join(
        f'<link rel="alternate" hreflang="{alt}" href="{canonical(alt)}">'
        for alt in ALT_LOCALES
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_grade1_14day_{locale.lower()}")
        if app_public
        else ""
    )
    app_card = ""
    if tracked_app_url:
        app_card = (
            '<article class="card app-card">'
            f'<h2>{html.escape(t["app_title"])}</h2>'
            f'<p>{html.escape(t["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></article>'
        )
    badges = "".join(
        f'<span class="badge">\u2713 {html.escape(item)}</span>'
        for item in t["badges"]
    )
    lanes = "".join(
        f'<article class="lane"><h3>{html.escape(title)}</h3>'
        f"<p>{html.escape(text)}</p></article>"
        for title, text in t["lane_items"]
    )
    routine = "".join(
        f'<div class="beat">{html.escape(item)}</div>'
        for item in t["routine_items"]
    )
    day_cards = "".join(
        '<article class="day">'
        f'<div class="day-no">{html.escape(day["day"])}</div>'
        f'<h3>{html.escape(day["focus"])}</h3>'
        f'<div class="route"><strong>{html.escape(t["base_label"])}</strong>'
        f'{html.escape(day["base"])}</div>'
        f'<div class="route stretch"><strong>{html.escape(t["stretch_label"])}</strong>'
        f'{html.escape(day["stretch"])}</div>'
        "</article>"
        for day in DAYS[locale]
    )
    sources = "".join(
        f'<li><a href="{html.escape(source_url)}" rel="noopener noreferrer">'
        f"{html.escape(label)}</a></li>"
        for label, source_url in zip(t["source_labels"], SOURCES, strict=True)
    )
    related = "".join(
        f'<li><a href="{html.escape(canonical(locale) if slug == SLUG else f"{SITE}/{prefix}tools/{slug}.html")}">'
        f"{html.escape(label)}</a></li>"
        for slug, label in zip(RELATED_SLUGS, RELATED_LABELS[locale], strict=True)
    )
    faq_html = "".join(
        f"<h3>{html.escape(question)}</h3><p>{html.escape(answer)}</p>"
        for question, answer in t["faq_items"]
    )
    day_options = "".join(
        f'<option value="{day}">{day}</option>' for day in range(DAY_MIN, DAY_MAX + 1)
    )
    lane_options = "".join(
        f'<option value="{html.escape(lane)}">'
        f'{html.escape(t["base_label"] if lane == "base" else t["stretch_label"])}'
        "</option>"
        for lane in LANE_VALUES
    )
    schema = {
        "@context": "https://schema.org",
        "@type": ["WebApplication", "LearningResource"],
        "name": t["title"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
        "browserRequirements": "JavaScript",
        "isAccessibleForFree": True,
        "learningResourceType": "Fourteen-day family warm-up calendar",
        "educationalUse": "Optional pre-school familiarity practice",
        "educationalLevel": "Beginner",
        "typicalAgeRange": "5-7",
        "license": LICENSE,
        "citation": list(SOURCES),
        "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
    }
    howto_schema = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": t["title"],
        "description": t["description"],
        "step": [
            {
                "@type": "HowToStep",
                "position": index,
                "name": f'{day["day"]}: {day["focus"]}',
                "text": day["base"],
            }
            for index, day in enumerate(DAYS[locale], 1)
        ],
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": locale,
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in t["faq_items"]
        ],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": home},
            {"@type": "ListItem", "position": 2, "name": t["tools"], "item": tools},
            {"@type": "ListItem", "position": 3, "name": t["title"], "item": url},
        ],
    }
    client_copy = {
        "shareTitle": t["share_title"],
        "shared": t["shared"],
        "cancelled": t["cancelled"],
        "copied": t["copied"],
        "copyFailed": t["copy_failed"],
        "invalidInput": t["invalid_input"],
        "baseLabel": t["base_label"],
        "stretchLabel": t["stretch_label"],
    }
    config = {
        "days": DAYS[locale],
        "copy": client_copy,
        "inputSchema": webmcp_input_schema(locale),
        "toolDescription": t["webmcp_description"],
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(t["source_labels"], SOURCES, strict=True)
        ],
        "optionalApp": (
            {
                "label": t["app_cta"],
                "boundary": t["app_text"],
                "app_store_url": tracked_app_url,
            }
            if tracked_app_url
            else None
        ),
    }
    config_json = json.dumps(
        config, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{url}">
{alternate_links}
<link rel="alternate" hreflang="x-default" href="{canonical("en")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
{feed_discovery_links()}
<style>{STYLE}</style>
{json_script(schema)}
{json_script(howto_schema)}
{json_script(faq_schema)}
{json_script(breadcrumb)}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="nav-links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#calendar">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["switch"])}</a></div></section>
<section class="wrap boundary"><article class="card"><h2 class="section-title">{html.escape(t["boundary"])}</h2><p class="notice">{html.escape(t["boundary_text"])}</p><h2 class="section-title">{html.escape(t["lanes"])}</h2><p>{html.escape(t["lane_intro"])}</p><div class="lanes">{lanes}</div><h2 class="section-title">{html.escape(t["routine"])}</h2><div class="routine">{routine}</div></article></section>
<section class="wrap calendar" id="calendar"><div class="calendar-head"><h2>{html.escape(t["calendar"])}</h2><div class="actions"><button class="button secondary" id="print-calendar" type="button">{html.escape(t["print"])}</button><button class="button" id="share-calendar" type="button">{html.escape(t["share"])}</button></div></div><div class="days">{day_cards}</div><div class="share-status" id="share-status" aria-live="polite"></div></section>
<section class="wrap card lookup"><h2>{html.escape(t["lookup"])}</h2><div class="lookup-controls"><div class="lookup-field"><label for="lookup-day">{html.escape(t["day_field_label"])}</label><select id="lookup-day">{day_options}</select></div><div class="lookup-field"><label for="lookup-lane">{html.escape(t["lane_field_label"])}</label><select id="lookup-lane">{lane_options}</select></div><button class="button secondary" id="lookup-show" type="button">{html.escape(t["show_day"])}</button></div><div class="lookup-result" id="lookup-result" aria-live="polite"></div></section>
<section class="wrap extras"><article class="card"><h2>{html.escape(t["privacy"])}</h2><p>{html.escape(t["privacy_text"])}</p></article><article class="card"><h2>{html.escape(t["reuse"])}</h2><p>{html.escape(t["reuse_text"])}</p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></article></section>
<section class="wrap card evidence"><h2>{html.escape(t["evidence"])}</h2><p>{html.escape(t["evidence_text"])}</p><h3>{html.escape(t["sources"])}</h3><ul class="source-list">{sources}</ul></section>
<section class="wrap extras related"><article class="card"><h2>{html.escape(t["related"])}</h2><ul>{related}</ul></article>{app_card}</section>
<section class="wrap card faq"><h2>{html.escape(t["faq"])}</h2>{faq_html}</section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="calendar-config">{config_json}</script>
<script>
(function(){{
  "use strict";
  var CONFIG=JSON.parse(document.getElementById("calendar-config").textContent);
  var DAYS_BY_NUMBER={{}};
  CONFIG.days.forEach(function(day,index){{DAYS_BY_NUMBER[index+1]=day;}});

  function validateInput(input){{
    if(input===null||typeof input!=="object"||Array.isArray(input)){{
      throw new TypeError("WebMCP input must be an object.");
    }}
    var allowed=Object.keys(CONFIG.inputSchema.properties);
    var key;
    for(key in input){{
      if(Object.prototype.hasOwnProperty.call(input,key)&&allowed.indexOf(key)===-1){{
        throw new RangeError(key+" is not supported.");
      }}
    }}
    var required=CONFIG.inputSchema.required;
    for(var i=0;i<required.length;i+=1){{
      if(!Object.prototype.hasOwnProperty.call(input,required[i])){{
        throw new TypeError(required[i]+" is required.");
      }}
    }}
    if(typeof input.day!=="number"||!Number.isInteger(input.day)||
       input.day===true||input.day===false){{
      throw new TypeError("day must be an integer.");
    }}
    var daySchema=CONFIG.inputSchema.properties.day;
    if(input.day<daySchema.minimum||input.day>daySchema.maximum){{
      throw new RangeError("day is not supported.");
    }}
    if(typeof input.lane!=="string"||
       CONFIG.inputSchema.properties.lane.enum.indexOf(input.lane)===-1){{
      throw new RangeError("lane is not supported.");
    }}
    return buildDayPlan(input.day,input.lane);
  }}

  function buildDayPlan(day,lane){{
    var entry=DAYS_BY_NUMBER[day];
    return {{
      selected_inputs:{{day:day,lane:lane}},
      day_label:entry.day,
      focus:entry.focus,
      instruction:lane==="stretch"?entry.stretch:entry.base
    }};
  }}

  function renderLookup(day,lane){{
    var plan=buildDayPlan(day,lane);
    var laneLabel=lane==="stretch"?CONFIG.copy.stretchLabel:CONFIG.copy.baseLabel;
    var result=document.getElementById("lookup-result");
    result.innerHTML="<strong>"+plan.focus+"</strong><div class=\\"route\\"><strong>"+
      laneLabel+"</strong>"+plan.instruction+"</div>";
  }}

  document.getElementById("lookup-show").addEventListener("click",function(){{
    var dayField=document.getElementById("lookup-day");
    var laneField=document.getElementById("lookup-lane");
    var day=Number(dayField.value);
    var lane=laneField.value;
    try{{
      renderLookup(day,lane);
    }}catch(error){{
      document.getElementById("lookup-result").textContent=CONFIG.copy.invalidInput;
    }}
  }});

  document.getElementById("print-calendar").addEventListener("click",function(){{window.print();}});
  document.getElementById("share-calendar").addEventListener("click",function(){{
    var status=document.getElementById("share-status");
    var data={{title:CONFIG.copy.shareTitle,url:location.href.split("#")[0]}};
    if(navigator.share){{
      navigator.share(data).catch(function(error){{
        if(error&&error.name==="AbortError"){{status.textContent=CONFIG.copy.cancelled;}}
      }});
    }}else if(navigator.clipboard){{
      navigator.clipboard.writeText(data.url).then(function(){{
        status.textContent=CONFIG.copy.copied;
      }}).catch(function(){{
        status.textContent=CONFIG.copy.copyFailed+" "+data.url;
      }});
    }}else{{
      status.textContent=data.url;
    }}
  }});

  async function registerWebMcp(){{
    if(!document.modelContext||!document.modelContext.registerTool)return;
    await document.modelContext.registerTool({{
      name:"plan_private_zhuyin_grade1_summer_calendar_day",
      description:CONFIG.toolDescription,
      inputSchema:CONFIG.inputSchema,
      annotations:{{readOnlyHint:true,untrustedContentHint:false}},
      execute:async function(input){{
        var plan=validateInput(input);
        var result={{
          result_type:"private_zhuyin_grade1_summer_calendar_day",
          deterministic:true,
          original_activity:true,
          not_assessment:true,
          no_score_grade_rank_or_diagnosis:true,
          no_readiness_or_learning_outcome_claim:true,
          no_child_data_received:true,
          no_progress_saved:true,
          sources_not_endorsement:true,
          plan:plan,
          official_sources:CONFIG.officialSources
        }};
        if(CONFIG.optionalApp)result.optional_lumibopomofo=CONFIG.optionalApp;
        return JSON.stringify(result);
      }}
    }});
  }}
  registerWebMcp().catch(function(error){{
    console.error("WebMCP tool registration failed.",error);
  }});
}})();
</script>
</body>
</html>
"""


def _index_card(locale: str) -> str:
    t = COPY[locale]
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
        f'{SLUG}.html">{html.escape(t["index_title"])}</a></h2>'
        f'<p>{html.escape(t["index_description"])}</p></article>'
    )


def _update_one_index(index: Path, locale: str) -> bool:
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    card = _index_card(locale)
    existing = re.compile(
        rf'<article class="card third"(?: data-tool="{SLUG}")?>'
        rf'<h2><a href="{SLUG}\.html">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    marker = '<section class="wrap grid">'
    if marker not in updated:
        raise RuntimeError(f"{index} is missing its tools grid")
    updated = updated.replace(marker, marker + card, 1)
    return write_text_if_changed(index, updated)


def update_tools_indexes(pages: Path = PAGES) -> int:
    return sum(
        _update_one_index(
            pages
            / ("tools" if locale == "en" else f"{locale}/tools")
            / "index.html",
            locale,
        )
        for locale in ALT_LOCALES
    )


def insert_answer_links(pages: Path = PAGES) -> int:
    changed = 0
    for slug in TARGET_ANSWER_SLUGS:
        for locale in ALT_LOCALES:
            directory = (
                pages / "answers" if locale == "en" else pages / locale / "answers"
            )
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _APP_STORE_ANCHOR.search(text)
            if not match:
                continue
            link = (
                f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
                f'data-zhuyin-grade1-summer-calendar-link="1" href="{canonical(locale)}" '
                f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
            )
            if write_text_if_changed(
                path,
                text[: match.start()] + link + text[match.start() :],
            ):
                changed += 1
    return changed


def build(
    pages: Path = PAGES,
    app_public: bool = False,
) -> list[str]:
    outputs = []
    for locale in ALT_LOCALES:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        target = pages / relative
        write_text_if_changed(
            target,
            render_page(locale, app_public=app_public),
        )
        outputs.append(canonical(locale))
    update_tools_indexes(pages)
    insert_answer_links(pages)
    return outputs


def main() -> None:
    app_public = APP_KEY in live_app_keys(APPSTORE, PAGES, refresh=False)
    outputs = build(app_public=app_public)
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"zhuyin grade1 summer calendar -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
