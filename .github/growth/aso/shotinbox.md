# ShotInbox 副標與關鍵字：模型 1/2 調教結果（2026-10-13）

這份是第一個模型的調教結果，還要等第二個模型獨立驗證。依你的長期規則，兩個模型都驗證過，副標和關鍵字才會自動套用到 ASC。這次沒有改 App Store Connect，也沒有改 `_engine/`。50 個語系的完整數字和證據在 [`shotinbox.json`](shotinbox.json)，套用檔是 [`shotinbox-asc-payload.json`](shotinbox-asc-payload.json)。

## 結論

1. **問題確認是「沒人看到」。** 在 US、TW、JP、KR、DE 實測 28 個目標詞，ShotInbox 一個都沒進前 12 名。名稱裡就有的「截圖整理」「スクショ整理」「스크린샷 정리」也一樣。
   - 這些詞的前 12 名大多只有 0–200 則評分，競爭不算硬。
   - Clutter 一款 App 在 TW、JP、KR 都拿到第 1（1,186／146／933 則）。
   - 結論：改文字是必要的，但不保證上榜。0 評分和下載速度還是主要瓶頸。
2. **副標改用實測過、搜尋意圖相同的詞，不再寫功能名稱。** 拿掉的是「時間軸／タイムライン／타임라인」「Photo Cleaner」「Tidy Camera Roll」這類詞，換成搜尋、刪除、整理類的詞。這樣「截圖＋刪除／搜尋／整理」可以在同一個語系內組成搜尋詞。
3. **照片清理類的字交給 PicClear。** 各語系刪掉 photo cleaner、duplicate、similar、storage、照片、重複、相似、容量這類字，避免兩款 App 搶同一組詞。德文舊副標「Fotos aufräumen」剛好就是 PicClear 的德文名稱，已經換掉。
4. **名稱一個字都沒改。** 實測發現資料檔已經過期：18 個語系的線上名稱或副標跟 `_engine/data/shotinbox_full.json` 不一樣（v1.0.4，10/09 上架）。例如繁中的名稱是「ShotInbox AI：截圖整理」，不是檔案裡的「Sort Screenshots」。所以套用檔的 name 用的是線上實測值。如果照檔案值送出，等於改了標題。
5. **最薄的機會：JP「スクショ 検索」。** 前 12 名只有 4 個截圖搜尋 App。其次是 TW「截圖 搜尋」和 KR 五個詞，前幾名幾乎都是 0 評分的新 App。

## 直接貼上（優先店面）

括號是字數。副標上限 30，關鍵字上限 100。關鍵字照原樣貼，逗號後面不要加空格。名稱欄不要動。

| 店面 | ASC 語言 | 名稱（不動） | 副標 | 關鍵字 |
|---|---|---|---|---|
| US（en-US 也在 TW、HK、KR、GB、AU、DE、JP 被索引） | English (U.S.) | ShotInbox AI: Sort Screenshots | `Organizer, Search & Delete`（26） | `cleaner,manager,text,ocr,find,organize,cleanup,remove,old,bulk,archive,categorize,sorter,tidy`（93） |
| TW＋HK | 繁體中文 | ShotInbox AI：截圖整理 | `OCR文字搜尋・自動分類・刪除清理`（17） | `螢幕,屏幕,截屏,快照,管理,收納,歸檔,歸類,尋找,找圖,辨識,擷取,批次,大量,清除,移除,手機,斷捨離,篩選`（57） |
| JP | 日本語 | ShotInbox AI：スクショ整理 | `OCR文字検索・自動仕分け・削除で片付け`（20） | `スクリーンショット,管理,分類,認識,テキスト,探す,見つける,一括,まとめて,断捨離,掃除,消す,整頓,収納,振り分け,スマホ`（64） |
| KR | 한국어 | ShotInbox AI: 스크린샷 정리 | `캡처 텍스트 검색·자동 분류·삭제`（18） | `스샷,캡쳐,화면,관리,글자,문자,OCR,찾기,보관함,일괄,청소,정돈,지우기,인식,아카이브`（49） |
| DE | Deutsch | ShotInbox AI: Screenshots | `Sortieren, Suchen & Löschen`（27） | `text,ocr,ordnen,aufräumen,organisieren,verwalten,finden,bildschirmfotos,entfernen,ausmisten`（91） |
| GB、AU（另有 en-US） | English (U.K.) | ShotInbox AI: Sort Screenshots | `Organiser, Search & Delete`（26） | `screengrab,screencap,clear,finder,categorise,organise,cleaner,manager`（69） |

