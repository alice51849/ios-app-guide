# Daily cloud-health candidate

Zero-model, deterministic replacement for the approved cloud-health v3 audit.

Approval anchor:

`CLOUD HEALTH AUDIT V3 VERIFIED 339f48d201b11698c366836899f75d9bca125246abd80f1798be3dd458b7b03d`

## Safety contract

- Network acquisition is HTTPS `GET` only.
- It never dispatches or reruns Actions, and never issues HTTP `POST`, `PATCH`,
  `PUT`, or `DELETE`.
- It never logs request headers, credentials, or ASC/GitHub tokens.
- It does not call a model.
- Every run starts from a new in-memory snapshot. Missing, stale, partial,
  rate-limited, or malformed evidence is emitted as `BLOCKED`; an old green
  artifact is never read or carried forward.
- Output files are sibling-staged, fsynced, and replaced. The digest manifest is
  replaced last, so consumers reject a torn set.

## Evidence and semantics

The collectors reuse the approved v3 GitHub/public-GET and ASC report parsing
logic. Each source record has `observed_at`, `run_id` (nullable when a source
has no run identity), and a SHA-256 digest.

The output keeps these claims separate:

1. capacity
2. natural `schedule` attempt-1 run
3. deployed
4. independent public GET
5. crawler/index
6. click
7. ASC download

`nominal_cron_delivery_ratio` remains a nominal comparison, never an SLA or
capacity metric. Nostr relay ACK remains separate from public GET and never
counts as exposure. Standard.site App coverage and document count remain
separate units and are never subtracted.

ASC metrics preserve v3 window semantics:

- latest daily: one date
- rolling 7d: `as_of - 6` through `as_of`
- month to date: first day of month through `as_of`
- every metric carries its own `start`, `end`, `metric`, `known`, `unknown`,
  `denominator`, and `unknown_no_row`
- Sales and Trends is exact; Analytics privacy suppression is not applied

## Run

```sh
python3 cloud_health/run.py \
  --output-dir "$HOME/.growth-private/cloud-health-daily"
```

Optional `GITHUB_TOKEN` is read only from the environment to raise GET rate
limits. It is never emitted. Without adequate current evidence, the command
still writes a complete fresh `BLOCKED` bundle and exits successfully.

Offline golden replay:

```sh
python3 cloud_health/run.py \
  --golden-v3 cloud_health/tests/fixtures/cloud-health-audit.v3.json \
  --output-dir cloud_health/tests/.golden-output
```

## Test

```sh
python3 -m unittest cloud_health.tests.test_daily -q
```

The suite covers the v3 golden digest, 15 semantic mutations, network failure,
rate-limit recovery/exhaustion, partial evidence, source provenance, GET-only
enforcement, exact46 recomputation, atomic replacement, and complete bundle
generation.

## Inactive production candidates

- `ops/launchd/com.alice51849.cloud-health-daily.plist.candidate` is a daily
  local scheduler definition. It is intentionally not loaded.
- The Guide mirror includes
  `.github/workflow-candidates/cloud-health-daily.yml`. GitHub ignores that
  directory, so it is intentionally not active. Its proposed self-hosted job
  persists the GET-only bundle locally without committing, deploying, or
  uploading it.
