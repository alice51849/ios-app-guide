# 新 App 規格：Lensafe（針孔偵測）

> Lumi Studio 組合第 **58** 號（資料夾 `58_Lensafe`，Bundle ID `com.alice51849.Lensafe`）。這份是給本機 Mac Claude 照著開工的完整規格，研究日期 2026-10-14。
> 給店主看的說明一律用繁體中文（台灣用語）；商店文案用各目標語言撰寫。
> **店主已拍板（2026-10-14）：付費下載 US$4.99。沒有免費版、沒有 App 內購買、沒有訂閱、沒有廣告、不追蹤、不用帳號。上市不做早鳥價，也不排漲價。**
> 結構與設計慣例對齊 57_OFFDAY（`project.yml`、`Docs/DESIGN_V2.md`／`DESIGN_V4.md`、`Packages/OffdayFeatures/Tools/brand.json`、`Docs/research/05_registration_receipt.md`、`Docs/research/15_pricing_study.md`），只參考，不複製程式或字串。

---

## ★ 第一優先：UX 方向與七個招牌功能（店主 2026-10-14 指定，其他章節有衝突時以這節為準）

### ★.1 打開就是相機，自動標出可能的鏡頭
- **App 一打開就是全螢幕的即時相機**：沒有引導頁，也沒有選單。手電筒自動開始脈衝閃爍，反光差分在畫面上即時畫出標記。使用者唯一要做的事，就是拿著手機慢慢掃過房間。
- **第一次開啟**：直接跳出系統的相機授權，用途說明只有一句話（en：「Lensafe uses the camera and flashlight to spot lens reflections around you. Video never leaves your iPhone.」；zh-Hant：「Lensafe 用相機和手電筒找出周圍的鏡頭反光，影像不會離開你的 iPhone。」）。被拒絕時，畫面中央只顯示一句話，加上「開啟設定」按鈕。
- **誠實說明不擋路**：第一次掃描時，底部浮出一個玻璃小膠囊，寫著「手機能查的是三種常見跡象，不是全部 · 了解」，6 秒後自動收起。之後隨時可以從控制列的 ⓘ 打開完整的限制說明。結果永遠不說「安全」。
- **其他功能都是次要的**：紅外線、Wi-Fi／藍牙、清單、報告，都從底部一條小小的玻璃控制列進入，以 sheet 或疊加層出現，關掉就回到相機。

### ★.2 七個招牌功能（商品頁和鉤子片的故事主軸）與可行性
| # | 招牌功能 | 做法 | 可行性（依 Apple 文件查核） |
|---|---|---|---|
| H1 | **零點擊即時偵測**：打開就出現標記，標記外圈是信心環（「可能是鏡頭」或「反光」），不是假雷達 | 6.1 的手電筒脈衝加差分，再加時間追蹤。信心環的弧長等於分數。分數 ≥ 0.7 用實線琥珀色圈，標「可能是鏡頭」；0.4–0.7 用虛線，標「反光？」 | ✅ 可行。AVFoundation 的手電筒和自訂曝光都是公開 API。 |
| H2 | **確認這一點**：點一下標記 → 自動放大 → 視差檢查 → 手電筒開關測試 → 給出判斷 | 見 6.1A。真正的鏡頭反光換角度後還是一個小點，位置固定在場景上；一般亮面的反光會拉長、會在表面上滑動。再加上 3 次手電筒開關測試：關燈就消失、開燈就回來，才算「很可能是鏡頭」。這一步直接處理競品評論最常罵的誤報問題。 | ✅ 可行。放大有兩種：從 1080p/4K 畫面做數位裁切；Pro 機型可以切到長焦虛擬鏡頭（`videoZoomFactor`，用 `ramp`）。判斷準確度要靠 6.1 的 QA 矩陣實測，⚠️ 上架前不可以宣稱任何準確率數字。 |
| H3 | **全房間掃描覆蓋率**：用陀螺儀記錄已經掃過的方向，顯示「已掃描 82%」，並提示還沒掃到的區域 | 見 6.5A。用 CoreMotion 的 `CMMotionManager.deviceMotion` 姿態（不需要任何權限），把鏡頭朝向切成 15° × 15° 的方位格，範圍是水平 360°、垂直 −35° 到 +65°（藏東西最常見的高度）。在某個方位格穩定停留 ≥ 0.5 秒、而且有處理到有效影格，才算「已掃過」。畫面邊緣用小箭頭指向最近的還沒掃到的方位。 | ✅ 可行。**刻意不用 ARKit**，因為 ARKit 會接管相機，跟我們自己控制手電筒和曝光的 AVCaptureSession 衝突。覆蓋率指的是「方向」，不是牆面面積，畫面上要寫清楚。 |
| H4 | **雙鏡頭 IR 輔助**：支援 `AVCaptureMultiCamSession` 的機型，在暗房時自動開一個小小的前鏡頭 IR 子母畫面 | 環境夠暗（6.2 的暗度門檻）時，自動在角落浮出前鏡頭的 IR 子母畫面。**前鏡頭看的是你背後的方向**，所以一次掃描可以同時看兩個半球，要在畫面上說明。不支援的機型或系統壓力過高時，改成「一鍵切到前鏡頭」。 | ✅ 大致可行。`AVCaptureMultiCamSession.isMultiCamSupported` 從 iOS 13 起支援 iPhone XS/XR 以後的機型，iOS 26 支援的機型全部在內。前後鏡頭可以同時用（Apple 工程師在論壇確認），合法組合以 `supportedMultiCamDeviceSets` 為準。⚠️ multicam 只能用支援它的格式，而且有 `hardwareCost`／`systemPressureCost` 的限制。要先實測「後鏡頭手電筒脈衝＋前鏡頭長曝光」能不能同時跑，跑不動就退回一鍵切換。 |
| H5 | **LiDAR 鏡頭檢查（Pro 機型，實驗功能）** | 用 ARKit 的 `ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth)`，取得 `sceneDepth.depthMap` 和 `confidenceMap`，找出「影像上有反光、深度圖卻在同一點出現低信心或異常值」的點，當作**輔助證據**，加權到 H2 的判斷。參考 LAPD（SenSys '21，以手機 ToF 偵測針孔鏡頭）。只在支援 sceneDepth 的機型顯示，其他機型完全隱藏。 | ⚠️ **不確定，標為實驗功能**。iOS 只提供深度和信心，**不開放 LiDAR 的原始反射強度**；LAPD 用的正是強度。深度圖解析度也低（約 256×192），遠處的小鏡頭可能根本落不到一個像素上。ARKit 執行時會接管相機，所以只能在 H2 確認流程裡短暫切過去跑 1–2 秒。ARKit 的 `configurableCaptureDeviceForPrimaryCamera` 能不能同時控制手電筒，也沒查到確定答案。v1 預設關閉，放在「實驗功能」開關後面。**商店文案與鉤子片都不提**，等 QA 證明有加分再說。 |
| H6 | **住宿報告**：證據照片附上時間和地點，一鍵輸出 PDF，傳給房東、飯店或警方；依每次住宿保存歷史紀錄 | 5.8、F9。地點是使用者自己輸入的住宿名稱，**不用定位權限**；照片的時間戳來自系統時鐘。 | ✅ 可行。 |
| H7 | **完全離線**，不用帳號，沒有廣告，50 種語言 | Wi-Fi 檢查只在區域網路內進行，沒有任何對外連線。 | ✅ |

### ★.3 安全與續航（自動脈衝帶來的新要求）
- **光敏感**：閃爍的頻率要 **≤ 3 次／秒**，參考 WCAG 2.3.1 的三次閃光門檻。所以手電筒脈衝的預設值是 3 Hz（亮 167 ms、暗 167 ms），不用 5 Hz。設定裡提供「穩定模式」：手電筒常亮，只做單幀偵測。開啟「減少動態效果」時，預設就用穩定模式。第一次脈衝前，在 ⓘ 說明裡寫清楚「手電筒會閃爍」。
- **發熱與電量**：監看 `ProcessInfo.thermalState` 和 `AVCaptureDevice.systemPressureState`。到了 `.serious`，就把手電筒亮度降到 0.6、影格率降到 24 fps；到了 `.critical`，就暫停脈衝並提示。App 退到背景時，立刻關掉手電筒。閒置 90 秒（陀螺儀顯示手機沒在動）時，暫停脈衝。

---

## 0. 一頁摘要（先看這裡）

| 項目 | 內容 |
|---|---|
| UX | **打開就是相機，自動標出可能的鏡頭**（見 ★ 節）。紅外線、Wi-Fi／藍牙、清單、報告都是從玻璃控制列進入的次要功能。 |
| 一句話 | 入住前花幾分鐘查房：用 iPhone 檢查三種常見跡象，分別是**鏡頭反光、夜視紅外線光點、同一個 Wi-Fi／藍牙上像攝影機的裝置**，再配一份依場景整理的「常見藏匿點」清單。 |
| 不做的事 | 不用磁力計當偵測器（不可靠）。不宣稱抓得到竊聽器。不說「100%」或「保證」。不登入攝影機、不看串流、不猜密碼。 |
| 名稱 | **Lensafe**（店主 2026-10-14 選定）。建立 Bundle ID 之前，要先完成正式商標檢索（第 1 節）。 |
| 價格 | **US$4.99 付費下載**（₩7,700／¥800／NT$150）。理由與風險見第 7 節。 |
| 主力市場 | KR（몰카）、JP（盗撮）、TW（針孔）、US，再加上旅遊市場。KR、JP、TW 的搜尋結果前幾名評分數都只有幾十到幾百則，**新 App 有機會排進前段**；US 前段是 1 萬多則評分的訂閱制 App，要靠外部流量。 |
| 差異化 | 競品幾乎都是「免費下載，掃描結果鎖在每週 $8.99–$9.99 的訂閱後面」（評論裡最常被罵的就是這點），而且多半拿磁場或「AI」當賣點。我們是**付一次、全部能用，付款前在截圖就看清楚它檢查什麼、不檢查什麼**，還內建「自我測試」：用電視遙控器或另一支手機的鏡頭，當場證明功能有在運作。 |
| 技術 | SwiftUI，iOS 26 起，Liquid Glass。AVFoundation（前、後鏡頭與手電筒）、Network.framework（Bonjour 與單點傳送探測）、CoreBluetooth。全部在手機上處理，不連任何伺服器。 |
| 審核風險 | 4.3(b)（類別已飽和）與 2.3.1（宣稱不實）。對策見第 9 節。 |

---

## 1. 名稱

### 1.1 定案：**Lensafe**（店主 2026-10-14 從十選一選定）
- 顯示名稱：`Lensafe`。資料夾與 repo 是 `58_Lensafe`，建議 Bundle ID 用 `com.alice51849.Lensafe`（跟 `com.alice51849.Offday` 同一套規則）。
- 為什麼合適：Lens 指的正是我們在找的「鏡頭」；safe 講的是住得安心。名稱沒有間諜或駭客的意味。
- 我做的初步查核（2026-10-14）：
  - USPTO 有一筆舊的 LENSAFE 文字商標（serial 73239868，1981 年註冊，類別是眼鏡盒），**2002 年已因 Section 8 註銷**；
  - 網路上找不到同名的 App 或品牌；
  - 協調者在 US、KR、JP、TW 的 App Store 網頁搜尋中，也沒有完全相同或前綴相同的名稱。
- **建立 Bundle ID 之前，本機管線一定要先做正式的商標檢索**：USPTO、EUIPO、JPO（J-PlatPat）、KIPO（KIPRIS）、TIPO（台灣智慧局），類別 9 與 42。只要有任何衝突，就停下來回報店主。
- 誠實提醒：名稱裡的「safe」不能被延伸成「保證安全」。副標和文案只說「檢查三種常見跡象」，結果頁永遠不說「安全」（第 5、9 節）。
- 十選一的其他候選（作為紀錄）：CamSense、Haloscan、Stayvue、RoomSure、Lenscout、Pinpeek、Camless、Roomlume、Glintra。

### 1.2 改名點與內部識別（照 57_OFFDAY 的做法）
- 內部識別名：`Lensafe`。
  - 模組：`LensafeCore`、`LensafeCapture`、`LensafeNetwork`、`LensafeDesignSystem`、`LensafeFeatures`。
  - Bundle ID：`com.alice51849.Lensafe`。
  - 資料夾與收據鍵：`58_Lensafe`。
  - **建立之後永遠不改**，就算以後顯示名稱要換也一樣。
- 顯示名稱只有一個改名點，由三個地方組成：
  - `Packages/LensafeFeatures/Tools/brand.json` 的 `productName`（不翻譯）；
  - `project.yml` 的 `LENSAFE_DISPLAY_NAME`（`CFBundleDisplayName = $(LENSAFE_DISPLAY_NAME)`）；
  - L10n key `app.name`。
- 程式碼、權限說明、HTTP User-Agent 都不寫死品牌名。
- 台帳要回寫兩處：`app-portfolio.md` 第 58 列，以及 `app-requirements.md` 的「### 58. Lensafe — 58_Lensafe」段落。

---

## 2. 市場與競品（2026-10-14 實測）