- 中、日、韓的關鍵字刻意沒有填滿 100 字。剩下能填的字不是錯意圖，就是 PicClear 的詞，所以先空著，等有量測證據再補。
- en-CA 用 en-US 那一組，en-AU 用 en-GB＋核心字，都只是保險：en-AU 在 AU 實測不被索引，en-CA 有沒有被索引還沒驗證。

## 證據（2026-10-13，App Store 網頁版搜尋前 12 名）

| 店面 | 搜尋詞 | 我們 | 第 1 名（評分數） | 意圖 |
|---|---|---|---|---|
| US | screenshot organizer | 不在前 12 | Tote（161） | 同意圖，12/12 是整理類，多數 0–104 則 |
| US | delete screenshots | 不在前 12 | Delete Screenshots（0） | 同意圖，12/12 是截圖清理 |
| US | screenshot search | 不在前 12 | CaptureMind（0） | 同意圖，7/12（其餘是以圖搜圖） |
| US | screenshot cleaner | 不在前 12 | Slidebox（1.7 萬） | 同意圖 |
| US | screenshot manager | 不在前 12 | Screenshot Manager（38） | 同意圖，11/12 |
| US | screenshots | 不在前 12 | ScreenshotApp（16） | 不同：多是拼接、編輯工具 |
| TW | 截圖整理 | 不在前 12 | Clutter - 截圖整理（1,186） | 同意圖，9/12 |
| TW | 截圖 刪除 | 不在前 12 | Clutter（1,186） | 同意圖，但多是照片清理大廠 |
| TW | 截圖 搜尋 | 不在前 12 | Screenshot Organizer 截圖整理與搜尋（0） | 同意圖，8/12，幾乎全是 0 評分 |
| TW | 截圖 清理 | 不在前 12 | Slidebox（2,882） | 照片清理意圖（PicClear 的範圍） |
| TW | 截圖／照片 文字 搜尋 | 不在前 12 | 長截圖工具／Google | 不同意圖，不採用 |
| JP | スクショ整理 | 不在前 12 | Clutter（146） | 同意圖，12/12 |
| JP | スクショ 削除 | 不在前 12 | Clutter（146） | 同意圖 |
| JP | スクショ 検索 | 不在前 12 | ScreenSeek（0） | 同意圖，只有 4/12 相關，**競爭最薄** |
| JP | スクリーンショット 整理 | 不在前 12 | Clutter（146） | 同意圖，11/12 |
| JP | スクショ／画像 文字 検索 | 不在前 12 | 截圖拍攝 App／OCR 掃描 App | 不同意圖 |
| KR | 스크린샷 정리／캡처 정리／스샷 정리／스크린샷 삭제／스크린샷 검색 | 都不在前 12 | Clutter（933）、Scrap（8）、SnapStash（3） | 全部同意圖，10–12/12 |
| DE | screenshots löschen | 不在前 12 | Slidebox（1,716） | 同意圖，其餘 0–27 則 |
| DE | screenshot organizer／screenshots sortieren | 不在前 12 | Slidebox／Swipewipe | 同意圖 |
| DE | bildschirmfoto | 不在前 12 | Longshot（25） | 不同：螢幕錄影、桌布 |

**索引探針：**「shotinbox receipts」（US）、「截圖 食譜」（TW）、「スクショ 買い切り」（JP）都沒有命中。這三個字都在資料檔的關鍵字裡，所以線上的關鍵字很可能已經和檔案不一樣。

**同名 App：** iTunes API 在 US 搜「shotinbox」，第 1 名是另一款叫「ShotInbox」的 App（id 6799644679），我們排第 2。這是品牌風險，不在這次能改的欄位裡。

