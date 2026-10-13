# 外宣成長作戰（2026-10-12）

範圍：只做外部宣傳。App 本身與 App Store Connect 一律不動。

## 一句話結論

53 款 App 裡，只有 Mochi 拿到國際自然流量。原因不是其他 App 做得差，而是過去 8 天外宣機器有一半停擺，而且火力分散在 4 萬個模板頁。接下來的打法是把「50 種語言＋App 內切換」變成具體族群的入口，並每天量測 App Store 上有沒有真的變好。

## 數據診斷

| 項目 | 現況 |
|---|---|
| Mochi 評分 | 35 則，分布 8 個以上國家（美國 19 則，4.1★；巴西、德國、澳洲、英國、法國、義大利都有）→ 真正的國際自然流量 |
| 其他 51 款 | 每款約 1–3 則，幾乎都在台灣 → 海外沒有人看到 |
| 正式網站 | 10/4 之後沒有再上線。只有 GrowthEngine 的「配對發布」才會上傳；每日建置跑綠燈也不會上線 |
| 每日 GEO 產線 | 10/11 晚起卡住：Lumi Weather、Snapport 商店文案改版，決策頁 copy 契約需要重新封存 |
| aef0ee01 推送 | 本機半成品建置覆蓋正式內容：sitemap_index 584→4、ja 首頁 172KB→2.9KB、1,079 頁用錯網域 |
| Telegram 頻道 | 9/18 起沒有新貼文：名冊寫死 47 款，App 數變動後直接拒絕發文 |

## 這次已完成

1. **還原 aef0ee01**：整棵樹回到最後一次完整產線輸出 598fde7138；網域稽核 0 違規。
2. **Telegram 恢復**：名冊合約更新為已審核的 53 款；社群發文測試 51/51、Telegram 自測 34/34 通過。
3. **每日 Telegram 精選主打 50 語言**：每則開頭寫明「50 種語言、App 內一鍵切換、不必改手機語言」，並修正誤導的分類標籤（多益、旅遊會話原被標成「親子學習」）。
4. **每日成長成績單**（`growth-scoreboard` issue）：每天量測 53 款 × 50 語系的評分數、7,950 組母語關鍵字的搜尋名次、各國類別排行榜，並列出「最接近第 1 名」的語言／國家，外宣要優先投放到那些組合。只讀 Apple 公開 API。
5. **50 語言宣傳素材**（`fifty-languages-campaign.json`）：5 個情境、21 則五語貼文（中文、印尼文、越南文、英文、日文），每則都帶獨立追蹤碼（`ct=ml_...`），可直接接到自動發文。

## 2026–2027 真正有效的做法（研究結論）

- **頁數幾乎沒用**：AI 推薦能見度與自家網站頁數的相關只有 0.19；與 YouTube 提及是 0.74，與第三方網站提及約 0.7。ChatGPT 推薦 App 時，47.5% 的引用來自 App Store 商品頁本身，所以真實下載和評分才是根本。
- **模板頁有風險**：Google 2026 年已跑 4 次垃圾內容更新，5 月起明文禁止操縱 AI 答案。4 萬個多語模板頁同時符合「規模化內容」和「門頁」兩種樣態。建議縮成「每 App 每語系一頁高品質頁」。
- **社群要像人**：每個帳號每天最多 1–3 則、內容不重複、連結放留言或簡介。舊 Threads 帳號就是因為一天 30–48 則、篇篇帶連結而被停權。
- **50 語言最強的入口在台灣本地**：
  - 87 萬移工（印尼 37%、越南 34%），看護最大困難是語言。
  - 61 萬新住民家庭。
  - 海外 2,336 所僑校在教注音。
  - 學外語的人「把每天用的 App 換成目標語言」。
- **Lite／Pro 兩個商品頁**：外部連結集中導向同一個（建議免費起步那個），讓評分集中、排名才會上來。

## 分組打法

