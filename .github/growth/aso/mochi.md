# Mochi 商店文字：副標與關鍵字（模型 1／2，2026-10-13）

這是第一個模型的調教結果。依長期規則，要等第二個模型驗證後才會自動套用；這一輪沒有動 App Store Connect、App 本身和 `_engine/`。每個語系的完整證據在 [`mochi.json`](mochi.json)，套用檔是 [`mochi-asc-payload.json`](mochi-asc-payload.json)。標題（App 名稱）照線上原樣，不改。

## 結論

1. **名稱已經在幫忙，不動。** 今天實測 US cute to do list、kawaii to do list、cute checklist 都是第 2 名；BR lista de tarefas fofa、checklist fofo、planner fofo 第 1 名，lista de tarefas 第 5 名；DE süße to-do liste 第 1 名；TW 可愛待辦 第 2 名。
2. **1.0.16 的新副標有三組字沒帶來名次，而且搜到別種 App。** US 的「Chores」：chore list 前 11 名沒有 Mochi，前排是家務排程。TW 的「療癒手帳」：手帳 前 12 名全是貼紙日記。TW 的「購物清單」：前 12 名幾乎都是購物清單 App。
3. **5 個優先店面裡改 4 個副標，BR 不動。**
   - **US**：改「Kawaii & Aesthetic To-Do List」。aesthetic to do list 目前不在前 12，第 7 名是零評分、副標寫 Aesthetic 的 App。
   - **TW**：改「療癒待辦事項・提醒・鎖定畫面小工具」，加強 待辦事項（現 #9）。
   - **JP**：主力詞 todoリスト、やることリスト、チェックリスト、タスク管理 目前全都不在前 12，副標直接並列這些詞。
   - **DE**：改「Aufgabenliste & Checkliste」。
   - **BR**：表現最好，副標不動，只換關鍵字。
4. **repo 裡的鏡像是舊的。** 線上 1.0.16（10-09）已改過 50 個語系的副標，韓文名稱也改成「Mochi: 귀여운 할 일 목록 & 체크리스트」，`_engine/data/mochi_full.json` 還是 10-03 的版本。所以本檔的「現值」：
   - 名稱、副標用線上值。
   - 關鍵字公開查不到，只能用鏡像，ASC 上可能已經不同。payload 已寫明處理方式：名稱或副標對不上就停下回報；只有關鍵字對不上時，先記下 ASC 舊值，再照建議覆寫。
5. **期望要實際。** 各地評分數只有個位數到二十幾則，to do list、todoリスト、aufgabenliste 這類大詞不會因為換字就進前 10。這次主要是把 aesthetic、kawaii、可愛、süß 這類利基詞做滿。
6. **沒有 Lite／Pro 版本。** 同品牌的 Mochi DoneStamp（記錄上次做某件事的時間）是另一款 App，所以 Mochi 不放 chores、반복 這類週期字，避免兩款 App 搶同一批字。

## 直接貼上（優先店面）

括號裡是字數：副標上限 30，關鍵字上限 100。關鍵字照原樣貼上，逗號後面不要加空格。名稱欄只是對照，不要改。

| 店面 | App Store Connect 語言 | 名稱（不動） | 副標 | 關鍵字 |
|---|---|---|---|---|
| US（核心英文，全球多數店面都會讀） | English (U.S.) | `Mochi: Cute Checklist` | `Kawaii & Aesthetic To-Do List`（29） | `todo,widget,planner,reminder,task,daily,cozy,pastel,routine,girly,watch,organizer,habit,grocery`（95） |
| TW＋HK | 繁體中文（zh-Hant） | `Mochi: 可愛待辦清單` | `療癒待辦事項・提醒・鎖定畫面小工具`（17） | `todo,任務,檢查清單,備忘錄,購物,習慣,打卡,每日計畫,時間管理,目標,讀書,作業,工作,便利貼,記事,手錶,重複,少女心,粉色,效率,生活,計畫`（76） |
| JP | 日本語（ja） | `Mochi: かわいいToDo` | `やることリスト・チェックリスト・タスク管理`（21） | `リマインダー,ウィジェット,ロック画面,習慣,ルーティン,買い物,予定,勉強,仕事,家事,目標,メモ,時間管理,シンプル,日課,通知,毎日,癒し,パステル,ウォッチ,女子,学生,整理`（91） |
| BR | Português (Brasil)（pt-BR） | `Mochi: Lista fofa` | `Tarefas fofas e checklist`（25） | `afazeres,planner,lembrete,rotina,hábitos,widget,organização,compras,kawaii,fofinha,diário,metas`（95） |
| DE | Deutsch（de-DE） | `Mochi: Süße To-do-Liste` | `Aufgabenliste & Checkliste`（26） | `aufgaben,widget,todo,erinnerung,planer,tagesplaner,kawaii,niedlich,routine,einkaufsliste,ziele`（94） |
| GB、AU（也是 TW、HK、KR、DE 的第二層英文） | English (U.K.)（en-GB） | `Mochi: Cute Checklist` | `Pastel To-Do List & Organiser`（29） | `tick,girly,pink,pretty,adorable,simple,emoji,lockscreen,shopping,homework,goals,tidy,revision,uni`（97） |

