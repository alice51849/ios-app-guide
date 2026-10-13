# UsageNow（claudeusagemini）商店文字稽核：標題／副標／關鍵字

量測日：2026-10-13（App 上架第 6 天）。這份只提建議，App Store Connect 與 `_engine/data/claudeusagemini_full.json` 都沒有改動。逐語系的完整建議、字數和每個搜尋詞的證據都在 [`claudeusagemini.json`](claudeusagemini.json)。

## 結論：目前有浪費字元，最嚴重的是英文欄位重複和標題

1. **英文第二欄幾乎整欄重複。** en-GB 關鍵字 15 個字中有 13 個與 en-US 相同，en-CA 則 15 個字完全相同。實測 en-US 在每個探測過的店面都會被索引，包括 US、GB、TW、HK、JP、KR、DE、CA、AU。所以在 GB、TW、HK、KR、DE、AU 這些同時索引兩欄的店面，en-GB 約 85／98 字元等於白放；在 CA，en-CA 的 99 字元全部白放。
2. **非英文欄位重複了 en-US 已有的英文字。** zh-Hant、ja、ko、de、fr、es、pt、it、nl 都放了 7–11 個英文字（usage、tracker、meter、quota、dev、llm、widget、reset…），每欄約浪費 40–57 字元。
3. **用了類別字和錯意圖字。**
   - 類別字：dev、developer、coding、開發者、開発者、개발자、entwickler。類別名本來就會被索引。
   - 錯意圖字：countdown、カウントダウン、倒數計時、카운트다운，搜到的是計時器 App；生成ai、생성형、agent、管理、利用状況、api、cli 也都是錯的意圖。
4. **標題正在輸掉主力搜尋詞。** 「AI Usage Tracker」至少有 12 個競品的標題用了一模一樣的詞組。目前排名：
   - US「claude usage」#19（共 77 筆），「codex usage」#30（共 119 筆）。
   - US「ai usage tracker」#21（共 193 筆）：標題一字不差仍只排 #21，代表這個詞組已經飽和。
   - 「ai usage tracker」在 US、GB、CA、AU、JP、KR、DE 都不在前 12 名。

   這些詞的第 1 名都把品牌和「Usage」直接寫在標題裡，例如 Usage for Claude（5 則評分）、CodexBar - Usage of AI（6 則）、iCodex: Claude & Codex Usage（1 則）、Codex Tracker - 額度重置與用量（0 則）。前幾名的評分都不到 40 則，所以現在決定名次的是標題相關度，不是評分數。
5. **日文標題「AI使用量トラッカー」寫成一長串，不利斷詞。** 標題含「AI使用量」的競品（AI使用量、Agent Meter: AI使用量）能排上「claude code 使用量」「トークン 使用量」，我們卻都不在前 12 名。另外，現有的「制限／上限／使用量／残量」單獨搜尋時，前 10 名分別是 0、1、0、0 個 AI 用量追蹤器，搜到的都是螢幕時間或手機流量 App。

**Developer Tools 免費榜**：在 US、TW、JP、HK、GB、KR、DE 的前 25 名都沒有 UsageNow。前 3 名幾乎都是 TestFlight、GitHub，第三位是 Cursor、Userscripts、Orca IDE、LocalDevVPN 這類工具，要靠下載量，光改商店文字進不去。目前唯一進榜的 AI 用量 App 是 AI Limits Tracker：KR #18（當地名稱「AI 사용량 트래커」，3 則評分）、JP #25。也就是說，KR／JP 的前 25 名靠少量下載就進得去，應該先搶這兩國的搜尋第 1 名，把那份流量變成上榜。

## 量測方法與無法使用的端點

- **主要證據有兩個來源：**
  - iTunes Search API：取 UsageNow 的名次與結果數。
  - App Store 網頁版搜尋（`apps.apple.com/{cc}/iphone/search`）：伺服器只回前 12 名，但有每個 App 的副標和評分數，用來數前 10 名裡有幾個 AI 用量追蹤器。
