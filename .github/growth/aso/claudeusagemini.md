# UsageNow 商店文字：最終版（2026-10-13 驗證後）

這份是分析師建議經過四個角度對抗驗證、修正後的最終版。App Store Connect 和 `_engine/data/claudeusagemini_full.json` 都沒有改動，要由妳自己貼上。每個語系的完整證據都在 [`claudeusagemini.json`](claudeusagemini.json)。

## 結論

1. **標題要放 Claude、Codex，但寫成「UsageNow for Claude & Codex」。** 「for」（日文用「対応」）表示「支援這兩個服務」，不會讓人以為 App 叫「Claude & Codex Usage」。排名效果幾乎一樣，商標和審查風險比較低。
2. **台灣最重要：繁中標題是「UsageNow for Claude、Codex 用量額度」。** 品牌進標題，同時保住「額度」。額度追蹤 #1、claude 額度 #2、ai 額度 #3 都是靠標題裡的「額度」排上的。
3. **實測：不同語系的字不會組成一個搜尋詞。** 例如「gemini daily quota」的三個字必須都在同一個語系（標題＋副標＋關鍵字）裡。所以 limit、alert、daily、gpt 都集中放進 en-US。
4. **刪掉沒有證據或搜到別種 App 的字**，例如 openai、github、max、pro、訂閱、方案、opus。空出來的位置先留空，等量測證明有用再補。
5. **期望要實際。** 標題放品牌是必要條件，但不保證第 1 名。名次也看下載量和評分的累積速度。Developer Tools 排行榜只能靠下載量進去。
6. **主要語言維持 English (U.S.)，不要改。** en-US 在 TW、HK、KR、GB、AU 都會被搜尋到，很可能是因為它是主要語言。

## 直接貼上（優先店面）

括號裡是字數，全部都在上限內：標題、副標 ≤30，關鍵字 ≤100。關鍵字照原樣貼上，逗號後面不要加空格。

| 店面 | App Store Connect 語言 | 標題 | 副標 | 關鍵字 |
|---|---|---|---|---|
| TW＋HK | 繁體中文（zh-Hant） | `UsageNow for Claude、Codex 用量額度`（30） | `AI 剩餘追蹤、重置倒數提醒・Copilot、Gemini`（29） | `使用量,限額,限制,配額,token,code,監控,小工具,通知,每週,5小時,鎖定畫面,上限,重設,多帳號,統計`（58） |
| JP | 日本語（ja） | `UsageNow：Claude・Codex対応 使用量と上限`（30） | `AIのリセット時刻を通知・Copilot/Gemini`（27） | `code,token,制限,週間,5時間,レートリミット,リミット,トークン,ウィジェット,残り,使用状況,使用率,アラート,クォータ`（67） |
| US | English (U.S.)（主要語言） | `UsageNow for Claude & Codex`（27） | `AI Usage for Copilot & Gemini`（29） | `tracker,widget,reset,quota,token,code,rate,llm,weekly,session,hour,monitor,limit,alert,daily,gpt`（96） |
| GB | English (U.K.) | `UsageNow for Claude & Codex`（27） | `AI Usage for Copilot & Gemini`（29） | `premium,requests,model,watch,remaining,allowance,notify,percent`（63） |
| KR | 한국어（ko） | `UsageNow for Claude·Codex 사용량`（29） | `AI 한도·리셋 시간 알림·Copilot·Gemini`（29） | `클로드,코덱스,코파일럿,제미나이,트래커,code,코드,토큰,token,위젯,잔여,남은,할당량,사용률,주간,5시간,세션,초기화,제한,모니터`（76） |

- **HK** 沒有獨立欄位，和 TW 共用「繁體中文」。
- **en-CA、en-AU 的標題和副標跟 US 相同**，關鍵字見文末表格。
- **韓文貼上前先做一件事：** 把 App Store Connect 目前的韓文關鍵字，和本檔 JSON 裡 `ko.current` 比對一次。잔여、할당량、초기화 現在在 KR 連加上 App 名都搜不到，可能是線上欄位跟檔案不一樣。

## 標題風險：採用哪一種寫法、為什麼