### 2.1 競品
| App | 模式與價格 | 規模 | 主打 | 我們可以利用的弱點 |
|---|---|---|---|---|
| Hidden Camera Detector – Peek（88 Tech／Kupertino Labs） | 免費下載＋內購。每週 $8.99／$9.99、每季 $29.99、終身 $59.99，另有 $6.99–$44.99 的各種組合 | US 1.7 萬則評分（4.4 星），KR 86 則，JP 392 則；年齡分級 18+ | 磁場偵測、網路掃描 | 內購品項多到讓人看不懂；把磁場當賣點。 |
| Hidden Spy Camera Finder Pro（DREAMTEAM） | 免費＋訂閱 | US 11,840 則，KR 158 則 | — | 訂閱 |
| Cam Detector App: Home Security（AppNexus） | 免費＋訂閱 | US 15,987 則 | — | 訂閱 |
| Camera Detector App（Om Solutions） | 免費＋訂閱 | US 9,990 則 | — | 訂閱 |
| #1 Hidden Camera Detector（Gibco） | 免費＋內購 | US 3,744 則，JP 51 則（18+） | **磁場感測器**，連隱藏麥克風也宣稱抓得到 | 宣稱誇大 |
| 針孔攝像頭探測器（META GRAPH，TW） | 免費＋每週／每年／終身訂閱 | TW 8 則（3.0 星） | Wi-Fi、藍牙、紅外線 | 簡體用語，評分低 |
| Electronics & Spy Cam Detector | **付費 $4.99**（iPad 版） | 少 | 鏡頭反光 | 證明這個類別有人願意付 $4.99 買斷 |
| DontSpy | 列價 $2.99（第三方比較頁，未在 App Store 驗證） | — | 被動 IR | — |

**評論裡最常見的抱怨**（彙整自第三方評論）：掃描完結果鎖在付費牆後面，「一直要我付錢」；強制訂閱、不知道怎麼取消；有人覺得被騙。這個抱怨模式正是我們做「付費下載、全部功能直接給」的理由。

### 2.2 各國競爭強度（App Store 搜尋前段的評分數）
- **US**「hidden camera detector」：前 8 名裡有 5 款超過 9,900 則評分（Peek 16,689、Cam Detector 15,987、DreamTeam 11,840、Om 9,990）→ **高**。付費 App 很難靠這個主詞排上去。
- **KR**「몰카탐지기」：第 1 名只有 228 則，其他多半 0–158 則 → **低**。
- **JP**「隠しカメラ」「盗撮カメラ発見」：Peek 392 則、スパイカメラ 277 則，其他 1–63 則 → **低**。另外要注意：搜「隠しカメラ」時，前段混了「無音カメラ／シークレットレコーダー」這類**偷拍工具**，我們的文案要和它們劃清界線。
- **TW**「針孔」：前段 35–568 則（第 1 名 223 則，其他像 360防護 568 則、防拍衛士 467 則）→ **低**。大多是簡體或港式用語（攝像頭、酒店），**台灣用語（攝影機、飯店、民宿）幾乎沒人在用**。

### 2.3 技術事實（決定功能能宣稱到哪裡）
- **鏡頭反光（retroreflection）**：鏡頭加上感光元件會把光反射回光源方向（貓眼效應）。手電筒緊貼著後鏡頭，所以反光點特別亮。這招**對沒開紅外線、沒連網的攝影機也有效**。不過第三方實測指出，距離要在 1 公尺左右，角度也要剛好對到。學術上可參考 LAPD（SenSys '21，用 ToF 雷射找針孔鏡頭，88.9% 對比肉眼 46.0%）；但 **iOS 不開放 LiDAR 的原始強度資料**，我們做不出 LAPD，只能用手電筒閃爍加影像差分。
- **紅外線**：很多針孔攝影機有夜視 IR LED（850 nm 看得到微弱紅光，940 nm 更不明顯）。iPhone **前鏡頭**的 IR 濾鏡比較弱，看得到一些紅外線；**後鏡頭**濾得很乾淨，幾乎看不到。所以 IR 模式要用前鏡頭，而且只在「關燈，加上對方有開夜視」時才有用。效果依機型而異，所以要內建遙控器自我測試。
- **Wi-Fi**：iOS **拿不到 MAC 位址，也不能掃描附近的 Wi-Fi 熱點**，只看得到「自己連上的這個網路」裡的裝置。很多飯店 Wi-Fi 開了用戶端隔離，裝置之間互相看不到；有些攝影機用 4G 或只錄進記憶卡。這些都要在畫面上直接說清楚。
- **藍牙**：只看得到正在廣播 BLE 的裝置。多數 Wi-Fi 針孔攝影機只在設定模式時才會廣播。
- **磁力計**：磁場「偵測」碰到任何金屬或電器都會跳，**不放進產品**，文案也不提。

---

## 3. 定位

- **英文定位句**：*Check a room for three common signs of a hidden camera — before you unpack.*
- **中文定位句**：入住先查房。三種常見跡象，加一份藏匿點清單。付一次，全部能用。
- **對誰**：一個人旅行的女性、出差族、Airbnb／民宿房客（在 App Store 中繼資料裡不寫 Airbnb）、去健身房更衣室的人、租屋族、韓國的 모텔 住客，還有日本出差住 ビジホ 的人。
- **跟競品比**：
  1. **誠實**：付款前就看得到「它檢查什麼、不檢查什麼」；結果頁永遠不說「安全」。
  2. **證明有效**：內建自我測試（遙控器 → IR 模式；另一支手機的鏡頭 → 反光模式）。使用者馬上看到它有在動，大幅降低「根本沒用」的一星。
  3. **流程**：一個「查房流程」把四個工具串起來，最後產出一份可以存證的報告（PDF）。
  4. **在地**：台灣用語、韓文、日文都由母語文案撰寫，不是簡體直轉，也不是機翻。
  5. **定價**：付一次，沒有訂閱陷阱。

---

## 4. 功能清單（含 iOS API、Info.plist、Entitlements）

### 4.1 功能
| # | 功能 | API | 說明 |
|---|---|---|---|
| F1 | 鏡頭反光掃描（Lens Glint） | AVCaptureSession（後置 `.builtInWideAngleCamera`）、`AVCaptureDevice.setTorchModeOn(level:)`、自訂曝光 `setExposureModeCustom`、Accelerate／vImage、Vision `VNTranslationalImageRegistrationRequest` | 手電筒閃爍＋影像差分＋時間追蹤。演算法見 6.1。 |
| F2 | 紅外線光點掃描（IR） | AVCaptureSession（前置 `.builtInWideAngleCamera`）、自訂曝光與白平衡 | 關燈後找肉眼看不到的光點。演算法見 6.2。 |
| F3 | IR 自我測試 | 同 F2 | 「對著前鏡頭按電視遙控器」。看得到 → 這支手機能用 IR 模式；看不到 → 標示「這支手機的前鏡頭看不到紅外線」，把 IR 檢查標成「不可用」，不假裝有檢查。 |
| F4 | 反光自我測試 | 同 F1 | 「在 1 公尺外對準另一支手機或筆電的鏡頭」，應該出現光圈。 |
| F5 | Wi-Fi 裝置檢查 | Network.framework：`NWBrowser`（Bonjour）、`NWConnection`（TCP 單點探測）、`getifaddrs`（自己的 IP 與遮罩） | 列出同一個網路上的裝置，標出 RTSP、ONVIF、攝影機品牌的標頭。演算法見 6.3。 |
| F6 | 藍牙裝置檢查＋靠近測量 | CoreBluetooth `CBCentralManager.scanForPeripherals(withServices: nil, options: [CBCentralManagerScanOptionAllowDuplicatesKey: true])` | 名稱或廠商資料像攝影機的會標出來；點進去有「冷／熱」靠近指示（RSSI 平滑）。演算法見 6.4。 |
| F7 | 藏匿點清單 | SwiftUI、SwiftData（或 Codable JSON） | 分成飯店、民宿／短租、更衣室／試衣間、公廁、租屋、健身房、辦公室。逐項打勾，可加註記與照片。 |
| F8 | 查房流程（選用） | — | 從「清單」進入，依序：相機掃到覆蓋率 ≥ 80% → Wi-Fi → 藍牙 → 關燈 IR → 清單 → 報告。可以跳過任一步，跳過的步驟會在報告上誠實標成「未檢查」。 |
| F9 | 報告 | `ImageRenderer` → PDF（CGContext）、`ShareLink` | 時間、地點名稱（使用者自己輸入，不用定位）、每項檢查的狀態、可疑點的截圖。用來向房東、平台或警方說明。 |
| F10 | 發現可疑怎麼辦 | 本地化靜態內容 | 不要自己拆、先拍照、換房、聯絡平台或警方，附當地專線（見 5.9）。 |
| F12 | 確認這一點（H2） | AVCaptureDevice `videoZoomFactor`／`ramp(toVideoZoomFactor:withRate:)`、Vision 追蹤 | 演算法見 6.1A。 |
| F13 | 掃描覆蓋率（H3） | CoreMotion `CMMotionManager.startDeviceMotionUpdates(using: .xArbitraryCorrectedZVertical)` | 演算法見 6.5A。 |
| F14 | 雙鏡頭 IR 子母畫面（H4） | `AVCaptureMultiCamSession`、`supportedMultiCamDeviceSets` | 不支援時，退回一鍵切換到前鏡頭。 |
| F15 | LiDAR 實驗（H5） | ARKit `sceneDepth`／`confidenceMap` | 預設關閉，只在支援的機型顯示。 |
| F11 | App 內切換語言 | String Catalog＋工作室既有的 App 內語言切換元件 | 約 50 種語言，沿用工作室慣例。 |

**明確不做**：磁力計偵測、「AI 一鍵找出所有攝影機」、竊聽器或麥克風偵測、登入攝影機或看串流、帳號、雲端、分析、廣告、App 內購買。

### 4.2 Info.plist
| Key | 值（en；其他語言放進 InfoPlist.xcstrings） |
|---|---|
| `NSCameraUsageDescription` | "This app uses the rear camera with the flashlight to spot lens reflections, and the front camera in the dark to spot infrared lights. Video never leaves your iPhone." |
| `NSLocalNetworkUsageDescription` | "This app looks for devices on the Wi-Fi you're connected to that answer like a camera (for example, a video stream port). It never logs in to or views any device." |
| `NSBonjourServices` | `_rtsp._tcp`、`_http._tcp`、`_https._tcp`、`_hap._tcp`、`_airplay._tcp`、`_googlecast._tcp`、`_onvif._tcp` |
| `NSBluetoothAlwaysUsageDescription` | "This app lists nearby Bluetooth devices and flags ones that look like cameras. Nothing is sent anywhere." |
| `NSPhotoLibraryAddUsageDescription` | "Save a snapshot of a suspicious spot to your Photos when you choose to." |
| `UIRequiredDeviceCapabilities` | `camera-flash`、`front-facing-camera`（避免沒有手電筒的裝置買了不能用；**上架後就不能再加**，所以第一版就要放） |
| `ITSAppUsesNonExemptEncryption` | `NO` |
| `TARGETED_DEVICE_FAMILY` | `1`（只做 iPhone） |

- 不需要定位權限。不讀 SSID，因為讀 SSID 必須要定位權限，不值得。
- **PrivacyInfo.xcprivacy**：`NSPrivacyTracking = false`，CollectedDataTypes 留空；Required Reason API 只列實際用到的，例如 UserDefaults `CA92.1`。
- **Entitlements**：v1 **不需要任何特殊 entitlement**，所有探測都是單點傳送 TCP。v1.1 如果想加 SSDP／WS-Discovery 的群播探索，再去 developer.apple.com/contact/request/networking-multicast 申請 `com.apple.developer.networking.multicast`。審核要好幾週，**不要卡住 v1**。

### 4.3 技術基準
- **iOS 26 起**：要用 Liquid Glass 的 `glassEffect`、`GlassEffectContainer` 和 `.buttonStyle(.glass)`。代價是 iPhone XS／XR 跑不了（iOS 26 不支援這兩款）。2026 年 10 月 iOS 26 以上已是主流，而且這兩款的手電筒和前鏡頭也比較舊，付費使用者買了也容易失望，所以取捨合理。
- Swift 6、SwiftUI、Observation、Swift Concurrency。影像處理放在專用的序列佇列（`AVCaptureVideoDataOutput` 的 delegate queue），UI 只吃處理完的結果（`@MainActor`）。
- 工程結構對齊 57_OFFDAY：
  - 用 XcodeGen 的 `project.yml`：`bundleIdPrefix: com.alice51849`、`deploymentTarget.iOS: "26.0"`、`developmentLanguage: en-US`；
  - 模組拆成本地 Swift Package：`LensafeCore`（偵測演算法，純邏輯、可單元測試）、`LensafeCapture`（AVFoundation／手電筒）、`LensafeNetwork`（Bonjour、TCP 探測、BLE）、`LensafeDesignSystem`、`LensafeFeatures`（畫面）；
  - 字串用 String Catalog，搭配工作室既有的 `build_strings.py`／`localize_catalogs.py` 流程；
  - 資料夾結構照 OFFDAY：`App/`、`Packages/`、`Resources/`、`StoreAssets/`、`Docs/`、`Tests/`、`UITests/`、`Tools/`、`SupportSiteRepo/`；
  - 不做 Widget、Watch、App Intents（v1 不需要）。

---

## 5. 逐頁 UX

> 文案先寫 zh-Hant 與 en；其他語言由本機依 String Catalog 生成。結果頁的用詞規則：**永遠不說「安全／沒有攝影機／Safe／No cameras」**，只能說「這次沒看到跡象」加上限制說明。

### 5.1 第一次開啟
直接進入相機，流程照 ★.1。沒有引導頁。

### 5.2 主畫面＝相機（App 的根畫面）
- 全螢幕的後鏡頭預覽，手電筒自動以 3 Hz 脈衝閃爍，偵測標記即時出現（H1）。
- **上方玻璃 HUD**（靠左）：覆蓋率小環加上「已掃描 82%」（H3）。
- **上方玻璃 HUD**（靠右）：手電筒狀態（脈衝／穩定），以及 ⓘ（限制說明）。
- **底部玻璃控制列**（一個 `GlassEffectContainer`，五顆按鈕）：
  - 紅外線
  - 網路（Wi-Fi＋藍牙）
  - **中央大顆的「存證」快門**
  - 清單
  - 報告

  場景（飯店、民宿等）在清單裡選，不放在主畫面。
- 暗房偵測：環境夠暗時，自動浮出前鏡頭 IR 子母畫面（H4），並顯示一行提示「也在看你背後」。
- 沒有分頁列，也沒有首頁選單。所有次要畫面都是 sheet，關掉就回到相機。

