# Canonical 搜尋與 AI crawler eligibility

## 部署歸屬

- 唯一有效 robots：`https://open.cait518.cc/robots.txt`。
- `/ios-app-guide/robots.txt` 是子目錄參考副本，不能授予或拒絕抓取權限。
- 根站真正來源：`alice51849/alice51849.github.io` 的
  `scripts/gen_link_hub.py`，不是 Guide 的 generated robots。
- `geo/crawler_policy.py` 是共用政策來源；須逐位元組同步至
  Guide 的 `_engine/geo/crawler_policy.py` 與根站的
  `scripts/crawler_policy.py`。兩個 Guide robots generator 共用此政策。
- 本次公開變動僅在根站；Guide／Growth 是 engine-only 同步。
  隔離 feature 上完成測試及獨立審查，再 fetch／安全整合並非 force push。
  不觸發 `geo-daily`、社群、ASC、IndexNow 或任何付費模型 API；
  只由根站 `main` 的一次 push 觸發一次 Pages 部署。

## 搜尋、訓練與 WAF

`OAI-SearchBot`、`PerplexityBot`、`Applebot`、`Googlebot`、`Bingbot`
以及一般搜尋 crawler 可抓公開頁、50 locale URL、sitemap 與 rendering assets。
工具來源目錄的 Disallow 不是安全認證機制，不可存放秘密。

保留 canonical host 已有的 Cloudflare 訓練拒絕選擇：GPTBot、
Applebot-Extended、Google-Extended 等訓練產品不取得 Allow；
尤其不可把 GPTBot 的拒絕擴大成 OAI-SearchBot 的拒絕。
Cloudflare Managed robots 與 origin 規則會合併，重複 bot group 的
Allow／Disallow 同長度時 Allow 可能勝出，所以原先矛盾的 Allow 必須從來源移除。

WAF 如需 crawler exception，必須使用**正確 product token AND 當下官方
CIDR**，不可只信 UA、不可停用全站安全防護，也不可讓所有 AI bot 共用訓練封鎖。
官方 IP JSON 位址由 `crawler_policy.CRAWLER_SOURCES` 管理；每次公開驗證重新
GET 並解析 CIDR，不把範圍永久寫死（Bing 明示至少每日更新）。
此工具不變更 WAF、不冒充 crawler、不把 audit HTTP 200 當成真 bot 的通行證。

## Discovery 與驗證

根站 robots 宣告 Guide sitemap index；sitemap、canonical、50 語 hreflang、
`llms.txt`、`llms/index.json`、verified JSON catalog 及根站 ARD metadata 互連。
`llms.txt`／JSON／Agentmap 是閱讀與 discovery 文件，不是官方提交 endpoint，
也不保證收錄、排名或引用。既有合理 noindex 不因 robots Allow 而移除。
根站 ARD 的 URL migration 保留原本 version-bound MCP snapshot 的版本與
coverage，不修改已發布的 Registry card，也不謊報為新 MCP release 或新 inventory；
完整 portfolio 的 verified JSON catalog 是另一份獨立、明確連結的資料。

使用既有 Python unittest：

```sh
PYTHONDONTWRITEBYTECODE=1 GEO_PAGES=/path/to/guide \
  python3 -m unittest geo.tests.test_crawler_eligibility
python3 geo/crawler_eligibility.py \
  --pages-dir /path/to/guide --root-site-dir /path/to/root-site \
  --live --report path/inside/session/files/crawler-readback.json
```

`--live` 只送公開 GET，UA 固定為 `LumiCrawlerEligibilityAudit/1.0`，
核對 root／child robots、50 語代表性公開 App 頁的 self-canonical／hreflang／noindex、
discovery、assets、官方 IP JSON 與 Cloudflare 回應 headers。
所有結果限定於報告列出的 URL；不是全站所有頁面均可索引的宣稱。
報告永久區分 `crawler_eligibility` 與 `actual_crawl_receipt`、
`actual_indexing`、`actual_citation`；後三者沒有可信 provider 證據時皆為 `unknown`。
真實 crawler IP 專屬 WAF 行為未有可信證據時同樣為 `unknown`。

## 官方依據

- [OpenAI：OAI-SearchBot 與 GPTBot 各自獨立](https://developers.openai.com/api/docs/bots)
- [Perplexity：search bot、IP JSON 與 UA＋IP WAF 條件](https://docs.perplexity.ai/docs/resources/perplexity-crawlers)
- [Applebot：搜尋、Applebot-Extended、Googlebot fallback、rendering 與 noindex](https://support.apple.com/en-us/119829)
- [Google：root scope、group 合併、最長規則與 Allow precedence](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)
- [Google：驗證 crawler 的官方 IP 範圍](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests)
- [Bing：crawler UA 與 robots](https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0)
- [Bing：UA 不能單獨驗真、雙向 DNS／每日更新官方 IP 範圍](https://www.bing.com/webmasters/help/how-to-verify-bingbot-3905dc26)
- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
