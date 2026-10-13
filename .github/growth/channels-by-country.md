# 各國推廣管道（2026-10-14）

範圍：Lumi Studio 53 款小型工具／效率／親子／教育／旅遊／開發工具 iOS App，預算近乎零，只做誠實、平台允許的推廣。本表由 30 次搜尋整理，**沒有逐頁爬取**；標「未驗證」者只是背景知識，首次發文前請自己讀一次該站規則。

## 結論

**可在一次性設定 token 後，用官方 API／官方機制全自動發文：** Threads（Threads API，token 60 天要續期）、Bluesky（AT Protocol，app password）、Mastodon（`POST /api/v1/statuses`）、DEV（Forem API v1）、Hashnode（GraphQL PAT）、Qiita（API v2）、Zenn（GitHub 推送即發布）、既有的 Telegram 頻道（Bot API）。未驗證但官方有此機制：Facebook 自家粉專（Graph API）、Hatena Blog（AtomPub）。X 有官方 API 但改為按量計費（約 $0.015／則、含連結約 $0.20／則，第三方資料），預算為零時請手動發。

**一定要人工發：** Product Hunt、Show HN、Reddit（Data API 自 2025/11 起新應用需人工審核，實務上不可用）、Indie Hackers、AlternativeTo、BetaList、Apple 精選提名（App Store Connect，需注意 growth README 把它排除在範圍外）、note、PTT、Dcard、Mobile01、LIHKG、Clien、Disquiet、Naver 部落格、TabNews（未確認官方自動化）、所有媒體／評測站投稿、所有 Facebook 社團、越泰印尼在地論壇。

**共同紀律：** 每個帳號每天 1–3 則、每則文字獨立、發文時揭露「我是開發者」、連結放留言或簡介、不開分身、不拉票、不買評測、不繞過驗證。舊 Threads 帳號就是因為高頻帶連結被停。

**各市場前 3 名：**

| 市場 | 前 3 名 |
|---|---|
| 台灣 (TW) | Threads、Facebook groups (local)、蘋果仁 (applealmond.com) |
| 香港 (HK) | Threads、Facebook groups (local)、unwire.hk |
| 日本 (JP) | X (Twitter)、Zenn、note |
| 南韓 (KR) | Clien (클리앙) - 아이포니언 / 직접홍보、Naver Blog / Naver Cafe、Disquiet (디스콰이엇) |
| 美國 (US) | Product Hunt、Hacker News - Show HN、Reddit r/SideProject |
| 英國 (UK) | Product Hunt、Hacker News - Show HN、Reddit r/iOSProgramming (App Saturday) |
| 德國 (DE) | iphone-ticker.de、appgefahren.de、Mastodon (per-instance) |
| 法國 (FR) | Korben.info、MacG / iGeneration、iPhoneSoft |
| 西班牙 (ES) | Applesfera、Xataka / Genbeta (Webedia)、DEV Community |
| 巴西 (BR) | TabNews、MacMagazine (Contato)、DEV Community |
| 墨西哥 (MX) | Threads、Xataka México、Facebook groups (local) |
| 印尼 (ID) | Facebook groups (local)、Threads、Kaskus |
| 越南 (VN) | Facebook groups (local)、Tinhte.vn、Viblo |
| 泰國 (TH) | Facebook groups (local)、Threads、Blognone |
| 印度 (IN) | Product Hunt、Hashnode、DEV Community |

跨市場共用（未列入各市場表）：Apple 精選提名、Bluesky／Mastodon／X、DEV／Hashnode、Telegram、Facebook 粉專、r/iosapps、r/AppHookup（僅限降價／免費／兌換碼）、BetaList（排隊約 2 個月、別付費加速）。完整欄位見 JSON 的 `global`。

## 台灣 (TW)

