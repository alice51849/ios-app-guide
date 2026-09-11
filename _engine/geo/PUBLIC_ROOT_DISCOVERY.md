# Public root discovery 修復與配對整合

## 單一來源與範圍

`site_config.PUBLIC_ROOT` 管理根層 `/.well-known/`；`PUBLIC_SITE` 管理 Guide
路徑。`ORIGIN_*` 只供部署、exact-readback 與拒絕漏洩的驗證器使用。
`gen_llms`、`static_api_catalog` 與 `zhuyin_resourcesync` 的 root URL 全由
公開常數推導。`public_reference_text` 只投影完整 owned URL 的主機／Guide
prefix，保留其他文字、path、query、fragment 與第三方 URL；不是 audit 白名單。

本輪只改 root discovery，不整合 `cfa33b69` 的 canary、E0、dynamic roster，
也不改 `build_pages_i18n.py`、bn-BD、App metadata、外部紀錄或正式 main。
9 份 Guide 產物中，除 ResourceSync 必須更新的 checksum／snapshot 外，
全部非 host bytes 保持不變。再生沿用原頁面的 Standard.site、feed、CTA
與既有裝飾，不拿一次 full rebuild 帶進其他內容修訂。

## 正常再生與 root export

完整生成器仍使用 canonical 常數；隔離的 root 修復可呼叫：

```python
gen_llms.refresh_public_roots(pages)
static_api_catalog.refresh_public_roots(pages)
zhuyin_resourcesync.refresh_public_roots(pages)
zhuyin_resourcesync.export_root_discovery(geo / "root_discovery_export")
```

最後一項是給真正根站 owner 的部署輸入，不在 Guide 子目錄冒充根站
`/.well-known/resourcesync`。它與已驗證的 Guide Source Description 逐 byte
一致；本輪不改、不推送、不部署 `alice51849.github.io` 根站。

## Frozen contract 的合法解凍

`sync_standard_site.py` 是 Guide contract **consumer**，不是這三個
ResourceSync URL 的 producer。真正 producer 是 `zhuyin_resourcesync.py`，
根站目前仍放著舊 export。Consumer 原先的 publication／well-known URL
也錯綁 origin，因此本輪遷移到 `PUBLIC_SITE`／`PUBLIC_ROOT`。

只以 `high_intent_decision_routes.py --write-sync-contract` 重建既有 frozen
表格，再逐 byte 同步到 `_engine/geo`；不新增例外、不手編 digest、不放寬
schema 或 host Gate。這波僅 `site_config.py` 與 `sync_standard_site.py` 的
既有 frozen entry 變動，其餘 entry 保持原 SHA。

**整合前置條件：**目前公開 `standard_site_guide_contract.json` 仍宣告 origin
publication 與 42 份 document，新的 consumer 必須拒絕。須由根站／原始
Standard.site 紀錄 owner 完成一致的 canonical 遷移並取得 fresh GET 證據，
不得只改 JSON 假裝遠端 publication 已遷移。本輪不發任何 ATProto／社群請求。

## 零漏洩與未解項要分開

`public_origin_audit.py` 掃所有 public bytes，包括無副檔名、根層 dotfile
與 `/.well-known/resourcesync`；不再只找 `origin/ios-app-guide` 或 HTML
canonical。它沒有針對某 URL 或字串的放行清單。

本輪生成的 root discovery 候選與 root export 為零漏洩。全 Guide 盤點
另有既有 `100notes-support/privacy.html` 與 family-library 引用，屬
build-pages／資料內容 consumer 邊界；原始完整列表及剩餘項仍保留為 FAIL，
不可把「本輪輸出零漏洩」寫成「全站無 origin」。
根站現行 `/.well-known/resourcesync` 的三處 origin 同樣在真正部署前仍存在，
GET 200 只證明路由可達，不代表候選已上線。

## 整合順序

1. 保留 bn-BD／build-pages worker 的獨立變更，不 cherry-pick 整個既有研究 feature。
2. 根站 owner 使用 `root_discovery_export/.well-known/resourcesync`，並先完成
   Standard.site publication／contract 的 canonical source 遷移與 exact GET。
3. 最新 main 上重新整合 Guide feature、Growth feature，重建 frozen contract，
   核對鏡像、既有 conversion64／47×50、email/image/crawler 與全量 leak inventory。
4. Guide 先 commit/push，再由 Growth gitlink 釘選，最後按授權部署；本 feature
   只保存來源及候選產物，不能作為 deploy、通知或索引提交授權。

## Root 前置已完成（第七輪配對發布）

上文記錄的是初次 feature 稽核狀態。Root owner 已以
`7b44f70d2f71b76efd26b14532f1e410b37515ac`／Pages run `34651941627`
完成正式修復：ResourceSync root body SHA 為
`0aa42115aff3eaf4908f2117ad0a0705ba9f33faa57c23367b1657f6f3f9df80`，
canonical Standard.site contract SHA 為
`2592154b1fb35c524a0b6233dc064fad58edf1bfb5726d2cfb7b0936683b811e`；
42 份 document 已通過本 consumer，公開 publication 本來就已是 canonical，
無須修改任何 ATProto／社群紀錄。

第七輪按當次明確授權整合原 paired feature，使用既有精確雙 SHA 發布流程，
不修改、停用或放寬任何 workflow Gate。先在 feature 封存配對 release commits，
Guide main 與 Growth gitlink/source 全部一致後才進行一次有效 Pages 部署。
初次稽核列出的 331 份歷史 support/library 內容保持原 bytes，不混入其他修復。
