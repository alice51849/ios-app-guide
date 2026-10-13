# Unblurry Pro：資料檔名稱同步與量測詞提案（unblurry-02）

| 項目 | 內容 |
|---|---|
| 用途 | _engine/data/unblurry_full.json 落後於線上 ASC：TW／JP／KR 名稱還是舊版，成績單量的是舊詞；DK「gør foto skarpt」已第 1，同樣的母語動詞短句還沒複製到 nl／sv／no／fi。這份是要寫回資料檔的確切值，以及給成績單覆寫的量測詞 |
| 給誰 | 本機 Claude／GrowthEngine（資料檔由 GrowthEngine 匯出，雲端這次不直接改，避免下次匯出被蓋掉）；店主（nl／sv／no／fi 關鍵字要在 ASC 貼上並隨新版本送審） |
| 發送者 | 店主 Guan Feng Lai 本人在 ASC 操作；本次工作不碰 ASC、不改資料檔 |
| 規則 | 每個 keywords 字串已用程式算過長度（≤100 字元）；不放其他 App 名稱或商標；名稱以 2026-10-13 公開 Lookup 回傳的線上版本為準（見 .github/growth/apps/unblurry.md） |

---

## 1. 名稱同步（線上版 → 資料檔）

| 語系 | 資料檔現值 | 線上版（寫回這個） |
|---|---|---|
| zh-Hant | Unblurry Pro：模糊變清晰 | Unblurry Pro：照片變清晰 |
| ja | Unblurry Pro：ぼやけ補正 | Unblurry Pro：写真高画質化 |
| ko | Unblurry Pro: 흐림 보정 | Unblurry Pro：사진 선명하게 |

寫回前請再做一次 iTunes Lookup（country=tw／jp／kr）確認全形冒號與空白，和線上逐字一致。

## 2. 關鍵字（≤100 字元，前 3 個是量測詞）

| 語系 | 字元數 | keywords |
|---|---|---|
| zh-Hant | 78 | `照片變清晰,模糊照片變清晰,老照片修復,手震,失焦,去模糊,銳化,降噪,4K,放大,超解析,低光源,人像修復,文件,畫質,清晰度,對焦,AI修圖,HD,買斷` |
| ja | 79 | `写真 高画質化,ぼやけ 補正,古い写真,手ブレ,ピンボケ,くっきり,鮮明,シャープ,ノイズ除去,超解像,4k,拡大,復元,書類,暗い写真,HD,AI,買い切り` |
| nl-NL | 95 | `foto scherper maken,wazige foto,foto verscherpen,onscherp,oude foto,ruis,4k,vergroten,kwaliteit` |
| sv | 95 | `gör foto skarpare,suddig bild,skärpa foto,oskärpa,gamla foton,brus,4k,förstora,kvalitet,skakigt` |
| no | 96 | `gjør bilde skarpt,uskarpt bilde,uklart bilde,gamle bilder,støy,4k,forstørr,kvalitet,rystet,fokus` |
| fi | 92 | `tarkenna kuva,terävöitä kuva,sumea kuva,vanhat kuvat,kohina,4k,suurenna,kuvanlaatu,tarkennus` |

說明：
- zh-Hant 的「照片變清晰」和名稱重複，在 ASC 上是浪費 5 個字元；放在第一個只是為了讓還在讀「前 3 個詞」的成績單量到它。若成績單已改讀覆寫清單（challenge_terms），店主在 ASC 可以刪掉這個詞，換成「清楚」。
- nl／sv／no／fi 依 DK 打法，把母語動詞短句放第一個。北歐語詞是依各語系現有關鍵字與常用說法整理，沒有實測搜尋量；送審前建議在 Apple Search Ads 後台看熱度。
- da 保持現狀（「gør foto skarpt」已第 1，不要動）。

## 3. 寫回資料檔（給本機 Claude）

```json
{
  "zh-Hant": { "name": "Unblurry Pro：照片變清晰", "keywords": "照片變清晰,模糊照片變清晰,老照片修復,手震,失焦,去模糊,銳化,降噪,4K,放大,超解析,低光源,人像修復,文件,畫質,清晰度,對焦,AI修圖,HD,買斷" },
  "ja":      { "name": "Unblurry Pro：写真高画質化", "keywords": "写真 高画質化,ぼやけ 補正,古い写真,手ブレ,ピンボケ,くっきり,鮮明,シャープ,ノイズ除去,超解像,4k,拡大,復元,書類,暗い写真,HD,AI,買い切り" },
  "ko":      { "name": "Unblurry Pro：사진 선명하게" },
  "nl-NL":   { "keywords": "foto scherper maken,wazige foto,foto verscherpen,onscherp,oude foto,ruis,4k,vergroten,kwaliteit" },
  "sv":      { "keywords": "gör foto skarpare,suddig bild,skärpa foto,oskärpa,gamla foton,brus,4k,förstora,kvalitet,skakigt" },
  "no":      { "keywords": "gjør bilde skarpt,uskarpt bilde,uklart bilde,gamle bilder,støy,4k,forstørr,kvalitet,rystet,fokus" },
  "fi":      { "keywords": "tarkenna kuva,terävöitä kuva,sumea kuva,vanhat kuvat,kohina,4k,suurenna,kuvanlaatu,tarkennus" }
}
```

## 4. 量測詞

已放進回傳的 challenge_terms（unblurry）：zh-Hant、ja、en-US、ko、da、nl-NL、sv、no、fi。
