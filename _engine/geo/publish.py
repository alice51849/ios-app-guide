#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 一鍵發布 — 重建多語頁 → git commit/push(GitHub Pages)→ IndexNow 推送。

ASO 文案(data/<app>_full.json)更新後,跑這支即可讓全球 LLM 索引更新。可排程。

    python geo/publish.py            # 全量重建+部署+推送
    python geo/publish.py --no-push  # 只重建(不部署/推送)
"""
import os
import subprocess
import sys

from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE)
STANDARD_SITE_GUIDE_CONTRACT_URL = os.environ.get(
    "STANDARD_SITE_GUIDE_CONTRACT_URL",
    "https://raw.githubusercontent.com/alice51849/"
    "alice51849.github.io/main/standard_site_guide_contract.json",
)
PY = sys.executable
COMMIT_TRAILERS = (
    "\n\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
    "\nCopilot-Session: b7c8e3bc-512c-4743-b32a-1ca766a33c21"
)


def run(cmd, cwd=None, env=None):
    print(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip()[-1500:])
    return r.returncode, out


def require(cmd, cwd=None, env=None):
    returncode, output = run(cmd, cwd=cwd, env=env)
    if returncode != 0:
        raise RuntimeError(
            f"Command failed ({returncode}): {' '.join(cmd)}\n"
            f"{output[-1500:]}"
        )
    return output


def sync_standard_site(env):
    """Reconcile the verified Standard.site discovery links (see geo-daily.yml)."""
    require(
        [
            PY,
            os.path.join(HERE, "sync_standard_site.py"),
            "--site-root",
            PAGES,
            "--contract-url",
            STANDARD_SITE_GUIDE_CONTRACT_URL,
            "--allow-initial-404",
            "--timeout",
            "10",
            "--retries",
            "3",
            "--retry-delay",
            "2",
        ],
        env=env,
    )


def reconcile_lastmod_after_rebase(env):
    sync_standard_site(env)
    require([PY, os.path.join(HERE, "reconcile_answer_semantics.py")], env=env)
    require([PY, os.path.join(HERE, "publisher_intent_visuals.py")], env=env)
    require([PY, os.path.join(HERE, "gen_sitemap_lastmod.py")], env=env)
    require(["git", "add", "-A"], cwd=PAGES)
    returncode, output = run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=PAGES,
    )
    if returncode == 0:
        return
    if returncode != 1:
        raise RuntimeError(
            "Unable to inspect post-rebase sitemap changes:\n"
            f"{output[-1500:]}"
        )
    require(
        [
            "git",
            "-c",
            "user.name=alice51849",
            "-c",
            "user.email=alice51849@users.noreply.github.com",
            "commit",
            "-m",
            "Reconcile truthful sitemap lastmod after rebase" + COMMIT_TRAILERS,
        ],
        cwd=PAGES,
    )


def main():
    env = dict(os.environ, GEO_SITE=SITE)
    if "--no-push" not in sys.argv:
        branch = require(["git", "branch", "--show-current"], cwd=PAGES).strip()
        if branch != "main":
            raise RuntimeError(
                f"Pages publishing requires main, found {branch or 'detached'}"
            )
    # 1) 重建
    require(
        [PY, os.path.join(HERE, "refresh_storefront_availability.py")],
        env=env,
    )
    require([PY, os.path.join(HERE, "build_pages_i18n.py")], env=env)
    require([PY, os.path.join(HERE, "aeo_guide.py"), "--missing"], env=env)
    require([PY, os.path.join(HERE, "passport_photo_print_sheet.py")], env=env)
    require([PY, os.path.join(HERE, "document_scan_planner.py")], env=env)
    require([PY, os.path.join(HERE, "blurry_photo_diagnostic.py")], env=env)
    require([PY, os.path.join(HERE, "daily_checklist_planner.py")], env=env)
    require([PY, os.path.join(HERE, "cycle_privacy_planner.py")], env=env)
    require([PY, os.path.join(HERE, "screen_time_block_planner.py")], env=env)
    require([PY, os.path.join(HERE, "hourstag_work_hours_tool.py")], env=env)
    require([PY, os.path.join(HERE, "photo_storage_cleanup_planner.py")], env=env)
    require([PY, os.path.join(HERE, "film_look_recipe_planner.py")], env=env)
    require([PY, os.path.join(HERE, "family_routine_card_planner.py")], env=env)
    require([PY, os.path.join(HERE, "resume_evidence_planner.py")], env=env)
    require([PY, os.path.join(HERE, "vocabulary_habit_planner.py")], env=env)
    require([PY, os.path.join(HERE, "toeic_study_allocation_planner.py")], env=env)
    require([PY, os.path.join(HERE, "wordmate_language_support.py")], env=env)
    require([PY, os.path.join(HERE, "portfolio_app_finder.py")], env=env)
    require([PY, os.path.join(HERE, "gen_hubs.py")], env=env)
    require([PY, os.path.join(HERE, "portfolio_cost_calculator.py")], env=env)
    # W19 需求導向工具頁(shortlist.json 驗證過有搜尋量的 checker/converter/maker)
    require([PY, os.path.join(HERE, "demand_tools.py")], env=env)
    require([PY, os.path.join(HERE, "outreach_scorecard.py")], env=env)
    require([PY, os.path.join(HERE, "gen_data_hub.py")], env=env)
    # 這支之前沒被任何排程呼叫過,線上那份 feed 是手動跑出來的。
    require([PY, os.path.join(HERE, "agent_product_feed.py")], env=env)
    require([PY, os.path.join(HERE, "family_travel_static_api.py")], env=env)
    require([PY, os.path.join(HERE, "family_travel_observation_passport.py")], env=env)
    require([PY, os.path.join(HERE, "family_travel_opds_catalog.py")], env=env)
    require([PY, os.path.join(HERE, "family_travel_ro_crate.py")], env=env)
    require([PY, os.path.join(HERE, "family_travel_mission_cards.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_heritage_lesson_plan.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_readiness_tool.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_grandparent_call_kit.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_picture_book_club_kit.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_parent_teacher_handoff_kit.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_library_storytime_kit.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_grade1_summer_calendar.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_blending_card_generator.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_sentence_reading_cards.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_mini_reader.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_story_sequence_cards.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_grade1_guide.py")], env=env)
    # 開學季 zh-Hant 內容叢集(hub + 先修/怎麼教/教學順序/符號表/拼讀)。
    # 必須排在 zhuyin_grade1_guide.py 之後:兩者都會重建 sitemap_guides.xml,
    # 由後跑的這支把新頁一起寫進去。
    require([PY, os.path.join(HERE, "zhuyin_back_to_school.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_anki_deck.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_skos_vocabulary.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_croissant_dataset.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_frictionless_package.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_csvw_metadata.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_bagit_package.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_ocfl_object.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_iiif_presentation.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_ro_crate.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_mets_premis_package.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_static_api.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_ldes_event_stream.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_ore_resource_map.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_lms_assessment_bank.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_epub_opds.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_library_catalog.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_oer_metadata.py")], env=env)
    require([PY, os.path.join(HERE, "zhuyin_dcat_catalog.py")], env=env)
    require(
        [PY, os.path.join(HERE, "bopomofo_symbol_contrast_cards.py")], env=env
    )
    require(
        [PY, os.path.join(HERE, "bopomofo_matching_pair_cards.py")], env=env
    )
    require(
        [PY, os.path.join(HERE, "bopomofo_bingo_cards.py")], env=env
    )
    require(
        [PY, os.path.join(HERE, "bopomofo_flashcards.py")], env=env
    )
    require(
        [PY, os.path.join(HERE, "bopomofo_practice_sheet.py")], env=env
    )
    require(
        [PY, os.path.join(HERE, "prioritize_trip_planet_resources.py")],
        env=env,
    )
    require(
        [PY, os.path.join(HERE, "refresh_primary_resource_answers.py")],
        env=env,
    )
    require(
        [
            PY,
            os.path.join(HERE, "cleanup_localized_assets.py"),
            "--cached-live",
        ],
        env=env,
    )
    require(
        [
            PY,
            os.path.join(HERE, "aeo_answers.py"),
            "--cached-live",
            "--limit",
            "0",
        ],
        env=env,
    )
    require(
        [
            PY,
            os.path.join(HERE, "reconcile_answer_semantics.py"),
            "--repair",
        ],
        env=env,
    )
    require(
        [PY, os.path.join(HERE, "family_outing_weather_planner.py")],
        env=env,
    )
    require([PY, os.path.join(HERE, "add_related_answers.py")], env=env)
    # 每個官方語系的 answers 之間也要有同主題橫向連結,不能只有 en/zh-Hant。
    # 沒有 answers 目錄的語系會自己 no-op。
    for locale in OFFICIAL_LOCALES:
        require(
            [PY, os.path.join(HERE, "add_related_answers.py"),
             "--locale", locale],
            env=env,
        )
    require([PY, os.path.join(HERE, "add_related_tools.py")], env=env)
    for locale in OFFICIAL_LOCALES:
        require(
            [PY, os.path.join(HERE, "add_related_tools.py"), "--locale", locale],
            env=env,
        )
    # 工具頁的「新工具上線通知」訂閱。跑在工具頁產生器之後,否則會被覆蓋。
    # tool_email_capture.json 沒填 endpoint 時它只會移除舊區塊,不會上線壞表單。
    require([PY, os.path.join(HERE, "gen_tool_email_capture.py")], env=env)
    # 檔期曝光:讓入口頁跟著開學季/報稅季/新年走(agent/season_engine.py 算的)
    require([PY, os.path.join(HERE, "gen_seasonal_spotlight.py")], env=env)
    require([PY, os.path.join(HERE, "fix_en_hreflang.py")], env=env)
    require([PY, os.path.join(HERE, "gen_webstories.py")], env=env)
    require([PY, os.path.join(HERE, "gen_webstories_i18n.py")], env=env)
    require([PY, os.path.join(HERE, "gen_linkset.py")], env=env)
    require([PY, os.path.join(HERE, "gen_social_previews.py")], env=env)
    require([PY, os.path.join(HERE, "gen_image_sitemap.py")], env=env)
    require([PY, os.path.join(HERE, "gen_mobile_app_identity.py")], env=env)
    require([PY, os.path.join(HERE, "gen_webmcp_install_tools.py")], env=env)
    require([PY, os.path.join(HERE, "portfolio_app_catalog_api.py")], env=env)
    require([PY, os.path.join(HERE, "publisher_intent_catalog.py")], env=env)
    require([PY, os.path.join(HERE, "publisher_intent_visuals.py")], env=env)
    require([PY, os.path.join(HERE, "app_video_lessons.py")], env=env)
    require(
        [
            PY,
            os.path.join(HERE, "gen_social_previews.py"),
            "--oembed-only",
        ],
        env=env,
    )
    require(
        [PY, os.path.join(HERE, "gen_github_discovery_readmes.py")],
        env=env,
    )
    require([PY, os.path.join(HERE, "gen_publisher_disclosures.py")], env=env)
    require([PY, os.path.join(HERE, "gen_guide_design.py")], env=env)
    # 免費版優先導流:品類需求頁的商店 CTA 換成免費/Lite 版(app_pairs.py 11 對)。
    # 必須跑在 normalize/decision-cards/banner/QR/attribution 鏈之前,讓下游
    # 依「換門後」的連結重建 QR 與歸因。
    # 換門前先拍一張身份快照(頁面 store id + social 分享圖),換門後用同一支
    # 稽核對照。2026-08-31:換門模組把本來就正確的免費門頁翻成付費 id、分享圖
    # 沒跟著換,gen_social_previews / gen_image_sitemap 都已經跑過了沒人會修,
    # 雲端 geo-daily 於是連續失敗、內容生產停擺兩天。這個 gate 讓同樣的事在
    # 發布前就擋下來,而不是隔天在雲端炸。
    identity_before = os.path.join(HERE, "reports", "free_first_identity_before.json")
    require(
        [
            PY,
            os.path.join(HERE, "audit_free_first_identity.py"),
            "--snapshot",
            identity_before,
        ],
        env=env,
    )
    require([PY, os.path.join(HERE, "gen_free_first_links.py")], env=env)
    require(
        [
            PY,
            os.path.join(HERE, "audit_free_first_identity.py"),
            "--baseline",
            identity_before,
            "--report",
            os.path.join(HERE, "reports", "free_first_identity.json"),
        ],
        env=env,
    )
    require([PY, os.path.join(HERE, "gen_app_store_facts.py")], env=env)
    require([PY, os.path.join(HERE, "app_install_decision_routes.py")], env=env)
    # Source-of-truth lives in GrowthEngine. A newly verified App is allowed to
    # leave only its unreviewed route cell degraded here, so unrelated daily
    # generators can still finish and push. The separate Pages pre-upload gate
    # remains strict and will not deploy this materialization.
    require(
        [
            PY,
            os.path.join(HERE, "high_intent_decision_routes.py"),
            "--output-dir",
            PAGES,
            "--materialize-current-inventory",
        ],
        env=env,
    )
    require([PY, os.path.join(HERE, "normalize_app_store_links.py")], env=env)
    # ResourceSync writes a Bopomofo page with a clean App Store URL, so it
    # must run before every conversion surface and the attribution pass.
    require([PY, os.path.join(HERE, "zhuyin_resourcesync.py")], env=env)
    require([PY, os.path.join(HERE, "gen_app_decision_cards.py")], env=env)
    require([PY, os.path.join(HERE, "gen_smart_app_banners.py")], env=env)
    require([PY, os.path.join(HERE, "gen_mobile_store_ctas.py")], env=env)
    require([PY, os.path.join(HERE, "gen_app_store_qr_ctas.py")], env=env)
    require([PY, os.path.join(HERE, "gen_app_store_share_ctas.py")], env=env)
    # Off-page reach: give every page a store path, keep only App-Store-reachable
    # locales in the index, then attribute every outbound store link.  These run
    # after the page generators on purpose — editing built pages outside the
    # pipeline is silently undone by the next publish.
    # App 頁 → 該 App 的 answers/guides(每頁 3–8 條)。**必須跑在
    # gen_free_first_links / normalize_app_store_links 之後**:那兩支會把
    # 商店連結換成免費版,頁面的 App Store ID 會變,提早跑就會挑到舊 App 的
    # 問答,下一輪再被改掉。只加站內連結,不動商店連結,所以不影響下游
    # 「一頁一個 App ID」的身份判定。
    require([PY, os.path.join(HERE, "gen_app_page_related.py")], env=env)
    # 連結圖補完:把只存在於 sitemap 的孤兒頁接回首頁 3 次點擊內。必須跑在
    # 所有頁面產生器之後(才掃得到全部頁),而且要在 build_pages_i18n 重寫
    # 語系首頁之後,否則注入的導覽會被蓋掉。
    require([PY, os.path.join(HERE, "gen_link_hubs.py")], env=env)
    require([PY, os.path.join(HERE, "gen_store_reach.py")], env=env)
    require([PY, os.path.join(HERE, "gen_locale_indexation.py")], env=env)
    # 內容其實沒在地化的頁(標題+描述與英文一字不差,正文也是英文)不該以
    # 獨立頁面身分進索引 —— 它們只會跟自己的英文原頁互搶 canonical。這支
    # 先前只被手動跑過一次,沒進管線,於是每次發布都把 noindex 洗掉
    # (2026-08-12 實測 noindexed=0、重複 21,713 頁)。
    require(
        [PY, os.path.join(HERE, "dedupe_locale_meta.py"), "--apply"], env=env
    )
    # 連結圖第二趟(冪等,靜態樹上 0 變更,約 15 秒)。gen_link_hubs 是「注入
    # 受管理區塊」,而 build_pages_i18n / dedupe_locale_meta 這類產生器會整份
    # 重寫語系首頁 —— 只要有一支跑在它後面把區塊洗掉,整個語系的子樹就會在
    # 下一次發布前變成孤兒(2026-08-10 就這樣上線過:全站語系首頁都沒有 hub
    # 導覽,4,413 個可索引頁零入連)。dedupe 也會改頁面的 noindex 狀態,連結圖
    # 要用**最終**的 noindex 狀態重算才正確。跑第二趟讓最後落地的狀態一定是對的。
    require([PY, os.path.join(HERE, "gen_link_hubs.py")], env=env)
    # 以同一份最終靜態樹封閉 sitemap + link graph，讓新生成的 high-intent
    # routes 進 sitemap index 且不成為孤兒頁。
    require([PY, os.path.join(HERE, "close_sitemap_graph.py")], env=env)
    require([PY, os.path.join(HERE, "gen_store_attribution.py")], env=env)
    require([PY, os.path.join(HERE, "validate_webstories.py")], env=env)
    require([PY, os.path.join(HERE, "gen_llms.py"), "--cached-live"], env=env)
    require([PY, os.path.join(HERE, "gen_feed.py")], env=env)
    sync_standard_site(env)
    require([PY, os.path.join(HERE, "reconcile_answer_semantics.py")], env=env)
    require([PY, os.path.join(HERE, "publisher_intent_visuals.py")], env=env)
    require([PY, os.path.join(HERE, "gen_sitemap_lastmod.py")], env=env)
    # 發布前的硬閘門:可索引頁一頁都不可以從首頁點不到。這是量測不是產生 ——
    # 它擋的是「某支下游產生器把連結圖洗掉,結果我們把孤兒站推上線」。
    # 失敗時整條管線中止、不 commit、不 push、不送 IndexNow;工作樹留在原地,
    # 修好再跑一次就好。noindex 頁不算在內(它們本來就不進索引)。
    require(
        [
            PY,
            os.path.join(HERE, "audit_link_depth.py"),
            "--max-indexable-orphans",
            "0",
        ],
        env=env,
    )
    # 日常只驗 materialization：已審 route 必須完整閉合；新增 App 的未審
    # copy gap 可明確 degraded。Pages upload 仍另跑 strict pre-upload gate。
    require(
        [
            PY,
            os.path.join(HERE, "high_intent_decision_routes.py"),
            "--output-dir",
            PAGES,
            "--check-materialization-closure",
        ],
        env=env,
    )
    if "--no-push" in sys.argv:
        print("\n(--no-push:略過部署/推送)")
        return
    # 2) git commit + push(用 porcelain 偵測變更,locale 無關)
    require(["git", "add", "-A"], cwd=PAGES)
    status = require(["git", "status", "--porcelain"], cwd=PAGES)
    if not status.strip():
        print("內容無變更,略過部署與 IndexNow。")
        print("\n✅ GEO 發布完成(無變更)")
        return
    require(["git", "-c", "user.name=alice51849",
             "-c", "user.email=alice51849@users.noreply.github.com",
             "commit", "-m", "Update multilingual GEO pages" + COMMIT_TRAILERS],
            cwd=PAGES)
    # 2b) 健壯 push:固定在 main;被拒就安全 rebase 後重試。
    CRED = "credential.helper=!gh auth git-credential"
    pushed = False
    for _ in range(3):
        rc, _ = run(["git", "-c", CRED, "push", "-q", "origin", "main"], cwd=PAGES)
        if rc == 0:
            pushed = True
            break
        rc2, _ = run(["git", "-c", CRED, "pull", "--rebase",
                      "-q", "origin", "main"], cwd=PAGES)
        if rc2 != 0:
            run(["git", "rebase", "--abort"], cwd=PAGES)
            print("⚠️ rebase 衝突已中止；本機提交保留，等待下次重試。")
            break
        reconcile_lastmod_after_rebase(env)
    if not pushed:
        raise RuntimeError("未能 push；已保留本機提交，未送出 IndexNow。")
    # 3) IndexNow:有變更才推
    require(
        [
            PY,
            os.path.join(HERE, "indexnow_submit.py"),
            "--pages-dir",
            PAGES,
        ],
        env=env,
    )
    print("\n✅ GEO 發布完成")


if __name__ == "__main__":
    main()