- **BR 副標維持「Tarefas fofas e checklist」不變**，只換關鍵字。
- **en-CA、en-AU 的副標和 US 相同。** en-CA 關鍵字也和 US 相同，當作保險；en-AU 實測不被 AU 讀到，放第三層備用字。完整內容見文末表格。

## 證據（2026-10-13 App Store 網頁版搜尋，34 次，全部成功，沒有被限流）

「同／不同」是指前 10 名是不是和 Mochi 一樣的待辦清單 App。

| 店面 | 搜尋詞 | Mochi | 第 1 名（評分數） | 意圖 | 備註 |
|---|---|---|---|---|---|
| US | cute to do list | #2 | Lists To do（106K） | 同 |  |
| US | aesthetic to do list | 不在前 12 | Digital Planner – Task Journal（14K） | 同 | 第 7 名 Perspexa 零評分，只靠副標 Aesthetic 進榜 |
| US | kawaii to do list | #2 | Kawaii To-Do List（5） | 同 |  |
| US | cute checklist | #2 | mimi – Cute notes（7.9K） | 同 |  |
| US | to do list | 不在前 11 | To Do List MinimaList & Widget（48K） | 同 |  |
| US | cute planner | 不在前 11 | Pencil Calendar: Daily Planner（11K） | 不同 | 前 11 名是貼紙行事曆／手帳，意圖不同 |
| US | chore list | 不在前 11 | Lists To do（106K） | 不同 | 前排是家務排程、獎勵表 App；副標 Chores 沒帶來名次 |
| TW | 可愛待辦 | #2 | Kummy行事曆 - 簡單可愛的日曆應用（1289） | 同 |  |
| TW | 待辦清單 | 不在前 11 | 極簡待辦 - To Do List &備忘錄&記事本（5634） | 同 |  |
| TW | 待辦事項 | #9 | 提醒事項（3.5萬） | 同 |  |
| TW | 可愛 todo | #3 | Cat Todo - 備忘錄 & 待辦事項 & 記事本（64） | 同 |  |
| TW | 代辦事項 | #9 | 提醒事項（3.5萬） | 同 | 錯字變體，結果與 待辦事項 完全相同（Apple 已正規化），不需另放 |
| TW | 手帳 | 不在前 12 | 微手帳 - 花樣日記本電子手賬咕卡（9445） | 不同 | 前 12 名全是貼紙日記手帳，意圖不同；副標裡的 手帳 沒帶來名次 |
| TW | 購物清單 | 不在前 12 | 購物清單 - 購物備忘錄 & 核對清單（1492） | 不同 | 前 12 名幾乎都是購物清單 App；副標裡的 購物清單 沒帶來名次 |
| JP | かわいい todo | #4 | 可愛いウィジェットのToDoリスト（1） | 同 |  |
| JP | todoリスト | 不在前 11 | ToDoリスト リマインダー通知付きのメモ帳&やることリスト（4.3万） | 同 |  |
| JP | やることリスト | 不在前 12 | ToDoリスト リマインダー通知付きのメモ帳&やることリスト（4.3万） | 同 |  |
| JP | チェックリスト | 不在前 12 | ToDoリスト リマインダー通知付きのメモ帳&やることリスト（4.3万） | 同 |  |
| JP | タスク管理 | 不在前 11 | ToDoリスト リマインダー通知付きのメモ帳&やることリスト（4.3万） | 同 |  |
| JP | やることリスト かわいい | 不在前 12 | メモ帳 サンリオキャラクターズ（+ウィジェット）（3978） | 同 |  |
| JP | 可愛い todo | #5 | 可愛いウィジェットのToDoリスト（1） | 同 | 漢字寫法與 かわいい todo 結果幾乎相同，不需另放 可愛い |
| BR | lista de tarefas fofa | #1 | Mochi: Lista fofa（4） | 同 |  |
| BR | lista de tarefas | #5 | To Do List: Lembretes Tarefas（2 mil） | 同 |  |
| BR | planner fofo | #1 | Mochi: Lista fofa（4） | 同 |  |
| BR | checklist fofo | #1 | Mochi: Lista fofa（4） | 同 |  |
| BR | to do list | 不在前 11 | Todoist: To do list–Calendário（22 mil） | 同 |  |
| BR | lista de afazeres | 不在前 12 | Checklist fácil: rotina diaria（2,4 mil） | 同 | Mochi 欄位沒有 afazeres |
| BR | checklist | #8 | Checklist Fácil（5,1 mil） | 同 |  |
| DE | süße to-do liste | #1 | Mochi: Süße To-do-Liste（2） | 同 |  |
| DE | to do liste | 不在前 11 | To do list & erinnerungen（7584） | 同 |  |
| DE | aufgabenliste | 不在前 11 | Microsoft To Do（85.132） | 同 | 第 3 名 Memo-Widget 只有 5 則評分，靠標題放 Aufgabenliste |
| DE | checkliste | 不在前 11 | Checklisten: To-Dos（12） | 同 |  |
| DE | kawaii to do liste | #6 | Google（460.283） | 不同 | 前 5 名是 Google、Crunchyroll 等熱門 App，代表需求很低 |
| DE | todo | 不在前 11 | Microsoft To Do（85.132） | 同 |  |

