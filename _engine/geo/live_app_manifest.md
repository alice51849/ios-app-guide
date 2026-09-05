# 共用 live App manifest

`live_app_manifest.json` 是版本控制內、不因時間過期的唯一 roster identity。2026-09-05 的 Apple
iTunes Lookup（US、TW、JP、GB）唯讀查核確認 **46 款**，包含 BattAI；Zafe、
Zodira 未出現在該次公開查核中，不屬於這份 live roster。已上架 App 不因最新
ASC 版本 non-ready、報告 pending、查核暫時失敗或下載／購買雙零而移出 roster。

## 契約

`live_app_manifest.py` 統一供 `acquisition_feedback.py`、
`agent/acquisition_routing_runner.py`、`aso/growth_scorecard.py`、
`geo/outreach_scorecard.py`、`agent/app_outreach_optimizer.py`、
`agent/download_growth_controller.py`、`new_app_catchup.py` 及
`geo/aeo_answers.py` 的 coverage reader 使用：

- 版本化 identity 使用 `schema=lumi.live-app-roster/v1`、`version=1`、
  遞增 `revision`、`apps` 與 `roster_digest`，**沒有 TTL 或 availability 時間戳**。
- 可刷新 evidence 另使用 `schema=lumi.live-app-manifest/v2`、`version=2`，
  只放 gitignored `.growth-runtime/`（或指定的 private/build 路徑）。
- `apps` 是完整 `key → {app_id, name}`；拒絕重複 ID／JSON 欄位與不足 46 款。
- `roster_digest` 是 `apps` 經 UTF-8、`sort_keys=True`、
  `separators=(",", ":")` 序列化後的 SHA-256，亦必須符合版本化基線。
  僅重算 digest、用另一款替掉 BattAI 或更新筆數，不能繞過 identity drift。
- `generated_at`、各 App 的 `observations.checked_at` 必須含時區；
  不接受未來日期。`ttl_seconds` 必須為正整數且不超過 24 小時；到期即 stale。
- 每款 App 必須有一筆 `observations`：`live`、附原因的 `unknown`，或經三次
  完整 clean miss 才成立的 `unavailable`；`last_verified_at` 保留 last-good。
  個別觀測或整份 snapshot 過期時，consumer 將該 App 明確標為 `stale`。
  缺少 snapshot 則是 `unknown`，不是把整份版本化 roster 判為過期。
- 已驗證的 roster identity 不因 availability unknown/stale 失去 public eligibility；
  fresh verification 另計 `verified_public_apps`。三次 clean miss 只停用該 App
  的 public eligibility，不從逐款報表刪除 identity。
- `live_state_sha256` 與 roster、availability 共同綁定 acquisition generation。
  檢查時間仍須通過 TTL，但不納入重建指紋，避免每次查核都觸發昂貴完整收集。

版本化檔案只作身分錨點，**不能當成永久有效的 availability evidence**。
舊版 v1 inventory、`apps.json` 陣列、舊 45 款 baseline 都直接拒收，沒有自動
接受舊 schema 或靠 current-version readiness 重建子集合的 fallback。

## 唯讀刷新及 consumer

下列路徑均為 repository 內可重建、gitignored 的 `.growth-runtime/` 或 `build_*` 工作區；正式私有
acquisition runtime 仍使用既有 owner-only 路徑。

```sh
python3 geo/live_app_manifest.py --refresh \
  --output .growth-runtime/live-app-manifest.json

GROWTH_LIVE_MANIFEST=.growth-runtime/live-app-manifest.json \
  python3 geo/outreach_scorecard.py --require-complete

python3 acquisition_feedback.py --inventory-only \
  --live-inventory-output build_growth_inventory/private-inventory.json

python3 aso/growth_scorecard.py \
  --manifest build_growth_inventory/private-inventory.json \
  --feedback build_growth_inventory/feedback.json \
  --json-output build_growth_inventory/growth.json \
  --markdown-output build_growth_inventory/growth.md
```

