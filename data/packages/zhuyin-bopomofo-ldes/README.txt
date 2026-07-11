Bopomofo LDES 1.0 + TREE event stream
========================================

Canonical entry point
---------------------
https://alice51849.github.io/ios-app-guide/data/packages/zhuyin-bopomofo-ldes/bopomofo-event-stream.jsonld

The entry point is both the ldes:EventStream and the mutable TREE root node.
It has exactly one tree:view pointing to itself and six typed relations: paired
inclusive lower and exclusive upper time bounds for each of three immutable
JSON-LD member nodes.

Member model
------------
- 37 immutable member IRIs
- ldes:timestampPath = dcterms:created
- ldes:versionOfPath = dcterms:isVersionOf
- ldes:versionCreatePath = rdf:type
- ldes:versionCreateObject = https://alice51849.github.io/ios-app-guide/data/packages/zhuyin-bopomofo-ldes/#BopomofoSymbolVersion
- each event links one stable SKOS concept and carries the canonical CSV fields

Consumption
-----------
1. Dereference bopomofo-event-stream.jsonld.
2. Confirm one tree:view and read the LDES context.
3. Follow each tree:relation/tree:node link that cannot be pruned.
4. Extract objects of tree:member from the event-stream IRI.
5. Verify each member against bopomofo-event-member.shacl.ttl.
6. Persist member IRIs so each immutable event is emitted only once.

Static-hosting note
-------------------
The Turtle file is a discovery overview whose tree:view links to the canonical
JSON-LD root. Node pages declare ldes:immutable true inside RDF. This host does
not claim content negotiation or custom Cache-Control headers.

Specifications
--------------
LDES 1.0: https://semiceu.github.io/LinkedDataEventStreams/releases/1.0.0/
LDES server primer: https://semiceu.github.io/LinkedDataEventStreams/releases/1.0.0/server-primer.html
TREE: https://w3id.org/tree/specification
SHACL: https://www.w3.org/TR/shacl/

Limits
------
This publisher-authored snapshot does not claim registry listing, external
replication, certification, institutional endorsement or LDES/TREE community
endorsement.

繁體中文
--------
此靜態事件流以三個 immutable JSON-LD node 發布完整 37 個注音符號的第一版
事件。請從 canonical JSON-LD entry point 開始，沿成對時間上下界 relation
走訪 node，檢查 tree:member、dcterms:created、dcterms:isVersionOf 與 SHACL
shape，並使用 checksums-sha256.txt 驗證下載 bytes。
