# CEE owned-surface discovery

## Production asset contract

An owned asset is **first-party production content**, not a filename ending in
`-support.html` or a third-party article that happens to have our canonical URL.
For this audit, one eligible cell is one canonical App Store ID × one locale:
`47 × cs/hu/pl/ro/ru/sk/sl-SI/tr/uk/he = 470`.

These assets already exist and must be reused rather than copied:

- `data/lumi-studio-publisher-search-intent-catalog.json`: 47 × 50 publisher-authored
  task records, with localized decision context, disclosure and matching App Store
  identity. Its localized HTML views are
  `<locale>/data/lumi-studio-publisher-search-intent-catalog.html`.
- `api/v1/ios-app-catalog/locales/<locale>.json`: 47 localized app records per
  locale. A complete native app summary can be used when the task catalog's
  metadata excerpt is clipped. The record must retain the correct purchase model,
  factual Apple storefront evidence and direct campaign link.
- Existing localized task/app HTML pages are linked evidence, not additional
  independent channels. Support/privacy pages remain useful, but are not the only
  discoverable owned assets.

`owned_app_surfaces.py` generates **references and content hashes only**. It never
creates another native catalog or clones the existing app/task pages. Original
catalog generators and their localization sources remain the content owners.
Record selection is by locale, canonical app key **and App Store ID**, never by
app-name substring or URL domain alone.

## No false green

- Presence, deterministic source checks, native review and public GET readback
  are independent states. File existence never implies a native-quality PASS.
- English fallback, edition confusion, unsupported outcome claims, mismatched
  paid-upfront/freemium boundaries, broken canonical/hreflang, Hebrew RTL and
  missing sitemap evidence remain visible even when another existing record is
  usable. No price is authored or hard-coded by this discovery generator.
- Native review only counts with an exact content-bound review packet, canonical
  roster digest, GPT-6 Astra Max identity and 470 reviewed cells. Source changes
  invalidate that review rather than silently retaining a green result.
- **dev.to remains English-only and N/A for all 470 CEE cells.** It is a
  third-party channel, is excluded from the owned eligibility denominator and
  cannot supply a native receipt. An English article is neither a missing
  first-party page nor successful multilingual distribution.
- The optional audit adapter changes owned/dev.to fields only. Original
  RSS/social/GEO findings, receipts and historical artifacts are not rewritten.

## Reproduction

Run from an isolated Growth worktree with its matching Guide source tree:

```sh
python3 geo/owned_app_surfaces.py \
  --pages /path/to/isolated/guide \
  --output /path/to/isolated/guide/data/owned-app-surfaces-cee.json \
  --review-packet /path/to/session/files/owned-native-review-packet.json
```

After independent native review, pass `--review <content-bound-receipt.json>`.
`--check` verifies reproducibility without rewriting the discovery output.
`--audit-source` and `--audit-output` may create a new audit revision while
preserving the original CEE artifacts. No ASC request, App mutation, RSS/feed
write, social publishing or model API call is performed by this command.

Public GET readback is separate (`--readback-output`). Full source bytes must
match for the selected JSON records and their identity/disclosure sources.
HTML-view receipts are a **separate** `catalog_page_public_readback` field, never
silently counted as byte-verified when only the JSON data matches. For HTML only,
the known Cloudflare email-obfuscation span, mailto rewrite
and empty email-decoder script are decoded before comparing the complete bytes.
All other presentation/content changes remain a failed HTML readback, including
the Cloudflare Insights beacon observed on no-cache GET responses. That beacon is
not stripped, changed or presented as an exact HTML match by this repair.

## Scoped deployment

Guide commits use `[owned-surface-only]` to avoid the normal Pages workflow's
full-site regeneration. The dedicated `owned-app-surfaces.yml` workflow requires
the reviewed Guide SHA and the currently successful production deployment run.
It downloads that **already deployed** Pages artifact and overlays only
`data/owned-app-surfaces-cee.json`; it never runs GEO, conversion, feed generators
or syndication notifiers. All referenced source assets must match the deployed
artifact. A complete before/after tree hash comparison fails if any other byte
changes, including RSS, exact-50 feeds, conversion routes or locale copy.
The existing `pages-deploy` concurrency group is shared without cancelling other
owners. A changed baseline or native-review packet requires a fresh validation,
not a force-push, content copy or automatic green result.