- **`search.itunes.apple.com` 的搜尋建議端點（MZSearchHints）連不到。** 本環境的出口政策在 CONNECT 階段就回 403，所以拿不到熱度。改用三個代理指標：結果數、前 10 名中的 AI 追蹤器數、競品是否把該詞放進標題或副標。
- **`itunes.apple.com/search` 被 Apple 限流。** 這個出口 IP 從一開始就頻繁收到 HTTP 403。依指示每次 403 先退避 90 秒，連續 8 次就停止。所以 JSON 裡多數詞只有網頁版前 12 名的資料，標記為 `source=web-top12`：`our_rank=null` 代表不在前 12 名，`results=null` 代表沒量到結果數。
- **跨語系索引（各店面實際索引哪些語系的文字）是實測的。** 以 Apple 公布的店面語系對照表為底，再用探測法驗證：在某店面搜「usagenow＋只存在於某一語系關鍵字欄的字」，看 UsageNow 會不會出現，並用負對照確認不是誤判：xyzzyq 是根本不存在的字；cuota 只出現在西文欄位，而西文欄位不在 GB 索引範圍內，所以在 GB 應該搜不到。

| 店面 | 實際被索引的語系 | 實測結果 |
|---|---|---|
| US | en-US、es-MX、zh-Hant、fr，另依 Apple 表還有 ko、pt-BR、ru、vi、ar、zh-Hans | en-GB ✗ |
| GB | en-GB、**en-US** | weekly #77、allowance #140；負對照都不命中 |
| TW／HK | zh-Hant、**en-US**、**en-GB** | zh-Hans ✗ |
| JP | ja、en-US | en-GB ✗ |
| KR | ko、en-US、**en-GB** | — |
| DE | de、en-GB、**en-US** | — |
| CA | en-CA／en-US、fr-CA | en-GB ✗ |
| AU | en-GB、en-US | **en-AU 專屬字 gauge、programmer 都不命中** |
| SG、IN、FR、ES、BR、MX、IT、NL | 未測完 | 沿用 Apple 表＋「en-US 到處都被索引」的實測規律 |

由此把英文關鍵字分成三層，彼此不重複：

- **A 層＝en-US**：全球都會被索引，放最核心的字。
- **B 層＝en-GB 與 en-CA**：GB、歐洲、TW、HK、KR、AU、CA 會用到。
- **C 層＝en-AU 和輕量語系的剩餘空間。**

另外，es-MX、pt-BR 也會在 US 被索引，所以把它們的欄位尾端拿來放 US 用的英文字。

「不同語系的字能不能互相組成片語」沒有被證實過。所以 token、code 刻意留在 zh-Hant、ja、ko、de 欄位裡，確保「token 用量」「claude code 制限」這類中英混合的搜尋在同一個語系內就能成立。

## 各重點店面

### TW（zh-Hant；同時索引 en-US＋en-GB）

| | 現在 | 建議 |
|---|---|---|
| 標題 | UsageNow：AI 用量與額度追蹤 | **UsageNow：Claude、Codex AI 用量追蹤**（29） |
| 副標 | Claude、Codex、Copilot 重置倒數 | **剩餘額度與重置倒數・Copilot、Gemini**（24） |
| 關鍵字 | code,dev,開發者,工程師,usage,tracker,meter,quota,token,使用量,限額,配額,限制,剩餘,倒數計時,小工具,監控,每週,程式,人工智慧,大型語言模型,llm | 使用量,限額,限制,配額,token,code,監控,儀表,小工具,widget,提醒,通知,每週,5小時,鎖定畫面,手錶,上限,消耗,訂閱,方案,重設,刷新,用完,多帳號,統計,opus（97） |

- **現況已經不錯。** 第 1 名的詞：claude 使用量、claude 限制、claude code 用量、claude 剩餘、copilot 用量、額度追蹤。第 2 名：claude 用量（iTunes 也是 #2，但全部只有 16 筆結果，搜尋量很小）、claude 額度、codex 用量。另外 ai 額度 #3、ai 用量 #4、token 用量 #4。
- **還沒拿到第 1 的詞，第 1 名都把品牌放在標題：**
  - claude 用量：Usage for Claude
  - claude 額度：iCodex - Claude,Codex额度监控
  - codex 用量：Codex Tracker - 額度重置與用量

  改標題後，這三個詞預期可以從 #2 升到 #1。
