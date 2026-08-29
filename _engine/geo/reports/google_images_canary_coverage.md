# Google Images canary coverage

- Experiment: `google-images-unique-asset-canary-2026-08-29`
- Qualified / abstained apps: **7 / 0**
- Categories: **7**
- Randomized unique assets / pages: **38 / 38**
- Treatment / sitemap-only holdout: **19 / 19**
- Checksum-pinned authentic images: **38**

| Category | App | Units | Treatment | Holdout | Images | Min width | ct |
|---|---|---:|---:|---:|---:|---:|---|
| Photo & utility | Unblurry | 3 | 2 | 1 | 3 | 1320px | `gimg_unblurry` |
| Productivity | ScanTo Pro | 9 | 4 | 5 | 9 | 1320px | `gimg_scanto` |
| Health | Cyca | 6 | 3 | 3 | 6 | 1320px | `gimg_cyca` |
| Money & travel | G+Money | 3 | 1 | 2 | 3 | 1320px | `gimg_gmoney` |
| Kids & learning | Lumi Letters | 10 | 5 | 5 | 10 | 1320px | `gimg_lumiletters` |
| Education | Aim990 | 4 | 2 | 2 | 4 | 1320px | `gimg_aim990` |
| Sleep & focus | Sereno | 3 | 2 | 1 | 3 | 1290px | `gimg_sereno` |

Every page has a distinct problem/workflow/result record. Images are exact copies of pre-existing, checksum-pinned en-US App Store screenshots; no generated UI, fake before/after, rating, or review is present.

Each image URL is owned by exactly one page and one arm. The design uses preregistered complete randomization within App strata and stratified randomization inference; it makes no same-image matched-pair or pure page-treatment claim.

Unknown and pending observations remain `null`. A URL that is still not indexed after 42 days is a technical failure, not a market zero.