**量測用量：** 網頁搜尋 30 次、iTunes API 3 次（遇到 1 次 403 就停用），沒有超過約 35 次的上限。另外逐一抓了 50 個語系的產品頁，核對名稱和副標。

## 刪了什麼、加了什麼、為什麼

**刪掉**
- **照片清理意圖，交給 PicClear：** Photo Cleaner、photos、duplicate(s)、similar、storage、camera roll、album、gallery、照片、重複、相似、瘦身、釋放空間、写真、重複、類似、容量節約、クリーナー、사진、중복、유사、용량확보、Fotos aufräumen、reiniger、duplikate、speicher。
- **沒有人搜的賣點詞：** 隱私保護、離線處理、永久買斷、端末内、買い切り、プライバシー、평생소장、기기내처리、private、offline。
- **會搜到別種 App 的分類詞：** receipts／收據、links、notes、QR、食譜、地圖、對話、레시피、지도、채팅、belege。
- **錯字：** 韓文「청소기」是吸塵器。
- **跟名稱或副標重複的字：** 例如日文副標裡的「スクショ」，名稱裡已經有。
- **競品品牌：** clutter 是主要競品的名字，刻意不放進關鍵字。

**加上**
- **截圖的口語與同義詞：** 螢幕、屏幕（HK）、截屏；スクリーンショット；스샷、캡쳐；bildschirmfotos；screengrab（英式）。
- **刪除和清理類的詞（這是 App 實際能做的事，刪除前「照片」App 會再確認）：** delete、remove、bulk、刪除清理、清除、削除、消す、掃除、断捨離、삭제、지우기、Löschen、ausmisten。
- **搜尋和文字類的詞（App 的核心功能是 OCR）：** search、text、ocr、文字搜尋、辨識、文字検索、テキスト、텍스트 검색、글자、Suchen、text。
- **整理和管理類的詞：** organizer、manager、organize、管理、收納、仕分け、관리、ordnen、verwalten。

## 其他 45 個語系（較輕量）

規則相同，只修有問題的地方，`depth` 標為 `light`：

- 刪掉混在本地欄位裡的英文「photo cleaner」，有 cs、hr、hu、pl、ro、ru、sk、sl-SI、uk、vi。
- 刪掉重複、相似、照片、隱私、買斷、時間軸類的字，補上當地的「刪除」「截圖」說法。例如 pt-BR 用 print，it 用 screenshot、schermata，ru 用 скрин，th 用 แคปจอ。
- 英文三個語系（en-GB、en-AU、en-CA）之外，還有 8 個語系的副標改了：
  - es-ES、es-MX、it：原本是「清理照片」意圖，改成截圖用語。
  - pt-BR：改成「Organize e apague seus prints」。
  - zh-Hans：名稱是英文，所以「截图整理」放進副標。
  - vi：名稱沒有 screenshot，副標補「Chụp màn hình」。
  - th、ru：各補「搜尋、刪除」或「搜尋」。
- 印度各語系、ar、he、ur 的線上副標已經是「截圖整理＋OCR 搜尋」，保留不動，只清關鍵字。

## 套用前要注意

1. **這 18 個語系的線上關鍵字可能跟資料檔不同：** ar-SA、bn-BD、de-DE、gu-IN、he、hi、ja、kn-IN、ko、ml-IN、mr-IN、or-IN、pa-IN、ta-IN、te-IN、ur-PK、vi、zh-Hant。
   - 套用檔在這些語系標了 `expected_current_keywords_verified: false`。
   - 套用時只比對 name 和 subtitle。name 不同就停；keywords 不同是預期中的，照樣用建議值覆蓋。
2. **還沒驗證的事：**
   - 各詞的搜尋量：Apple 的搜尋建議端點不能用。
   - Apple 會不會把 organize／organizer、sort／sorter 當成同一個字。如果會，organize 和 sorter 可以換成別的字。
   - 印度各語系在 IN 店面會不會被索引。
   - en-CA 在 CA 會不會被索引。
3. **期望要實際。** 文字只決定「搜得到」，不決定排第幾。上線 2–4 週後重測同一組詞。如果還是進不了前 12，瓶頸就是評分和下載速度，不是文字。
