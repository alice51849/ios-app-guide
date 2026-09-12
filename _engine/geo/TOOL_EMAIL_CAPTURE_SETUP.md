# Buttondown owned-email：exact47 × Apple official50

## 授權與證據界線

本契約只產生候選內容、驗證同意、計算寄送資格及執行 GET readback。
**沒有寄送／建立 draft／建立 subscriber／自動訂閱／ASC mutation／社群
writer，也不部署或 push main。** `sender_enabled` 固定為 `false`；
`owned_email_sender.plan()` 即使找到合格讀者，也只回 `plan_only`、
`send_allowed=false`、`send_requests=0`。

2026-09-12 新要求：47 款 canonical sellable App × 50 官方 locale，
capture inventory 恰好 **2350** 格；原有五語免費工具通知不可轉作 App 行銷。
來源：Session `2fd0fa72-ea4f-49fe-94ee-f12ec0ac0d6a`，
「新的第5位 live worker／Buttondown capture consent sender readback exact47×50」。

| 證據 | 可以證明 | 不可以證明 |
|---|---|---|
| 原始碼／HTML／表單／HTTP 200 | `content_ready`，且必須綁定內容 digest | 有訂閱者、有人收到信、原生發送 |
| 完整 Buttondown subscriber GET census | 服務商當下名單總量 | `regular` 等於 double opt-in |
| 已驗 HMAC 的 confirmation＋前置 scope＋新鮮 subscriber GET | 特定 App／locale／campaign 的同意資格 | 郵件已寄送或送達 |
| 原生 email ID GET＋其公開 archive URL GET＋完整 body/scope | `buttondown_public_archive_verified` | 指定真人已收到信 |
| queue／workflow success／本機 receipt 的自填旗標 | 無原生發送證據 | 任何 subscriber/delivery 數量 |

未知名單量回 `UNKNOWN`；有證據的 double opt-in／native 數量才可累計。
產生的 content inventory 永遠保持 verified subscribers=0、subscriber total=
`UNKNOWN`、native emails=0，不可把 2350 張表單當成 2350 位訂閱者。

## 內容與同意

- `owned_email_copy.json` 是 50 locale 母語文案唯一來源，包括 email label、
  成人明確同意、Buttondown 處理資料、隱私、取消訂閱及第一方發行者揭露。
  缺語、缺欄或未知 locale 一律 fail closed；沒有英文 fallback。
- 原有 `gen_tool_email_capture.py` 保留 `new_free_tools_v1` scope；
  App 表單使用獨立的 `app_updates_v1`。舊名單不遷移、不擴權、不自動補同意。
- `<locale>/email/<app_key>.html` 一 App × 一 locale × 一 campaign，
  共 2350 張。另有 50 個語系目錄與 1 個語言入口，不算 capture 格。
  這些偏好頁是 `noindex,follow`，不冒充 2350 篇搜尋內容。
- 表單只收 email 與 scope metadata，使用官方 `metadata__<key>` 欄位。
  唯一的 `metadata__owned_consent=yes` 來自**未預選、required 的 checkbox**。
  沒有 `type=regular`、付費名單、import、JS 自動提交或「訂閱才能用工具」。
- 同意文字的 digest 同時綁 App、locale、campaign、consent version、
  隱私與第一方揭露；不能換文案後沿用舊 receipt。
- Buttondown metadata 是服務商方案功能；沒有實際 GET 回讀完整 metadata
  就不算可用，不能以「表單接受 POST」推論服務商有保存 scope。

## sender eligibility

1. `observe_pending()` 只 GET 真實 `unactivated`、`source=organic` 的表單申請，
   把當時 App／locale／campaign 與信箱雜湊封進私有 HMAC receipt。
2. `confirm_pending()` 只接受官方 `subscriber.confirmed` 的原始 webhook bytes
   及 `X-Buttondown-Signature` HMAC；newsletter／subscriber 必須完全相同。
   再 GET 同一 subscriber：需為 `regular`，且 scope／信箱仍相同。
   不能只看 `regular`，因為 API 可直接建立 regular 而略過 double opt-in。
3. `ConfirmationLedger` 使用 mode `0600` SQLite 與 transaction 防重。
   重送同 event 只回同一 receipt，不重複計數；沒有事前 pending snapshot
   或無法確認 event 身分就保留 blocked，不追溯補造證據。
4. 規劃前再次 GET subscriber；取消訂閱、complaint、bounce、封鎖、移除、
   import／API 自動加入、代購名單、地址變更、scope 改變都失去資格。
   另驗新鮮且完整、經 HMAC 封存的全域／scope suppression 與發送歷史。
