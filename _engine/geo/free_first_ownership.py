#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""免費門歸屬 — 一條品類問句的 answer 頁該由付費版還是免費版**產生**。

背景(2026-09-05 稽核):`gen_free_first_links` 只換門不換事實,遇到「付費 key
產生的答案本身斷言付費購買模式」就整頁不換(誠實優先)。稽核發現其中一批
頁面其實是**免費兄弟版能誠實回答**的品類問句(Lumi 四對的 `_PRO_INHERITS`
共用題、WiFi Aid Lite persona 已涵蓋的 Wi-Fi 診斷題),卻因為頁面當初由付費
key 產生而一直停在付費門 —— 頁→下載 0–2.7% 的那道門。

規則(產生器輸入層,不看頁面文字):
  • 明確要求「零內購」的問句永遠歸付費版(配對免費版靠內購解鎖,不是答案)。
  • 只搬「今天卡在付費門」的那一類:付費 key 自己的事實斷言付費購買模式(所以
    gen_free_first_links 拒絕換門),而免費兄弟版交給 answer_facts 能產出**非泛用**
    且**不含付費模式字樣**的事實 → 改由免費版擁有;其餘問句維持原歸屬,門由
    既有換門處理(頁面文案講哪一版,門就開哪一版)。
  • 判準只取自 canon 側輸入(queries / answer_facts),不可拿頁面文字當身份證據。

消費者:`queries.ALL`(產生時的歸屬)、`reclaim_free_first_answers`(把既有
付費門頁重生成免費門)、`audit_free_first_links --strict`(fail-closed gate)。
"""
from __future__ import annotations

import functools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "social") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "social"))

from app_pairs import free_to_paid, paid_to_free  # noqa: E402
from videogen.registry import APPS  # noqa: E402

# 明確要求「零內購」的問句:配對免費版一定有內購(free_with_lifetime_unlock),
# 所以它**不是**這題的答案。
PAID_ONLY_INTENT_RE = re.compile(r"in[-\s]?app purchase", re.I)
# 代表「付費下載 / 一次付清價格」的字樣(不分大小寫)。
PAID_MODEL_RESIDUE_RE = re.compile(
    r"paid[-\s]download|paid[-\s]upfront|upfront price", re.I
)


def paid_only_intent(question: str) -> bool:
    return bool(PAID_ONLY_INTENT_RE.search(question))


def facts_text(facts) -> str:
    """把 answer_facts 的覆蓋層攤平成純文字,供付費模式偵測。"""
    parts = []
    for value in (facts or {}).values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("q", "")))
                    parts.append(str(item.get("a", "")))
    return " ".join(parts)


@functools.lru_cache(maxsize=None)
def free_sibling_facts(question: str, free_key: str):
    """免費版交給 answer_facts 產出的事實(None = 只能落回泛用樣板)。"""
    import answer_facts  # 延遲匯入:內容庫很大,只有真的要判斷時才載

    app = APPS.get(free_key)
    if not app:
        return None
    return answer_facts.topic_facts(question, free_key, app) or None


def free_answers_honestly(question: str, free_key: str) -> bool:
    """免費版能不能**誠實**回答這題:有專屬事實、且事實不斷言付費購買模式。"""
    if paid_only_intent(question):
        return False
    facts = free_sibling_facts(question, free_key)
    if not facts:
        return False
    return not PAID_MODEL_RESIDUE_RE.search(facts_text(facts))


@functools.lru_cache(maxsize=None)
def paid_asserts_paid_model(question: str, paid_key: str) -> bool:
    """付費 key 自己產出的事實是否斷言付費購買模式(換門會變成假話的那類頁)。"""
    import answer_facts  # 延遲匯入

    app = APPS.get(paid_key)
    if not app:
        return False
    facts = answer_facts.topic_facts(question, paid_key, app)
    return bool(facts) and bool(PAID_MODEL_RESIDUE_RE.search(facts_text(facts)))


def should_move_to_free(paid_key: str, question: str) -> bool:
    """只搬「今天卡在付費門」的那一類:付費事實斷言付費模式(所以換門被拒),
    而免費兄弟版能誠實回答。其餘品類問句維持原歸屬 —— 它們的門由
    gen_free_first_links 的換門處理,不需要改產生器歸屬。"""
    free_key = paid_to_free().get(paid_key)
    if not free_key or paid_only_intent(question):
        return False
    return paid_asserts_paid_model(question, paid_key) and free_answers_honestly(
        question, free_key
    )


def owner_for(paid_key: str, question: str) -> str:
    """回傳應該產生這一頁的 key(付費 key 或其免費配對)。"""
    free_key = paid_to_free().get(paid_key)
    if not free_key:
        return paid_key
    return free_key if should_move_to_free(paid_key, question) else paid_key


def apply_free_first_ownership(all_queries: dict) -> tuple[dict, dict]:
    """依歸屬規則重排 {key: [question]},回 (新清單, 搬動紀錄)。

    搬動紀錄:{"to_free": {paid: [q]}, "to_paid": {free: [q]}};清單順序保留,
    新加入的問句排在該 key 清單尾端,大小寫不同視為同一題。
    """
    pairs = paid_to_free()
    result = {key: list(values) for key, values in all_queries.items()}
    moves = {"to_free": {}, "to_paid": {}}

    def add(key, question):
        seen = {q.lower() for q in result.setdefault(key, [])}
        if question.lower() not in seen:
            result[key].append(question)

    for paid, free in sorted(pairs.items()):
        if paid not in result:
            continue
        keep = []
        for question in result[paid]:
            if should_move_to_free(paid, question):
                moves["to_free"].setdefault(paid, []).append(question)
                add(free, question)
                continue
            keep.append(question)
        result[paid] = keep
    for free, paid in sorted(free_to_paid().items()):
        if free not in result:
            continue
        keep = []
        for question in result[free]:
            if paid_only_intent(question):
                moves["to_paid"].setdefault(free, []).append(question)
                add(paid, question)
                continue
            keep.append(question)
        result[free] = keep
    return result, moves


if __name__ == "__main__":
    import json
    import queries

    print(json.dumps(queries.FREE_FIRST_MOVES, ensure_ascii=False, indent=1))