- scoreboard（iTunes Search API，10-13 13:24 UTC）的第 1 名紀錄：BR checklist fofo、BR lista de tarefas fofa、DE süße to-do liste、US cute to do list。今天網頁版的 US cute to do list 是第 2 名（第 1 名 Lists To do 有 10.6 萬則評分），兩個來源的排序不同。
- 各店面會讀哪些語系的字，沿用 UsageNow 的實測，本次沒有重測：en-US 在 US、GB、AU、TW、HK、JP、KR、DE 都會被讀到；en-GB 在 GB、AU、TW、HK、KR、DE；en-AU 連 AU 都讀不到。不同語系的字不會組成同一個搜尋詞。

## 刪了什麼、補了什麼、為什麼

**US（en-US）**
- **副標：** Chores 換成 Aesthetic。kawaii（#2）和 cute（名稱）都保住；chore list 沒有排名，前排是家務排程和獎勵表 App。
- **刪：** list（副標已有）；notes、calendar、agenda、schedule（搜到筆記和行事曆）；habits、tasks 改成單數。
- **補：** todo、widget（首頁和鎖定畫面小工具）、daily、cozy、pastel、girly、watch（1.0.16 新的 Apple Watch 介面）、organizer。

**TW＋HK（zh-Hant）**
- **副標：** 拿掉 手帳、購物清單，放 待辦事項、提醒、鎖定畫面、小工具。
- **刪：** 待辦、清單（名稱已有）；小工具、桌面小工具（副標已有）；手帳；日曆、日程、課表；番茄鐘（App 沒有計時器）；備考。
- **補：** todo。「可愛 todo」現在 #3，但要和 可愛 組成同一個搜尋詞，todo 必須放在繁中欄位。另外補 檢查清單、便利貼、手錶、重複、少女心、粉色。
- **代辦事項 不必另放：** 搜尋結果和 待辦事項 完全一樣。