`--refresh` 只 GET Apple 公開資料，不建立 ASC report request、不修改 App Store、
不發文、不 push。各 storefront 獨立重試；單一 storefront 失敗不抹掉其他市場
的正向證據，也不增加或重設 miss count。網路失敗或某款暫時查不到時仍保留完整
roster、last-good 與原因，availability advisory 不得中止 GEO publish。

新 live App 必須同時存在於已登錄的 `APPSTORE`／`APPS`，並由至少兩個獨立
Apple storefront 的當次結果確認，才可用 `--refresh --adopt` 自動納入。
`new_app_catchup.refresh_registered_inventory()` 在 registry 已落盤後呼叫此
路徑；roster 與 digest 受 lock 保護、原子替換，revision 遞增，納入來源 commit
後才保存 runtime snapshot。單來源或 aggregate 結果只列為 `pending_adoptions`；
未登錄 ID、identity drift 或壞 schema/digest 一律 hard fail，不改 roster。

Scorecard 本身不隱式查網路。`GROWTH_LIVE_MANIFEST` 指定同一份最新 snapshot；
**絕不**把 `GEO_PUBLIC_INVENTORY_BASELINE`／`apps.json` 當作 snapshot fallback。
`geo/publish.py` 在重建前刷新 private snapshot（或使用 catchup 已準備的同一份），
runtime snapshot 與內嵌 evidence 的 scorecard 都不寫進 Pages source。
Guide workflow 明確設定 v2 `GROWTH_LIVE_MANIFEST` 及 private `GEO_REPORTS`，
以 roster-scoped Actions cache 保留 last-good／三次 miss 狀態；部署副本必須
同步 `live_app_manifest.py`、`live_app_manifest.json` 及所有修改過的 consumer。
Optimizer 與 download controller 預設直接使用 feedback 內綁定的 manifest；
不再讀取無時間契約的 `.appstore_live_state.json`。既有 `--live-state` 參數
及其 `--live-manifest` 別名只接受 v2 manifest。

## 報表與失敗語意

- ASO growth scorecard 左連接完整 roster。`acquisition_feedback.py` 將當次
  `live_inventory` **先**綁入 feedback，再 `validate_feedback`、建立及核對
  signal，最後才寫入兩份輸出。任何 App transport failure 或 partial generation
  都不得覆蓋 last-good feedback/signal，不能為了 scorecard 放寬 ASC fail-closed。
- 與 ASC `6caa9c0a`／`c647e3d4` 整合時，保留 `load_feedback_snapshot`、
  `snapshot_fatal_issues`、pinned snapshot 與 snapshot output 路徑；
  `live_inventory` 綁定必須在 `validate_feedback`／`build_social_signal` 前。
  Scorecard 讀 last-good，並以 `snapshot_generated_at` 而非重新產生報表的時間
  驗資料年齡；cached data 不得因新 `generated_at` 被假裝成新測量。
- 缺少／無效 feedback、non-ready 或個別資料過期時，該 App 仍逐款列入 JSON
  及 Markdown；不可量測的值為 `null`／`unknown`，不是 `0`。
- 真正 ready 的下載／購買雙零仍保留；總數只加總有完整新鮮測量的 App，並
  標明分母。未知的額外 App 另列 unknown，identity drift 不能被靜默丟棄。
- Outreach 主表包含全部 46 款，包括 stale／unknown；registry 中另外兩款
  non-live App 可另表列示，不混入 live denominator。
- 私有 coverage 發佈也驗同一契約；已過期的列會明示 stale，不刷新原始證據
  時間。AEO 排序拒收舊版／過期 coverage，不把 45 款子集合當作完整。
- Outreach 的 availability unknown/stale 為 advisory（exit 0），schema／digest／
  roster 壞掉仍 exit 1；`--require-complete` 另行強制 owned-asset coverage，
  不因 availability outage 混淆 structural inventory completeness。
  ASO scorecard 缺測仍完整列示 unknown／stale 並回傳非零，不修改 last-good。
- ASO JSON／Markdown 使用 `0600`，不可提交私有營收資料或執行產物。
