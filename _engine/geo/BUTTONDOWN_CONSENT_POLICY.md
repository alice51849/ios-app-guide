# Buttondown：帳戶綁定的同意／退訂 policy Gate

第3輪獨立 follow-up，基於 Growth `1845e308`／Guide `f39a337f`。
**原 26 個 readiness／layout／browser／測試檔逐 byte 保留**；本層不改
shared layout、capture HTML、rollout 或既有 geometry 證據，不部署、不寄信、
不建立訂閱、不註冊 webhook、不修改 provider 設定。
來源：Session `2fd0fa72-ea4f-49fe-94ee-f12ec0ac0d6a`，
2026-09-12 使用者第3輪「獨立驗證同意／退訂管線」。

## 官方查核的關鍵更正

1. [Event types](https://docs.buttondown.com/event-types) 明確寫明：
   **未啟用 double opt-in 的 newsletter 也會在 subscriber.created 後立即
   發出 subscriber.confirmed。** 因此 `regular`、signed `confirmed`、
   表單存在、HTML `required`、HTTP 200 都不能單獨證明 DOI。
2. [Double opt-in](https://docs.buttondown.com/double-opt-in) 說明預設 DOI、
   例外及 API `type=regular` bypass，並提及 hidden setting
   `should_require_double_optin`；當次查到的
   [Newsletter 公開 schema](https://docs.buttondown.com/api-newsletters-introduction)
   **未列出此欄位**。不能把平台預設當作本帳戶已啟用。
   Adapter 只有在 authenticated GET 真的回傳這個明確布林欄位時才使用；
   缺欄、字串 `"true"` 或只有文件描述全部是 UNKNOWN。
   測試中該欄位為 true 的案例是明示 mock，並非本帳戶 GET 證據。
3. [Confirmation email](https://docs.buttondown.com/transactional-emails-confirmation)
   的 default template 只確認 newsletter，不會自動證明某個 App／locale／
   campaign。需 GET 驗證明確 scope variables 與 confirmation link；未知
   custom template wrapper 可能隱藏 body，故 blocking。
4. [Newsletter schema](https://docs.buttondown.com/api-newsletters-introduction)
   可回傳 **api_key**。本層永不保存或列印該值，也不保存 account email、
   newsletter template 原文或其他可能含私人資訊的原始 authenticated body。
5. [Sending-domain GET](https://docs.buttondown.com/api-newsletters-sending-domain)
   的 `force=true` 雖然名義上使用 GET，卻會觸發 DNS re-verification；
   **本層永久拒絕此參數**，只讀已存在狀態。

## 可驗證與仍未知的項目

當次環境未提供 `BUTTONDOWN_API_KEY`／`BUTTONDOWN_API_TOKEN`；
已實際 GET `/v1/accounts/me` 得到 **401**。Public form endpoint GET 為
302、公開 profile 與 archive GET 為 200，這些只屬 content/endpoint health。

因此本帳戶的 DOI、App-scope confirmation template、unsubscribe
configuration、tracking、sender identity 及 named subscriber census 全部
保持 **UNKNOWN/BLOCKED**；verified audience=0 是 evaluator 無可用人選，
**不是宣稱帳戶有 0 位訂閱者**。同樣沒有 native email ID/body readback，
native verified=0，不推測實際寄送數。

若日後現有 credential 可讀，僅執行：

- [`GET /accounts/me`](https://docs.buttondown.com/api-accounts-me)：具名 account。
- [`GET /newsletters`](https://docs.buttondown.com/api-newsletters-list)、
  [`GET /newsletters/{id}`](https://docs.buttondown.com/api-newsletters-retrieve)：
  唯一 `hourstag` newsletter、public form identity 與設定。
- [`GET /newsletters/{id}/sending-domain`](https://docs.buttondown.com/api-newsletters-sending-domain)：
  `status=valid`、全部 DNS requirements 已驗證、無 warnings／pending；
  `checked_date` 必須在 24 小時內。`none`／`deliberately_cold` 等不能補成 valid。
- [`GET /subscribers/{id}`](https://docs.buttondown.com/api-subscribers-retrieve)：
  個別生命週期、scope、unsubscribe、bounce、地址變更等明確欄位。

不使用瀏覽器登入、不尋找／新增測試帳號、不用 POST 測 endpoint，
沒有 GET 證據就記 UNKNOWN，不自動變更任何 hidden setting。

## Snapshot 與 source／TTL

`buttondown_consent_policy.collect()` 建立 account/public-form/config 綁定：

- named account username＋email SHA-256、newsletter ID／username、
  精確 public form URL；
- API/public GET method、URL、HTTP status、authenticated 標記、
  observed_at、原始 body SHA-256（**不保存原始 authenticated body**）；
- curated config、visible template tokens 與 template hashes；
- `source_digest` 同時綁定本 add-on 與 frozen R2 source；
  `local_config_digest` 綁 capture／consent／rollout 的本機設定；
- 300 秒 TTL、timezone-aware timestamps、account/config digest。
  DNS 的觀測時間不被誤當成同意條款變更，但仍獨立驗 freshness。

`validate()` 不能靠手填 `VERIFIED` 或重算總 digest 跳過欄位驗證。
每次 nonempty audience 的 evaluator 都會**重新 GET account/config**，
比對 binding/config digest；換帳戶、換 newsletter、設定前進、stale、
缺欄、缺 authentication 或 source 改變皆 no-op。

Snapshot 固定 mode `0600`，放 Session 私有證據或專案 gitignored 區，
**不可 commit authenticated snapshot**。公開報告只列狀態、來源和摘要。

```bash
python3 geo/buttondown_consent_policy.py \
  --snapshot <private-evidence>/consent-policy.json
```

## Sender evaluator：新入口，不是寄送器

`buttondown_consent_evaluator.evaluate()` 是本層唯一的 policy-qualified
入口。R2 `owned_email_sender.plan()` 保留作為未授權的 legacy no-send
capacity helper，不能拿它的 `plan_only` 當成已通過本層 policy Gate。
所有入口都固定 `send_allowed=false`、`post_requests=0`。

必須同時具有：

1. 新鮮、完整、authenticated GET 衍生的 policy configuration；
2. `unactivated` 的 organic pending GET，App／locale／campaign 與
   consent digest 明確相同，並綁 account/config 與獨立 generation；
3. HMAC 驗證的 `subscriber.confirmed`，先驗 policy DOI=true，才可採用；
4. confirmation timestamp、generation、具名 subscriber fresh GET；
5. 同帳戶且新鮮完整的 suppression／cooldown／revocation state。

任何欄位缺失都視為 UNKNOWN，不把省略的 `unsubscription_date`、
`bounce_date` 或 history 欄位解讀成「沒有被抑制」。
`confirmed_at` 明確是**接收端驗證事件與 GET 後的觀測時間**，
不是捏造的 provider click time；payload 未提供的 click time 仍是 UNKNOWN。

空 audience 立即 no-op，不讀 credential、不查 provider、不建立任何名單。
非空 audience 任一全域證據缺失也回 0 qualified audience／no-op，
不是用「HTTP 200 就算成功」繼續。

## 退訂與重新訂閱

- 官方 [`subscriber.unsubscribed`／`subscriber.complained`／
  `subscriber.deleted`／`subscriber.type.changed`](https://docs.buttondown.com/event-types)
  必須驗證 HMAC、newsletter/account、event ID，再 GET 同一 subscriber
  的對應狀態。未公開的 `subscriber.blocked` 事件名不被假設存在。
- 新鮮 signed revocation state 綁 account；有 unsubscribe 時，舊 pending／
  confirmed receipt 立即失效。GET 再次顯示 regular **不會**恢復舊同意。
- 重新訂閱必須先有新 organic unactivated GET、new generation，再有新的
  policy-bound signed confirmation，時間必須晚於最新 unsubscribe。
  scope 改變同樣要新確認；complaint／blocked／deleted 不藉重新註冊清除。
- `ConsentLedger` 的 SQLite transaction／event-ID primary key 讓 webhook
  retry 冪等；同事件不能替另一 account、scope 或新 generation 授權。
  只保存 hash 和 scoped sealed receipts，不保存原始 email address。
- local helpers 只回傳或保存私有證據，**不會呼叫 resubscribe／unsubscribe
  POST／PATCH**；真實 webhook intake 與完整 suppression watcher 尚未部署，
  未有實際 GET 證據前維持 integration blocker。

## Subscriber count 與 native email 不混用

`named_census()` 必須先有 fresh named account/newsletter GET，再取得完整、
唯一 subscriber IDs 與精確 count。缺 count、403、privacy/redaction 欄位、
重複 ID 或不完整 pagination 全回 **UNKNOWN**；只有具名 API 明確
`count=0, results=[]` 才能回真實 0。

`native_evidence()` 保留 R2 的個別 email ID GET、公開 archive URL GET、
App／locale／campaign metadata 與 body digest 契約，另綁 account。
表單、policy snapshot、queue/workflow success、GET 200 都不會升級為 native。

## Layout 外仍需整合的證據

1. 本環境沒有可用 credential／account GET=401；
2. 官方公開 API schema 未曝露 DOI hidden setting，不能引用 default 代替；
3. 本帳戶可見 App-scope confirmation／unsubscribe template 與 sender DNS
   identity／tracking setting 未取得 authenticated GET；
4. signed confirmation／revocation intake、完整 suppression history 尚未有
   真實接收及 fresh GET 證據；未做真實訂閱、退訂或寄信測試；
5. [`List-Unsubscribe`](https://docs.buttondown.com/building-your-subscriber-base)
   與 [open](https://docs.buttondown.com/open-tracking)／
   [click tracking](https://docs.buttondown.com/click-tracking) 的實際郵件行為仍
   未驗，不拿 configuration 或平台文件當作 delivered-email readback。

目前只做 mock-only protocol tests 與原 65／64 regression。
本輪不修改、重測或接管另一 worker 的 shared layout。