主場：用繁中講真實故事，優先度最高。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Threads](https://www.threads.net) | social | 可發自家 App 貼文，但重複、連續帶連結會被限流或停權（舊帳號曾因一天 30–48 則帶連結被停）。每天最多 1–3 則、內容不重複、連結放留言或簡介。 主場；用繁中、一則一款 App，追蹤碼放在留言連結。 | 是（可全自動） | 需 Instagram/Meta 帳號；人工一次性建立 Meta 開發者 App 並取得 token（60 天需續期）；Meta 註冊可能要求手機驗證（未驗證） | 全部 | A | 部分佐證 |
| [Facebook groups (local)](https://www.facebook.com/groups/) | community | 每個社團各有規則，多數要管理員核准推廣貼文。先讀規則、先問管理員、每個社團只發一次、不可洗版。 親子、語言學習、旅遊社團，以及印尼／越南移工與新住民社團（50 語言切入點）。先取得管理員同意。 | 否，需人工 | 真實 Facebook 帳號；每個社團需管理員同意 | 親子、教育、工具、旅遊 | A | 未驗證 |
| [蘋果仁 (applealmond.com)](https://applealmond.com) | review-site submission | 編輯型媒體；以聯絡管道寄送簡短誠實的投稿／爆料（頁面未取得，是否受理未驗證）。不買版位。 只投一款有故事的主打 App，不要一次投 53 款。 | 否，需人工 | 不需帳號（Email） | 工具、效率、旅遊、開發工具 | B | 未驗證 |
| [Dcard](https://www.dcard.tw) | community | 站規於 2026/03/30 更新並有獨立的「廣告、商業內容規範」（存在已確認，條文未取得）：推廣受規範，只在相符看板發真實的經驗分享。 只在相符看板發真實經驗分享；先讀 2026/03 的廣告規範。 | 否，需人工 | 以信箱／手機／Apple／Google 註冊（未驗證） | 親子、教育、效率、旅遊 | B | 部分佐證 |
| [PTT (iOS / Soft_Job / topic boards)](https://www.ptt.cc/bbs/iOS/index.html) | community | 各板置頂版規各自不同，許多板禁止廣告或要加分類標籤；版規本次未能取得——先讀置頂並問板主。 先讀置頂版規；許多板禁廣告。 | 否，需人工 | 需信箱認證，新帳號有發文限制（未驗證） | 工具、效率、開發工具 | B | 未驗證 |
| [Mobile01](https://www.mobile01.com) | community | 有手機／App 相關討論區；廣告規定依版而異（未取得）。 規則確認前優先度低。 | 否，需人工 | 會員帳號（未驗證） | 工具、效率、旅遊 | C | 未驗證 |

## 香港 (HK)

市場小、管道類似台灣但用香港用語；論壇對廣告敏感。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Threads](https://www.threads.net) | social | 可發自家 App 貼文，但重複、連續帶連結會被限流或停權（舊帳號曾因一天 30–48 則帶連結被停）。每天最多 1–3 則、內容不重複、連結放留言或簡介。 用香港用語（非台灣用語）。 | 是（可全自動） | 需 Instagram/Meta 帳號；人工一次性建立 Meta 開發者 App 並取得 token（60 天需續期）；Meta 註冊可能要求手機驗證（未驗證） | 全部 | A | 部分佐證 |
| [Facebook groups (local)](https://www.facebook.com/groups/) | community | 每個社團各有規則，多數要管理員核准推廣貼文。先讀規則、先問管理員、每個社團只發一次、不可洗版。 香港親子／旅遊／iPhone 社團；需管理員同意。 | 否，需人工 | 真實 Facebook 帳號；每個社團需管理員同意 | 親子、教育、工具、旅遊 | B | 未驗證 |
| [unwire.hk](https://unwire.hk) | review-site submission | 香港科技媒體；透過編輯／聯絡管道投稿；政策未取得。不買版位。 Email 投一款主打 App。 | 否，需人工 | 不需帳號（Email） | 工具、效率、旅遊、開發工具 | B | 未驗證 |
| [LIHKG](https://lihkg.com) | community | 強烈反廣告文化；條款未取得。若發，僅限低調的真實分享。 只做低調真實分享；被反感風險高。 | 否，需人工 | 信箱註冊（過去曾有邀請／驗證機制；未驗證） | 工具、開發工具 | C | 未驗證 |
| [HKEPC forum](https://www.hkepc.com) | community | 硬體／電子產品論壇，有 App 區；自薦規則未取得。 先確認論壇規則。 | 否，需人工 | 會員帳號（未驗證） | 工具、開發工具 | C | 未驗證 |

## 日本 (JP)

開發者部落格（Zenn／Qiita）是唯一可全自動的在地管道；觸及主要靠 X。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [X (Twitter)](https://x.com) | social | 可發文；禁止垃圾／重複貼文，自動帳號需標示。手動發文免費。 日本觸及最高的管道；手動發文（免費），用 #個人開発 / #buildinpublic。自動發文要付費。 | 是，但要付費 | 新帳號通常需手機驗證（未驗證） | 全部 | A | 部分佐證 |
| [Zenn](https://zenn.dev) | blog platform | 以技術／知識文章為主；「個人開発」心得文很常見，單薄的廣告不受歡迎（規約原文未取得）。 「作ってみた」心得文，GitHub push 即發布；可全自動。 | 是（可全自動） | GitHub 登入；不需手機 | 開發工具、效率、工具 | A | 部分佐證 |
| [note](https://note.com) | blog platform | 可介紹自己的產品；業配／隱性廣告須揭露（一般條款，未取得原文）。 故事型文章，最適合非開發者向 App；需人工發。 | 否，需人工 | 信箱／Apple／Google 註冊（未驗證是否需手機） | 工具、效率、親子、教育、旅遊 | A | 未驗證 |
| [Qiita](https://qiita.com) | blog platform | 以技術文章為主，純廣告／公關稿不受歡迎（規約原文未取得）；在有技術內容的文章中介紹自己的工具是常態；必須加標籤。 必須有技術切角；可用 API v2 自動。 | 是（可全自動） | 信箱／GitHub 註冊；未見手機要求（未驗證） | 開發工具、效率、工具 | B | 部分佐證 |
| [Hatena Blog / Hatena Bookmark](https://hatenablog.com) | blog platform | 可發自家產品文章；はてなブックマーク只能自然累積，不可拉票。 可選；AtomPub API 未驗證。 | 是（可全自動） | Hatena ID（信箱）（未驗證） | 開發工具、效率、工具 | C | 未驗證 |
| [Japanese app-review sites (AppBank, gori.me, iPhone Mania, Appliv etc.)](https://www.appbank.net) | review-site submission | 歷史上 AppBank 會自行購買 App 後評測，Applis／AnytenApps 等免費收錄服務多為舊資料、可能已停止；目前受理狀況未驗證——走各站聯絡表單、誠實投稿、不付費。 只能走聯絡表單；是否受理未驗證。 | 否，需人工 | 不需帳號（表單／Email） | 工具、親子、教育、旅遊 | C | 未驗證 |

## 南韓 (KR)

沒有可 API 自動的在地管道，全部需人工用韓文發。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Clien (클리앙) - 아이포니언 / 직접홍보](https://www.clien.net/service/board/cm_iphonien) | community | 自製 App 在需要說明內容時可發；附帶營收連結或明顯營利的貼文可能被刪並限制帳號；有「직접홍보」自薦板；2026/7 會員正在討論把自製 App 文章獨立成板（搜尋佐證）。 發在「아이포니언」或「직접홍보」板，揭露自己是開發者，不放營利連結。 | 否，需人工 | 需 Clien 會員，新會員可能有發文限制（未驗證） | 工具、效率、開發工具、旅遊 | A | 部分佐證 |
| [Naver Blog / Naver Cafe](https://blog.naver.com) | blog platform | 可介紹自己的產品；業配須揭露。Cafe 依各 Cafe 規則（需先加入）。 韓國主要搜尋入口；寫韓文文章，不能自動發。 | 否，需人工 | Naver ID 通常需手機認證（未驗證）；用本人手機即可 | 工具、效率、親子、教育、旅遊 | A | 部分佐證 |
| [Disquiet (디스콰이엇)](https://disquiet.io) | community | 韓國的 maker／產品發表社群（類似 Product Hunt）；規則未取得。 Maker 產品發表社群；規則未驗證，先確認。 | 否，需人工 | 社群帳號登入（未驗證） | 工具、效率、開發工具 | B | 未驗證 |
| [GeekNews (news.hada.io) - Show GN](https://news.hada.io) | community | 韓國版 Hacker News 風格的彙整站，有 Show GN 供自己的專案（來自背景知識；規則未取得）。 開發工具 App 用 Show GN。 | 否，需人工 | 需帳號（未驗證） | 開發工具 | B | 未驗證 |
| [Velog](https://velog.io) | blog platform | 開發者部落格平台；有內容的專案文章可（未取得原文）。 僅限開發工具心得。 | 否，需人工 | GitHub／Google 登入 | 開發工具 | C | 未驗證 |

## 美國 (US)

發表平台最重要；全部需人工發。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Product Hunt](https://www.producthunt.com) | directory | 本來就是讓作者發表自己的產品（免費、每次發表一次）；禁止拉票／灌評論，發表當天需親自回覆留言（背景知識，官方頁面未取得）。 一款 App 發表一次；先選最強的 2–3 款，不拉票。 | 否，需人工 | 信箱／Google／X 帳號並完整個人檔案；新帳號可能受限（未驗證） | 全部 | A | 部分佐證 |
| [Hacker News - Show HN](https://news.ycombinator.com/showhn.html) | community | Show HN 限「自己做、別人可以試用」的作品；作者要留言互動；禁止拉票。純 iOS App 若難以試用屬邊緣（官方規範頁未取得）。 只限開發工具 App；需容易試用。 | 否，需人工 | 免費帳號，不需手機／邀請；全新帳號帶推廣連結可能被標記（未驗證） | 開發工具 | A | 部分佐證 |
| [Reddit r/SideProject](https://www.reddit.com/r/SideProject/) | community | 第三方整理稱其歡迎自薦且有每週分享串，但要回饋他人專案；子版規則原文未取得，發文前先讀側欄。 故事先行、附截圖；留言要互動。 | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號（信箱，不需手機）；子版常有帳齡／karma 門檻；只能用一個帳號 | 全部 | A | 部分佐證 |
| [Reddit r/iOSProgramming (App Saturday)](https://www.reddit.com/r/iOSProgramming/) | community | 只能在「App Saturday」（週六，以發文者當地時間）發，同一款 App 一年一次（版主 2025/4 公告）；2026/1 的提案要求最低 karma＋固定模板（技術堆疊、挑戰、AI 揭露），是否實施未確認——先讀置頂規則。 只能在 App Saturday，每款一年一次；先讀置頂。 | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號；可能有 karma 門檻（未確認） | 開發工具、效率、工具 | B | 部分佐證 |
| [Indie Hackers](https://www.indiehackers.com) | community | 歡迎有內容的文章（做了什麼、學到什麼）並在脈絡中附產品連結；只丟連結會被忽略或刪除（第三方整理）。 「53 款 App × 50 語言」的 build-in-public 故事很契合。 | 否，需人工 | 信箱／Google／X 註冊；不需手機（未驗證） | 全部 | B | 部分佐證 |
| [AlternativeTo](https://alternativeto.net) | directory | 免費、社群審核式投稿；App 必須是既有軟體的真正替代品；內容會被審核。 只投真的是既有軟體替代品的 App。 | 否，需人工 | 免費帳號 | 工具、效率、開發工具 | B | 部分佐證 |

## 英國 (UK)

未找到英國專屬 App 探索管道；沿用美國的發表。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Product Hunt](https://www.producthunt.com) | directory | 本來就是讓作者發表自己的產品（免費、每次發表一次）；禁止拉票／灌評論，發表當天需親自回覆留言（背景知識，官方頁面未取得）。 與美國同一次發表；想要英國觸及可排英國早上。 | 否，需人工 | 信箱／Google／X 帳號並完整個人檔案；新帳號可能受限（未驗證） | 全部 | A | 部分佐證 |
| [Hacker News - Show HN](https://news.ycombinator.com/showhn.html) | community | Show HN 限「自己做、別人可以試用」的作品；作者要留言互動；禁止拉票。純 iOS App 若難以試用屬邊緣（官方規範頁未取得）。 同美國。 | 否，需人工 | 免費帳號，不需手機／邀請；全新帳號帶推廣連結可能被標記（未驗證） | 開發工具 | A | 部分佐證 |
| [Reddit r/iOSProgramming (App Saturday)](https://www.reddit.com/r/iOSProgramming/) | community | 只能在「App Saturday」（週六，以發文者當地時間）發，同一款 App 一年一次（版主 2025/4 公告）；2026/1 的提案要求最低 karma＋固定模板（技術堆疊、挑戰、AI 揭露），是否實施未確認——先讀置頂規則。 同樣是 App Saturday 規則。 | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號；可能有 karma 門檻（未確認） | 開發工具、效率、工具 | B | 部分佐證 |
| [Bluesky](https://bsky.app) | social | 可發自家專案；自動化需不洗版（建議標示為機器人、不主動 @ 陌生人）——政策原文未取得。 開發者／科技受眾；可 API 自動。 | 是（可全自動） | 信箱驗證；不需手機／邀請碼（未驗證） | 開發工具、效率、工具 | B | 部分佐證 |
| [Indie Hackers](https://www.indiehackers.com) | community | 歡迎有內容的文章（做了什麼、學到什麼）並在脈絡中附產品連結；只丟連結會被忽略或刪除（第三方整理）。 同美國。 | 否，需人工 | 信箱／Google／X 註冊；不需手機（未驗證） | 全部 | B | 部分佐證 |
| [UK tech press (Stuff, Pocket-lint, TechRadar)](https://www.stuff.tv) | review-site submission | 僅能 Email 向編輯提案；未取得投稿頁；不買評測。 成功率低，僅 Email。 | 否，需人工 | 不需帳號（Email） | 工具、效率、旅遊 | C | 未驗證 |

## 德國 (DE)

德語評測站：只能無償投稿（iphone-ticker 聲明不販售評測）。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [iphone-ticker.de](https://www.iphone-ticker.de/kontakt/) | review-site submission | 有聯絡頁；廣告頁明言不販售贈品、編輯內容或評測——只能寄無償、誠實的投稿信，不保證刊登（廣告頁已搜尋佐證）。 寄無償誠實投稿；強調隱私／無追蹤，德國讀者重視。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育、旅遊 | B | 部分佐證 |
| [appgefahren.de](https://www.appgefahren.de) | review-site submission | 德語 App 評測部落格；受理方式未取得——用聯絡表單誠實投稿。 走聯絡表單；先備好德文商店文案。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育、旅遊 | B | 未驗證 |
| [Mastodon (per-instance)](https://docs.joinmastodon.org/methods/statuses/) | social | 規則依各 instance 而定；多數允許偶爾分享自己的專案，自動帳號多半要勾選 bot 旗標。 德語 instance（逐一確認規則）；可 API 自動。 | 是（可全自動） | 依 instance：信箱驗證，部分需人工審核；不需手機 | 開發工具、效率、工具 | B | 部分佐證 |
| [Apfeltalk](https://www.apfeltalk.de) | community | 德語 Apple 論壇；自薦規則未取得——先查 App 區版規。 先查 App 區版規。 | 否，需人工 | 論壇帳號（未驗證） | 工具、效率、親子 | C | 未驗證 |
| [t3n](https://t3n.de) | review-site submission | 德國數位／科技雜誌；編輯投稿管道未取得。 投稿管道未驗證。 | 否，需人工 | 不需帳號（Email） | 開發工具、效率 | C | 未驗證 |

## 法國 (FR)

法國媒體管道多半未驗證，信心低。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Korben.info](https://korben.info) | review-site submission | 影響力大的法語科技部落格，常介紹工具；透過聯絡管道投稿（未取得）。 有明確賣點的工具再投。 | 否，需人工 | 不需帳號（Email） | 開發工具、工具、效率 | B | 未驗證 |
| [MacG / iGeneration](https://www.macg.co) | review-site submission | 法語 Apple 新聞站；編輯投稿管道未取得。 Email 投稿；先備好法文商店文案。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育、旅遊 | B | 未驗證 |
| [iPhoneSoft](https://www.iphonesoft.fr) | review-site submission | 法語 iPhone 新聞站；編輯投稿管道未取得。 Email 投稿。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育、旅遊 | B | 未驗證 |
| [Journal du Geek](https://www.journaldugeek.com) | review-site submission | 搜尋未找到現行投稿管道（僅 2007 年徵稿舊文）；走聯絡頁，成功率低。 成功率低。 | 否，需人工 | 不需帳號（Email） | 工具、效率、旅遊 | C | 部分佐證 |
| [Developpez.com](https://www.developpez.com) | community | 法語開發者社群／論壇；自薦規則未取得——僅適合有技術切角的開發工具 App。 僅限有技術切角的開發工具 App。Frandroid 以 Android 為主，故不列入。 | 否，需人工 | 論壇帳號（未驗證） | 開發工具 | C | 未驗證 |
| [Mastodon (per-instance)](https://docs.joinmastodon.org/methods/statuses/) | social | 規則依各 instance 而定；多數允許偶爾分享自己的專案，自動帳號多半要勾選 bot 旗標。 法語 instance；可 API 自動。 | 是（可全自動） | 依 instance：信箱驗證，部分需人工審核；不需手機 | 開發工具、效率、工具 | C | 部分佐證 |

## 西班牙 (ES)

西語媒體管道多半未驗證；西語內容可同時服務墨西哥／拉美。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Applesfera](https://www.applesfera.com) | review-site submission | 西語 Apple 新聞站；頁尾有「Contacta con nosotros」（已確認）；是否受理獨立 App 未驗證。 聯絡連結已確認；投一款 App。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育、旅遊 | B | 部分佐證 |
| [Xataka / Genbeta (Webedia)](https://www.genbeta.com) | review-site submission | 西語科技／開發媒體（Genbeta 專談 App 與開發）；投稿管道未取得。 Genbeta 專談開發與 App。 | 否，需人工 | 不需帳號（Email） | 開發工具、工具、效率 | B | 未驗證 |
| [DEV Community](https://dev.to) | blog platform | 自家專案文章可發，但須有實質內容（開發心得／教學），不能純廣告；適用 DEV 行為準則（來自背景知識）。 用西語寫；可 API 自動。 | 是（可全自動） | GitHub／信箱註冊；不需手機或邀請 | 開發工具 | B | 部分佐證 |
| [iPadizate](https://www.ipadizate.es) | review-site submission | 西語 iOS 部落格；受理方式未取得。 受理方式未驗證。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育 | C | 未驗證 |
| [Menéame](https://www.meneame.net) | community | 西語社群新聞站；一般不歡迎自推連結、可能被扣分（未驗證）——只投真正有新聞價值的文章。 只投真正有新聞價值的文章。 | 否，需人工 | 需帳號（未驗證） | 工具、效率、開發工具 | C | 未驗證 |

## 巴西 (BR)

驗證最完整的市場之一：TabNews 規則與 MacMagazine 受理皆已確認。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [TabNews](https://www.tabnews.com.br/faq) | community | 可發自己的專案，但需帶來價值（技術細節、心得）；短篇宣傳標題要加「Pitch」；純商業貼文明禁；不可重發相同內容；刪除被倒讚的文再重發可能被永久停權（FAQ／條款搜尋佐證）。 短宣傳標題加「Pitch」，否則寫真實開發故事；不可重發。 | 否，需人工 | 信箱註冊；未見手機／邀請要求（未驗證） | 開發工具、工具、效率 | A | 部分佐證 |
| [MacMagazine (Contato)](https://macmagazine.com.br/contato/) | review-site submission | 聯絡表單明列接受「新聞線索、App 建議、開發者聯絡」；僅在必要時回覆（搜尋佐證）。 表單明確接受開發者的 App 建議。 | 否，需人工 | 不需帳號（表單） | 工具、效率、親子、教育、旅遊 | A | 搜尋佐證 |
| [DEV Community](https://dev.to) | blog platform | 自家專案文章可發，但須有實質內容（開發心得／教學），不能純廣告；適用 DEV 行為準則（來自背景知識）。 用巴西葡語寫；可 API 自動。 | 是（可全自動） | GitHub／信箱註冊；不需手機或邀請 | 開發工具 | B | 部分佐證 |
| [Reddit r/brdev](https://www.reddit.com/r/brdev/) | community | 巴西開發者子版；自薦規則未取得。 規則未驗證。 | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號 | 開發工具、效率、工具 | C | 未驗證 |
| [Tecnoblog](https://tecnoblog.net) | review-site submission | 巴西科技新聞；投稿管道未取得。 投稿管道未驗證。 | 否，需人工 | 不需帳號（Email） | 工具、效率、旅遊 | C | 未驗證 |

## 墨西哥 (MX)

已驗證的在地管道少；以西語 Threads／Facebook 社團為主。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Threads](https://www.threads.net) | social | 可發自家 App 貼文，但重複、連續帶連結會被限流或停權（舊帳號曾因一天 30–48 則帶連結被停）。每天最多 1–3 則、內容不重複、連結放留言或簡介。 用墨西哥西語；可 API 自動。 | 是（可全自動） | 需 Instagram/Meta 帳號；人工一次性建立 Meta 開發者 App 並取得 token（60 天需續期）；Meta 註冊可能要求手機驗證（未驗證） | 全部 | A | 部分佐證 |
| [Xataka México](https://www.xataka.com.mx) | review-site submission | Xataka 墨西哥版；投稿管道未取得。 投稿管道未驗證。 | 否，需人工 | 不需帳號（Email） | 工具、效率、親子、教育、旅遊 | B | 未驗證 |
| [Facebook groups (local)](https://www.facebook.com/groups/) | community | 每個社團各有規則，多數要管理員核准推廣貼文。先讀規則、先問管理員、每個社團只發一次、不可洗版。 教師／家長／旅遊社團；需管理員同意。 | 否，需人工 | 真實 Facebook 帳號；每個社團需管理員同意 | 親子、教育、工具、旅遊 | B | 未驗證 |
| [X (Twitter)](https://x.com) | social | 可發文；禁止垃圾／重複貼文，自動帳號需標示。手動發文免費。 手動發文（API 要付費）。 | 是，但要付費 | 新帳號通常需手機驗證（未驗證） | 工具、效率、開發工具、旅遊 | B | 部分佐證 |
| [DEV Community](https://dev.to) | blog platform | 自家專案文章可發，但須有實質內容（開發心得／教學），不能純廣告；適用 DEV 行為準則（來自背景知識）。 西語；可 API 自動。 | 是（可全自動） | GitHub／信箱註冊；不需手機或邀請 | 開發工具 | C | 部分佐證 |

## 印尼 (ID)

以 Facebook 為主；在台移工切入點可連動台灣宣傳。在地論壇規則未驗證。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Facebook groups (local)](https://www.facebook.com/groups/) | community | 每個社團各有規則，多數要管理員核准推廣貼文。先讀規則、先問管理員、每個社團只發一次、不可洗版。 印尼社團，含在台移工與教師社團；需管理員同意。 | 否，需人工 | 真實 Facebook 帳號；每個社團需管理員同意 | 親子、教育、工具、旅遊 | A | 未驗證 |
| [Threads](https://www.threads.net) | social | 可發自家 App 貼文，但重複、連續帶連結會被限流或停權（舊帳號曾因一天 30–48 則帶連結被停）。每天最多 1–3 則、內容不重複、連結放留言或簡介。 用印尼文；可 API 自動。 | 是（可全自動） | 需 Instagram/Meta 帳號；人工一次性建立 Meta 開發者 App 並取得 token（60 天需續期）；Meta 註冊可能要求手機驗證（未驗證） | 全部 | A | 部分佐證 |
| [Kaskus](https://www.kaskus.co.id) | community | 印尼大型論壇，有科技／App 區；自薦與商業規定未取得（廣告／販售常被限制在專區）。 先查分區規則；不得在非許可區域放廣告。 | 否，需人工 | 信箱／手機驗證（未驗證） | 工具、效率、旅遊 | B | 未驗證 |
| [Dicoding community](https://www.dicoding.com) | community | 印尼主要的開發者教育／社群；規則未取得——僅適合開發工具 App。 僅限開發工具 App。 | 否，需人工 | 需帳號（未驗證） | 開發工具 | C | 未驗證 |
| [Kompasiana](https://www.kompasiana.com) | blog platform | Kompas 旗下開放式公民部落格；推廣內容會被審核（未取得原文）。 故事型部落格；會被審核。 | 否，需人工 | 需帳號（未驗證） | 親子、教育、工具、旅遊 | C | 未驗證 |

## 越南 (VN)

以 Facebook 為主；在地論壇／部落格規則未驗證（搜尋無可用結果）。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Facebook groups (local)](https://www.facebook.com/groups/) | community | 每個社團各有規則，多數要管理員核准推廣貼文。先讀規則、先問管理員、每個社團只發一次、不可洗版。 越南社團，含在台移工；需管理員同意。 | 否，需人工 | 真實 Facebook 帳號；每個社團需管理員同意 | 親子、教育、工具、旅遊 | A | 未驗證 |
| [Tinhte.vn](https://tinhte.vn) | community | 越南最大科技論壇，有 App 區；廣告規定未取得（預期反洗版嚴格）。 App 區；先讀規則。 | 否，需人工 | 需帳號（未驗證） | 工具、效率、旅遊 | B | 未驗證 |
| [Viblo](https://viblo.asia) | blog platform | 越南技術知識分享平台，使用者可發文（已確認，Sun*）；自薦規則未取得——寫技術心得而非廣告。 寫技術心得而非廣告。 | 否，需人工 | 信箱／GitHub 註冊（未驗證） | 開發工具 | B | 部分佐證 |
| [Spiderum](https://spiderum.com) | blog platform | 越南綜合型部落格平台；推廣規則未取得。 故事型文章。 | 否，需人工 | 需帳號（未驗證） | 親子、教育、效率 | C | 未驗證 |
| [Threads](https://www.threads.net) | social | 可發自家 App 貼文，但重複、連續帶連結會被限流或停權（舊帳號曾因一天 30–48 則帶連結被停）。每天最多 1–3 則、內容不重複、連結放留言或簡介。 用越南文；可 API 自動。 | 是（可全自動） | 需 Instagram/Meta 帳號；人工一次性建立 Meta 開發者 App 並取得 token（60 天需續期）；Meta 註冊可能要求手機驗證（未驗證） | 全部 | B | 部分佐證 |

## 泰國 (TH)

以 Facebook 與 Threads 為主；在地媒體管道未驗證。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Facebook groups (local)](https://www.facebook.com/groups/) | community | 每個社團各有規則，多數要管理員核准推廣貼文。先讀規則、先問管理員、每個社團只發一次、不可洗版。 泰國 Facebook 為主流；需管理員同意。 | 否，需人工 | 真實 Facebook 帳號；每個社團需管理員同意 | 親子、教育、工具、旅遊 | A | 未驗證 |
| [Threads](https://www.threads.net) | social | 可發自家 App 貼文，但重複、連續帶連結會被限流或停權（舊帳號曾因一天 30–48 則帶連結被停）。每天最多 1–3 則、內容不重複、連結放留言或簡介。 用泰文；可 API 自動。 | 是（可全自動） | 需 Instagram/Meta 帳號；人工一次性建立 Meta 開發者 App 並取得 token（60 天需續期）；Meta 註冊可能要求手機驗證（未驗證） | 全部 | A | 部分佐證 |
| [Blognone](https://www.blognone.com) | review-site submission | 泰國科技新聞站；有讀者投稿新聞的管道（背景知識，未驗證）。 新聞投稿管道未驗證。 | 否，需人工 | 帳號／Email（未驗證） | 工具、效率、開發工具 | B | 未驗證 |
| [Pantip](https://pantip.com) | community | 泰國最大論壇；商業貼文通常受限（未取得）——只在相符討論室發真實的提問／心得。 只在相符討論室發真實提問／心得。 | 否，需人工 | 需帳號；可能要手機驗證（未驗證） | 工具、親子、教育、旅遊 | C | 未驗證 |

## 印度 (IN)

以英文開發者社群為主；iOS 占比小，投入宜低。

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Product Hunt](https://www.producthunt.com) | directory | 本來就是讓作者發表自己的產品（免費、每次發表一次）；禁止拉票／灌評論，發表當天需親自回覆留言（背景知識，官方頁面未取得）。 PH 上印度 maker 社群大；但印度 iOS 市占小。 | 否，需人工 | 信箱／Google／X 帳號並完整個人檔案；新帳號可能受限（未驗證） | 全部 | A | 部分佐證 |
| [Hashnode](https://hashnode.com) | blog platform | 可發自家專案文章，需有實質內容；純廣告會被移除（背景知識）。 印度開發者讀者多；可 API 自動。 | 是（可全自動） | 信箱／GitHub／Google 註冊；不需手機 | 開發工具 | B | 部分佐證 |
| [DEV Community](https://dev.to) | blog platform | 自家專案文章可發，但須有實質內容（開發心得／教學），不能純廣告；適用 DEV 行為準則（來自背景知識）。 可 API 自動。 | 是（可全自動） | GitHub／信箱註冊；不需手機或邀請 | 開發工具 | B | 部分佐證 |
| [Reddit r/developersIndia](https://www.reddit.com/r/developersIndia/) | community | 嚴格限制自我推廣；每月「Showcase Sunday」置頂串可展示 App／工具／進行中專案；以連結開頭、像廣告的貼文會被移除（搜尋佐證）。 只能發在每月 Showcase Sunday 置頂串。 | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號 | 開發工具、效率、工具 | B | 搜尋佐證 |
| [Peerlist (Launchpad)](https://peerlist.io) | community | 印度出身的專業人士網路，有每週專案發表；搜尋未找到資料——規則未驗證。 每週發表；未驗證。 | 否，需人工 | LinkedIn／GitHub／Google 登入（未驗證） | 開發工具、效率、工具 | B | 未驗證 |
| [X (Twitter)](https://x.com) | social | 可發文；禁止垃圾／重複貼文，自動帳號需標示。手動發文免費。 手動發文。 | 是，但要付費 | 新帳號通常需手機驗證（未驗證） | 開發工具、效率、工具 | C | 部分佐證 |

## 全球共用管道

| 管道 | 類型 | 自薦規則／備註 | 官方 API 自動發文 | 帳號門檻 | 適合 | 優先 | 驗證 |
|---|---|---|---|---|---|---|---|
| [Apple App Store featuring nomination](https://developer.apple.com/help/app-store-connect/manage-featuring-nominations/nominate-your-app-for-featuring) | directory | App Store Connect 內的免費提名表單（新 App、新內容、重大更新）；需 Account Holder／Admin／App Manager／Marketing 角色；要提前提交（3 週／3 個月為第三方說法）。注意：growth README 把 App Store Connect 排除在範圍外，需人工決定。  | 否，需人工 | Apple 開發者帳號且具備合格角色 | 全部 | - | 搜尋佐證 |
| [Bluesky](https://bsky.app) | social | 可發自家專案；自動化需不洗版（建議標示為機器人、不主動 @ 陌生人）——政策原文未取得。  | 是（可全自動） | 信箱驗證；不需手機／邀請碼（未驗證） | 全部 | - | 部分佐證 |
| [Mastodon (per-instance)](https://docs.joinmastodon.org/methods/statuses/) | social | 規則依各 instance 而定；多數允許偶爾分享自己的專案，自動帳號多半要勾選 bot 旗標。  | 是（可全自動） | 依 instance：信箱驗證，部分需人工審核；不需手機 | 全部 | - | 部分佐證 |
| [X (Twitter)](https://x.com) | social | 可發文；禁止垃圾／重複貼文，自動帳號需標示。手動發文免費。  | 是，但要付費 | 新帳號通常需手機驗證（未驗證） | 全部 | - | 部分佐證 |
| [DEV Community](https://dev.to) | blog platform | 自家專案文章可發，但須有實質內容（開發心得／教學），不能純廣告；適用 DEV 行為準則（來自背景知識）。  | 是（可全自動） | GitHub／信箱註冊；不需手機或邀請 | 全部 | - | 部分佐證 |
| [Hashnode](https://hashnode.com) | blog platform | 可發自家專案文章，需有實質內容；純廣告會被移除（背景知識）。  | 是（可全自動） | 信箱／GitHub／Google 註冊；不需手機 | 全部 | - | 部分佐證 |
| [Telegram channel (own)](https://core.telegram.org/bots/api) | social | 自己的頻道：沒有限制但自然曝光低（repo README 顯示已有每日自動貼文）。  | 是（可全自動） | 建立 Telegram 帳號時需手機一次 | 全部 | - | 部分佐證 |
| [Facebook Page (own)](https://developers.facebook.com/docs/pages-api/) | social | 自己的粉專：免費，適用一般 Meta 社群守則。  | 是（可全自動） | Facebook 帳號＋Meta 開發者 App（人工一次性） | 全部 | - | 未驗證 |
| [Reddit r/iosapps](https://www.reddit.com/r/iosapps/) | community | 規則未取得——發文前務必先讀側欄。  | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號 | 全部 | - | 未驗證 |
| [Reddit r/AppHookup](https://www.reddit.com/r/AppHookup/) | community | 只限優惠（降價、免費、兌換碼）；必須走 App Store 內購（不接受 RevenueCat/Adapty 發放的權益）；App Store 兌換碼可（來源為規則鏡像頁，2024/6、2025/11）。  | 否（Reddit API 需審核，實務上人工發） | Reddit 帳號 | 全部 | - | 部分佐證 |
| [BetaList](https://betalist.com/submit) | directory | 免費排隊（2025 年的整理稱約 2 個月）或付費 $130 加速（預算為零，不付）；定位是上市前新創，對已上架的工具 App 契合度低。  | 否，需人工 | 免費帳號 | 全部 | - | 部分佐證 |

驗證說明：搜尋佐證＝搜尋結果直接支持；部分佐證＝只佐證部分內容或僅有第三方來源；未驗證＝只有背景知識。優先 A＝觸及高＋平台允許＋適合；B／C 依序遞減。資料機器可讀版：`channels-by-country.json`。
