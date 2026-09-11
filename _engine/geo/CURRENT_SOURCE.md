# 純外宣 current-source 契約

`geo/live_app_manifest.json` 是已審閱的 identity authority；
`geo/current_source.py` 是 GEO、videogen、social 與 owned consumers 共用的驗證器。
`geo/official_locales.py` 提供唯一官方 locale 清單。本次契約是 **47 App IDs × 50 locales = 2350 pairs**：
Zipbox／BattAI 在內，Zodira／Zafe 不在內。Creative banks 可保留歷史資料，但不得決定 live membership。

## Identity 與 observation 分離

- Source 不依賴網路，不會因 iTunes 偶發回應增加／刪除 App。
- `live-app-manifest/v3` observation 必須綁定 `source_sha256`、
  `locale_roster_sha256`、`observed_at`、47 個 identity 與完整 pair denominator。
- `source_sha256` 是 roster 原始 bytes 的 SHA-256；`observed_at` 是該次 Apple GET run 的時間。
  複製、載入、測試或重新產生相同 evidence 不得刷新觀察時間。
- 公開生成必須通過 `require_public_inventory()`。缺檔、過期、unknown、
  identity／SHA 不符一律整批失敗；不得縮成 45/46 款，也不得 fallback 到舊 registry。
- `.appstore_live_state.json` 只接受 `lumi.live-state/v2` 的完整、有來源與時效的 observation。
  無 schema／時間的舊 state 不是可信 baseline，即使它碰巧也有 47 個 IDs。
- `--adopt` 不再能在 runtime 寫 source。新 App 必須以明確的 source migration、
  creative facts、exact-locale tests 與獨立 review 一起提交。

## 唯讀更新 evidence

以下只會做公開 Apple GET 與本機檔案寫入，不做 ASC mutation 或發文：

```sh
python3 geo/live_app_manifest.py --refresh \
  --output .growth-runtime/live-app-manifest.json \
  --live-state-output geo/pages/.appstore_live_state.json
export GROWTH_LIVE_MANIFEST="$PWD/.growth-runtime/live-app-manifest.json"
```

同一 workflow 的 consumers 共用同一 observation。明確指定但失效的 observation
不會被隱性網路重試或其他 state 取代；應先重跑上述 GET-only preflight。

## 鏡像同步

不能手抄清單。Identity 三檔使用同一份 source 精準複製與反查：

```sh
python3 geo/sync_current_source.py --layout guide --target geo/pages
python3 geo/sync_current_source.py --layout social --target workspaces/threads-autopilot
python3 geo/sync_current_source.py --layout owned --target growth-agent-deploy
# 對同一命令加入 --check 只驗證 byte-for-byte 一致。
```

修改 consumer 後仍須同步既有 `_engine` 對應檔；不得只同步 JSON 而留下舊 parser。
不重寫 conversion-route feature 的文案、路由 source 或 generated content。

## 驗證

- `geo.tests.test_current_source`：固定 GET evidence、47 IDs、50 locales、
  2350 pairs、removed／added、SHA、時效與禁止 fallback。
- `geo.tests.test_current_source_generators`：App／hub／decision／alternatives／persona
  共用 eligibility；實際生成 2350 install-decision records，以及 Zipbox／BattAI 各 50 語 App／hub HTML。
- Social `test_current_source`：2350 筆母語 campaign 與缺 App 時先失敗。
- Owned `agent/test_current_source.py`：47／50 source 與禁止 ratings／registry fallback。

來源：Caitlyn 2026-09-11 指令，Session `2fd0fa72-ea4f-49fe-94ee-f12ec0ac0d6a`。