### 5.3 查房流程（選用，從「清單」進入）
- 從清單的「完整查房」開始，依序是：相機掃到覆蓋率 ≥ 80% → 網路 → 關燈 IR → 清單 → 報告。
- 每一步都可以跳過，報告上會誠實標成「未檢查」。

### 5.4 反光標記與「確認這一點」（主畫面上的互動）
- 全螢幕預覽。上方是玻璃 HUD：手電筒狀態、閃爍頻率（標準／穩定）、靈敏度（低／中／高）。
- 偵測到的點：細圓環＋柔光，再加一圈呼吸脈衝。確認後的點會加上角括號準星和分數（例如「強」）。
- **點一下標記 → 確認這一點**（H2，6.1A）：
  1. 畫面放大到那一點；
  2. 提示「左右輕移手機」，做視差檢查；
  3. 手電筒自動做 3 次開關；
  4. 給出判斷：「很可能是鏡頭」「比較像一般反光」或「無法判斷，請靠近用眼睛看」。

  判斷可以一鍵存成證據，存進報告。
- 按中央快門可以凍結畫面並存證。證據只存在 App 裡，要不要存進照片由使用者決定。
- 底部提示列會輪播：「慢慢移動」「靠近一點再看」「玻璃、金屬螺絲也會反光，靠近確認」。
- 按「這是什麼？」會跳出半頁說明：判斷鏡頭反光的方法是「換個角度它還在原位、而且是很小的一點」。

### 5.5 紅外線掃描（前鏡頭）
- 進入前會檢查暗度，太亮就顯示「請關燈」。
- 自我測試卡：「拿電視遙控器對著螢幕上方的前鏡頭按任一鍵」。看到閃光 → ✅；10 秒內沒看到 → 顯示「這支手機的前鏡頭看不到遙控器的紅外線，IR 檢查效果有限」，並把狀態設成「不可用」。
- 偵測到光點時，問使用者：「你用眼睛看得到這個光點嗎？」看不到 → 標成「疑似紅外線」；看得到 → 標成「一般指示燈（仍建議靠近看）」。
- 因為用的是前鏡頭，要提醒：「螢幕朝向你，把手機背面朝自己，讓前鏡頭對著房間」。畫面左右鏡像要處理正確。

### 5.6 Wi-Fi 裝置
- 依信心分組：「像攝影機」（RTSP 回應、ONVIF 回應、攝影機品牌標頭）→「需要留意」（攝影機常用的連接埠有開，但沒有標頭）→「其他裝置」。
- 每列顯示：IP、Bonjour 名稱或 HTTP 標題、命中的特徵（膠囊標籤），以及「這代表什麼」。
- 空狀態與限制要分開講：「沒看到」和「看不到」不一樣。偵測到用戶端隔離時（只看得到閘道器），要顯示「這個 Wi-Fi 可能封鎖了裝置互看，這一步的結果參考性低」。
- 被拒絕權限時（NWBrowser 回報 PolicyDenied）→ 引導去設定開啟。

### 5.7 藍牙裝置
- 依 RSSI 排序。像攝影機的置頂並標記。
- 點進去 → 靠近測量：一個大圓環代表訊號強度（平滑過），走近變暖色、走遠變冷色，加上輕觸覺回饋。

### 5.8 摘要與報告
- 四張狀態卡（反光／紅外線／Wi-Fi／藍牙），各自顯示「已檢查｜需要再看 N 處｜未檢查（原因）｜不可用（原因）」，下方再加清單完成度。
- 頂部一句話的範例：「已完成 4 項檢查中的 3 項，有 1 處需要再看」。**不打分數，不說「安全」**。
- 「輸出 PDF」與「發現可疑怎麼辦」兩個按鈕。

### 5.9 發現可疑怎麼辦（依語系顯示當地資訊；**上架前請本機再核對號碼**）
- 共同建議：不要碰也不要拆、先拍照或錄影存證、離開或要求換房、聯絡業者或平台、報警。
- KR：112、디지털성범죄피해자지원센터 02-735-8994、여성긴급전화 1366。
- JP：110、警察相談専用電話 #9110。
- TW：110、113 保護專線。
- US：911（緊急時），其他情況打當地警察的非緊急電話。

### 5.10 設定
語言（App 內切換）、自我測試、靈敏度預設值、關於與限制說明（和 ⓘ 是同一頁）、手電筒模式（脈衝或穩定）、實驗功能（LiDAR，只在支援的機型顯示）、隱私、致謝。**沒有「恢復購買」**，因為沒有內購。

---

## 6. 偵測演算法（給工程師）

### 6.1 鏡頭反光（F1）
**採集**
- 後置廣角鏡頭，1920×1080，30 fps，`420YpCbCr8BiPlanarFullRange`，只用 Y 平面，CbCr 留著算色相分數。
- 曝光：`setExposureModeCustom(duration: 1/500–1/250 s, iso: 接近 minISO)`，讓環境光變暗，只有反光點會飽和。白平衡鎖定。對焦用連續自動對焦。
- 手電筒：`setTorchModeOn(level: 1.0)` 和 `.off` 以 3 Hz 交替（亮 167 ms、暗 167 ms；光敏感限制見 ★.3）。**不要依賴指令時間**，因為手電筒的延遲會變動，要用每一幀的近景平均亮度做兩群分類，判定這幀是「亮」還是「暗」。
- 備用的「穩定模式」：手電筒常亮、不閃爍，只做單幀亮點檢測，給對閃光敏感的人用，設定裡切換。

**每個亮暗配對**
1. 用 vImage 把 Y 縮到 960×540，做 σ≈1 的高斯模糊。
2. 對齊：用 240p 縮圖跑 `VNTranslationalImageRegistrationRequest`，估算暗幀相對亮幀的平移量，再位移暗幀。
3. 差分：`D = max(0, Y_on − Y_off_aligned)`。
4. 候選點要同時符合：
   - `D` 是局部最大值（3×3），而且 `D ≥ T_abs`（預設 60／255，靈敏度高 45、低 80）；
   - `D / (15×15 局部平均 + 4) ≥ R`（預設 4）；
   - 亮幀在該點接近飽和（`Y_on ≥ 235`）；
   - 連通區面積在 1–40 px（540p 尺度），圓度 `4πA/P² ≥ 0.6`。
5. 色相加分：CbCr 偏藍、紫或綠時（鏡頭鍍膜常見）分數 ×1.15。只加分，不當作必要條件。

**時間追蹤與確認**
- 用最近鄰配對，扣掉全域平移，閘門 12 px，在週期之間追蹤候選點。
- 最近 6 個亮暗週期裡命中 ≥ 4 次（3 Hz 下約 2 秒）就算「確認」。在確認之前，先用虛線的「候選」圈顯示（第 2 個週期就會出現），讓畫面一打開就有反應，又不會過早下結論。
- 分數 = 平均 D × 命中率 × 圓度。分數 ≥ 0.7 標「強」，0.4–0.7 標「可能」。
- **排除鏡面反射**：亮面反光通常比較大、呈長條形，而且視角一變它就沿著表面滑動。鏡頭反光則固定在場景裡的同一點，又小又圓。所以要同時滿足「跟著全域平移走」和「面積小」。
- **排除自發光光源**：在暗幀也很亮（`Y_off ≥ 200`）的點是燈或 LED，不是反光。把它另外列成「光源」，交給 IR 流程或使用者判斷，不算反光。
- 新的確認點出現時給 `.sensoryFeedback(.impact(weight: .medium))`。同一個點 3 秒內不重複震動。

**驗收基準（QA）**
- 測試組：手機後鏡頭、筆電視訊鏡頭、USB 針孔攝影機（自備的測試機），分別放在 0.5／1／2／3 m、正對以及偏 15° 與 30°，燈開與燈關。
- 目標：1 m 正對要 100% 確認；2 m 正對 ≥ 80%；30° 可能失敗，但要在說明裡講清楚。
- 誤報要記錄：螺絲頭、玻璃、鏡面、亮面家電。
- iPhone 12 以上全幀率處理每幀 < 20 ms。

### 6.1A 確認這一點（H2、F12）
1. **放大**：
   - 以點選的位置為中心，從原始 1080p（或 4K 格式）裁切出 4 倍的局部畫面，顯示在放大視窗裡；
   - Pro 機型如果有長焦鏡頭，可以改用 `builtInTripleCamera` 虛擬鏡頭的 `ramp(toVideoZoomFactor:withRate:)`，並提示把點移到畫面中央。
2. **視差檢查**（約 2 秒，提示「左右輕移手機」）：
   - 用 Vision 追蹤點周圍 64×64 的特徵，再對照陀螺儀的角度變化，蒐集 ≥ 5° 的視角變化；
   - **鏡頭反光**：在每個視角下都還是 1–40 px 的緊密亮點，圓度 ≥ 0.6，相對周圍特徵的位移 ≤ 3 px；
   - **鏡面反光**：相對周圍特徵的位移 > 3 px，或拉長成條狀（長寬比 > 2.5），或亮度隨角度劇烈變化（變異係數 > 0.6）。
3. **手電筒開關測試**：手電筒以 1 Hz 開關 3 次。開燈時 D 值 ≥ 門檻，關燈時 Y_off < 200，才是「反光」，否則是「光源」。
4. **判斷**：
   - 「很可能是鏡頭」：視差和開關測試都通過，分數 ≥ 0.7；
   - 「比較像一般反光」：視差檢查不通過；
   - 「光源（可能是指示燈）」：關燈時仍然亮；
   - 「無法判斷」：手機晃動太大，或角度變化不夠。

   LiDAR 實驗功能（H5）開啟時，它的結果只能做 ±0.1 的加權，不能單獨決定判斷。
5. 判斷文字一律加上「請靠近用眼睛確認」，不寫「確定是攝影機」。

### 6.2 紅外線（F2、F3）
- 前置廣角（就是 TrueDepth 模組裡的彩色鏡頭）。**TrueDepth 的 IR 相機與點陣投射器不開放原始影像**，不能用。
- 曝光：允許範圍內最長的 duration（約 1/30 s）和接近 maxISO。白平衡鎖在白熾燈增益，讓 IR 呈現偏紫或偏白。
- **暗度門檻**：畫面平均 Y < 25（0–255）而且曝光已頂到上限，才開始掃描；不夠暗就提示關燈。
- 候選點：`Y ≥ 180`、面積 1–60 px（640×480 尺度）、跟周圍的反差 ≥ 6 倍。色度偏紫或接近白色時加分。
- 時間條件：最近 20 幀命中 ≥ 15 幀算「常亮」；或者亮滅有週期性（自相關峰值）算「閃爍」。
- 加上人來判斷：問使用者肉眼看不看得到（見 5.5）。
- **自我測試**：遙控器會發出 38 kHz 調變的脈衝串，在畫面上是短促閃爍的點。偵測到「出現後 1 秒內消失、按鍵時又出現」就算通過。結果依裝置型號（`utsname.machine`）存起來，下次直接沿用，但可以重測。
- 誠實限制：940 nm LED 在多數 iPhone 上很弱；遠距離的小 LED 可能看不到。

### 6.3 Wi-Fi（F5）
1. 用 `getifaddrs` 取得 en0 的 IPv4 和遮罩。網段大於 /24（飯店常見 /16）時，只掃自己所在的 /24，畫面上要說明。
2. **Bonjour**：對 4.2 列出的每個類型各開一個 `NWBrowser`，持續 8 秒，收集名稱並解析位址。
3. **單點 TCP 探測**：對 /24 裡的每個主機（排除自己），同時最多 32 個 `NWConnection`，逾時 400 ms。連接埠：
   - `554`、`8554`（RTSP）
   - `80`、`8080`、`8000`（HTTP，或 Hikvision SDK 的 8000）
   - `37777`（Dahua）
   - `34567`（雄邁／XMEye，便宜攝影機很常見）
   - `6668`（Tuya 本地協定）
   - `8899`、`2020`（部分 ONVIF）
   - `1935`（RTMP）
4. 連得上的埠：
   - **RTSP**：送出 `OPTIONS rtsp://<ip>:<port>/ RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Lensafe/1.0\r\n\r\n`，回應以 `RTSP/1.0` 開頭 → 「串流埠回應」（強）。
   - **HTTP**：`GET / HTTP/1.0`，讀前 4 KB，取 `Server:` 標頭和 `<title>`，跟本機內建的品牌字典比對，例如 hikvision、dahua、uniview、xiongmai、goahead、boa、ipcam、netwave、tuya、v380、yoosee、icsee、ezviz、imou、tapo、wyze、reolink、eufy、foscam、amcrest、xiaomi／mijia、360。命中 → 強。
   - **ONVIF**：對 80、8080、8899、2020 的 `/onvif/device_service` POST SOAP `GetSystemDateAndTime`（這個請求按規範不需要驗證），回應合法 → 強。
5. 分級：
   - 強 = RTSP 或 ONVIF 回應，或是攝影機品牌標頭；
   - 留意 = 攝影機常用埠有開但沒有特徵，或 Bonjour 名稱含 cam、ipc、nvr、dvr；
   - 其他 = 其餘裝置。
6. **用戶端隔離偵測**：/24 裡除了閘道器以外完全沒有回應 → 顯示 5.6 的提示。
7. **紅線**：不做任何驗證嘗試、不抓串流畫面、不猜密碼、不掃 /24 以外的範圍、不做 UDP 洪泛。

### 6.4 藍牙（F6）
- 前景掃描，`allowDuplicates`。記錄 `localName`、`manufacturerData` 的公司代碼、`serviceUUIDs` 和 RSSI。
- 像攝影機的規則（字典放在本機，可以更新）：名稱比對 `(?i)(cam|ipc|spy|hidden|v380|a9|x5|lookcam|yoosee|icsee|tuya|ezviz|dvr|wifi_?cam)`，或屬於常見攝影機模組廠的公司代碼。只能標成「名稱或特徵像攝影機」，**不說「是攝影機」**。
- 靠近測量：RSSI 先做 EMA（α=0.2），再加 1D Kalman（Q=0.05、R=4）。用 −90 到 −40 dBm 對應 0–1 的圓環。每 1 秒最多一次輕觸覺回饋。
- 誠實限制：多數 Wi-Fi 攝影機平常不廣播 BLE。