- **刪掉的字：**
  - code 和 token 以外的英文字，因為 en-US／en-GB 已經涵蓋。
  - 開發者、工程師、程式（類別字）。
  - 倒數計時：搜到的是計時器 App，副標的「倒數」已經涵蓋這個意思。
  - 人工智慧、大型語言模型。
- **保留「限制」。** 單獨搜「限制」時前 10 名是 0 個 AI 追蹤器，但「claude 限制」是 #1，而且全部 3 筆結果都是 AI 追蹤器，符合「仍排在 AI 意圖」的例外條件。
- **「用量」「額度」「使用量」單獨搜都是別的意圖**（流量、借貸、照片壓縮 App），只拿來跟品牌組合。

### HK（zh-Hant＋en-US＋en-GB）
跟 TW 用同一份 zh-Hant，但 HK 名次較弱：claude 用量 #8、claude 額度 #3、codex 用量 #9、copilot usage #10，ai 用量和 ai 額度不在前 12 名。標題放 Claude、Codex 對 HK 的幫助比 TW 更大。en-GB 改成 B 層之後，HK 也會多出 premium、requests、daily 等英文搜尋詞。

### JP（ja＋en-US；en-GB 不會被索引）

| | 現在 | 建議 |
|---|---|---|
| 標題 | UsageNow：AI使用量トラッカー | **UsageNow：Claude・Codex AI 使用量**（28） |
| 副標 | Claude・Codex・Copilot・Gemini残量 | **上限とリセット時刻・Copilot/Gemini**（24） |
| 關鍵字 | code,dev,開発者,エンジニア,制限,上限,トークン,usage,tracker,meter,quota,token,ウィジェット,リセット,利用状況,残り,カウントダウン,生成ai,週間,管理 | code,制限,週間,5時間,レートリミット,リミット,トークン,ウィジェット,通知,残量,残り,使用状況,使用率,監視,アラート,opus,sonnet,max,プラン,セッション,クォータ（96） |

- **不在前 12 名的詞：**
  - ai 使用量（前 10 名中 8 個是 AI 追蹤器）。
  - claude code 使用量（7/10）。
  - claude 使用量：iTunes 量到 #30（共 32 筆，第 1 名是 ギガ残量）；網頁版前 10 名只有 2 個是 AI 追蹤器。
- **現有名次：** codex 使用量 #12、claude 上限 #9、codex 制限 #9、claude 使用状況 #5、copilot／gemini 使用量 #4、claude code 制限 #2。
- **「制限」改成有條件保留。** 單獨搜「制限」，前 10 名全是螢幕時間 App（0/10）。但「claude code 制限」是 #2（只有 2 筆結果），「codex 制限」的前 10 名有 8 個是 AI 追蹤器，所以留下來專門給組合搜尋用。
- **「上限」移到副標。** claude 上限、ai 上限、codex 上限的前 10 名中，AI 追蹤器分別是 9、9、10 個。
- **刪除的字：**
  - カウントダウン、生成ai、管理、利用状況：單獨搜都不是 AI 意圖。
  - 開発者、エンジニア：類別或泛用詞。
  - 英文重複字 dev、usage、tracker、meter、quota、token。
- **新增的字：**
  - 使用状況：claude 使用状況 5/5 是 AI 追蹤器，我們排 #5。
  - 5時間、レートリミット：claude レートリミット的前 10 名有 4 個是 AI 追蹤器。

### US（en-US＋es-MX＋zh-Hant＋fr＋ko＋pt-BR…）

| | 現在 | 建議 |
|---|---|---|
| 標題 | UsageNow: AI Usage Tracker | **UsageNow: Claude & Codex Usage**（30） |
| 副標 | Claude, Codex & Copilot Limits | **AI Limits for Copilot & Gemini**（30） |
| 關鍵字 | code,dev,developer,coding,quota,token,meter,monitor,reset,widget,countdown,llm,agent,session,weekly | tracker,widget,reset,quota,token,code,rate,llm,weekly,session,openai,github,hour,monitor,max,pro（96） |

- **主力詞的現況：**
  - claude usage #19／77、codex usage #30／119、ai usage tracker #21／193（標題完全一致仍是 #21）。
  - ai usage、claude limit 不在前 12 名。
  - 長尾詞已經進前 6 名：claude weekly limit #4（靠關鍵字裡的 weekly）、copilot usage #4、claude usage limit #5、claude usage tracker #5、claude reset #6。