**JP（ja）**
- **副標：** 從「やることリストをかわいく整える」改成並列三個主力詞，讓「ToDo（名稱）＋リスト」組成 todoリスト。
- **刪：** ToDo、かわいい、TODO管理（名稱已有）；タスク、チェックリスト（副標已有）；手帳、日記、予定表（日記意圖）。
- **補：** ロック画面、シンプル、日課、通知、毎日、癒し、パステル、ウォッチ、女子、学生、整理。
- **可愛い 不必另放：** 「可愛い todo」#5、「かわいい todo」#4，兩種寫法的結果幾乎一樣。
- **繰り返し 不放：** 讓給 DoneStamp。

**BR（pt-BR）**
- **副標不動。**
- **刪：** tarefas、lista（名稱或副標已有）；notas、calendário、agenda。
- **補：** afazeres（lista de afazeres 目前不在前 12）、kawaii、fofinha、diário、metas。
- **保留：** planner（planner fofo #1）。

**DE（de-DE）**
- **副標：** 放 Aufgabenliste。aufgabenliste 的第 3 名只有 5 則評分，靠標題放這個字排上去。原副標的 Aufgaben、Widget 移到關鍵字。
- **刪：** liste（名稱已有）；notizen、kalender、zeitplan、agenda。
- **補：** todo、tagesplaner、kawaii（kawaii to do liste #6，但需求很低）、niedlich、einkaufsliste、ziele。

**英文第二、三層**
- **en-GB 不再重複 en-US 的字。** 副標改「Pastel To-Do List & Organiser」。
- **en-GB 關鍵字只放 en-US 沒有的字：** tick（英式 tick list）、girly、pink、simple、emoji（11 組表情符號）、lockscreen、homework、revision 等。

**其他 44 個語系（輕量）**
- **刪掉同語系名稱或副標已經有的字**，例如副標已有 widget、關鍵字又放 widget。
- **刪掉錯意圖的字：** 筆記、行事曆、行程表，以及時鐘（ساعة）。
- **補上當地的待辦清單說法：** seznam úkolů、gjøremålsliste、lista de afazeres、cose da fare、туду。
- **也補了這些字：** kawaii、可愛的同義詞、每日、目標。
- **副標大多維持 1.0.16 的線上值。** 只改 3 個語系：
  - **ko**：原副標只有 플래너 一個搜尋詞，改成「포근한 투두리스트·플래너·위젯」。
  - **vi**：原副標的 dễ thương 和名稱重複，改成「Việc cần làm & widget nhắc nhở」。
  - **zh-Hans**：比照 TW，拿掉 手帐、购物清单。

## 上線後 72 小時內要看的事

1. **US：**
   - aesthetic to do list 能不能進前 12。
   - kawaii to do list、cute to do list、cute checklist 要維持第 2 名。
2. **TW：** 待辦事項 能不能從第 9 名往上；可愛 todo 能不能從第 3 名往上。
3. **JP：** todoリスト、やることリスト、タスク管理 有沒有任何一個進前 12。
4. **DE：** aufgabenliste、checkliste 能不能進前 11；süße to-do liste 要維持第 1 名。
5. **BR：** lista de afazeres 能不能進前 12；lista de tarefas 要維持第 5 名。

## 其他語系

<details>
<summary>其餘 44 個語系（en-CA、en-AU、ko、zh-Hans、vi 和輕量處理的語系）</summary>