### 6.5A 掃描覆蓋率（H3、F13）
- 用 `CMMotionManager.deviceMotion`（60 Hz）的 `attitude`，以 `.xArbitraryCorrectedZVertical` 作為參考座標，換算成後鏡頭光軸的方位角和仰角。
- 方位格大小 15° × 15°。範圍是方位 0–360°、仰角 −35° 到 +65°，共 24 × 7 = 168 格。
- 某一格要同時符合下面三點，才算「已掃過」：
  1. 光軸停在該格的時間 ≥ 0.5 秒；
  2. 角速度 < 40°/s；
  3. 那段時間處理過 ≥ 3 個有效的亮暗配對。
- 覆蓋率 = 已掃過的格數 ÷ 168。畫面上顯示四捨五入到整數的百分比（`.contentTransition(.numericText())`）。
- 提示：找出離目前光軸最近的未掃格，在畫面邊緣顯示一個小箭頭（`signal.lens` 色）。
- 使用者走動造成的座標漂移：每次「存證」或停留超過 30 秒時，提示「站在房間中央掃一圈效果最好」。覆蓋率指的是**方向**，不是牆面面積，說明裡要寫清楚。

### 6.5 測試與資料
- 單元測試：分級規則、差分與候選點（用固定的測試影格）、RSSI 濾波、IR 時間條件。
- 儀器測試：在真機錄 10 段測試影片（6.1 的測試組），回放跑演算法，結果放進 CI 前比對。
- 不收集遙測資料，任何偵測結果都不離開手機。

---

## 7. 付費模式與定價（店主決定：US$4.99 付費下載）

### 7.1 決定
- **US$4.99 付費下載，沒有 App 內購買，沒有免費版。上市就是 $4.99，不做早鳥價，也不排漲價。**
- 由本機新 App 管線在 ASC 設定：Pricing and Availability → Price Schedule → Base Country **United States** → **$4.99**。前提是 Paid Apps Agreement 為 Active。
- 主力市場的當地價，以工作室目前同樣是 $4.99 的 App 實際上架價為準（Zipbox、HoursTag 付費版，2026-10-14 的商品頁）：
  | 市場 | 當地價 |
  |---|---|
  | 美國 | US$4.99 |
  | 韓國 | ₩7,700 |
  | 日本 | ¥800 |
  | 台灣 | NT$150 |
- 其他國家由 ASC 以美國為基準**自動換算**（Apple 會依匯率和稅制調整）。除非店主另外指定，否則不手動覆寫。存檔前，在 ASC 的「All Prices」確認 KR、JP、TW 三國是上表的數字。

### 7.2 為什麼 $4.99 站得住（給店主的背景）
- $4.99 是工作室的**組合底價**（57_OFFDAY `15_pricing_study.md`：「US$4.99（組合底價，不可再低）」），所以沒有更低的選項。
- 每筆淨收入約 US$4.24：$4.99 × 85%（小型企業方案）。實際再扣地區 VAT 和退款，估計每筆淨額約 US$3.5。
- 同類真的有人用買斷價在賣：Electronics & Spy Cam Detector 標 $4.99。
- 競品的訂閱價：Peek 每週 $8.99–$9.99、終身 $59.99。**$4.99 還不到競品一週的錢。** 這只是內部依據，**不寫進商店文案**：不跟別家比價，也不寫價格暗示。
- 這個需求有明確的使用時機（出發、入住），付費意願比一般工具高，而且一次查房就值回票價。

### 7.3 付費下載的代價與對策
| 代價 | 證據 | 對策 |
|---|---|---|
| 搜尋排名吃虧：免費 App 下載多，排名就上去 | 我方 Zipbox（$4.99）在 US「unzip」排第 116，前段全是免費 App | 主攻 **KR、JP、TW 這些競爭低的市場**，加上長尾詞（hotel、motel、更衣室、民宿）。US 主要靠外部流量（鉤子片、GEO 頁、Reddit 回答）。 |
| 沒有試用，商品頁轉換率低 | 付費下載的轉換本來就比免費低 | 截圖和預覽影片**完整展示每一步的真實畫面**，第 1 張就講清楚「三種跡象＋清單」。把「它做不到什麼」也放進截圖。 |
| 退款與一星：「找不到東西＝沒用」 | 競品評論的抱怨模式 | 用自我測試證明功能在動；結果頁不說「安全」；第一次掃描就用玻璃膠囊講限制，ⓘ 隨時可以看；說明裡有「沒看到跡象代表什麼」。在 App 內好的時機請求評分（`requestReview`）：**完成自我測試並成功看到光圈後**，而不是查房什麼都沒找到時。 |
| 4.3 飽和類別的審核風險 | 類別裡大量換皮 App | 見第 9 節，審核備註附測試方法。 |

### 7.3A 轉換風險：$4.99 付費下載 vs 免費下載的競品
- 每個市場搜尋第一頁約 10–12 款競品，**全部是免費下載**（付費牆在 App 裡）。使用者在搜尋結果看到「$4.99」和一排「取得」並列，**按下去的比例會明顯偏低**。商品頁到下載的轉換率，預期只有免費 App 的一小部分。工作室自己的付費 App 也有同樣的狀況：Zipbox 在 US「unzip」排第 116，WiFi Aid 付費版在母語搜尋全部缺席。
- 我們不能靠試用說服使用者，**只能靠商品頁讓人付款前就確定買到什麼**：
  1. **第 1 張截圖要讓人 2 秒看懂「一打開就在找」**：真機實拍的相機畫面，畫面上已經有一個琥珀色信心環，字卡寫「一打開，就開始找」。
  2. **第 2 張是「確認這一點」的判斷畫面**：這是跟所有競品最不一樣的地方，直接回應誤報的抱怨。
  3. 第 3–6 張依序是覆蓋率、紅外線、Wi-Fi、報告，全部真機實拍，加上條件字卡（例如「0.5–3 m，慢慢掃」「關燈後」「同一個 Wi-Fi」）。
  4. **第 7 張是「做不到的事」**，避免期待落差帶來退款或一星。App Preview 影片（15–30 秒，各主力語系各一支）用真機錄影，依序是：打開 → 標記出現 → 點一下確認 → 覆蓋率上升 → 關燈 IR → 報告。前 3 秒就要出現標記，因為搜尋結果頁會自動播放。
  5. 宣傳文字講清楚「付一次就全部能用」：沒有訂閱、沒有內購、不用帳號。這是免費競品給不了的承諾，也剛好回應評論裡最多的抱怨。
- 成效追蹤：上架 2 週後，看 ASC 的商品頁轉換率。若 KR、JP、TW 明顯低於 US，優先換第 1 張截圖和影片封面，不動價格（價格由店主決定）。

### 7.4 付費的人付款前就要知道的事（截圖與文案的原則）
付 $4.99 的人在按「購買」之前，要能從商品頁確認以下幾件事：
1. **確切檢查哪三種跡象**，以及各自的條件（反光：1–3 m、要慢慢掃；IR：要關燈、看前鏡頭能力；Wi-Fi：只看得到同一個網路）。
2. **有一份依場景分的清單**。
3. **做不到的事**：有一張截圖專門講。
4. **付一次就全部能用**：沒有訂閱、沒有內購、不用帳號。
5. **只支援有手電筒的 iPhone、iOS 26 以上**。

---

## 8. 隱私
- 所有影像都在記憶體裡處理，除非使用者按「存證」，否則不存檔。存證圖只放在 App 容器裡，要不要匯出由使用者決定。
- 網路活動只有同一個區網裡的探測，**沒有任何對外連線**。沒有分析 SDK，沒有當機回報 SDK（需要時用 Apple 內建的、使用者同意分享的那種）。
- App Privacy 標籤：**Data Not Collected**。
- 不要定位。地點名稱由使用者自己輸入。
- 隱私政策頁沿用工作室既有的 GEO 和支援站路由（`/<lang>/lensafe.html` 加上隱私頁）。

---

## 9. App Review 風險與對策
| 規範 | 風險 | 對策 |
|---|---|---|
| 2.3.1／2.3.7 中繼資料要準確 | 「偵測所有攝影機」「100%」「抓竊聽器」 | 文案只寫「檢查三種常見跡象」，清楚寫出限制，不提磁場、不提麥克風。關鍵字不放競品名稱（例如 glint、peek）和商標（例如 Airbnb）。 |
| 4.3(a)／4.3(b) | 類別飽和，加上我方帳號已有 57 款 App | **見 9A「4.3 防線」**（這是最大的風險）。 |
| 2.1 功能完整 | 審核人員在亮的辦公室裡測，什麼都沒看到 | 審核備註要寫：「請在 1 公尺外，讓反光掃描對準另一支 iPhone 的後鏡頭；IR 模式請關燈後用任一遙控器測試。」也可以附上錄好的示範影片連結。 |
| 5.1.1 權限 | 用途說明寫得太含糊 | 照 4.2 的寫法具體說明。相機授權在第一次開啟時直接請求，用途說明只有一句話（★.1）。本地網路和藍牙要等使用者第一次點「網路」時才請求，請求前先顯示一句說明。 |
| 5.2.1 第三方商標 | 中繼資料出現 Airbnb | 只在 App 內清單的場景名稱用一般說法「短租／民宿」，中繼資料裡完全不出現。 |
| 1.1／形象 | 被誤認為偷拍工具 | 文案只寫保護方的用途。JP 的「隠しカメラ」搜尋結果裡混了無音カメラ這類工具，我們的副標要明確寫「探知、確認」。 |
| 年齡分級 | 競品多選 18+ | 照實填問卷：沒有成人內容，預期是 4+。清單裡出現「廁所」「更衣室」只是場景名稱，不構成成人內容。 |

審核備註的完整文字放在 9A.4。

---

## 9A. 4.3 防線（被當成垃圾 App 退件的風險）

### 9A.1 風險有多大
- **4.3(b) 飽和類別**：協調者實測，每個市場的搜尋第一頁都有約 10–12 款專門的競品，查詢詞包括 US「hidden camera detector」、KR「몰카 탐지」、JP「盗撮 カメラ 発見」、TW「針孔 偵測」。其中很多是換皮作品（NSpy、Vulk、Spy Scanner、Glint…），我的實測也看到同一批開發者在各國重複上架。準則原文的意思是：已經飽和的類別不要再擠進去，除非能提供獨特、高品質的體驗。
- **4.3(a) 同一開發者大量相似 App**：我方帳號已經有 57 款 App，其中有 Lite／Pro 成對的組合。審核人員看帳號時，標準會更嚴。
- 對策的原則是：**一款 App、一個 Bundle ID，不做 Lite 版**（付費下載本來就是單一版本）。差異必須是**看得到、測得到的真功能**，不能靠文案。

### 9A.2 二進位檔裡一定要有的差異（驗收時逐項實測）
| # | 必須存在 | 驗收方式 |
|---|---|---|
| D1 | **手電筒閃爍的影像差分反光偵測**：**打開 App 就自動開始**，手電筒真的以 3 Hz 交替亮暗，逐幀做差分，追蹤確認後在即時畫面上標記，標記會跟著鏡頭移動黏在原位（6.1） | 1 m 外對準另一支手機的鏡頭：標記出現、穩定、跟著畫面移動。用手遮住手電筒：標記消失。 |
| D2 | **IR 模式**：前鏡頭、暗度門檻、遙控器自我測試，能分辨常亮和閃爍（6.2） | 在暗房按電視遙控器：自我測試通過，畫面顯示「閃爍」。拿一顆常亮的 IR LED（或夜視攝影機）：顯示「常亮」。 |
| D3 | **真的去探索區域網路**：Bonjour 加上單點 TCP 探測，用白話說明結果（「這台裝置有回應影像串流的請求，攝影機常這樣」），進度數字等於真實已探測的位址數（6.3） | 家用網路放一台測試攝影機：出現在「像攝影機」，並寫出命中的特徵。拔掉網路：進度停止，並顯示原因。 |
| D5 | **確認這一點**：放大、視差檢查、手電筒開關測試，最後給出判斷（6.1A） | 對手機鏡頭：判斷「很可能是鏡頭」。對亮面螺絲或玻璃：判斷「比較像一般反光」。 |
| D6 | **掃描覆蓋率**：依陀螺儀方位格累計，並提示未掃區域（6.5A） | 原地轉一圈，數字會穩定上升；手機沒在動時，數字不會變。 |
| D4 | **查房流程與每次住宿的報告**：依場景分的清單、可以跳過、每一趟的報告存在手機裡、可輸出 PDF（5.3、5.8） | 完成一趟查房 → 關掉 App 再開 → 報告還在 → 輸出的 PDF 內容和畫面一致。 |

**禁止出現**：
- 假的雷達掃描動畫；
- 用磁力計做「偵測」；
- 和真實工作量無關的假進度條或「掃描中」動畫；
- 沒有實際訊號就產生的結果；
- 隨機或裝飾用的「威脅指數」；
- 宣稱「AI 找出所有攝影機」。

所有「掃描中」的畫面，都要對應真實的工作量：已處理幾幀、已探測幾個位址、已收到幾個廣播、已掃過幾個方位格。

### 9A.3 誠實的文案
- 只寫「檢查三種常見跡象」。
- 限制要寫在商品頁、第一次掃描的提示膠囊（ⓘ 也找得到）和結果頁三個地方。
- 不寫 100% 或保證，不寫竊聽器或磁場。
- 名稱裡有 safe，但結果頁永遠不寫「安全」。

