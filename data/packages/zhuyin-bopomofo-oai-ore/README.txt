Bopomofo OAI-ORE 1.0 Resource Map
=====================================

Aggregation URI
---------------
https://open.cait518.cc/ios-app-guide/data/packages/zhuyin-bopomofo-oai-ore/bopomofo-resource-map.ore.rdf#aggregation

This URI follows the OAI-ORE no-server hash-URI pattern. Dereferencing it
removes #aggregation and retrieves the authoritative RDF/XML Resource Map.

Resource Maps
-------------
- bopomofo-resource-map.ore.rdf  application/rdf+xml
- bopomofo-resource-map.ore.ttl  text/turtle
- bopomofo-resource-map.ore.jsonld  application/ld+json

Each Resource Map has its own URI-R, describes the same URI-A and exposes the
same sixteen-member Aggregation Graph. The maps also record creator,
modification time, media type, byte size and SHA-256 for every aggregated
resource.

Validation
----------
1. Verify checksums-sha256.txt.
2. Parse each map as RDF.
3. Confirm one ore:describes triple from each URI-R to the Aggregation URI.
4. Confirm sixteen ore:aggregates objects and identical membership across maps.
5. Compare dcat:byteSize and SPDX SHA-256 values to each live resource.

Specification
-------------
Abstract Data Model: https://www.openarchives.org/ore/1.0/datamodel
Vocabulary: https://www.openarchives.org/ore/1.0/vocabulary
HTTP hash URI guidance: https://www.openarchives.org/ore/1.0/http
RDF/XML profile: https://www.openarchives.org/ore/1.0/rdfxml

Limits
------
This publisher-authored map does not claim OAI endorsement, external repository
ingest, DOI assignment, third-party certification, content negotiation or Atom
serialization conformance.

Generated: 2026-09-04T14:41:43Z

繁體中文
--------
本套件以 OAI-ORE Resource Map 描述完整 37 個注音符號資料的 16 項機器可讀
資源。Aggregation URI 採不需伺服器設定的 hash URI 模式；三份 RDF map
具有不同 URI-R，但公開相同的 Aggregation Graph。請先核對 SHA-256，再解析
RDF 並逐一比對 ore:aggregates、byte size 與來源檔案。
