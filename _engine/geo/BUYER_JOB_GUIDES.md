# Evidence-bound buyer job guides

An additive first-party surface for nine apps outside the eleven-app conversion
route contract. It does not change ASC, App code, the catalog's **47 apps × 50
locales**, or its **13 paid-download / 34 freemium** model split.

## Sources and rebuilding

- `data/buyer_job_guides_v1.json`: stable App IDs, jobs, exclusions, related jobs.
- `data/buyer_job_copy_en-US.json` and `buyer_job_copy_zh-Hant.json`: complete,
  separately authored buyer guidance and purchase boundaries. No locale fallback.
- `data/buyer_job_evidence_v1.json`: dated public Apple lookup and screenshot GET
  receipts. Screenshots demonstrate published interfaces, not independently
  tested output files, learning gains, savings, or security certifications.
- `buyer_job_guides.py`: deterministic HTML, Markdown, RSS, JSON Feed, source
  manifest, and one Dev.to article candidate. It reuses existing `pt`/`ct` links.

```sh
GEO_PAGES=/path/to/ios-app-guide python3 geo/buyer_job_guides.py
GEO_PAGES=/path/to/ios-app-guide python3 geo/buyer_job_guides.py --check
```

The normal all-locale `gen_app_page_related.py` pass invokes this producer after
its existing links. Only the selected apps' English and Traditional Chinese
detail pages receive a separately owned backlink block. The new surface is
`buyer-guides/`; the existing decision-route namespace is not touched.

The source must be mirrored byte-for-byte to the Guide repository's `_engine/geo`
copy. Source and Guide feature branches are reviewed together; no `main` push,
deployment, or social publication is implied by materialization.
The Daily GEO initial, fast, localized, and rebase paths reseal authored bytes.
The separately owned conversion/deployment workflow is not modified here.

## Truth and publication

Paid downloads cannot gain free-trial or in-app-unlock copy. Freemium entries
must name both their usable free core and optional one-time unlock. Current local
prices remain on Apple's purchase interface, not hardcoded into guides or schema.
FAQ structured data uses the same answers as the visible page.

`.github/scripts/devto_buyer_job_articles.json` is a generated candidate, not a
publication receipt. The Dev.to publisher script must verify the **exact
canonical HTML digest** before accepting it, preserve its 72-hour cadence, and
deduplicate by title or canonical URL. Do not run a second local publisher.
GET success, a screenshot, and publication are not evidence of impressions,
attributed downloads, purchases, or causal lift.

## Buyer-only independent publication

`traffic_scope=buyer_decision_only` requires every title and query to name the
app and a buying/unlock decision. Each app also declares excluded general
information intents. Purchase summaries and the model-specific App Store CTA
remain distinct for paid downloads and freemium apps. The real published
interface image precedes the purchase action in HTML and Markdown; narrow
screens retain one reachable purchase action rather than adding duplicate CTAs.

The standalone exporter is used by the existing `awesome-ios-pay-once` topical
repository, without updating the shared conversion deployment or gitlink:

```sh
GEO_SITE=https://alice51849.github.io/awesome-ios-pay-once \
  python3 geo/buyer_job_guides.py --standalone \
  --catalog-pages /read-only/portfolio --pages /independent/site
```

The catalog input and output must be different directories. Standalone output
does not patch portfolio App pages or create a Dev.to queue; original App detail
and publisher links retain their original owner. The independent repository
ships the same source/data, a public catalog snapshot with its digest, tests,
source-managed README links, and a Pages workflow that deploys only its `docs/`.