### 9A.4 審核備註（en，貼到 App Review Information → Notes）
> Lensafe helps travelers check a room for three common signs of a hidden camera. Each method uses real sensor data on the device. Nothing is simulated, and nothing leaves the iPhone.
>
> 1) Lens reflections run automatically when the app opens. The flashlight pulses 3 times per second (kept at or below the 3-flashes-per-second photosensitivity guideline; a steady mode is in Settings) while the rear camera compares lit and unlit frames. Small points that light up only when the flashlight is on, and stay fixed in the scene, are tracked and marked with a confidence ring. How to test: open the app and point it at another phone's rear camera, or a laptop webcam, about 1 m away. A marker locks onto the lens. Tap the marker to run "Confirm this spot": the view zooms in, asks you to move the phone slightly left and right (a true lens glint stays a fixed point; shiny surfaces shift or smear), toggles the flashlight 3 times, and then shows a verdict. A glossy screw or glass gives "looks like an ordinary reflection".
>
> 2) Room sweep coverage. The top-left ring shows the share of directions already swept, based on the gyroscope (Core Motion, no permission needed). Turning around in place increases it.
>
> 3) Infrared lights (Infrared button in the bottom bar). Many night-vision cameras use infrared LEDs that the eye cannot see. The front camera picks up some infrared in a dark room. On devices that support multi-camera capture, a small front-camera picture-in-picture appears automatically in the dark. How to test: turn the lights off, open Infrared → Self-test, and press any TV remote button toward the front camera. The blinking remote LED is detected and labeled "blinking". If a particular iPhone's front camera cannot see infrared, the app says so and marks this check as unavailable instead of pretending.
>
> 4) Camera-like devices (Network button). On the Wi-Fi the iPhone is connected to, the app lists devices through Bonjour and asks each address on the local /24 whether it answers on common camera ports (RTSP OPTIONS, an unauthenticated ONVIF GetSystemDateAndTime, HTTP server banners). Results are explained in plain language. It never logs in, never views a stream and never guesses passwords. Nearby Bluetooth LE advertisements with camera-like names are flagged. How to test: on a network with any IP camera, smart TV or printer, the device list fills, and a camera shows under "Looks like a camera".
>
> 5) Checklist and stay report (List and Report buttons). Checklists for each place type (hotel, rental, changing room, restroom, gym), plus a saved report for each stay, with evidence photos and timestamps, that can be exported as a PDF.
>
> The app explains its limits (no app can find every camera) and never labels a room "safe". There is no magnetometer "detector" and no simulated scanning; progress numbers reflect real frames, addresses and directions processed. Paid app: no account, no in-app purchases, no data collection.

### 9A.5 portfolio-distinctness 契約（`StoreAssets/contracts/portfolio-distinctness.json`，phase=concept）草稿
本機要跑：`portfolio_spam_gate.py --app ~/58_Lensafe --phase concept`、`requirements_gate.py --app ~/58_Lensafe`。`portfolioComparisons` 要照 57_OFFDAY 的做法列出**全部 57 款**，下面只先寫最接近的幾款。上架前另外要跑 `--phase release`：原始碼相似度對每一款都要 ≤ 0.35。

```json
{
  "schemaVersion": "portfolio.distinctness/v1",
  "appFolder": "58_Lensafe",
  "phase": "concept",
  "workingName": "Lensafe (display name locked by Caitlyn 2026-10-14)",
  "targetUser": "Solo and business travelers, short-term-rental guests, gym and changing-room users, and renters in Korea, Japan, Taiwan, the US and travel markets who worry about hidden cameras in rooms they do not control.",
  "triggerSituation": "Right after checking in to a hotel, motel, rental or guesthouse, or before using an unfamiliar changing room or restroom, when the user wants to look around properly before unpacking or undressing.",
  "jobToBeDone": "Check a room in a few minutes for the three common signs a phone can actually observe (lens reflections, infrared night-vision lights, camera-like devices on the same Wi-Fi or nearby Bluetooth) and walk the usual hiding spots, then keep a record.",
  "primaryOutcome": "A saved per-stay report listing which checks ran, each spot that needs a closer look with a snapshot, which checks were unavailable and why, plus checklist progress, exportable as a PDF. It never says 'safe'.",
  "firstRunFlow": "No onboarding: the app opens straight into the live rear camera, asks for camera access with a single sentence, and starts the flashlight pulse; glint markers appear automatically while the user sweeps. A one-time glass hint states what a phone can and cannot check (dismisses after 6 s, reopenable from the info button).",
  "homeInformationArchitecture": "The root is the live camera with a top glass HUD (sweep-coverage ring with percentage, flashlight mode, info) and a bottom glass control bar: Infrared, Network (Wi-Fi + Bluetooth), central evidence shutter, List (place-type checklists and the optional full room check), Report (saved stays). No tab bar; secondary screens are sheets.",
  "onboardingPromise": "Before you unpack, check for three common signs of a hidden camera, and know exactly what a phone can and cannot find.",
  "dataModel": "Stay (name typed by the user, date, place type) -> CheckResult per method (status: checked, needsReview(n), skipped, unavailable(reason)) -> Finding (method, score, snapshot file, user note) and ChecklistItem state; DeviceCapability (IR self-test result per device model). Stored on device only.",
  "iconMetaphor": "A glassy round lens on a deep aurora gradient, with one small four-point glint at the upper right. No eye, no radar, no camera body.",
  "storeNarrative": "Open it and it is already looking: the flashlight pulses, possible lenses get a ring, tap one to confirm it from two angles, and a coverage ring tells you when the whole room is swept. Lights off for infrared, the Wi-Fi asked who answers like a camera, and a report for the stay. Pay once, nothing uploaded.",
  "exclusiveCapabilities": [
    {
      "id": "torch-flicker-glint-differencing",
      "userOutcome": "Live markers stay locked on small retroreflective points that only light up with the flashlight, so the user can walk closer and inspect them.",
      "entryRoute": "Automatic on launch (live camera is the root screen)",
      "acceptanceTest": "Phone lens at 1 m head-on is confirmed within 2 s in 10/10 recorded test clips; covering the torch removes the marker; a glossy screw-head set produces under 1 false confirmation per clip on average."
    },
    {
      "id": "confirm-spot-parallax-torch-verdict",
      "userOutcome": "Tapping a marker zooms in, checks parallax as the phone moves slightly and toggles the flashlight, then gives a verdict (likely a lens / ordinary reflection / light source / cannot tell), which cuts the false positives users complain about in this category.",
      "entryRoute": "Live camera > tap any marker",
      "acceptanceTest": "In recorded test clips, a phone lens at 1 m yields 'likely a lens' in at least 9 of 10 runs; glossy screw heads and glass yield 'ordinary reflection' or 'cannot tell' in at least 8 of 10 runs; standby LEDs yield 'light source'."
    },
    {
      "id": "gyro-sweep-coverage",
      "userOutcome": "A live percentage of room directions already swept, with an arrow to the nearest unswept direction, so the user knows when the sweep is complete.",
      "entryRoute": "Live camera > top-left coverage ring",
      "acceptanceTest": "A full slow 360-degree turn at three heights reaches at least 90%; holding the phone still does not increase it; directions are counted only after 0.5 s of dwell with valid frames processed."
    },
    {
      "id": "front-camera-ir-with-remote-self-test-and-blink",
      "userOutcome": "The user learns whether this iPhone can see infrared (TV-remote self-test), then sees invisible IR lights classified as steady or blinking.",
      "entryRoute": "Bottom glass bar > Infrared > Self-test; automatic front-camera picture-in-picture in the dark on multicam devices",
      "acceptanceTest": "A TV remote passes the self-test on at least 3 device models; a steady 850 nm LED reads 'steady' and the remote reads 'blinking'; with room light above the darkness gate, scanning does not start."
    },
    {
      "id": "lan-camera-protocol-probe-plain-language",
      "userOutcome": "Devices on the same Wi-Fi that answer like a camera (RTSP, ONVIF, vendor banner, camera ports) are listed with a plain-language reason; client isolation is detected and explained.",
      "entryRoute": "Bottom glass bar > Network",
      "acceptanceTest": "A test IP camera on a home /24 shows as 'Looks like a camera' with its RTSP or ONVIF reason; an isolated guest network shows the isolation notice; no authentication attempt appears in a packet capture."
    },
    {
      "id": "guided-stay-check-with-saved-report",
      "userOutcome": "A step-by-step check per place type ends in a saved report for each stay, exportable as a PDF, that honestly marks skipped or unavailable checks.",
      "entryRoute": "Bottom glass bar > List > Full room check, or Report > Export PDF",
      "acceptanceTest": "Complete a check, relaunch the app, and the report persists; the PDF matches the on-screen statuses; skipped steps read 'Not checked'."
    }
  ],
  "portfolioComparisons": [
    {
      "appFolder": "27_WiFiAid",
      "samePrimaryConcept": false,
      "sameCoreLoop": false,
      "overlap": "Both look at the Wi-Fi the phone is on.",
      "distinctOutcome": "WiFi Aid diagnoses why the connection or internet is not working; Lensafe lists local devices that answer like cameras and records findings for a stay.",
      "distinctWorkflow": "WiFi Aid runs connectivity diagnostics and fixes; Lensafe probes camera protocols on the local /24 as one step of a room check alongside camera-based methods."
    },
    {
      "appFolder": "37_WiFiAidLite",
      "samePrimaryConcept": false,
      "sameCoreLoop": false,
      "overlap": "Same network-context overlap as WiFi Aid.",
      "distinctOutcome": "Connectivity troubleshooting versus a hidden-camera room-check report.",
      "distinctWorkflow": "No camera, torch, infrared or checklist steps in WiFi Aid Lite."
    },
    {
      "appFolder": "47_dBHalo",
      "samePrimaryConcept": false,
      "sameCoreLoop": false,
      "overlap": "Both turn a phone sensor into a live meter-like view.",
      "distinctOutcome": "dBHalo measures sound level; Lensafe marks lens glints and infrared lights in the camera view.",
      "distinctWorkflow": "A microphone meter versus torch-flicker frame differencing and front-camera IR scanning."
    },
    {
      "appFolder": "24_TripBeePro",
      "samePrimaryConcept": false,
      "sameCoreLoop": false,
      "overlap": "Same travel moment and audience.",
      "distinctOutcome": "A trip itinerary versus a room-check report.",
      "distinctWorkflow": "TripBee plans days; Lensafe scans a room on arrival."
    },
    {
      "appFolder": "11_ScanToPro",
      "samePrimaryConcept": false,
      "sameCoreLoop": false,
      "overlap": "Both use the rear camera as the main input.",
      "distinctOutcome": "Scanned documents versus marked lens glints.",
      "distinctWorkflow": "Document capture and edge detection versus torch-synchronized differencing with temporal tracking."
    }
  ],
  "marketComparisons": [
    {
      "appStoreId": 1571925628,
      "name": "Hidden Camera Detector - Peek",
      "storefront": "United States App Store",
      "overlap": "Same job; magnetic-field and network scanning; free download with weekly or lifetime IAP.",
      "distinctOutcome": "Lensafe has no magnetometer detector, a torch-flicker glint detector, an IR self-test and a per-stay report; paid once with no IAP.",
      "checkedAt": "2026-10-14"
    },
    {
      "appStoreId": 1560989782,
      "name": "Hidden Spy Camera Finder Pro",
      "storefront": "United States App Store",
      "overlap": "Same job, subscription.",
      "distinctOutcome": "Honest limits, real protocol probing explained in plain language, guided stay report.",
      "checkedAt": "2026-10-14"
    },
    {
      "appStoreId": 6450695466,
      "name": "Cam Detector App: Home Security",
      "storefront": "United States App Store",
      "overlap": "Same job, subscription.",
      "distinctOutcome": "As above.",
      "checkedAt": "2026-10-14"
    },
    {
      "appStoreId": 1665597557,
      "name": "#1 Hidden Camera Detector",
      "storefront": "Japan App Store",
      "overlap": "Same job; relies on the magnetic sensor and claims microphone detection.",
      "distinctOutcome": "Lensafe makes no magnetometer or microphone claims.",
      "checkedAt": "2026-10-14"
    },
    {
      "appStoreId": 1605066265,
      "name": "針孔攝像頭探測器-檢測隱藏攝像頭",
      "storefront": "Taiwan App Store",
      "overlap": "Same job; Wi-Fi, Bluetooth and IR; weekly, yearly or lifetime subscription.",
      "distinctOutcome": "Taiwan-native wording, torch-flicker glint detection, IR self-test, paid once.",
      "checkedAt": "2026-10-14"
    },
    {
      "appStoreId": 6654924497,
      "name": "Glint: Detect Hidden Camera / Camera Detector & AI Finder",
      "storefront": "United States App Store",
      "overlap": "Lens-reflection approach.",
      "distinctOutcome": "Torch-synchronized differencing plus temporal confirmation, combined with IR, network and checklist in one guided flow.",
      "checkedAt": "2026-10-14"
    }
  ],
  "attestations": {
    "notNameColorMetadataOnly": true,
    "notFeatureRemovalOnly": true,
    "notTemplateRepackage": true,
    "notSaturatedClone": true
  }
}
```

---

## 10. ASO 去重與勝率

### 10.1 規則（每個語系都照做）
- Apple 會把**標題、副標、關鍵字欄位合起來建索引**。所以同一個字只出現一次，不放複數或重複的字。關鍵字欄不放 App 名稱和類別字（例如 app、utility）。用逗號分隔、不加空格。長度上限：關鍵字 ≤ 100 字元、標題 ≤ 30、副標 ≤ 30。
- 不放競品名稱或商標，例如 Peek、Glint、Airbnb。
- 不放我們做不到的字：bug、竊聽器、盗聴器、도청、磁場、magnetic。**付費 App 被錯誤期待吸引進來的使用者，只會變成一星評論**。
- **CJK 例外（每個語系最多一個，已標註）**：韓文和日文的連寫複合詞（例如「몰카탐지기」）跟分寫版本在 Apple 的斷詞裡可能是不同的字串，而搜尋提示的第 1 名就是連寫版本，所以韓文的關鍵字欄保留一次連寫，作為例外。