- **刪掉的字：**
  - developer、dev、coding：類別或泛用詞。
  - countdown：claude timer、reset timer 的前 10 名分別只有 1 個、0 個是 AI 用量追蹤器。
  - agent。
  - meter：usage meter 前 10 名只有 3 個是 AI 追蹤器。
- **新增的字：**
  - rate：claude rate limit 6/10。
  - openai：openai usage 6/10。
  - hour：claude 5 hour limit 的第 2 名是 Usage for Claude。
  - max、pro：Claude 的付費方案名稱。
  - github：Copilot 的全名是 GitHub Copilot。
- **es-MX 欄位尾端放 US 專用英文字。** 加入 premium、requests、daily、model、watch、meter。
  - premium、requests 對應「copilot premium requests」：目前前 10 名是 0/10 AI 追蹤器，等於沒人在搶。
  - daily、model 對應 Gemini 的每日配額和各模型的上限。

### GB（en-GB＋en-US）
- 標題和副標跟 US 相同。關鍵字改成 B 層：premium,requests,daily,model,alert,watch,meter,counter,plan,remaining,subscription,allowance,cap（96）。原本 15 個字中有 13 個與 en-US 重複。
- **GB 名次：** 只有 claude weekly limit 進前 12（#8）。這證明 en-US 的 weekly 在 GB 也有作用。claude usage、codex usage、ai usage tracker、claude limit、copilot usage 都不在前 12 名。
- 「rate limit」單獨搜，前 10 名是 0 個 AI 追蹤器（全是心率 App），所以 rate 只當組合字用，放在 en-US。

### KR（ko＋en-US＋en-GB）

| | 現在 | 建議 |
|---|---|---|
| 標題 | UsageNow: AI 사용량 트래커 | **UsageNow: Claude·Codex AI 사용량**（29） |
| 副標 | Claude·Codex·Copilot·Gemini 한도 | **한도·리셋 시간 알림 Copilot·Gemini**（26） |
| 關鍵字 | code,dev,개발자,usage,tracker,meter,quota,token,토큰,할당량,리셋,초기화,남은양,잔여,위젯,카운트다운,생성형,주간,세션,코딩,에이전트,llm,모니터 | 클로드,코덱스,코파일럿,제미나이,트래커,code,코드,클로드코드,토큰,위젯,잔여,남은,할당량,사용률,주간,5시간,세션,초기화,제한,모니터,소진,요금제,실시간,opus,max（96） |

- **不在前 12 名的詞：** claude 사용량（9/10 是 AI 追蹤器；iTunes 量到 #12，共 18 筆，第 1 名 Agent Meter: AI 사용량）、ai 사용량（9/10）、ai 한도（9/10）、codex 사용량（9/10）、코덱스 사용량（9/10）、클로드 사용량（5/7）、클로드 한도（4/5）。
- **其中 ai 사용량、ai 한도、클로드 한도的第 1 名都是「AI 사용량 트래커」**，也就是 AI Limits Tracker 在 KR 的名稱，只有 3 則評分，已經排上 Developer Tools #18。它的標題跟我們現在的韓文標題幾乎一樣，所以「AI 사용량 트래커」這個詞組對我們沒有區隔效果。
- **新增音譯：** 加入 클로드、코덱스、코파일럿、제미나이（韓國使用者常打韓文音譯）。
- **刪掉的字：** 카운트다운、생성형、코딩、에이전트、개발자，以及 8 個英文重複字。

### DE（de＋en-GB＋en-US）

| | 現在 | 建議 |
|---|---|---|
| 標題 | UsageNow: KI-Nutzung Tracker | **UsageNow: Claude/Codex-Nutzung**（30） |
| 副標 | Claude, Codex & Copilot Limits | **KI-Limits für Copilot & Gemini**（30） |
| 關鍵字 | ai,code,dev,entwickler,usage,verbrauch,kontingent,token,quota,zähler,widget,reset,countdown,llm,api | verbrauch,kontingent,token,code,ai,zähler,stunden,sitzung,warnung,auslastung,abo,übrig,woche（92） |

