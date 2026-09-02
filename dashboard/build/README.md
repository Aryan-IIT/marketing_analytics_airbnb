# Build

`export_assets.py` is the only thing that reads `datasets/`. It reproduces the
computations in `../four_master_questions.ipynb` and writes small JSON plus
per-panel SVGs into `docs/`. The site itself ships no CSVs.

```bash
python3 -m venv .venv                     # from the repo root
.venv/bin/pip install pandas matplotlib scipy
.venv/bin/python dashboard/build/export_assets.py
```

It ends by printing the twenty-number regression table from `plan.md` §5. If it
does not say `regression: PASS`, the output is wrong and nothing downstream is
worth looking at.

## What it writes

| Path | Contents |
|---|---|
| `docs/data/market_stats.json` | Per-market medians, spreads, Q1/Q2 statistics. ~2 KB. |
| `docs/data/cells.json` | 627 market × neighbourhood × room-type cells with `n >= 10`. ~88 KB. |
| `docs/data/assumptions.json` | Outside numbers, their ranges, and a `source` string each. The Method table on the page renders straight from this, so the page cannot claim a provenance the build did not record. |
| `docs/data/scorecard.json` | The two static scorecard rows. |
| `docs/figures/*.svg` | Nine per-panel figures, recoloured to the deck palette. |

## Preview

```bash
cd docs && python3 -m http.server 8000
```

The `fetch()` calls need a server; opening `index.html` from the filesystem
fails on CORS.

## Notes for whoever edits this next

- Cleaning rules mirror `findings.py`. Change them there conceptually, but this
  script restates them in pandas because the notebook is pandas.
- Figures are exported one panel per file, never as the notebook's 2×2 grid — a
  14×9in four-panel figure is illegible on a phone.
- `svg.fonttype: 'none'` keeps SVG text as real text; `save()` then rewrites the
  font-family to the site's web stack and strips the fixed width/height so CSS
  controls the size.
- The deck accent is `#FF3EB5`, sampled from the PDF's content streams, not the
  `#E8368F` that `plan.md` originally estimated.