### 10.2 需求證據（App Store 搜尋提示，2026-10-14 實測，各國店面）
| 語系 | 有提示的詞（需求證據） | 沒有提示的詞（需求低） |
|---|---|---|
| en-US | hidden camera detector (free)、hidden camera finder、hidden camera scanner app、spy camera detector／finder／scanner、spy cam finder、find hidden cameras、infrared camera detector、hotel camera（只有它自己） | airbnb camera、pinhole camera |
| ko | 몰카탐지기、몰카탐지기 무료、몰카어플、몰카감지기、몰카 찾기、몰래카메라 탐지기、숨겨진 카메라 탐지기、카메라 탐지기、히든카메라、불법촬영 | 숙소 몰카 |
| ja | 盗撮カメラ、盗撮カメラ探知機、盗撮カメラ発見器、盗撮カメラ発見、盗撮発見、隠しカメラ探知機（無料）、隠しカメラ発見、隠しカメラ探査機 | 盗撮 発見（分寫）、隠しカメラ 発見（分寫）、ホテル カメラ、カメラ 探知 |
| zh-Hant | 針孔攝像頭探測器、針孔探測器、針孔偵測、針孔攝影機（探測器）、針孔掃描、偷拍偵測、隱藏攝影機（偵測器／掃描器／檢查） | 密錄器、監視器偵測 |

其他公開訊號：在 Google 上，韓文「몰카 탐지 앱 아이폰 추천」、日文「盗撮カメラ 発見 アプリ」、中文「針孔攝影機 偵測 App iPhone 推薦」都有大量推薦文和新聞（ETtoday 2026-05 測試 iPhone 放大鏡的紅色濾鏡）。這些代表有持續的資訊需求，也都可以接上 GEO 頁。

### 10.3 誰已經佔住哪些詞（標題裡的字）
- **US**：「Hidden Camera Detector」幾乎每一款都有，前段都是破萬評分的 App；「Spy Camera Detector」「Hidden Camera Finder」也被佔了。**還沒被佔的是場景詞**（hotel rooms）和「check」的說法。
- **KR**：「몰카탐지기」「몰래카메라 탐지기」「숨겨진 카메라 탐지기」都被佔了，但持有的 App 評分數只有 0–228 則 → **主詞也打得下來**。「숙소（住宿）」「점검（檢查）」沒有人用。
- **JP**：「隠しカメラ探知機」「盗撮カメラ発見」有人佔，但評分數只有 1–392 則。「ホテル・民泊」只有一款（隠しカメラ探知＆スキャナー，63 則）用在副標。
- **TW**：「針孔攝像頭探測器」被簡體或港式用語的 App 佔滿，**台灣用語「針孔偵測」「防偷拍」「飯店民宿」幾乎空著**（只有一款用了「飯店民宿防偷拍查房神器」）。

### 10.4 最終定案（字數已驗證）
標題一律用「`Lensafe: ` + 描述」的格式。括號裡是總字數。

| 語系 | 標題（≤30） | 副標（≤30） | 關鍵字（≤100，逗號不加空格） |
|---|---|---|---|
| en-US | `Lensafe: Hidden Camera Check`（28） | `Spy Cam Finder for Hotel Rooms`（30） | `detector,scanner,find,pinhole,infrared,ir,lens,nanny,rental,motel,travel,bathroom,dressing,wifi,gym`（99） |
| ko | `Lensafe: 몰카 탐지기·숙소 점검`（22） | `몰래카메라 렌즈 반사·적외선 확인`（18） | `몰카탐지기,히든카메라,숨겨진,숨은,카메라,불법촬영,모텔,호텔,펜션,원룸,화장실,탈의실,여행,스캐너,감지,와이파이,블루투스,핀홀,안심`（73；「몰카탐지기」是 CJK 例外） |
| ja | `Lensafe: 盗撮カメラ発見・探知`（20） | `ホテル・民泊の隠しレンズを確認`（15） | `発見器,検出,スパイ,赤外線,反射,旅館,ビジホ,トイレ,更衣室,防犯,監視,出張,一人旅,女性,安心,ピンホール,ir,wifi,bluetooth`（75） |
| zh-Hant | `Lensafe: 針孔偵測・防偷拍`（18） | `飯店民宿更衣室 鏡頭反光與紅外線檢查`（18） | `攝影機,攝像頭,探測器,隱藏,密錄器,監視器,偷窺,查房,廁所,旅館,摩鐵,租屋,套房,藍牙,wifi,掃描,隱私,出差,自由行,安心`（67） |

**另一種寫法**：如果店主偏好 `Lensafe: Hidden Camera Finder`（29），副標就改成 `Spy Cam Check for Hotel Rooms`（29），讓 finder 和 check 對調。這樣「不重複」的規則不受影響。

**品牌名與去重**：Apple 很可能把「Lensafe」當成一個完整的字，不會拆成 lens 和 safe，所以關鍵字欄保留 `lens`。如果日後 ASO 探針發現「lens」可以靠品牌名命中，就把 `lens` 換成候補詞 `safety`；韓文的候補是 `캠`，日文是 `ネカフェ`，中文是 `汽旅`。

**組合能命中的查詢（舉例）**
- en：hidden camera detector（標題 hidden camera ＋ 關鍵字 detector）、hidden camera finder（＋副標 finder）、hidden camera scanner、spy camera detector、spy cam finder、find hidden cameras、infrared camera detector、hotel camera、nanny cam detector、motel／bathroom／dressing room hidden camera。
- ko：몰카 탐지기、몰카탐지기、몰래카메라 탐지기（副標＋標題）、숨겨진 카메라 탐지기、카메라 탐지기、히든카메라、모텔 몰카、숙소 몰카 점검。
- ja：盗撮カメラ発見、盗撮カメラ探知（機）、盗撮カメラ発見器、隠しカメラ探知・発見（隠し在副標，カメラ在標題）、ホテル 盗撮、民泊 隠しカメラ、トイレ 盗撮 発見。
- zh-Hant：針孔偵測、針孔攝影機探測器、針孔攝像頭探測器、偷拍偵測（標題的「偷拍」＋「偵測」）、隱藏攝影機、飯店／民宿 針孔、更衣室 偷拍、摩鐵 針孔。

### 10.5 為什麼這組贏得了
- **KR、JP、TW**：主詞的持有者評分少，用道地的在地用語（台灣用語、韓文「숙소 점검」、日文「ホテル・民泊」）加上場景詞，我們有機會排進主詞前段，同時拿下長尾。
- **US**：不跟破萬評分的 App 正面搶「hidden camera detector」第 1 名，而是用場景（hotel rooms、motel、bathroom、dressing、gym、nanny）加上「check」的說法拿長尾。主詞的曝光交給外部流量和評分慢慢累積。
- **每個欄位各講一件事，不重複**：標題講「是什麼」，副標講「在哪裡用或怎麼查」，關鍵字補足同義詞和場景，宣傳文字講「$4.99 買到什麼」，描述講「每種檢查怎麼運作、限制在哪」，截圖講「一步一步的真實畫面」。

---

## 11. 商店文案（各語言）

> 原則：用場景帶出需求，具體、誠實，同一個宣稱不在不同欄位重複出現。價格由商店顯示，文案不寫數字。
> 欄位分工：宣傳文字講「付一次拿到什麼」；描述講「每種檢查怎麼運作、限制在哪」；截圖講「一步一步的真實畫面」。
> 韓文「Lensafe는」：Lensafe 唸作 렌세이프，結尾是母音，所以助詞用 는。

### 11.1 en-US
**Promotional Text（≤170）**
> One purchase unlocks everything: live lens detection, spot confirmation, infrared, Wi-Fi and Bluetooth checks, checklists and stay reports. No subscription, no account.

**Description**
> You just checked in. Before you unpack, open Lensafe and sweep the room.
>
> It starts looking the moment it opens. The flashlight pulses while the rear camera watches for tiny points that light up and stay put — the way a camera lens bounces light back. Possible lenses get a ring right on the screen.
>
> CONFIRM A SPOT
> Tap a ring. Lensafe zooms in, asks you to move the phone slightly, and blinks the flashlight. A real lens glint stays a single fixed point; a shiny screw or glass shifts and smears. You get a plain verdict: likely a lens, an ordinary reflection, or a light source.
>
> KNOW WHEN THE ROOM IS COVERED
> A coverage ring counts the directions you have swept and points to the ones you missed.
>
> INFRARED IN THE DARK
> Many night-vision cameras use infrared LEDs you can't see. Turn the lights off and the front camera can pick some of them up. On supported iPhones, a small front-camera view opens automatically and watches the direction behind you. A TV-remote self-test shows whether your iPhone can see infrared at all.
>
> SAME WI-FI, NEARBY BLUETOOTH
> Lensafe lists devices on your Wi-Fi that answer like a camera (video stream ports, ONVIF, vendor banners) and nearby Bluetooth devices with camera-like names. It never logs in to anything.
>
> CHECKLISTS AND STAY REPORTS
> Hotel rooms, rentals, changing rooms, restrooms and gyms each get a list of usual hiding spots. Save evidence photos with time and place into a report for each stay, and export it as a PDF to send to a host, hotel or the police.
>
> WHAT IT CAN'T DO
> No app can find every camera. A camera with no infrared, no network, and a lens angled away from you may not show up. Hotel Wi-Fi often hides devices from each other. No signs found doesn't mean there is no camera, so use the checklist with your own eyes too.
>
> Works offline. No account, no tracking, no ads. 50 languages. The flashlight pulses up to 3 times per second; a steady mode is in Settings. Requires an iPhone with a flashlight.

**截圖字卡（7 張，一張講一件事；第 1 張決定點不點）**
1. Open it. It's already looking.
2. Tap a ring: lens, or just a reflection?
3. 82% swept — it shows what you missed
4. Lights off: see infrared, even behind you
5. Who on this Wi-Fi answers like a camera
6. A report for every stay, ready as a PDF
7. What a phone can't find — said up front

### 11.2 ko
**프로모션 텍스트**
> 한 번 구매로 실시간 렌즈 탐지, 지점 확인, 적외선·와이파이·블루투스 점검, 체크리스트와 숙소 기록까지 모두 사용합니다. 구독·계정 없음.

**설명**
> 체크인 직후, 짐 풀기 전에 Lensafe를 켜고 방을 천천히 비춰 보세요.
>
> 켜는 순간 바로 찾기 시작합니다. 플래시가 깜빡이는 동안 후면 카메라가 제자리에 머무는 작은 반사점, 즉 카메라 렌즈가 빛을 되돌려 보내는 모습을 찾고, 렌즈일 수 있는 곳에 화면에서 바로 원을 표시합니다.
>
> 지점 확인: 원을 탭하면 확대한 뒤 휴대폰을 살짝 움직이게 하고 플래시를 깜빡입니다. 진짜 렌즈 반사는 한 점에 그대로 남고, 반짝이는 나사나 유리는 위치가 바뀌거나 번집니다. 결과는 '렌즈 가능성 높음', '일반 반사', '광원' 중 하나로 알려 드립니다.
> 점검 범위: 이미 비춘 방향을 세어 '82% 점검' 처럼 보여 주고, 놓친 방향을 화살표로 알려 줍니다.
> 적외선: 야간 촬영용 적외선 LED는 눈에 보이지 않습니다. 불을 끄면 전면 카메라로 일부를 확인할 수 있고, 지원 기기에서는 등 뒤 방향을 비추는 작은 전면 카메라 화면이 자동으로 열립니다. TV 리모컨 자가 테스트로 내 아이폰에서 가능한지 먼저 확인합니다.
> 와이파이·블루투스: 연결된 와이파이에서 카메라처럼 응답하는 기기와, 이름이 카메라 같은 주변 블루투스 기기를 표시합니다. 어떤 기기에도 로그인하지 않습니다.
> 체크리스트와 숙소 기록: 호텔, 모텔, 펜션, 탈의실, 화장실별 점검 위치를 안내하고, 시간·장소가 담긴 증거 사진을 숙소별 기록으로 저장해 PDF로 보낼 수 있습니다.
>
> 할 수 없는 것: 모든 카메라를 찾을 수 있는 앱은 없습니다. 적외선·네트워크가 없고 렌즈 각도가 맞지 않으면 보이지 않을 수 있습니다. 숙소 와이파이는 기기끼리 서로 못 보게 막혀 있는 경우가 많습니다. 흔적이 없다고 확실히 없다는 뜻은 아니니, 체크리스트로 직접 함께 확인하세요.
>
> 오프라인 작동. 계정·추적·광고 없음. 50개 언어. 플래시는 초당 최대 3회 깜빡이며, 설정에서 고정 모드를 선택할 수 있습니다. 플래시가 있는 아이폰이 필요합니다.

**스크린샷 문구**
1. 켜자마자 찾기 시작합니다
2. 원을 탭: 렌즈일까, 그냥 반사일까?
3. 82% 점검 — 놓친 방향까지 알려 줘요
4. 불 끄면 적외선, 등 뒤까지
5. 같은 와이파이에서 카메라처럼 응답하는 기기
6. 숙소마다 남는 기록, PDF로 바로
7. 휴대폰이 못 찾는 경우도 먼저 알려 드립니다

### 11.3 ja
**プロモーションテキスト**
> 一度の購入で、リアルタイムのレンズ検出、地点の確認、赤外線・Wi-Fi・Bluetoothのチェック、チェックリスト、宿泊ごとの記録まですべて使えます。サブスク・アカウント不要。