- **現有名次：** claude verbrauch #6、ki nutzung #8、claude nutzung #10、token verbrauch #10。claude usage、codex usage、ai usage tracker 都不在前 12 名。
- **英文詞交給英文欄位。** 這些英文詞在 DE 會由 en-US、en-GB 處理，de 欄位專心放德文。
- **單獨搜會跑偏的字：** 「verbrauch」單獨搜是能源 App，「ki limit」單獨搜前 10 名是 0 個 AI 追蹤器，都只當組合字用。

### CA、AU、SG、IN（英文店面）
- **CA：** en-CA 原本跟 en-US 一字不差，整欄浪費。實測 CA 不會索引 en-GB，所以 en-CA 改放 B 層。fr-CA 用法文字。CA 主力詞都不在前 12 名：claude usage、codex usage、ai usage tracker、claude usage tracker。
- **AU：** 實測 AU 吃的是 en-GB 和 en-US，en-AU 專屬字不命中。所以 AU 的排名完全看 A 層和 B 層；en-AU 只放 C 層（opus、sonnet、gpt、credits…）當保險。
- **SG：** copilot usage #9、gemini quota #10。claude 用量、ai 用量不在前 12 名（zh-Hans 是輕量處理）。
- **IN：** copilot usage #1、ai usage tracker #12。IN 主要由 en-GB 和 en-US 涵蓋。

### FR、ES、BR、MX、IT、NL

| 店面 | 建議標題／副標 | 關鍵證據 |
|---|---|---|
| FR | UsageNow : usage Claude, Codex／Limites IA : Copilot et Gemini | 以下都不在前 12 名：utilisation claude（4/5 是 AI 追蹤器）、quota claude（8/10）、claude usage、codex usage。limite claude、suivi ia 都是 0/10，不放 |
| ES | UsageNow: Uso Claude y Codex／Límites IA: Copilot y Gemini | uso claude、uso ia、uso de claude 都已 #1。límite claude、límite de claude 有 8/10 是 AI 追蹤器，但我們不在前 12 名，所以補 límite |
| MX | 同 ES | uso claude #9、uso ia #11、uso de ia 不在前 12 名；es-MX 尾端放 US 用的英文字 |
| BR | UsageNow: Uso Claude e Codex／Limites IA: Copilot e Gemini | uso claude、uso do claude #9；uso ia 不在前 12 名（第 1 名 UsageScope: Uso de IA）；limite claude 只有 1/10、limite ia 0/10，不靠這兩個詞 |
| IT | UsageNow: Uso Claude e Codex／Utilizzo e limiti IA, Copilot | utilizzo claude #2、utilizzo ia #3；uso claude 不在前 12 名；limite claude、limite ia 都只有 0–1/10 |
| NL | UsageNow: Claude/Codex-gebruik／AI-limiet: Copilot en Gemini | claude gebruik #2、ai gebruik #3、claude limiet #4（6/6 是 AI 追蹤器）、ai usage tracker #8；verbruik 單獨搜是能源 App |

這六國的關鍵字都刪掉了 ai、code、dev、usage、tracker、quota、token、widget、llm、meter、api 等英文重複字和類別字（développeur、desarrollador、desenvolvedor、sviluppatore、ontwikkelaar），改放當地語言的字，例如 utilisation、conso、jeton、cuota、reinicio、restante、cota、rastreador、contatore、tegoed。

## 刪掉的浪費字（彙總）

| 類型 | 字 | 為什麼是浪費 |
|---|---|---|
| 與 en-US 重複 | en-GB 的 13 個、en-CA 的 15 個；非英文欄位的 usage、tracker、meter、quota、dev、llm、widget、reset、api、ai | en-US 在每個探測店面都被索引 |
| 類別字或泛用詞 | dev、developer、coding、programmer、開發者、工程師、程式、開発者、エンジニア、개발자、코딩、entwickler、développeur、desarrollador、desenvolvedor、sviluppatore、ontwikkelaar | 類別名 Developer Tools 本來就會被索引，這些字也沒有 AI 用量的意圖 |
| 錯意圖 | countdown、カウントダウン、倒數計時、카운트다운、agent、에이전트、生成ai、생성형、管理、利用状況、api、cli、stats、timer | 單獨搜時，前 10 名中 AI 追蹤器有 0–1 個 |
| 標題與關鍵字重複 | fr 的 usage | 標題已經有這個字 |

