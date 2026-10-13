# PicClear Pro：100 字元關鍵字提案與量測詞（picclear-03）

| 項目 | 內容 |
|---|---|
| 用途 | _engine/data/picclear_full.json 的 keywords 是 404／173／186 字元的候選清單，超過 ASC 100 字元上限，成績單量的「前 3 個詞」也是搶不到的大詞。這份提供三個市場可直接貼進 ASC、且 ≤100 字元的關鍵字字串，以及給成績單覆寫用的量測詞 |
| 給誰 | 1) 店主：在 ASC 貼關鍵字（要跟新版本一起送審）；2) 本機 Claude／GrowthEngine：把同一字串寫回 picclear_full.json（雲端這次不改資料檔，避免和 GrowthEngine 匯出衝突） |
| 發送者 | 店主 Guan Feng Lai 本人在 ASC 操作；本次工作不碰 ASC |
| 規則 | 每個字串都已用程式算過長度（≤100）；不放其他 App 名稱或商標；不放名稱已有的字（en「photo cleaner」、zh-Hant「照片清理」、ja「写真整理」「重複」）；依報告刻意不放 duplicate／重複（撞 iOS 內建，見 guide 草稿）；不放「清理大師」（與台灣一款競品名稱相同） |
| 依據 | .github/growth/apps/picclear.md 與 app-improvements.json 的 picclear-01／03；商店文案的六個類別（重複、相似、截圖、模糊、大型影片、大型照片） |

---

## 貼進 ASC 的關鍵字（逗號分隔、不加空白以外的符號）

| 語系 | 字元數 | 關鍵字 |
|---|---|---|
| zh-Hant | 82 | `連拍照片 刪除,截圖 清理,大型影片,相似照片,模糊照片,容量不足,儲存空間,手機瘦身,刪除照片,相簿整理,相片,影片,螢幕截圖,連拍,大型照片,離線,無廣告,買斷` |
| ja | 82 | `スクショ 整理,連写 削除,動画 容量,類似写真,ピンボケ,大きな動画,空き容量,容量不足,ストレージ,スクリーンショット,アルバム,一括削除,買い切り,オフライン` |
| en-US | 99 | `delete screenshots,burst photos,large videos,similar,blurry,storage full,free space,declutter,album` |

說明：
- 前 3 個詞依 picclear-03 指定為長尾詞（TW 連拍／截圖／大影片；JP スクショ／連写／動画；en 對應三類），這樣即使成績單仍讀「前 3 個詞」，也會量到有機會的詞。
- 如果店主採用 picclear-01 的新副標（「連拍・截圖・大影片 刪前預覽 買斷」／「スクショ・連写・大きな動画 買い切り」／「Bursts, screenshots, big videos. Pay once」），關鍵字裡的「連拍、截圖、大型影片」會和副標重複，可以改用下列替補詞補滿：
  - zh-Hant 替補：`手機容量,記憶體,iPhone,相機膠卷,照片管理`
  - ja 替補：`スマホ容量,写真管理,カメラロール,iPhone`
  - en-US 替補：`camera roll,tidy,space saver`（en 已 99 字元，替補時先刪掉同長度的詞）

- **和 ShotInbox 的重疊（請店主決定）**：shotinbox 報告建議「截圖類查詢只導 ShotInbox，容量／重複類只導 PicClear」。上面依 picclear-03 把「截圖 清理／スクショ 整理／delete screenshots」放在 PicClear 前 3 個，會和 ShotInbox 搶同一組詞。若決定截圖詞留給 ShotInbox，PicClear 改用：
  - zh-Hant 前 3：`連拍照片 刪除,大型影片,相似照片`（再補 `模糊照片` 以後的詞）
  - ja 前 3：`連写 削除,動画 容量,類似写真`
  - en-US 前 3：`burst photos,large videos,similar photos`
  量測（challenge_terms）兩邊都量沒有關係，量測不影響排名；要避免的是兩款的 ASC 關鍵字同時押同一組詞。

## 給成績單覆寫的量測詞

已一併放進回傳的 challenge_terms（picclear）。如果要寫進 .github/growth/measure-keywords.json，用同一組：
- zh-Hant：連拍照片 刪除／截圖 清理／大型影片
- ja：スクショ 整理／連写 削除／動画 容量
- en-US：delete screenshots／burst photos／large videos

## 寫回資料檔（給本機 Claude）

```json
{
  "zh-Hant": { "keywords": "連拍照片 刪除,截圖 清理,大型影片,相似照片,模糊照片,容量不足,儲存空間,手機瘦身,刪除照片,相簿整理,相片,影片,螢幕截圖,連拍,大型照片,離線,無廣告,買斷" },
  "ja":      { "keywords": "スクショ 整理,連写 削除,動画 容量,類似写真,ピンボケ,大きな動画,空き容量,容量不足,ストレージ,スクリーンショット,アルバム,一括削除,買い切り,オフライン" },
  "en-US":   { "keywords": "delete screenshots,burst photos,large videos,similar,blurry,storage full,free space,declutter,album" }
}
```

其餘 47 個語系的 keywords 也超過 100 字元；本機 Claude 截斷時請在逗號邊界截，並先刪掉與該語系名稱重複的詞。