**説明**
> チェックインしたら、荷ほどきの前に Lensafe を開いて部屋をゆっくり照らしましょう。
>
> 開いた瞬間から探し始めます。ライトを点滅させながら、背面カメラが動かない小さな反射点、つまりカメラのレンズが光を返す様子を探し、レンズの可能性がある場所に画面上でリングを表示します。
>
> 地点の確認：リングをタップすると拡大し、iPhoneを少し動かすよう案内してライトを点滅させます。本物のレンズの反射は一点に留まり、光るネジやガラスは位置がずれたりにじんだりします。結果は「レンズの可能性が高い」「普通の反射」「光源」のいずれかで表示します。
> 確認範囲：照らした方向を数えて「82%確認済み」のように表示し、見落とした方向を矢印で示します。
> 赤外線：暗視用の赤外線LEDは目には見えません。消灯すると前面カメラで一部を確認でき、対応機種では背後の方向を映す小さな前面カメラ画面が自動で開きます。テレビのリモコンを使ったセルフテストで、お使いのiPhoneで使えるかを先に確かめられます。
> Wi-Fi・Bluetooth：接続中のWi-Fiでカメラのように応答する機器と、カメラらしい名前の近くのBluetooth機器を表示します。どの機器にもログインしません。
> チェックリストと宿泊記録：ホテル、ビジネスホテル、民泊、更衣室、トイレごとに確認ポイントを案内し、日時と場所入りの証拠写真を宿泊ごとの記録として保存、PDFで送れます。
>
> できないこと：すべてのカメラを見つけられるアプリはありません。赤外線もネットワークもなく、レンズの向きが合わないカメラは映らないことがあります。ホテルのWi-Fiは機器同士が見えない設定が多いです。手がかりがなくても「ない」とは言い切れないので、チェックリストでご自身の目でも確認してください。
>
> オフラインで動作。アカウント・トラッキング・広告なし。50言語。ライトは最大で毎秒3回点滅します（設定で点灯モードに切り替え可）。ライト付きのiPhoneが必要です。

**スクリーンショット文言**
1. 開いた瞬間から、探し始める
2. リングをタップ：レンズか、ただの反射か
3. 82%確認済み — 見落としも矢印で
4. 消灯で赤外線、背後まで
5. 同じWi-Fiでカメラのように応答する機器
6. 宿泊ごとの記録を、そのままPDFに
7. スマホで見つけられないケースも最初に説明

### 11.4 zh-Hant（台灣）
**宣傳文字**
> 一次購買，即時鏡頭偵測、確認這一點、紅外線、Wi-Fi 與藍牙檢查、清單和住宿報告全部能用。沒有訂閱，不用帳號。

**描述**
> 剛 check in，行李還沒打開，先打開 Lensafe 慢慢掃一圈房間。
>
> 一打開就開始找。手電筒一閃一閃，後鏡頭會找出「亮起來而且停在原地」的小光點，這正是鏡頭把光反射回來的樣子。可能是鏡頭的地方，畫面上會直接圈起來。
>
> 確認這一點：點一下圓圈，畫面會放大，請你左右輕移手機，手電筒再閃幾下。真正的鏡頭反光會一直停在同一點；亮亮的螺絲或玻璃會移位、會糊開。最後直接告訴你：很可能是鏡頭、一般反光，還是光源。
> 掃描覆蓋率：記錄你掃過的方向，顯示「已掃描 82%」，還沒掃到的方向用箭頭提醒。
> 紅外線：夜視攝影機的紅外線 LED 肉眼看不到。關燈後，前鏡頭可以看到其中一部分；支援的機型會自動開一個小畫面，幫你看背後的方向。內建電視遙控器自我測試，先告訴你這支 iPhone 做不做得到。
> Wi-Fi 與藍牙：在你連上的 Wi-Fi 裡，找出回應方式像攝影機的裝置；也會標出名稱像攝影機的附近藍牙裝置。全程不登入任何裝置。
> 清單與住宿報告：飯店、民宿、摩鐵、更衣室、廁所各有一份藏匿點清單。證據照片附上時間和地點，存成每次住宿的報告，一鍵輸出 PDF，可以傳給房東、飯店或警方。
>
> 做不到的事：沒有任何 App 能找到所有攝影機。沒有紅外線、沒有連網、鏡頭角度又沒對到的機器，可能看不出來。飯店 Wi-Fi 常常讓裝置之間互相看不到。沒看到跡象不代表一定沒有，請搭配清單用眼睛確認。
>
> 離線可用。不用帳號，不追蹤，沒有廣告。50 種語言。手電筒每秒最多閃 3 次，設定裡可以改成常亮模式。需要有手電筒的 iPhone。

**截圖字卡**
1. 一打開，就開始找
2. 點一下：是鏡頭，還是只是反光？
3. 已掃描 82%，沒掃到的也告訴你
4. 關燈看紅外線，連背後也看
5. 同一個 Wi-Fi 裡，誰像攝影機
6. 每次住宿一份報告，直接輸出 PDF
7. 手機找不到的情況，先跟你說清楚

（其他約 46 種語言：由本機以 en 為基準，用母語語氣生成。中繼資料照 10.1 的規則各自去重，不要直譯關鍵字。LiDAR 實驗功能在任何語言的商店文案都不提。）

---

## 12. 視覺設計

> 對齊工作室最近幾款 App 的 Liquid Glass 慣例（57_OFFDAY 的 `DESIGN_V2.md` 第 3–4、7 節與 `DESIGN_V4.md`；以及 51_LEDMovingText）。形狀、節奏、動態、玻璃分層和 QA 門檻**直接沿用 OFFDAY**。色票是 Lensafe 自己的（夜間光學儀器的調性），本機 session 對照 OFFDAY 的 tokens 結構（`AM.canvas／surface／sunken／ink／quiet／faint／hairline／brand／tint`）再命名與微調。只參考，不複製程式。

### 12.1 原則
- 高級、安靜、精準。像一台光學儀器，**不是廉價的「雷達掃描」或駭客風**：不要綠色雷達掃描線、不要骷髏或眼睛圖示、不要紅色警報閃爍。
- 內容層（清單、報告）用不透明的表面；**玻璃只用在浮在內容上的控制層**（HUD、工具列、分頁列、按鈕）。不要玻璃疊玻璃。這和 OFFDAY 第 4 節 Liquid Glass map 的規則相同。
- 沿用 OFFDAY 原則：
  - 原生元件優先（`NavigationStack`、insetGrouped `List`、sheet＋detents、`ContentUnavailableView`）；自繪的部分只限五個：相機 HUD、偵測標記與信心環、覆蓋率環、靠近測量圓環、報告狀態卡。
  - 一屏只有一個主角。
  - 所有 UI 文字單行（放不下時先用 `ViewThatFits` 換排法，最後才縮字）。
  - 字級最小 13pt。
  - 每屏只有一個飽和的品牌元素。
  - 四芒星點綴每屏最多一組，只放在英雄卡的角落、空狀態和 icon。這剛好呼應「鏡頭反光」的意象。

### 12.2 Design Tokens
| Token | Light | Dark | 用途 |
|---|---|---|---|
| `canvas`（＝bg.base） | #F4F5FA | #06080E | 頁面底色（疊靜態的極光光暈，不模糊） |
| `surface`（＝bg.elevated） | #FFFFFF | #10131D | 卡片與清單表面（不透明，1pt hairline＋柔和陰影） |
| `sunken` | #ECEEF6 | #0B0E17 | 凹槽、圖示井、分段軌、停用按鈕 |
| `hairline` | #1B2340 @0.12 | #E8ECFF @0.12 | 卡片邊框與分隔線（1pt） |
| `ink.primary` | #0E1222 | #F2F4FA | 主要文字 |
| `ink.secondary` | #5A6178 | #9AA3BA | 次要文字 |
| `brand.aurora`（漸層） | #5B5BF7 → #9B5CF6 → #22C3D6（135°） | 同色，提高 8% 亮度 | 主按鈕著色、icon、截圖背景 |
| `signal.lens` | #F5A623 | #FFB547 | 反光標記（暖琥珀） |
| `signal.ir` | #8B5CF6 | #B78CFF | 紅外線標記（紫） |
| `signal.net` | #0FB5A6 | #3DD6C6 | Wi-Fi（青綠） |
| `signal.bt` | #2F7CF6 | #5AA8FF | 藍牙（藍） |
| `state.review` | #F2664A | #FF7A59 | 「需要再看」（珊瑚色，不用正紅） |
| `state.checked` | #6B7896 | #8E9BB5 | 「已檢查」（中性石板色。**不用綠色**，避免暗示「安全」） |
- 字體（同 OFFDAY）：
  - 內文用系統 SF 的文字樣式；
  - **大數字**（已檢查位址數、靠近測量的 dBm、發現數）用 SF Rounded Thin／Light，≥ 28pt，加 `.monospacedDigit()`；數字變化時用 `.contentTransition(.numericText())`；
  - 頁標用系統 large title；
  - CJK 自動套用系統字型；
  - 支援 Dynamic Type。
- 圓角（同 OFFDAY）：小圖示磚 10、井與 chip 14、按鈕與內層磚 20、**卡片 26**，一律用 `.continuous`，加上 `.containerShape`。
- 間距（同 OFFDAY）：4／8／12／16／20／24／32。區段間距 32，卡片內距 16–20，iPhone 頁面邊界 16。
- SF Symbols：
  | 用途 | 符號 |
  |---|---|
  | 反光 | `camera.aperture` |
  | 紅外線 | `light.beacon.max` |
  | Wi-Fi | `wifi.router` |
  | 藍牙 | `antenna.radiowaves.left.and.right` |
  | 清單 | `checklist` |
  | 報告 | `doc.text.magnifyingglass` |
  | 手電筒 | `flashlight.on.fill` |
  | 場景 | `bed.double`、`house`、`hanger`、`toilet`、`dumbbell`、`building.2` |

  掃描中用 `.symbolEffect(.variableColor.iterative)`，完成時用 `.symbolEffect(.bounce)`。
- 觸覺回饋：**工作室慣例是不用觸覺、不用 UI 音效**（OFFDAY DESIGN_V3 第 0 節第 6 點）。這款 App 只建議一個功能性的例外：**確認偵測點時，給一次 `.sensoryFeedback(.impact(weight: .medium))`**，讓使用者眼睛盯著房間時也知道鎖定了，設定裡可以關。其他地方一律不用觸覺。店主若要維持慣例，就整個拿掉。
- 動態（同 OFFDAY）：
  - 按壓：`press` spring(0.24, 0.72)，縮放到 0.97；
  - 狀態切換：`soft` spring(0.42, 0.82)；
  - 首次出現：`reveal` spring(0.68, 0.86)；
  - 偵測標記出現時從 0.6 縮放到 1，同時淡入並帶光暈；
  - 呼吸脈衝 1.6 秒，**只在相機頁、只套在已確認的標記上**（次要畫面和清單不可用 `repeatForever`）；
  - 開啟「減少動態效果」時，只保留淡入淡出，脈衝改成靜態雙圓環；
  - 開啟「減少透明度」時，系統玻璃會自動退回不透明，自繪的表面也要跟著改成不透明，對比維持 ≥ 4.5:1。

### 12.3 Liquid Glass 用法
- 相機頁的 HUD：用 `GlassEffectContainer` 包住手電筒、靈敏度和凍結這幾個控制。每個用 `.glassEffect(.regular.interactive())`，啟用中的狀態用 `.tint(signal.lens.opacity(0.35))`。「掃描中 ↔ 已找到」狀態切換時，用 `glassEffectID` 加 `@Namespace` 做形變。
- 主要行動按鈕用 `.buttonStyle(.glassProminent)`，再用 `brand.aurora` 著色；次要按鈕用 `.buttonStyle(.glass)`。
- **沒有分頁列**。根畫面是相機；底部控制列用一個 `GlassEffectContainer` 包五顆 `.glassEffect(.regular.interactive())` 按鈕，中央快門用 `.glassProminent`。次要畫面都是 sheet，sheet 裡用 `NavigationStack`，工具列沿用系統的玻璃樣式，捲動內容加 `.scrollEdgeEffectStyle(.soft, for: .top)`。IR 子母畫面是一塊 r20 的圓角視窗，外框用玻璃描邊，可以拖曳到四個角落。
- Sheet（說明、這是什麼）用系統預設的玻璃 sheet，搭配 `.presentationDetents([.medium, .large])`。

### 12.4 逐頁視覺
- **相機根畫面**：全螢幕即時畫面，邊緣加一層很淡的暗角。上方左右各一個玻璃 HUD 膠囊（覆蓋率環、手電筒模式加 ⓘ），底部是玻璃控制列，中央快門用 `brand.aurora` 著色的 `.glassProminent`。畫面上除了偵測標記，沒有其他飽和色。第一次的限制提示是一顆玻璃膠囊，6 秒後淡出。
- **反光掃描**：相機畫面上加一層很淡的暗角（vignette，邊緣 −20% 亮度），把視線集中在中央。標記是 1.5pt 的 `signal.lens` 細圓環，外面一圈 12pt 的柔光；確認後的點加上 4 個角括號準星，旁邊用玻璃小膠囊顯示「強／可能」。底部的提示是玻璃膠囊，文字淡入淡出。
- **紅外線**：整體偏暗，背景用 #06080E。標記是 `signal.ir` 的雙圓環加慢脈衝。暗度計是一條細長的玻璃膠囊，填滿代表夠暗。
- **Wi-Fi 與藍牙**：清單用不透明的分組卡。「像攝影機」那一組的標頭用 `state.review` 的小點，不用整片紅色。藍牙的靠近測量用一個大圓環，顏色從 `signal.bt` 漸變到 `signal.lens`，數字顯示平滑後的訊號強度。
- **報告**：像一份精緻的檢查單，白底（深色模式用 #10131D），四張狀態卡，PDF 用同一套版型輸出。