## 新增的字與證據（重點）

| 字 | 放在哪 | 證據 |
|---|---|---|
| Claude、Codex（移進標題） | 全部語系 | 各個主力詞的第 1 名都把品牌放標題，而且評分都不到 40 則 |
| weekly（保留） | en-US | US claude weekly limit #4、GB #8 |
| rate | en-US | claude rate limit 6/10 是 AI 追蹤器 |
| openai | en-US | openai usage 6/10 |
| premium、requests | en-GB、en-CA、es-MX | copilot premium requests 前 10 名 0/10 是 AI 追蹤器（沒人在搶），而 GitHub Copilot 的額度就是用 premium requests 計算 |
| daily、model | en-GB、es-MX | 對應 Gemini 每日配額和各模型的每週上限 |
| 클로드、코덱스 | ko | 클로드 한도 4/5、코덱스 사용량 9/10 是 AI 追蹤器，我們都不在前 12 名 |
| 使用状況、5時間、レートリミット | ja | claude 使用状況 5/5，我們 #5；claude レートリミット 4/10 |
| 剩餘額度（移進副標） | zh-Hant | 剩餘額度 #3（6/10 是 AI 追蹤器）、claude 剩餘 #1 |
| Gemini（各語系副標統一加入） | 全部語系 | 原本只有 ja、ko、zh-Hans、ru、el、sk、sl、uk 的副標有 Gemini，其他語系沒有，前後不一致 |

## 競品比較

| 競品 | 美國副標 | US 評分 | 在哪些詞排第 1 |
|---|---|---|---|
| Limits: AI Usage Tracker | Codex, Claude, Cursor limits | 39 | US ai usage、ai usage tracker、claude limit、codex limit；JP ai 使用量；DE codex usage／ai usage（共 40 個詞） |
| Usage for Claude | Track subscription usage | 5 | 各國的 claude usage、TW claude 用量、KR claude 사용량、BR uso claude（共 39 個詞） |
| iCodex: Claude & Codex Usage | Quota, Tokens & Widgets | 1 | GB codex usage、TW／HK claude 額度、TW codex 額度、US copilot quota |
| AI Limits Tracker（韓文名：AI 사용량 트래커） | AI limits in your menu bar | — | KR ai 사용량、ai 한도、클로드 한도；JP claude 上限、ai 上限；Developer Tools 榜 KR #18、JP #25 |
| AI Limits & Reset Tracker | Alerts, widgets, reset timers | — | GB、TW、HK、JP、KR、CA、AU、SG 的 ai usage tracker |
| CodexBar - Usage of AI | （沒有副標） | 6 | US、TW、HK、AU、SG、IN、NL 的 codex usage |
| Codex Tracker - Resets & Usage | Predict & notify \| Vibecoding | 1 | TW／HK codex 用量、JP codex 使用量、JP codex 制限 |
| usAge：AI 額度儀表 | 額度、Token 消耗、餘額監控（TW） | 1 | TW／HK ai 額度 |
| Token Monitor: AI Usage | Claude, Codex, GPT API Spend | — | HK、IN token usage |
| Claude Code Notifier Companion | Never miss a prompt | 8 | US、GB、TW 的 claude code 排前 3 名，但它是通知類 App，意圖不同 |

UsageNow 目前排第 1 的 13 個詞：TW 9 個長尾詞、ES 3 個（uso claude、uso ia、uso de claude），以及 IN 的 copilot usage。競品排第 1 靠的是「品牌＋Usage／額度」直接寫在標題，不是評分數，連前 5 名都是 0–39 則評分的小 App。

## 前 5 名變更（依預期影響排序）

1. **所有語系的標題都改成放 Claude、Codex，加上當地語言的「用量」**，例如 en「UsageNow: Claude & Codex Usage」、zh-Hant「UsageNow：Claude、Codex AI 用量追蹤」、ja「UsageNow：Claude・Codex AI 使用量」、ko「UsageNow: Claude·Codex AI 사용량」。
   - 直接命中各國流量最大的詞：claude usage／codex usage、claude 用量／codex 用量、claude 使用量、claude 사용량。
   - 現況是 US #19／#30、KR 不在前 12、JP 不在前 12。
   - 各詞的第 1 名評分都不到 40 則，標題相關度就是勝負關鍵。
