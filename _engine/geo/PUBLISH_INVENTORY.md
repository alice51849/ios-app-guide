# Pages publish inventory

`publish_inventory.py` stages the GitHub Pages artifact without deleting source
content. The policy is explicit in `publish_inventory_policy.json`.

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

The deterministic `.well-known/publish-inventory.json` records every included
and excluded path, hashes the content inventory, and reports legacy-versus-new
file, byte, and HTML counts. Budget, orphan, sitemap, feed, internal-link, and
deployment-SHA violations block publication.

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
