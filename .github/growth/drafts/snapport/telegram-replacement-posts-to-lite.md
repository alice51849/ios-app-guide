# Snapport：Telegram 11 則貼文改導向 Snapport Lite，德文改訴求（snapport-04）

| 項目 | 內容 |
|---|---|
| 用途 | `telegram_posts.json` 裡 app `6780575828`（Snapport 付費版）共 11 則（索引 22、23、36、41、51、55、64、69、72、123、124；en×2、zh-Hant、es、ja×2、ko、de、ar、pt-BR、fr）。依報告，外宣連結全部導向免費的 Snapport Lite（6792856304），付費版只在文末一句帶過；日文兩則不提付費版（JP 付費版目前是 1★ 一則評分，先只推 Lite）；德文刪除 Pass-／Ausweisfoto 訴求，改寫為簽證、求職照、他國證件 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（telegram-daily 自動發文）。本檔本身不發文；**本次沒有修改 `telegram_posts.json`**，由負責該檔的人照下方 JSON 逐則替換（`app` 與 `url` 都改成 Lite） |
| 發文者 | Lumi Studio 官方頻道（店主 Guan Feng Lai 經營） |
| 發文規則 | 沿用頻道規則：每則一個連結（ct=telegram），不重複、不灌版。不用其他 App 名稱、不寫排名、不寫第三方價格 |
| 為什麼正文改寫成 Lite 的功能 | 連結指向 Lite，正文就只能寫 Lite listing 裡有的功能：範本與編修免費、第一次匯出免費、一次購買不限次數匯出。付費版特有的說法（「no in-app purchases」）只出現在文末那一句 |
| 事實依據 | Lite：snapportlite_full.json（en-US、zh-Hant、es-ES、ja、ko、de-DE、ar-SA、pt-BR、fr-FR）——35 種範本（28 國家／地區，含 2×2 in、35×45、33×48、50×70 mm）；自訂尺寸 mm／inch／pixel 與 DPI；裝置上臉部偵測＋頭頂／眼睛／下巴導引線；保留原背景或換白、淺灰、藍、紅、自訂色；輕微亮度／對比／色溫／銳利度；JPEG／PNG／PDF；4×6 in、A4、Letter 排版、一頁多張、裁切線；裝置上處理不上傳、可離線；範本與編修免費、第一次匯出免費、一次購買不限次數匯出；無訂閱、廣告、追蹤、帳號；不保證受理、不隸屬政府。付費版：snapport_full.json en-US「Buy Snapport once… No subscription, no in-app purchases」。介面 50 種語言、App 內切換（店主確認；listing 末行仍寫 44，貼文以店主確認的 50 為準） |
| 德國規定 | 自 2025-05-01 起，德國護照與身分證只接受以數位方式傳送的照片（市政 FAQ：stemwede.de、stadt-muenster.de、wiesbaden.de）。德文貼文因此只講簽證、求職照、其他國家的證件申請，並加一句「不適用於德國護照與身分證」 |
| 不能寫 | 「30 秒」「compliant／合規」「保證」；「in 30s」這類速度宣稱；「不用跑相館」；第三方價格；任何「最好」「第一」；日文提到付費版；德文以 Passfoto／Ausweisfoto 為賣點 |
| 新連結 | 全部改為 `https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8`，`app` 欄改為 `6792856304` |

> 替換後，這 11 則加上 Lite 原有／新增的 Telegram 貼文都指向 6792856304。為避免同一週連發相似內容，11 則已刻意寫成 11 個不同情境（en 全家換護照、en 背景顏色、zh-Hant 台胞證＋美簽、es 履歷／簽證、ja 履歷照、ko 반명함、de 他國簽證＋求職照、ar 旅行簽證、pt-BR 3x4 履歷、fr CV／識別證、ja 就活背景色）。

---

## 1. 索引 22，取代 en（原文：`🛂 Snapport — take a compliant passport/ID photo at home in 30s…`）