| 語系 | 名稱（不動） | 副標 | 關鍵字（字數） |
|---|---|---|---|
| ar-SA | `Mochi: قائمة مهام لطيفة` | `تذكيرات متكررة وودجت للشاشة`（不動） | `المهام,تذكير,مخطط,عادة,روتين,تسوق,إنجاز,ودجت,مدرسة,عمل,هدف,كيوت,لطيف,يومية,منظم`（79） |
| bn-BD | `Mochi: মিষ্টি টাস্ক লিস্ট` | `কাজ, রিমাইন্ডার ও উইজেট`（不動） | `তালিকা,প্ল্যানার,অভ্যাস,রুটিন,কেনাকাটা,কিউট,চেকলিস্ট,টুডু,দৈনিক,লক্ষ্য,পড়াশোনা,todo,checklist`（94） |
| ca | `Mochi: Llista bonica` | `Tasques, recordatoris i widget`（不動） | `planificador,hàbits,rutina,compres,pendents,checklist,todo,kawaii,cuqui,diari,objectius,organitzador`（100） |
| cs | `Mochi: Roztomilé úkoly` | `Checklist, připomínky a widget`（不動） | `seznam,úkolů,úkolníček,plánovač,návyky,rutina,nákup,todo,kawaii,roztomilý,denní,cíle,organizér`（94） |
| da | `Mochi: Sød huskeliste` | `Tjekliste, opgaver og widget`（不動） | `opgaveliste,todo,påmindelse,planlægger,vaner,rutine,indkøbsliste,kawaii,søde,daglig,mål`（87） |
| el | `Mochi: Χαριτωμένες λίστες` | `Λίστα εργασιών & υπενθυμίσεις`（不動） | `εργασίες,todo,checklist,πλάνο,συνήθειες,ρουτίνα,ψώνια,widget,kawaii,χαριτωμένο,καθημερινές,στόχοι`（97） |
| en-AU | `Mochi: Cute Checklist` | `Kawaii & Aesthetic To-Do List` | `student,school,college,morning,themes,checkbox,memo,teen,organised`（66） |
| en-CA | `Mochi: Cute Checklist` | `Kawaii & Aesthetic To-Do List` | `todo,widget,planner,reminder,task,daily,cozy,pastel,routine,girly,watch,organizer,habit,grocery`（95） |
| es-ES | `Mochi: Lista monísima` | `Checklist y tareas con widget`（不動） | `pendientes,todo,recordatorio,planner,hábitos,rutina,compras,kawaii,bonita,cuqui,diaria,objetivos`（96） |
| es-MX | `Mochi: Lista súper cute` | `Tareas, pendientes y widget`（不動） | `checklist,todo,recordatorio,planner,hábitos,rutina,compras,kawaii,bonita,linda,diaria,objetivos`（95） |
| fi | `Mochi: Söpö tehtävälista` | `Tehtävät, muistutukset, widget`（不動） | `muistilista,tarkistuslista,todo,lista,suunnittelija,tavat,rutiini,ostoslista,kawaii,tavoitteet`（94） |
| fr-CA | `Mochi: Liste trop cute` | `Tâches, rappels et widget`（不動） | `todo,checklist,faire,choses,planificateur,habitudes,routine,épicerie,kawaii,mignonne,objectifs`（94） |
| fr-FR | `Mochi: Liste toute mignonne` | `Checklist, tâches et rappels`（不動） | `todo,faire,choses,widget,planning,habitudes,routine,courses,kawaii,mignon,jolie,quotidien,objectifs`（99） |
| gu-IN | `Mochi: ક્યૂટ ટાસ્ક લિસ્ટ` | `સુંદર કાર્યો અને વિજેટ`（不動） | `કામ,યાદી,રીમાઇન્ડર,પ્લાનર,આદત,રૂટીન,ખરીદી,અભ્યાસ,લક્ષ્ય,ચેકલિસ્ટ,ટુડુ,todo,checklist`（84） |
| he | `Mochi: רשימת משימות חמודה` | `צ'קליסט, תזכורות וווידג'ט`（不動） | `מטלות,רשימה,todo,מתכנן,הרגלים,שגרה,קניות,סדר,לימודים,עבודה,וידג׳ט,חמוד,יומי,מטרות`（81） |
| hi | `Mochi: प्यारी टास्क लिस्ट` | `प्यारे काम और विजेट`（不動） | `सूची,रिमाइंडर,प्लानर,आदत,रूटीन,खरीदारी,पढ़ाई,लक्ष्य,चेकलिस्ट,क्यूट,टूडू,दैनिक,todo`（82） |
| hr | `Mochi: Slatki zadaci` | `Obaveze, podsjetnici i widget`（不動） | `zadataka,popis,lista,todo,checklist,planer,navike,rutina,kupnja,kawaii,slatko,dnevni,ciljevi`（92） |
| hu | `Mochi: Cuki feladatlista` | `Teendők, emlékeztetők, widget`（不動） | `teendőlista,feladatok,lista,todo,ellenőrzőlista,tervező,szokások,rutin,bevásárlás,aranyos,kawaii`（96） |
| id | `Mochi: Checklist Lucu` | `To do list, pengingat & widget`（不動） | `tugas,daftar,todo,planner,kebiasaan,rutinitas,belanja,kawaii,imut,aesthetic,harian,tujuan`（89） |
| it | `Mochi: Lista carina` | `To do list, promemoria, widget`（不動） | `cose,fare,todo,checklist,attività,planner,abitudini,routine,spesa,kawaii,carino,obiettivi`（89） |
| kn-IN | `Mochi: ಕ್ಯೂಟ್ ಟಾಸ್ಕ್ ಲಿಸ್ಟ್` | `ಮುದ್ದಾದ ಕೆಲಸ ಮತ್ತು ವಿಜೆಟ್`（不動） | `ಪಟ್ಟಿ,ರಿಮೈಂಡರ್,ಪ್ಲಾನರ್,ಅಭ್ಯಾಸ,ರೂಟೀನ್,ಶಾಪಿಂಗ್,ಚೆಕ್ಲಿಸ್ಟ್,ಟುಡು,ದೈನಂದಿನ,ಗುರಿ,todo,checklist`（88） |
| ko | `Mochi: 귀여운 할 일 목록 & 체크리스트` | `포근한 투두리스트·플래너·위젯` | `할일,해야할일,알림,습관,루틴,장보기,공부,업무,목표,집안일,시간관리,계획,감성,파스텔,잠금화면,학생,데일리`（60） |
| ml-IN | `Mochi: ക്യൂട്ട് ലിസ്റ്റ്` | `ജോലികളും വിജറ്റും`（不動） | `ടാസ്ക്,ജോലി,റിമൈൻഡർ,പ്ലാനർ,ശീലം,റൂട്ടീൻ,ഷോപ്പിംഗ്,വിജറ്റ്,പഠനം,ചെക്ക്ലിസ്റ്റ്,ലക്ഷ്യം,todo,checklist`（100） |
| mr-IN | `Mochi: क्यूट टास्क लिस्ट` | `गोंडस कामे आणि विजेट`（不動） | `काम,यादी,रिमाइंडर,प्लॅनर,सवय,रूटीन,खरेदी,अभ्यास,ध्येय,चेकलिस्ट,टूडू,दैनंदिन,todo`（80） |
| ms | `Mochi: Senarai Comel` | `Tugas, peringatan dan widget`（不動） | `todo,checklist,semak,perancang,planner,tabiat,rutin,beli-belah,kawaii,harian,matlamat`（85） |
| nl-NL | `Mochi: Schattige taken` | `Takenlijst, checklist, widget`（不動） | `todo,lijst,herinnering,planner,gewoontes,routine,boodschappen,kawaii,schattig,dagelijks,doelen`（94） |
| no | `Mochi: Søt huskeliste` | `Gjøremål, sjekkliste og widget`（不動） | `gjøremålsliste,todo,oppgaver,liste,påminnelse,planlegger,vaner,rutine,handleliste,kawaii,daglig,mål`（99） |
| or-IN | `Mochi: କ୍ୟୁଟ୍ ଟାସ୍କ ଲିଷ୍ଟ` | `ସୁନ୍ଦର କାମ ଓ ୱିଜେଟ୍`（不動） | `ତାଲିକା,ରିମାଇଣ୍ଡର,ପ୍ଲାନର,ଅଭ୍ୟାସ,ରୁଟିନ,କିଣାକାଟା,ପଢ଼ା,ଚେକଲିଷ୍ଟ,ଲକ୍ଷ୍ୟ,todo,checklist`（81） |
| pa-IN | `Mochi: ਕਿਊਟ ਟਾਸਕ ਲਿਸਟ` | `ਪਿਆਰੇ ਕੰਮ ਤੇ ਵਿਜੇਟ`（不動） | `ਸੂਚੀ,ਰਿਮਾਈਂਡਰ,ਪਲੈਨਰ,ਆਦਤ,ਰੂਟੀਨ,ਖਰੀਦਦਾਰੀ,ਪੜ੍ਹਾਈ,ਟੀਚਾ,ਚੈਕਲਿਸਟ,todo,checklist`（73） |
| pl | `Mochi: Urocza lista zadań` | `To do, checklista i widżet`（不動） | `zadania,todo,przypomnienia,planner,nawyki,rutyna,zakupy,widget,kawaii,słodka,codzienne,cele`（91） |
| pt-PT | `Mochi: Lista amorosa` | `Checklist de tarefas giras`（不動） | `afazeres,todo,lembrete,planeador,hábitos,rotina,compras,widget,organização,kawaii,fofa,objetivos`（96） |
| ro | `Mochi: Listă drăguță` | `Sarcini, memento-uri și widget`（不動） | `todo,checklist,lucruri,făcut,planner,obiceiuri,rutină,cumpărături,kawaii,drăguț,zilnic,obiective`（96） |
| ru | `Mochi: Милый список дел` | `Чек-лист, задачи и виджет`（不動） | `дела,туду,todo,чеклист,напоминания,планер,ежедневник,привычки,рутина,покупки,кавай,милые,цели`（93） |
| sk | `Mochi: Milé úlohy` | `Checklist, pripomienky, widget`（不動） | `zoznam,úloh,todo,plánovač,návyky,rutina,nákup,kawaii,roztomilé,denný,ciele`（74） |
| sl-SI | `Mochi: Ljubek seznam` | `Ljubki opravki in gradnik`（不動） | `opravila,opravil,todo,checklist,opomnik,planer,navade,rutina,nakupi,widget,kawaii,dnevni,cilji`（94） |
| sv | `Mochi: Söt att-göra-lista` | `Checklista, sysslor & widget`（不動） | `todo,uppgifter,påminnelse,planerare,vanor,rutin,inköpslista,kawaii,söta,daglig,mål`（82） |
| ta-IN | `Mochi: க்யூட் டாஸ்க் லிஸ்ட்` | `அழகான பணிகள் விட்ஜெட்`（不動） | `வேலை,பட்டியல்,ரிமைண்டர்,பிளானர்,பழக்கம்,ரூட்டீன்,ஷாப்பிங்,செக்லிஸ்ட்,இலக்கு,படிப்பு,todo,checklist`（98） |
| te-IN | `Mochi: క్యూట్ టాస్క్ లిస్ట్` | `ముద్దైన పనులు విడ్జెట్`（不動） | `పని,జాబితా,రిమైండర్,ప్లానర్,అలవాటు,రూటీన్,షాపింగ్,చెక్లిస్ట్,లక్ష్యం,చదువు,todo,checklist`（89） |
| th | `Mochi: เช็กลิสต์น่ารัก` | `สิ่งที่ต้องทำ พร้อมวิดเจ็ต`（不動） | `งาน,รายการ,เตือนความจำ,แพลนเนอร์,นิสัย,รูทีน,ซื้อของ,เรียน,งานบ้าน,เช็คลิสต์,คิวท์,เป้าหมาย,todo`（96） |
| tr | `Mochi: Sevimli Liste` | `Yapılacaklar listesi ve widget`（不動） | `görevler,todo,kontrol,hatırlatıcı,planlayıcı,alışkanlık,rutin,alışveriş,kawaii,tatlı,hedefler`（93） |
| uk | `Mochi: Милий список справ` | `Чекліст, завдання та віджет`（不動） | `справи,задачі,туду,todo,нагадування,планер,звички,рутина,покупки,органайзер,кавай,милі,цілі`（91） |
| ur-PK | `Mochi: پیاری ٹاسک لسٹ` | `پیارے کام اور ویجٹ`（不動） | `فہرست,یاددہانی,پلینر,عادت,روٹین,خریداری,پڑھائی,مقصد,ویجیٹ,چیک لسٹ,ٹوڈو,todo,checklist`（85） |
| vi | `Mochi: Checklist dễ thương` | `Việc cần làm & widget nhắc nhở` | `todo,to do list,danh sách,công việc,planner,thói quen,routine,mua sắm,kawaii,cute,mục tiêu,hằng ngày`（100） |
| zh-Hans | `Mochi: 可爱待办清单` | `治愈待办事项・提醒・锁屏小组件` | `todo,任务清单,备忘录,习惯,计划,购物,打卡,时间管理,效率,学习,工作,便签,目标,生活,作业,日计划,记事,重复,少女心,手表,安排`（71） |

</details>