**採用：品牌放標題，加「for／対応」表示相容。**
- 英文：UsageNow for Claude & Codex
- 繁中：UsageNow for Claude、Codex 用量額度
- 日文：UsageNow：Claude・Codex対応 使用量と上限
- 韓文：UsageNow for Claude·Codex 사용량

**為什麼**
- **排名：** 「Usage for Claude」用同樣的 for 寫法，在 US、TW、JP、KR 的 claude usage／claude 用量 都排第 1。
- **商標：** Anthropic 消費者條款禁止以暗示合作關係的方式使用它的名稱。指南 5.2.1 也禁止仿冒式的名稱。英文「Claude & Codex」是遠端操控類 App 的慣用命名，例如 Omnara: Claude & Codex Mobile。
- **指南 5.2.2：** UsageNow 用妳在官方登入頁取得的登入狀態讀取用量。Anthropic 文件寫明第三方不得收集、儲存或中介 Claude.ai 的登入憑證或工作階段。標題放 Claude 會讓審查員要求出示授權、或 Anthropic 提出申訴的機率變高。**送審前先備好 5.2.2 的回覆**，說明登入在各服務自己的官方頁面完成、登入資訊只存在裝置的鑰匙圈（Keychain）、沒有 UsageNow 伺服器（描述裡已經這樣寫）。要知道這是 App 本身的風險，標題只是讓它更容易被注意到。
- **實際上 Apple 很寬鬆：** 約 65 個 AI 用量 App 裡有 14 個標題放了 Claude 或 Codex。沒有任何一個標題放 ChatGPT，所以 ChatGPT 不放任何欄位。

**備案只剩改名。** 描述裡已經有 50 個語系的「非官方 App、商標屬於各自擁有者」聲明，不必再加。如果收到 2.3.7、5.2.1、5.2.2 退件或權利人申訴：
- 英文改回「UsageNow: AI Usage Tracker」，繁中改回「UsageNow：AI 用量與額度追蹤」，也就是現在的標題。
- Claude、Codex 留在副標。

其他語系（德、法、西、葡等）的標題是「Claude/Codex-Nutzung」這種「品牌＋當地用量字」的描述寫法，沒有改成 for。如果英文版被要求改名，這些語系也一起改回現在的標題。

UsagEX 只在 TW、JP 上架，不能當成 US 的先例。

## 被挑戰後修正的地方

**標題與副標**
- **英文標題：** 原建議「UsageNow: Claude & Codex Usage」，改成「UsageNow for Claude & Codex」。副標從「AI Limits for…」改成「AI Usage for Copilot & Gemini」，usage 這個字才不會在所有欄位消失。
- **繁中標題：** 原建議拿掉「額度」，已改回保留。
- **日文標題：** 原本「AI 使用量 要用空白隔開」的理由被推翻，連寫的「AI使用量」照樣能排名。省下的字拿來放「対応」和「上限」（claude、ai、codex 上限 前 10 名有 9–10 個 AI 追蹤器）。

**關鍵字**
- **不同語系的字能不能組合：** 原報告寫「沒有被證實」，實測結果是不會組合。TW、KR 搜「usagenow weekly allowance」0 筆，但 weekly 和 allowance 單獨搜都是第 1。
  - 原本放在 en-GB、es-MX 尾端的 daily、model，組不出「gemini daily quota」這類片語。daily 改放 en-US，再補上 limit、alert、gpt。
  - es-MX 只留 premium、requests、watch。
- **刪掉的字：**
  - en-US：openai、github、max、pro。搜到的是官方 App 或 API 計費 App；GitHub 本身就在同一個排行榜前 3 名。
  - en-GB：subscription、plan、cap、meter、counter。Claude Counter 是競品的 App 名。
  - 繁中：訂閱、方案、手錶、用完、刷新、消耗、儀表、opus。單獨搜時前 12 名只有 0–1 個 AI 追蹤器，而且「訂閱」跟「沒有訂閱」的賣點衝突。widget 也刪了，因為 en-US 已經有。
  - 日文：残量（0/10）、max、opus、sonnet、プラン、監視、セッション。
  - 韓文：클로드코드（Anthropic 品牌規範不允許）、max、opus、소진、요금제、실시간。
  - 其他語系：abonnement 這類訂閱字，以及 gpt、opus、sonnet、vibe、credits、balance、budget、accounts。
