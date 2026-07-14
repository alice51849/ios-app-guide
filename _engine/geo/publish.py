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

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide")
PY = sys.executable


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


def reconcile_lastmod_after_rebase(env):
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
            "Reconcile truthful sitemap lastmod after rebase",
        ],
        cwd=PAGES,
    )


def main():
    env = dict(os.environ, GEO_SITE=SITE)
    # 1) 重建
    require([PY, os.path.join(HERE, "build_pages_i18n.py")], env=env)
    require([PY, os.path.join(HERE, "passport_photo_print_sheet.py")], env=env)
    require([PY, os.path.join(HERE, "document_scan_planner.py")], env=env)
    require([PY, os.path.join(HERE, "blurry_photo_diagnostic.py")], env=env)
    require([PY, os.path.join(HERE, "daily_checklist_planner.py")], env=env)
    require([PY, os.path.join(HERE, "screen_time_block_planner.py")], env=env)
    require([PY, os.path.join(HERE, "photo_storage_cleanup_planner.py")], env=env)
    require([PY, os.path.join(HERE, "vocabulary_habit_planner.py")], env=env)
    require([PY, os.path.join(HERE, "wordmate_language_support.py")], env=env)
    require([PY, os.path.join(HERE, "portfolio_app_finder.py")], env=env)
    require([PY, os.path.join(HERE, "gen_data_hub.py")], env=env)
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
    require([PY, os.path.join(HERE, "add_related_answers.py")], env=env)
    require(
        [PY, os.path.join(HERE, "add_related_answers.py"), "--locale", "zh-Hant"],
        env=env,
    )
    require([PY, os.path.join(HERE, "add_related_tools.py")], env=env)
    require(
        [PY, os.path.join(HERE, "add_related_tools.py"), "--locale", "zh-Hant"],
        env=env,
    )
    require([PY, os.path.join(HERE, "fix_en_hreflang.py")], env=env)
    require([PY, os.path.join(HERE, "gen_image_sitemap.py")], env=env)
    require([PY, os.path.join(HERE, "gen_linkset.py")], env=env)
    require([PY, os.path.join(HERE, "gen_social_previews.py")], env=env)
    require([PY, os.path.join(HERE, "gen_smart_app_banners.py")], env=env)
    require([PY, os.path.join(HERE, "gen_mobile_app_identity.py")], env=env)
    require([PY, os.path.join(HERE, "gen_mobile_store_ctas.py")], env=env)
    require([PY, os.path.join(HERE, "gen_app_store_qr_ctas.py")], env=env)
    require([PY, os.path.join(HERE, "gen_app_store_share_ctas.py")], env=env)
    require([PY, os.path.join(HERE, "gen_guide_design.py")], env=env)
    require([PY, os.path.join(HERE, "gen_llms.py"), "--cached-live"], env=env)
    require([PY, os.path.join(HERE, "zhuyin_resourcesync.py")], env=env)
    require([PY, os.path.join(HERE, "gen_feed.py")], env=env)
    require([PY, os.path.join(HERE, "gen_sitemap_lastmod.py")], env=env)
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
             "commit", "-m", "Update multilingual GEO pages"], cwd=PAGES)
    # 2b) 健壯 push:固定在 main;被拒就以「我方重生內容為準」rebase(-X theirs)後重試;
    #     萬一 rebase 仍衝突,abort + 對齊遠端(絕不留下 detached/衝突壞狀態,下輪重生再推)。
    CRED = "credential.helper=!gh auth git-credential"
    require(["git", "checkout", "main"], cwd=PAGES)
    pushed = False
    for _ in range(3):
        rc, _ = run(["git", "-c", CRED, "push", "-q", "origin", "main"], cwd=PAGES)
        if rc == 0:
            pushed = True
            break
        rc2, _ = run(["git", "-c", CRED, "pull", "--rebase", "-X", "theirs",
                      "-q", "origin", "main"], cwd=PAGES)
        if rc2 != 0:
            run(["git", "rebase", "--abort"], cwd=PAGES)
            print("⚠️ rebase 衝突已中止；本機提交保留，等待下次重試。")
            break
        reconcile_lastmod_after_rebase(env)
    if not pushed:
        raise RuntimeError("未能 push；已保留本機提交，未送出 IndexNow。")
    # 3) IndexNow:有變更才推
    require([PY, os.path.join(HERE, "indexnow_submit.py")], env=env)
    print("\n✅ GEO 發布完成")


if __name__ == "__main__":
    main()