5. 每 App／locale／campaign **7 天 cooldown**、每日最多 **100 recipients**、
   每位讀者每日最多 **1 封**。`reserved`／`attempted`／`unknown` 也保守占額，
   不因 timeout 或沒收到 native receipt 就重寄。
6. audience 為空立即 no-op：不讀 key、不查 provider、不寫歷史、不寄信。
   非空名單也只產 plan，不會觸發任何對外 mutation。

Webhook 接收服務、Buttondown 帳號設定與實際寄送均**沒有在本任務啟用**。
不能為了測試建立真人訂閱、要求確認信、註冊 webhook 或發送測試郵件。

## 市場、來源與時效

- `live_app_manifest.json` canonical roster 必須剛好 47 App，Apple 公開 US
  lookup 必須新鮮驗證全部 47；支援市場的公開 lookup 都要有 GET 來源、
  HTTP status、body SHA-256、ID 集合與時戳。
- 50 locale 內容永遠保留。`bn-BD` 依官方市場契約 CTA=`null`、
  conversion campaign=`N/A`；不得補 US、IN 或無國別 URL。
- 其他 49 locale 只用自己的 storefront，強制正確 `pt`／`ct`／`mt`，
  無硬編價格。**正確路由不等於該 App 在該市場可買**：個別 App lookup
  缺項仍保留 capture 內容，但 sender 回 `app_storefront_unverified`，
  不補市場、不把 HTTP 200／0 results 當可寄送。
- `conversion_cells=2303` 是路由格數，不是可寄送人數；另列
  `verified_conversion_cells`／`unverified_conversion_cells` 如實呈現。
- Growth source 與 Guide `_engine/geo` 必須逐檔 SHA-256 一致、各綁完整
  committed Git SHA；dirty source、錯誤 repo／prefix／digest、舊名單或
  超過 24 小時的 availability／inventory 都 fail closed。
  同 repo 的完整 source commit 也必須可由 Git 回讀；shallow checkout 缺物件
  時只能先唯讀 fetch 補齊，不能忽略 provenance Gate。
  subscriber／suppression／native GET 證據必須在 5 分鐘內。

## 隔離候選產生與驗證

先在兩個 feature worktree 同步 source 並 commit，再以只做 Apple 公開
GET 的 fresh availability snapshot 產生候選。不得改 live main worktree。

```bash
python3 geo/gen_owned_email_capture.py \
  --pages-dir <isolated-guide-worktree> \
  --growth-geo <isolated-growth-worktree>/geo \
  --guide-geo <isolated-guide-worktree>/_engine/geo \
  --availability <private-readonly-evidence>/apple-availability.json

python3 geo/gen_owned_email_capture.py \
  --pages-dir <isolated-guide-worktree> --check

python3 -m unittest discover -s geo/tests -p test_owned_email.py
python3 geo/owned_email_readback.py --subscriber-count
```

`--dry-run` 不寫檔；所有指令都不部署、不寄信。
公開 capture readback 指定 `--pages-dir --app --locale`；native readback 另給
`--native-reference`（僅 email ID、公開 archive URL、email body digest）。
有 credentials 才能 GET email ID；沒有就 blocked，不拿公開表單替代。

原有工具表單仍由 `publish.py`／Pages 管線在 hero 封存**之前**注入；
hero 的 `content_digest` 包含展開後的 50 語設定。禁止封存後直接改 hero HTML。
`enabled=false` 或清空 endpoint 仍會移除舊工具區塊；App capture 關閉時
產生器 fail closed，不自行部署或刪除已存在的公開素材。

## 官方依據（2026-09-12 GET）

- [HTML embed metadata](https://docs.buttondown.com/building-your-subscriber-base#adding-metadata-to-your-subscribers)
- [Metadata 保存與方案](https://docs.buttondown.com/subscriber-metadata)
- [Double opt-in 與 API regular bypass](https://docs.buttondown.com/double-opt-in)
- [Subscriber GET](https://docs.buttondown.com/api-subscribers-retrieve)
- [Confirmation webhook 與 HMAC](https://docs.buttondown.com/api-webhooks-introduction)
- [Email ID／absolute_url／status／body](https://docs.buttondown.com/api-emails-introduction)
- [公開 archive](https://buttondown.com/hourstag/archive/)
- [Buttondown 隱私政策](https://buttondown.com/legal/privacy)