- **補回 token：** ja、ko 補回 token，讓「token 使用量」這類搜尋在同一個語系內成立（JP 現在 #7）。
- **副標換成有證據的詞：**
  - it 副標補上 Gemini，它原本是唯一缺 Gemini 的語系。
  - de 副標改「KI-Kontingent」（7/10；ki limit 0/10）。
  - fr 副標改「Quota IA」（quota claude 8/10；limite claude 0/10）。
- **「copilot premium requests 可以直接拿第 1」撤回。** 這個詞的前 12 名全是航空、醫療類 copilot App，premium、requests 只算低成本的長尾押注。
- **en-CA 改放核心字當保險。** 原設計假設 CA 會讀 en-US 的字，但這點驗證不了。

**數字更正**
- 目前排第 1 的詞是 10 個，不是 13 個。
- TW 關鍵字原本寫 97 字，實際是 94 字。
- JP claude 使用量 前 10 名只有 3 個 AI 追蹤器。
- claude レートリミット 是 8/10（原寫 4/10），所以保留。
- KR claude 사용량 是 #12，不是「不在前 12 名」。
- SG gemini quota 是 #11。
- US copilot usage 今天是 #2。

**駁回 5 項**
- 繁中加 max、pro、opus：錯意圖，也沒有需求證據。
- 繁中加 chatgpt：熱門 App 名，觸犯 2.3.7；而且只有 1 筆結果。
- de、hu、sl-SI 刪 ai：不同語系的字不會組合，「ai nutzung」這類搜尋需要 ai 在德文欄位裡。
- nl 補 abonnement、opus、gpt：錯意圖。

## 證據摘要

**量測方式：** 2026-10-13 用 apps.apple.com 網頁版搜尋，桌面版瀏覽器識別、每次間隔 3 秒，約 280 次請求全部成功，沒有被限流。itunes.apple.com/search 先前被限流（HTTP 403），所以部分詞只有前 12 名的資料。

**各店面會讀哪些語系的字（實測）**

| 店面 | 會讀 | 不會讀 |
|---|---|---|
| TW、HK | 繁中、en-US、en-GB | 簡中（簡體字會被轉成繁體）、日、韓、西、法、en-AU |
| JP | 日文、en-US（英文字會對應到片假名） | en-GB、繁中 |
| KR | 韓文、en-US、en-GB（英文字會對應到韓文音譯） | 日、繁中、en-AU |
| US | en-US、es-MX、繁中、法文 | en-GB |
| GB、AU | en-GB、en-US | en-AU |
| CA | fr-CA；en-US 或 en-CA 至少一個 | en-GB |

**現況名次**
- **TW：**
  - 第 1：claude 使用量、claude 限制、claude code 用量、claude 剩餘、copilot 用量、額度追蹤。
  - 第 2：claude 用量、claude 額度、codex 用量。
  - 其他：ai 額度 #3、ai 用量 #4、token 用量 #4。
- **HK：** claude 用量 #8、claude 額度 #3、codex 用量 #9、copilot usage #10。
- **JP：** claude code 制限 #2、claude 使用状況 #5、claude 上限 #9。ai 使用量、claude 使用量 不在前 12 名。
- **US：** copilot usage #2、claude weekly limit #4、claude usage limit #5。claude usage #19、codex usage #30。
- **KR：** ai 사용량 트래커 #3、copilot 사용량 #4、claude 제한 #6、claude 사용량 #12。
  - ai 사용량 트래커 #3 是靠舊標題裡的 트래커。新標題拿掉 트래커 後可能下滑，要追蹤。
- **GB：** 只有 claude weekly limit 進前 12 名（#8）。

**競品與排行榜**
- 各詞第 1 名的競品評分都不到 40 則。
- iCodex 標題的字跟原建議幾乎一樣，在 US claude usage 也只排 #6。所以名次不只看標題。
- Developer Tools 免費榜前 25 名沒有 UsageNow。唯一進榜的 AI 用量 App 是 AI Limits Tracker（KR #18、JP #25），KR、JP 的門檻最低。

## 上線後 72 小時內要檢查的事