### 12.4A 設計 QA 門檻（沿用 OFFDAY DESIGN_V2 第 7 節）
- 裝置：iPhone 17 Pro Max、iPhone SE（375×667）。
- 外觀：淺色與深色。
- 語系：zh-Hant、en、ja、ko、ar（RTL）。
- Dynamic Type：預設與 accessibility1。
- 評分：用一個沒有前文脈絡的審查者逐屏打分，每項 ≥ 8、平均 ≥ 8.5。
- 直接不及格：文字換行或被截斷、灰色或平淡的背景、非原生的按鈕或分頁列、小於 13pt 的字、雷達或駭客風元素、假的掃描動畫。

### 12.5 App Icon
- 用 Icon Composer 做分層 icon（iOS 26），要有一般、深色、著色、透明四種外觀。
- 背景是 `brand.aurora` 的深色版漸層（#2B2A8F → #5B3BC9 → #0F7F8E）。前景是一枚玻璃質感的圓形鏡片，右上方帶一顆細小的四芒光點，代表那一下反光。
- 不要眼睛、不要放大鏡加人影、不要雷達、不要攝影機輪廓（避免讓人以為是攝影 App）。

### 12.6 截圖風格
- 6.9 吋直式。背景用深色 aurora 漸層，裝置外框用真機畫面。字卡放上方兩行內（11 節的文案），一張只講一件事。
- 偵測畫面**一定要用真機實拍**（用自備的測試攝影機或另一支手機），**不可以合成假的偵測結果**，左下角用小字標註「示範：使用自備測試鏡頭」。
- 第 6 張「做不到的事」用中性的石板色調，搭配限制說明頁的真實截圖。

---

## 13. 7 秒鉤子片（分鏡）：H1 零點擊偵測 → H2 確認這一點

> 全部用**真機螢幕錄影加實拍**（模擬器沒有相機，不能用）。示範的鏡頭是我們自己準備的測試攝影機，藏在煙霧偵測器或 USB 充電頭裡。片尾小字標註「示範用自備測試鏡頭」。不用 AI 生成偵測畫面。

| 秒 | 畫面 | 字幕（en／ko／ja／zh-Hant） |
|---|---|---|
| 0–1.2 | 飯店房間，拇指點 Lensafe 的 icon，**直接進入相機**，手電筒開始脈衝 | Open it. ／ 켜기만 하세요. ／ 開くだけ。 ／ 打開就好。 |
| 1.2–3.0 | 掃到煙霧偵測器：虛線候選圈出現，然後變成實線琥珀色信心環，標著「可能是鏡頭」 | A ring finds a possible lens. ／ 렌즈일 수 있는 곳에 원이 뜹니다. ／ レンズの可能性にリング。 ／ 可能是鏡頭，直接圈起來。 |
| 3.0–5.5 | 點一下 → 放大 → 「左右輕移手機」→ 手電筒閃 3 下 → 判斷卡片：「很可能是鏡頭 · 請靠近確認」 | Tap: lens, or just a reflection? ／ 탭: 렌즈일까, 반사일까? ／ タップ：レンズか、反射か。 ／ 點一下：鏡頭還是反光？ |
| 5.5–7.0 | 覆蓋率從 64% 跳到 82%，接著是 icon 和名稱 | Lensafe · pay once · on-device ／ Lensafe · 한 번 구매 · 기기 내 처리 ／ Lensafe・買い切り・端末内処理 ／ Lensafe・一次買斷・手機內處理 |
- 不放價格數字（工作室外宣規則），不寫「免費」，片尾可以寫「一次買斷」。
- 鉤子片要過工作室的光敏感檢查：手電筒脈衝 3 Hz，拍攝時讓閃光在畫面中只占小區域，避免整片畫面跟著閃。
- 無聲版加上字幕，給 TikTok／IG 手動配熱門音樂用。

---

## 14. 上市外宣計畫（接既有通路）

| 時點 | 通路 | 做法 |
|---|---|---|
| 上架前 | GEO 頁 | 在 `00_GrowthEngine/geo` 新增 `lensafe` 頁（en、ko、ja、zh-Hant 先做），鏡像到 Guide。高意圖 answers 頁：「how to check a hotel room for hidden cameras」「숙소 몰카 확인 방법」「ホテル 盗撮カメラ 確認方法」「飯店 針孔 怎麼檢查」。alternatives 頁：「hidden camera detector without subscription」。FAQ 只寫 App 真的做得到的事，不把關鍵字直接變成 FAQ 宣稱（這是 Zipbox 的教訓）。 |
| 上架當天 | 鉤子片 | 在 `shorts/storyboards/lensafe.json` 寫分鏡（照第 13 節），素材用真機錄影放在 `social/assets/lensafe/`。排進 `.github/growth/clips.json`，用 `schedule_posts.py` 排程，store_url 帶 `ct=h7_lensafe_<lang>`。 |
| 第 1 週 | Telegram LumiApps2026 | 每個語言一則場景貼文（`ct=telegram`），一則只放一個連結。 |
| 第 1–3 週 | Threads（threads-autopilot） | 照 reviewed_sources 的前例加入 reviewed onboarding。店主以開發者第一人稱寫：「我自己出差住飯店都會先查房，所以做了這個」。zh-Hant、ja、ko 各 3 則場景貼文，每帳號每天 ≤ 3 則，正文不放連結。 |
| 第 1–3 週 | IG Reels | 鉤子片加上無聲版。 |
| 季節窗口 | 全通路 | 跨年、2027 春節（2/6）、KR 설날、JP 年末年始和 GW 前 4–6 週加強推。KR 有몰카 相關新聞上 Google 熱搜時（爆款雷達會抓到），當週加推。 |
| 持續 | 社群回答 | Reddit r/solotravel、r/travel、PTT、Dcard、知恵袋，回答「怎麼檢查飯店有沒有針孔」時，先給不用 App 的方法，再附上 App，並標明自己是開發者。遵守各版規則，不洗版。 |
| 交叉推廣 | 支援站 | 在 TripBee／TripBee Lite／Trip Planet／WiFi Aid 的支援站和 GEO 頁互相連結（**不改這些 App 本體**）。 |

---

## 15. 驗收清單（送審前）
- [ ] 6.1 的 QA 矩陣：1 m 正對 100%，並記錄誤報清單。
- [ ] IR 自我測試在至少 3 款機型（例如 12、14、16 系列）上實測，結果寫進說明頁。
- [ ] Wi-Fi：家用網路（放一台測試攝影機）測得到「強」；飯店式隔離網路要出現隔離提示。
- [ ] 拒絕各項權限後，App 不會壞，而且報告上誠實顯示「未檢查」。
- [ ] 全部文案裡，下列字眼都不能當作正面宣稱出現：100%、guarantee、保證、一定找得到、確定是攝影機、「安全」當結論、磁場、竊聽。像「不代表一定沒有」這種否定說法可以用。
- [ ] 4 個主力語系的中繼資料長度和去重（10.4）。
- [ ] 隱私標籤是 Data Not Collected；PrivacyInfo.xcprivacy 已放進專案。
- [ ] 截圖 7 張，偵測畫面都是真機實拍。App Preview 影片前 3 秒就出現標記。
- [ ] 打開 App 到第一個候選圈出現 ≤ 1 秒（對準測試鏡頭時）；沒有引導頁。
- [ ] 確認這一點（6.1A）：手機鏡頭 ≥ 9/10 判為「很可能是鏡頭」；螺絲或玻璃 ≥ 8/10 判為「一般反光」或「無法判斷」。
- [ ] 覆蓋率（6.5A）：原地轉一圈會上升，手機靜止時不會變。
- [ ] 手電筒脈衝 ≤ 3 Hz；穩定模式可用；開啟「減少動態效果」時預設穩定模式；App 進背景時立刻關掉手電筒。
- [ ] 熱節流：連續掃描 10 分鐘，`thermalState` 變化時會正確降級。
- [ ] multicam 子母畫面：在支援的機型實測後鏡頭脈衝和前鏡頭 IR 能同時跑；跑不動時要正確退回一鍵切換。
- [ ] LiDAR 實驗功能預設關閉；沒有 LiDAR 的機型完全看不到這個選項。

---

## 16. 本機新 App 管線對照（58_Lensafe）
照工作室的標準新 App 流程走，可以參考 57_OFFDAY 的 `Docs/research/05_registration_receipt.md`。本機 session 依自己的 new-app-command.txt 執行；下面只列這款 App 要特別注意的地方。
1. 台帳：在 `~/00_Standards` 的 `app-portfolio.md` 新增第 58 列（`Lensafe` / `58_Lensafe` / `com.alice51849.Lensafe` / ASC —）。在 `app-requirements.md` 新增「### 58. Lensafe — 58_Lensafe」段落，內容包含產品契約、專屬要求、命名、4.3 防線、免費付費界線（**付費下載，無內購**）、隱私、namespace、Essential Matrix、品質、不可回歸、來源，取材自本 spec。
2. `StoreAssets/contracts/portfolio-distinctness.json`，phase=concept，以 9A.5 為底稿，`portfolioComparisons` 補齊 01–57。
3. 跑 `portfolio_spam_gate.py --phase concept`、`requirements_gate.py`、`newapp_register.py 58_Lensafe`，再用 `new_app_gate.py receipt 58_Lensafe requirements` 寫收據。
4. **正式商標檢索**（USPTO、EUIPO、JPO、KIPO、TIPO）通過之後，才建立 Bundle ID `com.alice51849.Lensafe` 和 ASC App（名稱 Lensafe、主要語言 English (U.S.)、主類別 Utilities、次類別 Travel）。
5. 價格：Paid Apps Agreement 要是 Active；Price Schedule 以 United States 為基準，設 $4.99，確認 KR ₩7,700／JP ¥800／TW NT$150。`price_policy_ok` 收據要註明「店主 2026-10-14 核准：付費下載、無內購」，因為工作室的預設是免費加買斷，這款是例外。沒有內購，所以 `iap_binary_ok` 標成不適用（或照 gate 的規定標示）。
6. 其他收據（design_selfcheck、visual_ok、lang_check、aso_dual_model、objectionable_scan、screenshots、hero_first_ok、persona 等）照管線產生。`screenshots_unlocked_ok` 在付費下載的 App 裡本來就成立。
7. 送審前跑 `portfolio_spam_gate.py --phase release`（原始碼相似度對每一款都要 ≤ 0.35），再找獨立的 Max 審查，最後用 `submit_one.py` 送出。審核備註貼 9A.4 的文字。

---

## 17. 來源
- App Store 搜尋提示（MZSearchHints）與搜尋結果：2026-10-14 實測，各國店面 US、KR、JP、TW。iTunes Search API（US、KR）；apps.apple.com 網頁版搜尋（TW「針孔」、JP「隠しカメラ」「盗撮カメラ発見」）。iTunes Search 後來被限流（403），JP、TW 改用網頁版搜尋頁。
- Peek 商品頁（US，內購清單與評分）：https://apps.apple.com/us/app/id1571925628
- Gibco #1 隠しカメラ検出器（JP，磁場宣稱、18+）：https://apps.apple.com/jp/app/id1665597557
- META GRAPH 針孔攝像頭探測器（TW）：https://apps.apple.com/tw/app/id1605066265
- KR 몰카탐지기 - Peek：https://apps.apple.com/kr/app/id1571925628
- Glint: Detect Hidden Camera：https://apps.apple.com/ru/app/glint-detect-hidden-camera/id6654924497
- Data Doctors（Glint Finder 實測：距離 3–4 英尺、角度要對）：https://www.datadoctors.com/help/question/22035-How-to-Detect-HIdden-Cameras/
- LAPD（SenSys '21）專案頁：https://www.cyphy.kaist.ac.kr/research/lapd ；The Register：https://www.theregister.com/2021/11/18/smartphone_camera_detection/
- 前鏡頭 IR 敏感度：https://nexttools.net/can-an-iphone-detect-infrared/
- 評論抱怨彙整：https://justuseapp.com/en/app/6737350119/hidden-camera-spy-bug-detector/reviews 、https://marlvel.ai/apps/hidden-camera-detector-app
- 付費競品價格：ones.com 比較頁 https://ones.com/blog/?p=1067029 ；Electronics & Spy Cam Detector https://apps.apple.com/mo/app/electronics-detector/id1340269276
- 台灣新聞（iPhone 放大鏡紅色濾鏡測試）：https://www.ettoday.net/news/20260511/3163780.htm
- App Review 準則 2.3.1、4.3（開發者論壇範例）：https://developer.apple.com/forums/thread/96879
- 商標：ROOMCHECKER https://trademarks.justia.com/859/52/roomchecker-85952699.html ；Lumu Pinhole https://www.japancamerahunter.com/2014/08/jch-product-review-lumu-lightmeter-ondu-pinhole/ ；LENSCHEK（光學儀器，與本案不同類別）https://trademarks.justia.com/870/60/lenschek-87060334.html
- AVCaptureMultiCamSession：https://developer.apple.com/documentation/avfoundation/avcapturemulticamsession ；WWDC19 249 筆記（iPhone XS/XR 起支援）：https://wwdcnotes.com/documentation/wwdc19-249-introducing-multicamera-capture-for-ios/ ；前後鏡頭同時使用（Apple 論壇）：https://developer.apple.com/forums/thread/847763
- ARKit sceneDepth 與 confidenceMap：https://developer.apple.com/documentation/arkit/arframe/scenedepth ；https://developer.apple.com/documentation/arkit/ardepthdata
- WCAG 2.3.1 三次閃光門檻（手電筒脈衝 ≤ 3 Hz 的依據）：https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold
- LENSAFE 舊商標（1981 年註冊，2002 年註銷）：https://trademarks.justia.com/732/39/lensafe-73239868.html
- 工作室慣例：57_OFFDAY 的 `Docs/DESIGN_V2.md`、`DESIGN_V3.md`、`DESIGN_V4.md`、`Docs/research/05_registration_receipt.md`、`Docs/research/15_pricing_study.md`、`project.yml`、`Packages/OffdayFeatures/Tools/brand.json`
- 本地價：工作室 $4.99 App 的實際上架價（`.github/growth/apps/zipbox.md`：$4.99／NT$150／¥800／₩7,700）
