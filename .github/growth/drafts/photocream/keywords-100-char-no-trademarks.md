# PhotoCream Pro：六個語系 ≤100 字元、不含商標的關鍵字（photocream-03）

| 項目 | 內容 |
|---|---|
| 用途 | photocream_full.json 的 50 個語系 keywords 全部超過 ASC 100 字元上限；其中 en／zh-Hant／zh-Hans／ja／ko／cs 還含「polaroid／寶麗來／宝丽来／ポラロイド／폴라로이드」商標（審核指南 2.3.7 風險）。這份給出六個語系可直接貼進 ASC 的字串，以及要寫回資料檔的 JSON |
| 給誰 | 店主（ASC 貼上，隨新版本送審）；本機 Claude／GrowthEngine（寫回 photocream_full.json，雲端這次不改資料檔） |
| 發送者 | 店主 Guan Feng Lai 本人在 ASC 操作；本次工作不碰 ASC |
| 規則 | 字元數都用程式算過；不放任何品牌或他社商品名（polaroid／寶麗來／チェキ／写ルンです／인스탁스／Instagram 簡稱「ins／インスタ／인스타」都不放）；「拍立得／一次性相機／disposable」屬通稱，保留；不重複名稱與副標已有的字 |

---

| 語系 | 字元數 | keywords |
|---|---|---|
| zh-Hant | 85 | `美顏,美肌,自拍,文青,拍立得,一次性相機,顆粒,漏光,光暈,暗角,日期戳,膠捲,35mm,類比,調色,曲線,HSL,邊框,質感,日系,韓系,電影感,黑白,vintage` |
| zh-Hans | 85 | `美颜,美肤,自拍,文艺,拍立得,一次性相机,颗粒,漏光,光晕,暗角,日期戳,胶卷,35mm,模拟,调色,曲线,HSL,边框,质感,日系,韩系,电影感,黑白,vintage` |
| ja | 86 | `エモい,盛れる,自撮り,美肌,美顔,韓国風,使い捨て,粒子,光漏れ,ハレーション,ビネット,日付,ヴィンテージ,アナログ,35mm,おしゃれ,トーンカーブ,シネマ,モノクロ` |
| ko | 72 | `필카,빈티지,레트로,셀카,뷰티,피부,일회용,그레인,빛샘,할레이션,비네팅,날짜,아날로그,35mm,흑백,시네마,인스턴트,보정앱,사진앱` |
| en-US | 98 | `vintage,analog,disposable,grain,light leak,halation,35mm,aesthetic,selfie,beauty,retouch,cinematic` |
| cs | 95 | `analogový fotoaparát,filmový,vintage,zrno,světelné úniky,selfie,retuš,jednorázový,35mm,estetika` |

各語系刪掉的詞：
- en-US：polaroid（商標）；film／filter／camera／retro（名稱「Film Filters」、副標「Film Camera & Retro Filters」已有）
- zh-Hant：寶麗來（商標）；底片／濾鏡／復古／修圖／相機（名稱、副標已有）
- zh-Hans：宝丽来（商標）；胶片／滤镜／复古／修图／相机（名稱「胶片滤镜·复古修图」、副標「胶片相机·复古滤镜修图」已有）
- ja：ポラロイド（商標）；フィルム／フィルター／カメラ／レトロ／加工（名稱、副標已有）
- ko：폴라로이드（商標）、인스타감성（Instagram 簡稱）；필름／필터／감성／보정／카메라（名稱、副標已有）
- cs：polaroid（商標）；「analogový fotoaparát」保留在第一個，因為它是成績單上第 11 名、最接近登頂的詞（見 photocream-04），先不動，避免排名波動

## 寫回資料檔（給本機 Claude）

```json
{
  "zh-Hant": { "keywords": "美顏,美肌,自拍,文青,拍立得,一次性相機,顆粒,漏光,光暈,暗角,日期戳,膠捲,35mm,類比,調色,曲線,HSL,邊框,質感,日系,韓系,電影感,黑白,vintage" },
  "zh-Hans": { "keywords": "美颜,美肤,自拍,文艺,拍立得,一次性相机,颗粒,漏光,光晕,暗角,日期戳,胶卷,35mm,模拟,调色,曲线,HSL,边框,质感,日系,韩系,电影感,黑白,vintage" },
  "ja":      { "keywords": "エモい,盛れる,自撮り,美肌,美顔,韓国風,使い捨て,粒子,光漏れ,ハレーション,ビネット,日付,ヴィンテージ,アナログ,35mm,おしゃれ,トーンカーブ,シネマ,モノクロ" },
  "ko":      { "keywords": "필카,빈티지,레트로,셀카,뷰티,피부,일회용,그레인,빛샘,할레이션,비네팅,날짜,아날로그,35mm,흑백,시네마,인스턴트,보정앱,사진앱" },
  "en-US":   { "keywords": "vintage,analog,disposable,grain,light leak,halation,35mm,aesthetic,selfie,beauty,retouch,cinematic" },
  "cs":      { "keywords": "analogový fotoaparát,filmový,vintage,zrno,světelné úniky,selfie,retuš,jednorázový,35mm,estetika" }
}
```

其餘 44 個語系也都超過 100 字元：本機 Claude 截斷時在逗號邊界截，並先刪掉 polaroid 與各語系的對應商標寫法，以及與名稱重複的詞。

## 量測詞

成績單如果改讀覆寫清單，用回傳 challenge_terms（photocream）裡的詞；不要用上面這些關鍵字的前 3 個（例如「美顏、美肌、自拍」不是我們要搶的詞）。
