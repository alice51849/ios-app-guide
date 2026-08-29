# Pages publish inventory

`publish_inventory.py` first stages a reversible allowlist without deleting
source content. `pages_stage.py` then builds a semantically checked publication
tree: repeated CSS and JSON-LD become content-addressed assets, JSON is
canonicalized, and valid indexable HTML hreflang relations move to
deterministic gzip sitemap shards. Repeated JSON-LD uses a synchronous
same-origin loader whose canonical rendered payload is checked against the
source graph. Hreflang relations involving `noindex` pages are removed rather
than being reintroduced through a sitemap. The policy is explicit in
`publish_inventory_policy.json`, and its selection portion is digest-pinned to
the latest authoritative crawl-budget allowlist.

Content-addressed assets use full SHA-256 base64url identifiers under compact
`a/c/` and `a/j/` paths. Ordinary same-site URL attributes use the shortest
page-relative or site-root-relative spelling that resolves to the identical
URL; canonical and HTML hreflang values remain absolute.

Reachable child sitemaps that are not linked directly from HTML may use
deterministic `.xml.gz` storage; parent indexes are rewritten and the full
public URL union is parsed before and after. Stable root and Google Images
canary sitemap names, plus any sitemap linked from HTML, keep their paths.
The large primary URL set moves to `sitemap-primary.xml.gz`;
`sitemap.xml` remains a valid static sitemap index at its existing route.

The artifact keeps every existing file under the 50 official locale roots and
the `answers/`, `guides/`, `hubs/`, `tools/`, `assets/`, and `.well-known/`
surfaces. Root feeds, every official-locale Atom feed, robots files, and
sitemaps are blocking requirements.

An HTML file is omitted only when all of these are true:

1. it is outside every protected surface;
2. it is unreachable from the configured site entrypoint;
3. no sitemap names it;
4. it is `noindex` or an exact/canonical duplicate; and
5. no retained HTML file links to it.

References to paths excluded by that authority are normalized without guessing:
an excluded Markdown alternate is removed, an anchor to an excluded Markdown
source uses its published `.html` peer when one exists, and other excluded
anchor targets become inert text while preserving their visible content.

The source inventory is retained as
`.well-known/source-publish-inventory.json.gz`. The deterministic
`.well-known/pages-stage-manifest.json.gz` binds every source/staged digest,
semantic roots, the public sitemap URL union, canonical/link/hreflang/feed
closure, staged content counts, and the manifest's own reported size.

`pages_artifact_gate.py` independently recounts the exact post-stage tree and
hard-fails when final staging `unpacked_bytes` exceed `870000000`, preserving
at least `30000000` bytes below the platform's `900000000`-byte ceiling. Tar bytes
and `deflate_upload_bytes` are reported separately; the latter has its own
secondary hard gate and can never make an oversized unpacked publication pass.
Source and final scans reject symlinks, multi-link inodes, and sparse files.

Rollback is a single workflow revert: source pages remain tracked and unchanged.
For a local audit that performs no deployment or network notification:

```sh
python3 _engine/geo/publish_inventory.py \
  --source . \
  --source-commit "$(git rev-parse HEAD)" \
  --git-tree HEAD \
  --dry-run \
  --manifest-out ../crawl-budget-report.json
```