2. **en-GB 和 en-CA 不再複製 en-US，改放 B 層字**（premium、requests、daily、model、alert、watch、meter、counter、plan、remaining、subscription、allowance、cap）。
   - GB、TW、HK、KR、DE、AU（靠 en-GB）和 CA（靠 en-CA）每個店面各多出約 96 字元的英文新詞。
   - 「copilot premium requests」目前前 10 名完全沒有 AI 追蹤器，可以直接拿第 1。
3. **JP 調整三件事：**
   - 標題用空白隔開「AI 使用量」，避免連寫影響斷詞。
   - 刪掉 カウントダウン、生成ai、管理、利用状況 和英文重複字。
   - 「上限・リセット」移到副標，「制限」只留給 claude code 制限（#2）、codex 制限（#9）這類組合。

   目標是 ai 使用量（8/10 是 AI 追蹤器）和 claude code 使用量（7/10），搭配 JP 的 Developer Tools 榜：AI 追蹤器排 #25 就能進榜，門檻很低。
4. **KR 加音譯：** 클로드、코덱스、코파일럿、제미나이，並把標題從跟競品撞名的「AI 사용량 트래커」改成「Claude·Codex AI 사용량」。KR 是唯一有 AI 追蹤器進到 Developer Tools 前 20 名的店面（#18），衝前 25 最可行。
5. **zh-Hant 和其他非英文欄位：**
   - 刪掉英文重複字、類別字和錯意圖字（倒數計時、人工智慧、大型語言模型）。
   - 副標加入剩餘額度和 Gemini。
   - es-MX、pt-BR 尾端補 US 專用的英文字。

   目標是 TW 的 claude 用量、claude 額度、codex 用量從 #2 升到 #1，HK 從 #8、#9 往前推，US 也多一批新詞。

## 商標風險（指南 2.3.7／5.2.1）
- 標題放 Claude、Codex，被審查要求改名的風險比只放副標高。不過以下競品都已經用品牌名當標題通過審查：
  - iCodex: Claude & Codex Usage
  - Usage for Claude
  - Tempo For Claude
  - Claude Counter
  - UsagEX - Claude & Codex Limit
  - Codex Tracker
- App 確實串接這四家服務，而且品牌名就是使用者實際在搜的詞，所以建議保留。
- 若被退回，備案是改成「UsageNow for Claude & Codex」（用 for 表示相容，不暗示是官方 App），描述或促銷文字再加一句「非 Anthropic／OpenAI／GitHub／Google 官方 App」。
- openai、github 只放在關鍵字欄。anthropic、chatgpt、cursor 不放：前兩個搜到的是官方 App，意圖不符；Cursor 是 App 不支援的服務。

## 輕量處理的語系
共 35 個語系只做了輕量處理：ar、bn、ca、cs、da、el、fi、he、hi、hr、hu、id、ms、no、pl、pt-PT、ro、ru、sk、sl、sv、th、tr、uk、ur、vi、zh-Hans，以及 gu、kn、ml、mr、or、pa、ta、te。

- **規則跟主力語系一致：**
  - 標題放 Claude/Codex＋當地語言的「用量」或「上限」。
  - 副標放 AI 上限＋Copilot、Gemini。
  - 刪掉 en-US／en-GB 已涵蓋的英文字，以及類別字和錯意圖字。
  - 剩下的空間放 C 層英文字。在 US、IN 這兩個同時索引多個語系的店面，各欄位放不同的字，避免互相重複。
- **沒有逐國量測**，JSON 標記為 `depth: "light"`。
- **印度各語系的關鍵字**沿用原本 metadata 裡的在地文字；剩餘空間寧可留著，也不放沒驗證過的字。

## 已接受的跨語系重複

| 重複的字 | 出現在 | 在哪個店面重複 | 為什麼接受 |
|---|---|---|---|
| contador、restante、semanal、horas、alerta | es-MX、pt-BR | US | 這幾個字西文和葡文拼法相同；兩個欄位分別是 MX、BR 的主語系 |
| 限制、提醒、通知等 7 個字 | zh-Hant、zh-Hans | US | 兩個欄位分別是 TW、CN 的主語系 |

兩組都只在 US 重複，在各自的主要店面不重複，所以接受。