1. **TW：** claude 用量、codex 用量、claude 額度、額度追蹤、ai 額度 的名次。目標是全部第 1。
2. **KR：** ai 사용량 트래커 的名次有沒有從 #3 掉下來。
3. **CA：** 搜「usagenow requests」。
   - 有出現 UsageNow，代表 CA 會讀 en-CA，en-CA 下次可以改放 en-US 沒有的字。
   - 沒出現，就維持現狀。
4. **測試片語時不要加 App 名。** 加了「usagenow」有時會跨語系命中，結果不準。
5. **單複數有沒有合併還沒驗證：** es-ES、es-MX 的 límite 和副標的 Límites，ru 的 лимит 和 лимиты。如果搜得到，下次可以把這兩個字的位置讓給別的字。

## 其他語系

<details>
<summary>次要語系（en-CA、en-AU、簡中、西、葡、德、法、義、荷）</summary>

| 語系 | 標題 | 副標 | 關鍵字（字數） |
|---|---|---|---|
| en-CA | `UsageNow for Claude & Codex` | `AI Usage for Copilot & Gemini` | `tracker,quota,token,widget,reset,weekly,session,limit,daily,alert,code,rate,hour,premium,requests`（97） |
| en-AU | `UsageNow for Claude & Codex` | `AI Usage for Copilot & Gemini` | `left,lockscreen,gauge,cooldown,dashboard`（40） |
| zh-Hans | `UsageNow for Claude、Codex 用量额度` | `AI 剩余追踪、重置倒计时提醒・Copilot、Gemini` | `配额,限额,限制,token,code,监控,小组件,通知,每周,5小时,锁屏,上限,多账号,统计,大模型,lockscreen,gauge`（70） |
| es-MX | `UsageNow: Uso Claude y Codex` | `Límites IA: Copilot y Gemini` | `cuota,contador,reinicio,restante,semanal,horas,alerta,límite,premium,requests,watch`（83） |
| es-ES | `UsageNow: Uso Claude y Codex` | `Límites IA: Copilot y Gemini` | `límite,consumo,cuota,contador,reinicio,restante,semanal,horas,alerta,seguimiento,medidor,sesión`（95） |
| pt-BR | `UsageNow: Uso Claude e Codex` | `Limites IA: Copilot e Gemini` | `consumo,cota,contador,reinício,restante,semanal,horas,alerta,rastreador,medidor,sessão`（86） |
| de-DE | `UsageNow: Claude/Codex-Nutzung` | `KI-Kontingent: Copilot, Gemini` | `verbrauch,ai,token,code,zähler,stunden,sitzung,warnung,auslastung,übrig,woche`（77） |
| fr-FR | `UsageNow : usage Claude, Codex` | `Quota IA : Copilot et Gemini` | `utilisation,conso,consommation,jeton,compteur,restant,hebdo,heures,alerte,plafond`（81） |
| fr-CA | `UsageNow : usage Claude, Codex` | `Quota IA : Copilot et Gemini` | `utilisation,conso,consommation,jeton,compteur,restant,hebdo,heures,alerte,plafond`（81） |
| it | `UsageNow: Uso Claude e Codex` | `Utilizzo IA: Copilot e Gemini` | `consumo,contatore,rimanente,settimanale,ore,avviso,monitoraggio,sessione,tetto`（78） |
| nl-NL | `UsageNow: Claude/Codex-gebruik` | `AI-limiet: Copilot en Gemini` | `verbruik,limieten,teller,tegoed,resterend,wekelijks,uren,melding,quotum,sessie`（78） |

</details>

<details>
<summary>輕量處理的 34 個語系（標題沿用原建議：品牌＋當地的用量或上限字；這次只刪錯意圖字；沒有逐國量測）</summary>

