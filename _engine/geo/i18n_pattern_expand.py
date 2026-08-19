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
LIST_SEP = {"ja": "、", "zh-Hant": "、", "zh-Hans": "、"}

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
                    parts = [x.strip() for x in raw.split(",")]
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
