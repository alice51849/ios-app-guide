# OnePage PPT（onepageppt）

**一句話診斷**：名稱選的詞都贏不了：美國「AI Slide Maker」撞訂閱套殼 App、日本「資料作成」被 Google／Word／Pages 佔住（我們不在前 200）；六個店面 0 評分、免費只能做一張——沒人搜得到，搜到了也沒理由試。

## 結論
六個店面 0 評分；名稱「AI Slide Maker」撞最擠的詞；而 live 文案寫「免費只能做一張」，使用者連六種改版都沒試過就要買 Lifetime Pro。曝光與試用兩頭都卡。

## 各市場真正問題
- **ja**：名稱詞「資料作成」被 Google ドキュメント／Word／Pages 佔住（185 筆我們不在前 200）；真正需求詞「1枚資料」沒進名稱副標。
- **ko**：「한장 요약」整店只有 4 筆結果；「한 장 보고서」沒進名稱。
- **zh-Hant**：文案最好，但免費一張＋沒有成品示範（51 語系 BLOCKED_EVIDENCE）。
- **en-US**：「one pager」可搜，名稱卻用 AI Slide Maker；簡報工作在桌機。

## 第一輪修正
貼文「免費做幾張」改為「一張」（live）；補上「試用只有一張」這個轉換瓶頸；確認 0 評分。

## 行動
| claude | local | you |
|---|---|---|
| 3 組公開資料示範素材＋15 秒腳本（店主錄） | GEO 每語系一頁真實成品、其餘 noindex | ja 副標「メモもPDFも1枚資料に」、ko 名稱「한 장 보고서」、en 副標「Notes & PDFs into a one-pager」 |
| 4 語貼文入庫；量測覆寫 1枚資料／한 장 보고서／一頁簡報／one pager | threads-autopilot 排程 | 評估免費額度（1 張→3 張）；第一張截圖改前後對照 |
| note.com／브런치 教學稿 | | 描述加 50 語言句；錄示範影片 |

## 二次審核修正

- 第一輪 zh-Hant 貼文「可以先免費做幾張」錯誤：live 文案是「免費做一張」。en 只寫「Try it free」、ja「無料で試せます」、ko「무료로 먼저 써 보세요」，貼文一律不寫張數或照 live 寫一張。
- 第一輪說 iTunes 連不上：本次確認 6 個店面全部 0 評分，v1.0.7，Productivity／Business。
- 第一輪只說 ja 缺「1枚資料」：本次實測現有名稱詞「資料作成」被 Google／Microsoft／Apple 的辦公套件佔住、我們不在前 200，所以 ja 不是補詞而是換詞。
- 第一輪漏掉「免費只有一張」本身就是轉換瓶頸：示範不足＋試用太短，兩者疊加。
- repo 的 result-image-coverage 顯示 51 個語系沒有任何成品示範圖，證實第一輪「沒有前後對照」的判斷。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| ja | 名稱選的詞「資料作成」是 Google ドキュメント、Pages、Word、Google スライド 這些辦公套件佔住的通用詞（評分 3.8 萬到 52.7 萬），185 筆結果裡我們不在前 200——這個詞永遠贏不了。日本真正的職場需求詞「1枚資料」「ワンペーパー」反而沒進名稱與副標；成績單量的又是「プレゼン／pptx／グラフ」。0 評分、沒有成品示範。 | iTunes search 2026-10-13 limit 200，country=jp「資料作成」：n=185，我們不在列；#1 Google ドキュメント（172,581）、#2 Pages（92,975）、#3 Microsoft Word（526,894）、#4 表作成（5,908）、#5 Google スライド（38,203）。iTunes lookup 2026-10-13：JP 名稱 OnePage PPT: AI資料作成，評分 0。成績單量測詞：プレゼン、pptx、グラフ。成績單 issue #8（2026-10-13 04:31 UTC）：最佳名次 86（ES presentació）。 |
| ko | 「한장 요약」整個店面只有 4 個結果，排第 4 等於沒人搜；名稱「AI 발표자료」通用，「한 장」只在副標。真正的需求詞是「한 장 보고서」，目前沒量也沒進名稱。 | iTunes lookup 2026-10-13：KR 名稱 OnePage PPT: AI 발표자료，評分 0。第一輪讀數，本次未重現：한장 요약 4／4、발표 자료 5／28。 |
| zh-Hant | zh-Hant 文案最完整，但 live 寫「可以先免費做一張試試」——只能做一張就要決定買 Lifetime Pro，使用者連「六種改版」都沒機會體驗，口碑無從產生。第一輪貼文寫「免費做幾張」與 live 不符。 | iTunes lookup 2026-10-13：TW 描述末段「可以先免費做一張試試…Lifetime Pro 是一次性購買」；評分 0。onepageppt_full.json 仍寫「幾張」，資料檔過時。 |
| en-US | 「one pager」在美國是可搜的詞，但名稱用「AI Slide Maker」去撞最擁擠的詞；0 評分、6 張截圖、沒有前後對照。做簡報的人在桌機工作，手機 App Store 不是入口，需求要先靠示範喚起。 | iTunes lookup 2026-10-13：US 名稱 OnePage PPT: AI Slide Maker，副標 Notes to one perfect slide，評分 0，6 張截圖。第一輪讀數，本次未重現：DE one pager 7／21、UK one page summary 21／56。result-image-coverage.json：onepageppt 51 語系 BLOCKED_EVIDENCE（沒有示範圖）。 |