| 組別 | App | 外宣主軸 |
|---|---|---|
| 主力 | Mochi | 已有國際流量，加碼「沉浸學外語」與「看護共用清單」，依成績單的機會表逐國推 |
| 照護／長輩 | Mochi DoneStamp、Stay Clock、CountDaysNow、Sereno | 台灣家庭＋外籍看護共用裝置，各用各的語言 |
| 注音與學齡前 | Lumi 注音星球（Pro）、Letters、Math、Mission | 新住民媽媽、海外僑校、雙語家庭 |
| 旅行 | G+Money、TripBee、LED Moving Text、QR Code Halo、Snapport | 旅伴各用母語、異國情境 |
| 其他工具 | 其餘 App | 先看成績單，哪個語言店面最接近第 1 名，就先推哪裡 |

---

## 交給你電腦上 Claude 的工作（整段貼給它即可）

> 雲端 session 沒有 `00_GrowthEngine` 與 `threads-autopilot` 的權限，以下只能在本機做。
>
> 1. **重新封存決策頁契約，讓 geo-daily 恢復**：自 10/11 晚起，geo-daily 在 `high_intent_decision_routes.py` 失敗，錯誤為 `Public inventory/copy drifted (copy 8c881ff8cf vs 56ceba2891)`。只有 `lumiweather`、`snapport` 兩款的公開文案指紋變了（CI 指紋 lumiweather=a13e7d8abe、snapport=994ad78c48）。先審過兩款新商店文案與決策頁內容是否仍正確，再在 00_GrowthEngine 重新封存 `geo/data/high_intent_decision_routes_v2.json` 與 `geo/data/high_intent_guide_sync_contract.json`，並逐位元組鏡像到 Guide 的 `_engine/geo/data/`。
> 2. **合併 Guide 分支 `claude/inspiring-keller-alhnz8`**：內容包括 aef0ee01 還原、Telegram 名冊合約、每日精選文案、成長成績單。之後不要再把本機只跑完第一步的建置直接推上 Guide main（aef0ee01 事故）。
> 3. **做一次配對發布**：正式站從 10/4 起沒有更新。
> 4. **在 GitHub Actions 頁面重新啟用 `telegram-daily`**：它是被手動停用的。名冊問題已修好。
> 5. **把 `.github/growth/fifty-languages-campaign.json` 接進 threads-autopilot**：遵守檔案裡的 `posting_rules`（每帳號每天 ≤3 則、連結放留言、21 天不重複）與 `honesty_rules`。
> 6. **GEO 降風險**：把排列組合式的模板頁改成 noindex 或移除，每 App 每語系保留一頁有真實截圖與 FAQ 的頁面；移除自家「最佳 X」排名頁和寫給 AI 看的指示文字；IndexNow 只送內容真的變了的網址。

---

## 0 token 自動運作（2026-10-13 起）

雲端額度接近上限，LLM 排程已經全部停用（每日巡檢、Mochi 調價報告）。下面這些是不花 token 的 GitHub Actions，會照常每天跑：

| 排程 | 做什麼 |
|---|---|
| growth-scoreboard（每天 10:41 台灣） | 53 款評分、母語關鍵字名次、類別榜；UsageNow 衝榜區塊：40 國開發者工具免費＋營收榜名次、8 個對手、27 組關鍵字。結果寫在 issue「growth-scoreboard」 |
| portfolio-daily / telegram-daily | Telegram 每日精選；10/27 前「今日焦點」輪播 UsageNow；截圖少於 3 張的 App 自動跳過 |
| geo-daily、indexnow-daily、pages | GEO 內容產生、IndexNow 通知；正式站上傳仍走配對發布（排隊組已修好，不會再被推送取消） |
| line-watchdog、arquivo-pt-daily、software-heritage-daily、sov-weekly | 線路健康檢查與備份 |

暫停中、要等額度重置（10/20 01:00 台灣）或你再開口才做：
- 其餘 App 的雙模型副標／關鍵字調教。Mochi、ShotInbox 已完成第一模型，待 Fable 驗證；其他 7 款與剩下的 App 尚未開始。
- 本機待辦：照 `LOCAL_TASKS.md` 執行，只在你於本機對話貼那一行時跑一次。