| 語系 | 標題 | 副標 | 關鍵字（字數） |
|---|---|---|---|
| ar-SA | `UsageNow: استخدام Claude/Codex` | `حدود AI: Copilot، Gemini` | `كلود,متتبع,توكن,حصة,عداد,ويدجت,تصفير,متبقي,أسبوعي,ساعات,تنبيه,استهلاك,ذكاء,اصطناعي,code`（87） |
| bn-BD | `UsageNow: Claude/Codex ব্যবহার` | `AI সীমা: Copilot, Gemini` | `টোকেন,কোটা,উইজেট,রিসেট,সাপ্তাহিক,বাকি,ট্র্যাকার,code,left,gauge`（63） |
| ca | `UsageNow: Ús de Claude i Codex` | `Límits IA: Copilot i Gemini` | `consum,comptador,reinici,restant,setmanal,hores,avís,giny,seguiment,sessió,gasto,control`（88） |
| cs | `UsageNow: Claude/Codex využití` | `Limity AI: Copilot a Gemini` | `spotřeba,kvóta,počítadlo,zbývá,týdenní,hodiny,upozornění,sledování,code`（71） |
| da | `UsageNow: Claude/Codex-forbrug` | `AI-grænser: Copilot og Gemini` | `kvote,tæller,tilbage,ugentlig,timer,advarsel,nulstil,sporing,code`（65） |
| el | `UsageNow: Χρήση Claude/Codex` | `Όρια AI: Copilot και Gemini` | `κατανάλωση,ποσόστωση,μετρητής,επαναφορά,υπόλοιπο,εβδομάδα,ώρες,ειδοποίηση,όριο,code`（83） |
| fi | `UsageNow: Claude/Codex-käyttö` | `AI-rajat: Copilot ja Gemini` | `tekoäly,kulutus,kiintiö,laskuri,jäljellä,viikko,tunnit,ilmoitus,nollaus,seuranta,code`（85） |
| gu-IN | `UsageNow: Claude/Codex વપરાશ` | `AI મર્યાદા: Copilot, Gemini` | `ટોકન,ક્વોટા,વિજેટ,રીસેટ,સાપ્તાહિક,બાકી,ટ્રેકર`（45） |
| he | `UsageNow: שימוש Claude/Codex` | `מגבלות AI: Copilot, Gemini` | `קלוד,מעקב,טוקן,מכסה,מונה,איפוס,נותר,שבועי,שעות,התראה,וידג׳ט,code,left`（69） |
| hi | `UsageNow: Claude, Codex उपयोग` | `AI लिमिट: Copilot, Gemini` | `टोकन,कोटा,काउंटर,विजेट,रीसेट,बाकी,साप्ताहिक,ट्रैकर,सीमा,अलर्ट,code`（66） |
| hr | `UsageNow: Claude/Codex limiti` | `AI potrošnja: Copilot, Gemini` | `kvota,brojač,preostalo,tjedno,sati,upozorenje,sesija,praćenje,code,left`（71） |
| hu | `UsageNow: Claude/Codex limitek` | `MI-használat: Copilot, Gemini` | `fogyasztás,kvóta,számláló,maradék,heti,órák,értesítés,követés,ai,code`（69） |
| id | `UsageNow: Batas Claude & Codex` | `Pemakaian AI: Copilot, Gemini` | `penggunaan,kuota,penghitung,sisa,mingguan,jam,notifikasi,pelacak,pantau,code`（76） |
| kn-IN | `UsageNow: Claude/Codex ಬಳಕೆ` | `AI ಮಿತಿ: Copilot, Gemini` | `ಟೋಕನ್,ಕೋಟಾ,ವಿಜೆಟ್,ರೀಸೆಟ್,ವಾರದ,ಬಾಕಿ,ಟ್ರ್ಯಾಕರ್,left`（49） |
| ml-IN | `UsageNow: Claude/Codex ഉപയോഗം` | `AI പരിധി: Copilot, Gemini` | `ടോക്കൺ,ക്വോട്ട,വിഡ്ജറ്റ്,റീസെറ്റ്,പ്രതിവാര,ട്രാക്കർ,lockscreen,gauge`（68） |
| mr-IN | `UsageNow: Claude/Codex वापर` | `AI मर्यादा: Copilot, Gemini` | `ट्रॅकर,शिल्लक,आठवडा,तास,सूचना,cooldown,dashboard`（48） |
| ms | `UsageNow: Had Claude & Codex` | `Penggunaan AI: Copilot, Gemini` | `kuota,pembilang,baki,mingguan,jam,notifikasi,penjejak,pantau,guna,code`（70） |
| no | `UsageNow: Claude/Codex-forbruk` | `AI-grenser: Copilot og Gemini` | `kvote,teller,gjenstår,ukentlig,timer,varsel,nullstill,sporing,økt,code`（70） |
| or-IN | `UsageNow: Claude/Codex ବ୍ୟବହାର` | `AI ସୀମା: Copilot, Gemini` | `ଟୋକେନ,କୋଟା,ୱିଜେଟ,ରିସେଟ,ସାପ୍ତାହିକ,ବାକି,ଟ୍ରାକର`（44） |
| pa-IN | `UsageNow: Claude/Codex ਵਰਤੋਂ` | `AI ਸੀਮਾ: Copilot, Gemini` | `ਟੋਕਨ,ਕੋਟਾ,ਵਿਜੇਟ,ਰੀਸੈੱਟ,ਹਫ਼ਤਾਵਾਰੀ,ਬਾਕੀ,ਟ੍ਰੈਕਰ`（44） |
| pl | `UsageNow: Zużycie Claude/Codex` | `Limity AI: Copilot i Gemini` | `licznik,pozostało,tygodniowy,godziny,alert,sesja,śledzenie,kwota,code`（69） |
| pt-PT | `UsageNow: Uso Claude e Codex` | `Limites IA: Copilot e Gemini` | `consumo,contador,restante,semanal,horas,alerta,sessão,monitorizar,rastreador,code`（81） |
| ro | `UsageNow: Consum Claude/Codex` | `Limite AI: Copilot și Gemini` | `cotă,contor,rămas,săptămânal,ore,alertă,resetare,urmărire,sesiune,code`（70） |
| ru | `UsageNow: Claude/Codex лимиты` | `Расход ИИ: Copilot и Gemini` | `клод,нейросеть,токены,квота,счетчик,виджет,сброс,остаток,неделя,часы,уведомления,трекер,лимит,code`（98） |
| sk | `UsageNow: Claude/Codex limity` | `Spotreba AI: Copilot a Gemini` | `využitie,kvóta,počítadlo,zostatok,týždenný,hodiny,upozornenie,sledovanie,code`（77） |
| sl-SI | `UsageNow: Claude/Codex limiti` | `Poraba UI: Copilot in Gemini` | `kvota,števec,preostanek,tedenski,ure,opozorilo,pripomoček,sledenje,ai,code,left`（79） |
| sv | `UsageNow: Claude/Codex-gränser` | `AI-användning: Copilot, Gemini` | `förbrukning,kvot,mätare,kvar,vecka,timmar,avisering,nollställ,spårning,code`（75） |
| ta-IN | `UsageNow: Claude/Codex வரம்பு` | `AI பயன்பாடு: Copilot, Gemini` | `டோக்கன்,ஒதுக்கீடு,விட்ஜெட்,ரீசெட்,வாராந்திர,மீதம்,டிராக்கர்`（59） |
| te-IN | `UsageNow: Claude/Codex పరిమితి` | `AI వినియోగం: Copilot, Gemini` | `టోకెన్,కోటా,విడ్జెట్,రీసెట్,వారపు,మిగిలిన,ట్రాకర్`（49） |
| th | `UsageNow: ใช้งาน Claude/Codex` | `ลิมิต AI: Copilot, Gemini` | `โควตา,โทเคน,วิดเจ็ต,รีเซ็ต,คงเหลือ,รายสัปดาห์,ชั่วโมง,แจ้งเตือน,ติดตาม,จำกัด,code`（81） |
| tr | `UsageNow: Claude/Codex limiti` | `AI kullanımı: Copilot, Gemini` | `yapay,zeka,kota,sayaç,kalan,haftalık,saat,bildirim,sıfırlama,takip,code`（71） |
| uk | `UsageNow: Claude/Codex ліміти` | `Витрата ШІ: Copilot і Gemini` | `клод,нейромережа,токени,квота,лічильник,віджет,скидання,залишок,тиждень,години,сповіщення,code`（94） |
| ur-PK | `UsageNow: Claude/Codex استعمال` | `AI کی حد: Copilot, Gemini` | `ٹوکن,کوٹہ,ویجیٹ,باقی,ٹریکر,نگرانی,code,left`（43） |
| vi | `UsageNow: Hạn mức Claude/Codex` | `Theo dõi AI: Copilot, Gemini` | `giới,dùng,sử,dụng,lượng,còn,lại,đặt,tuần,giờ,thông,báo,tiện,ích,đếm,phiên,code,left`（83） |

</details>