```json
{
  "lang": "en",
  "app": "6792856304",
  "text": "🛂 Four passports to renew means four photos. Snapport Lite has a 2×2 in template with head-top, eye-line and chin guides, then lays out a 4×6 in print sheet with several copies and cut guides. All presets and edits are free, your first export is free, and a one-time unlock covers the rest of the family. Photos are processed on your iPhone and never uploaded. Doesn't guarantee acceptance, so check the official rules. Prefer a paid app with no in-app purchases? That's Snapport.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 2. 索引 23，取代 zh-Hant（原文：`🛂 【Snapport】在家 30 秒自拍護照/證件照…不用跑相館。`）

```json
{
  "lang": "zh-Hant",
  "app": "6792856304",
  "text": "🛂 全家要辦台胞證和美簽，照片尺寸還不一樣？【Snapport Lite：在家拍證件照】內建 33×48mm、2×2 吋、35×45mm 等範本，在手機上偵測臉部、用頭頂／眼睛／下巴導引線對位，再排成 4×6 吋或 A4 沖印版、附裁切線。範本與編修免費、第一次匯出免費，之後一次買斷不限次數；照片不上傳。介面 50 種語言，可在 App 內切換。規格以各機關為準。想要沒有內購的付費版，可選 Snapport。",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 3. 索引 36，取代 es（原文：`📸 Haz tu foto de pasaporte o DNI en casa…`）

```json
{
  "lang": "es",
  "app": "6792856304",
  "text": "📸 ¿Te piden una foto de tamaño exacto para el currículum, un visado o una matrícula? Snapport Lite recorta tu retrato a la medida que elijas (plantillas como 35×45 mm o tamaño propio en mm, pulgadas o píxeles), con guías de coronilla, ojos y barbilla. Fondo blanco o el original, y hoja de impresión 4×6 pulgadas (10×15) o A4 con guías de corte. Plantillas y edición gratis, primera exportación incluida. Las fotos no se suben. Interfaz en 50 idiomas, se cambia dentro de la app. Revisa siempre los requisitos oficiales. ¿Prefieres pago único sin compras dentro de la app? Existe Snapport.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 4. 索引 41，取代 ja（原文：`📸 パスポート写真や証明写真を、自宅でサクッと。Snapportは…買い切りで使えます。`）——付費版不提

```json
{
  "lang": "ja",
  "app": "6792856304",
  "text": "📸 履歴書の写真、撮り直しのたびに出かけていませんか。Snapport Lite（自宅で証明写真）は、ライブラリの写真を端末上で顔検出し、頭頂・目・あごのガイド線に合わせてぴったりのサイズに切り抜きます。背景は元のまま、または白・ブルーなどに。4×6インチやA4の印刷シートにカットガイド付きで並べられます。テンプレートと編集は無料、最初の書き出しも無料。写真はアップロードされません。表示言語は50言語、アプリ内で切り替え。提出先の規定は必ず確認してください。",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 5. 索引 51，取代 ko（原文：`📸 여권사진과 증명사진을 집에서 준비하세요. Snapport는…한 번 결제 앱입니다.`）

```json
{
  "lang": "ko",
  "app": "6792856304",
  "text": "📸 이력서용 반명함, 사진관 가기 전에 집에서 먼저 만들어 보세요. Snapport Lite는 기기 안에서 얼굴을 인식해 정수리·눈·턱 가이드에 맞추고, mm·인치·픽셀로 원하는 크기에 딱 맞게 잘라 줍니다. 배경은 그대로 두거나 흰색·파란색 등으로 바꾸고, 4×6인치나 A4에 재단선과 함께 여러 장 배치할 수 있어요. 템플릿과 편집은 무료, 첫 내보내기도 무료. 사진은 업로드되지 않습니다. 표시 언어 50개, 앱 안에서 변경. 제출처 규정을 꼭 확인하세요. 인앱 결제 없는 유료 버전 Snapport도 있습니다.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 6. 索引 55，取代 de（原文：`📸 Pass- und Ausweisfotos einfach zu Hause erstellen…`）——改為簽證、求職照、他國證件

```json
{
  "lang": "de",
  "app": "6792856304",
  "text": "📸 Visumantrag für ein anderes Land oder ein Foto für die Bewerbung? Snapport Lite schneidet dein Porträt direkt auf dem iPhone exakt zu: Vorlagen wie 2×2 Zoll, 35×45 oder 50×70 mm oder eigene Größen in mm, Zoll und Pixeln, mit Hilfslinien für Scheitel, Augen und Kinn. Hintergrund behalten oder auf Weiß, Blau oder Rot wechseln, dann ein Druckbogen 4×6 Zoll oder A4 mit Schnittmarken. Vorlagen und Bearbeitung kostenlos, erster Export inklusive. Fotos werden nicht hochgeladen. Nicht für deutsche Reisepässe und Personalausweise: Dort werden seit Mai 2025 nur digital übermittelte Fotos angenommen. Prüfe immer die offiziellen Vorgaben.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 7. 索引 64，取代 ar（原文：`📸 جهّز صورة جواز السفر أو الهوية من البيت…`）

```json
{
  "lang": "ar",
  "app": "6792856304",
  "text": "📸 تحتاج صورة بمقاس محدد لطلب تأشيرة سفر؟ يقصّ Snapport Lite صورتك على iPhone بالمقاس الذي تختاره، مثل 2×2 بوصة أو 35×45 مم أو مقاس مخصص بالمليمتر أو البكسل، مع خطوط إرشاد لأعلى الرأس والعينين والذقن. احتفظ بالخلفية الأصلية أو بدّلها إلى الأبيض، ثم اطبع عدة نسخ على ورقة 4×6 بوصة أو A4 مع خطوط قص. القوالب والتعديل مجانًا، وأول تصدير مشمول. لا تُرفع صورك إلى أي خادم. الواجهة متاحة بـ 50 لغة ويمكن تغييرها داخل التطبيق. التطبيق لا يضمن قبول الصورة، فراجع الشروط الرسمية دائمًا. وإن فضّلت شراءً واحدًا بلا مشتريات داخل التطبيق فهناك Snapport.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 8. 索引 69，取代 pt-BR（原文：`📸 Faça foto de passaporte ou documento em casa…`）

```json
{
  "lang": "pt-BR",
  "app": "6792856304",
  "text": "📸 Precisa de foto 3x4 para currículo, matrícula ou crachá? No Snapport Lite você define o tamanho em mm (30×40), alinha o rosto pelas guias de topo da cabeça, olhos e queixo, deixa o fundo original ou troca por branco e monta uma folha 4×6 pol (10×15) ou A4 com várias cópias e guias de corte. Modelos e edição grátis, primeira exportação incluída. As fotos não são enviadas para nenhum servidor. Interface em 50 idiomas, troca dentro do app. Confira sempre as regras de quem pediu a foto. Prefere pagamento único sem compras no app? Existe o Snapport.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 9. 索引 72，取代 fr（原文：`📸 Faites vos photos de passeport ou d’identité à la maison…`）

```json
{
  "lang": "fr",
  "app": "6792856304",
  "text": "📸 Une photo au format exact pour un CV, un badge ou un visa pour un autre pays ? Snapport Lite recadre votre portrait sur l’iPhone : modèles comme 35×45 mm ou 2×2 po, ou format libre en mm, pouces ou pixels, avec repères pour le haut du crâne, les yeux et le menton. Fond d’origine ou fond blanc, puis planche 4×6 po (10×15) ou A4 avec repères de coupe. Modèles et retouches gratuits, premier export inclus. Les photos ne quittent pas l’appareil. Interface en 50 langues, modifiable dans l’app. Vérifiez toujours les règles officielles. Vous préférez un achat unique sans achats intégrés ? Il existe Snapport.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 10. 索引 123，取代 en（原文：`🛂 Need a passport, visa or ID photo with the exact background and size your country asks for?…`）

```json
{
  "lang": "en",
  "app": "6792856304",
  "text": "🛂 Some forms ask for a white background, others for blue or red. Snapport Lite keeps your original background or switches it to white, light gray, blue, red or a custom color, lets you compare before and after, and crops to the size you need: built-in presets for 28 countries and regions, or custom mm, inches or pixels with your own DPI. Free presets and edits, first export free, one-time unlock for unlimited exports. On-device and offline. 50 interface languages, switchable in the app. Always check the official requirements. Snapport is the paid version with no in-app purchases.",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

## 11. 索引 124，取代 ja（原文：`🛂 証明写真をiPhoneで。マイナンバー・パスポート・履歴書のサイズと背景(白・青)に対応。買い切り…Snapport`）——付費版不提

```json
{
  "lang": "ja",
  "app": "6792856304",
  "text": "🛂 就活の証明写真、背景の色を指定されたら。Snapport Lite は元の背景を残すことも、白・ライトグレー・ブルー・レッド・カスタムカラーに変えることもでき、変更前後を見比べて輪郭を微調整できます。サイズはテンプレートか、mm・インチ・ピクセルで自由に。JPEG・PNG・PDF で書き出し、4×6インチやA4の印刷シートにも。テンプレートと編集は無料、最初の書き出しも無料。写真は端末内で処理されます。表示言語は50言語からアプリ内で切り替え。提出先の規定を確認してください。",
  "url": "https://apps.apple.com/app/id6792856304?pt=118326163&ct=telegram&mt=8"
}
```

---

## 替換後檢查

- [ ] 11 則的 `app` 都是 `6792856304`，`url` 都是 id6792856304＋ct=telegram
- [ ] 沒有任何一則寫「30 秒」「compliant」「不用跑相館」「保證」
- [ ] 德文那則沒有 Passfoto／Ausweisfoto 字樣，且保留「不適用於德國護照與身分證」那一句
- [ ] 兩則日文都沒有提付費版 Snapport
- [ ] 提到 3x4（30×40 mm）的那則寫的是自訂尺寸，不是內建範本
- [ ] 每則只有一個 url
