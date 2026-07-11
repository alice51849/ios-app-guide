Bopomofo 37-Symbol METS 2.0 + PREMIS 3.0 Package
======================================================

This static transfer package describes the complete 37-symbol Bopomofo dataset
with a METS 2.0 file inventory and structure map plus PREMIS 3.0 preservation
Objects, fixity, Events, Agents and Rights.

Guide: https://alice51849.github.io/ios-app-guide/data/packages/zhuyin-bopomofo-mets2-premis3/
Traditional Chinese guide: https://alice51849.github.io/ios-app-guide/zh-Hant/data/packages/zhuyin-bopomofo-mets2-premis3/
METS schema: https://www.loc.gov/standards/mets/mets2.xsd
PREMIS schema: https://www.loc.gov/standards/premis/v3/premis-v3-0.xsd

Validation
----------
1. Verify checksums-sha256.txt.
2. Validate mets.xml with the pinned METS 2.0 XSD.
3. Validate premis.xml with the pinned PREMIS 3.0 XSD.
4. Confirm every METS file entry and PREMIS Object matches the local path,
   media type, byte size and SHA-256 digest.
5. Review local repository policy before ingest.

Scope and limits
----------------
The ZIP is a deterministic transfer wrapper, not a METS-defined archive format.
The package has no DOI and does not claim repository registration, external
ingest, certification, institutional endorsement or a digital signature.
Checksums provide fixity only.

繁體中文
--------
本靜態移轉套件以 METS 2.0 記錄完整 37 個注音符號資料的檔案清單與結構，
並以 PREMIS 3.0 記錄逐檔 Object、fixity、Event、Agent 與 Rights。

請先驗證 checksums-sha256.txt，再分別用固定版本的官方 XSD 驗證 mets.xml
與 premis.xml，並確認每個路徑、media type、byte size 與 SHA-256 完全一致。
ZIP 是 deterministic transfer wrapper，不是 METS 規範定義的封裝格式。本套件
沒有 DOI，也不宣稱已登錄或匯入典藏庫、通過第三方認證、獲機構背書或具有
數位簽章。
