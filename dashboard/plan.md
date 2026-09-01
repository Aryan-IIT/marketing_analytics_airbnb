# Host dashboard — website plan

An interactive companion to the host section of `ppt/Airbnb_Marketing_Analytics_Deck_Templated.pdf`,
built from `four_master_questions.ipynb` and deployed on GitHub Pages. This document is the spec: what
the site is for, design brief, architecture, file structure, and build steps. A new Claude picking this
up should be able to work from this file alone.

**Status:** planned, not built. Nothing in `site/` or `build/` exists yet.
**Decisions taken:** report + tool (not tool-only); public repo `Aryan-IIT/marketing_analytics_airbnb`;
Pages served from `/docs`.

---

## 1. Why this exists, given the deck already does

The 21-slide deck is the report. It covers all three perspectives, and the host section already is
Q1–Q4. **The site must not re-render the deck.** Its job is the three things the slide format prevented:

1. **Show all four markets on Q3 and Q4.** The deck's Q3 chart plots Rio and Amsterdam only; Q4 plots
   Antwerp and Rio only. That is a layout constraint, not an analytical choice — and it costs a real
   finding. Filling in the other two bars shows **two of the four markets are arithmetically blocked,
   not one**: LA needs 59.8% occupancy against an ordinance permitting 32.9%. The deck cannot say this.
2. **Let the reader move the assumptions.** The deck states plainly that Q3/Q4 are "scenario arithmetic,
   not a finding" and that the inputs come from outside the listings file. On paper that is an assertion
   the reader must take on trust. On the site they can try to break it and watch it hold.
3. **Answer for one listing, not one market.** The deck reports market medians. A host has a
   neighbourhood and a room type. The final section takes those and returns a number with a stated
   confidence.

Division of labour, to keep on a slide if asked: **the deck argues; the site lets you test the
argument and apply it.**

---

## 2. Design brief

**The deck sets the identity — follow it, not the notebook.** The notebook's teal/sand palette
(`#2a9d8f`, `#264653`, `#e9c46a`, `#e76f51`) conflicts with the deck and must be abandoned. Every
exported figure gets recoloured. This is real work; budget for it.

From the deck:

- Magenta accent, roughly `#E8368F`, used for emphasis, rules, and one highlighted value per view.
- Near-black text `#1d1d1d` on white.
- Display headings in a transitional serif; body and labels in a humanist sans; numbers tabular.
- Thin (~1.5px) magenta outline boxes for primary callouts. Flat light-grey fill boxes (`#f2f2f2`)
  for secondary notes. No shadows, no rounded corners beyond ~2px.
- The isometric cube motif, top-right and bottom-left. Reproduce as inline SVG at low opacity, or skip
  it rather than approximate it badly.
- Slide structure worth carrying over: small magenta eyebrow label → serif headline that states the
  finding as a sentence → chart left, notes right → an `IMPLICATION` bar at the bottom.

**Headlines state findings, not topics.** "Buying a property to run as an Airbnb business in Amsterdam
is not weak economics — it is arithmetically blocked", not "Capital analysis". Carry that discipline
onto the web page.

**Do not** — the "non-AI-like" instruction made concrete: no emoji; no gradients; no purple/indigo; no
card grids with drop shadows; no badges or pills; no icon set; no hero tagline; no dark-mode toggle; no
scroll-triggered animation; no hype adjectives ("powerful", "seamless", "unlock", "deep dive").

---

## 3. Architecture

**Static narrative for Q1/Q2, live computation for Q3/Q4, live lookup for the tool.**

Q1 and Q2 are descriptive findings about the data. Nothing the reader inputs changes them, so they ship
as recoloured exported figures with prose. Q3 and Q4 are scenario arithmetic on outside constants, so
those constants become controls. The tool is a lookup over precomputed per-cell statistics.

**Stack: none.** Vanilla HTML, one CSS file, one JS file. No framework, no build step, no npm, no chart
library. Five teammates can edit it and it will still work in three years. Q3/Q4 bars and the tool's
output are CSS-width divs, which is all they need.

**Q1/Q2 figures: SVG exported from matplotlib.** Text stays selectable, crisp at any zoom, and the site
cannot drift from the notebook because the figures *are* the notebook's figures — recoloured.

**Export each panel as its own SVG, not the 2×2 grid.** A 14×9in four-panel figure is illegible on a
phone. Per-panel files let the CSS reflow to one column. This means restructuring the notebook's
plotting cells to loop and save individually — the main piece of real work in the build script.

---

## 4. Page structure

Single page, `docs/index.html`, thin contents rail on desktop, anchor links.

```
Header          Title, standfirst, date, link to the full deck PDF.
Framing         ~150 words: what the deck established, what this page adds.
Q1              Recoloured panels + prose. Static.
Q2              Recoloured panels + prose. Static. Keeps the review-count
                reverse-causation warning.
Q3              Assumption panel → four live bars vs legal caps → prose.   [LIVE]
Q4              Four live bars vs 1.0× minimum wage → prose.               [LIVE]
Scorecard       4×4 as an HTML table, not an image. Q3/Q4 rows live.
Your listing    The tool. Market → neighbourhood → room type → unit size.  [LIVE]
Method          Cleaning rules, normalisation, where outside numbers came
                from and their year, what the data cannot answer.
Footer          Course, group, Inside Airbnb attribution (CC BY 4.0), repo.
```

---

## 5. Q3/Q4 assumption panel — spec

One panel at the top of Q3, controlling Q3, Q4 and the scorecard. Sticky on desktop while those
sections are in view.

| Control | Default | Range |
|---|---|---|
| Unit size | 50 m² | 25–120 |
| Payback horizon | 10 yr | 5–25 |
| Nights let per month | 15 | 5–30 |
| Property price per m² | per market (below) | ±50% |

Defaults, all from the deck and verified to reproduce it:

```
PPSQM    Antwerp €3,100   Amsterdam €8,500   LA $6,458   Rio R$9,500   (local ccy/m²)
MINWAGE  Antwerp €2,154   Amsterdam €2,400   LA $2,929   Rio R$1,621   (local ccy/month)
FX→USD   Antwerp 1.17     Amsterdam 1.17     LA 1.00     Rio 1/5.19
CAP      Antwerp none     Amsterdam 30n=8.2% LA 120n=32.9%  Rio none
```

Formulas, ported verbatim from the notebook:

```
breakeven_occupancy = (PPSQM × unit_size ÷ payback_years ÷ median_entire_home_price) ÷ 365
price_to_cost_ceiling = (median_entire_home_price × 365) ÷ (PPSQM × unit_size)
income_multiple = (median_entire_home_price × nights_per_month) ÷ MINWAGE
```

At defaults these must produce exactly:

| Market | Median entire home | Breakeven | Legal cap | Ceiling | Income multiple |
|---|---|---|---|---|---|
| Antwerp | €80 | 53.1% | none | 18.8% | 0.56× |
| Amsterdam | €147 | 79.2% | 8.2% | 12.6% | 0.92× |
| Rio | R$391 | 33.3% | none | 30.0% | 3.62× |
| LA | $148 | 59.8% | 32.9% | 16.7% | 0.76× |

Treat that table as a regression test. Amsterdam 79.2%, Rio 33.3%, Antwerp 0.56× and Rio 3.62× match
the deck; the other six are new and are the reason the site exists.

**The line the calculator must make unavoidable:** at no setting within these ranges does Amsterdam's
or LA's breakeven fall to its legal cap. Render a running verdict sentence under the chart that reads
the current state — "at these settings Amsterdam needs 79% and the law allows 8%; LA needs 60% and
allows 33%" — so the conclusion is in words, not inferred from bar lengths.

---

## 6. The per-listing tool — spec

Inputs: market → neighbourhood (populated from the chosen market) → room type → unit size.

Outputs, in this order:

1. **The comp band.** Median price for that neighbourhood × room type, with quartiles and `n`. Shown in
   local currency, never converted.
2. **How much to trust it.** The residual spread from Q1 — "otherwise-identical listings here still
   differ by 2.59×". This is the output that justifies the whole tool, and it is what no slide carries.
   Where `n` is below ~30, say the cell is too thin rather than printing a number.
3. **Minimum-stay penalty.** Median reviews/month for that cell at 1 night vs the host's intended
   minimum, from Q2.
4. **Capital math for this unit**, at the assumption-panel settings, against that market's legal cap.
5. **Income multiple** for this cell rather than the market median.

Every output labelled with its `n`. Nothing printed for a cell with too few listings — an honest blank
beats a fabricated number, and there are 499 neighbourhoods of which many are tiny.

---

## 7. Data pipeline

The site ships no CSVs. `build/export_assets.py` reads the four datasets, reproduces the notebook's
computations, and writes small JSON plus recoloured SVGs into `docs/`.

```
datasets/*.csv  ──►  build/export_assets.py  ──►  docs/data/*.json
   (~12 MB, gitignored)                      └─►  docs/figures/*.svg
```

Four JSON files:

- `market_stats.json` — per market: median price, median entire-home price, listing count, currency,
  professional share, the Q1 R² and residual spread. A few dozen numbers.
- `cells.json` — per market × neighbourhood × room type: `n`, median, p25, p75, median rpm, median rpm
  at 1-night vs 4–7-night minimums. Roughly 2,000 rows. Drop cells with `n < 10` at build time; expect
  150–300 KB, which is fine for a static page. **This is the only new data work versus the deck.**
- `assumptions.json` — `PPSQM`, `MINWAGE`, `FX_TO_USD`, `LEGAL_CAP`, defaults, each with a `source`
  string naming where the number came from and its year. The Method section renders this table straight
  from the file, so the page can never claim a provenance the build did not record.
- `scorecard.json` — the static Q1/Q2 rows.

Cleaning must match `findings.py`: drop `price <= 0`, fill `reviews_per_month` with 0 rather than
dropping (blank exactly when `number_of_reviews` is 0 — dropping deletes 42% of Rio), ignore
`last_review`. Import from `findings.py` rather than restating the rules.

**Fix the notebook's `/mnt/user-data/uploads/` paths to `../datasets/`** as part of this.

---

## 8. File structure

```
marketing_analytics_airbnb/            ← repo root = current project root
├── .gitignore                         ← datasets/, *.zip, syllabus, .DS_Store
├── findings.py                        ← shared cleaning rules, imported by the build
├── candidate_questions.pdf            ← the 20 tested candidates
├── analysis/                          ← standard-library scripts behind the findings
│
├── dashboard/
│   ├── plan.md                        ← this file
│   ├── four_master_questions.ipynb    ← source of truth for Q1/Q2 figures
│   ├── ppt/
│   │   └── Airbnb_Marketing_Analytics_Deck_Templated.pdf
│   └── build/
│       ├── export_assets.py           ← datasets → docs/data/*.json + docs/figures/*.svg
│       └── README.md
│
└── docs/                              ← GitHub Pages serves from here
    ├── index.html
    ├── css/style.css
    ├── js/app.js                      ← assumption panel, Q3/Q4, the tool. No dependencies.
    ├── data/
    │   ├── market_stats.json
    │   ├── cells.json
    │   ├── assumptions.json
    │   └── scorecard.json
    └── figures/
        ├── q1-a-room-mix.svg
        ├── q1-b-price-guess-error.svg
        ├── q1-c-host-concentration.svg
        ├── q1-d-price-spread.svg
        ├── q2-a-entire-home-premium.svg
        ├── q2-b-professional-premium.svg
        ├── q2-c-minimum-stay.svg
        └── q2-d-reviews-vs-price.svg
```

`docs/` rather than `dashboard/site/` because **GitHub Pages only serves from a repo root or `/docs`** —
it cannot serve an arbitrary subfolder.

Local preview: `cd docs && python3 -m http.server 8000`. The `fetch()` calls need a server; opening
`index.html` from the filesystem fails on CORS.

---

## 9. Deploy

Repo is initialised and committed locally. Remaining steps:

```bash
git remote add origin git@github.com:Aryan-IIT/marketing_analytics_airbnb.git
git push -u origin main
# GitHub → Settings → Pages → Source: main, folder /docs
```
URL: `https://aryan-iit.github.io/marketing_analytics_airbnb/`

SSH to GitHub is already working as `Aryan-IIT`. The repo must be **public** for Pages on a free
account — there is no authentication or access control on a Pages project site; it is world-readable
and crawlable.

---

## 10. Things to get right

- **Label every imported assumption on the page, not just in Method.** Q3 and Q4 use outside data —
  property prices, minimum wages, legal caps, FX. Each chart caption names its source and year. Earlier
  in this project we killed an "estimated revenue per listing" analysis for needing assumptions not in
  the data; Q3/Q4 are the same shape and survive only because the assumptions are visible and
  adjustable. Do not let them read as measurements.
- **Keep the review-count warning.** More reviews correlating with lower price is reverse causation —
  cheap listings book faster and accumulate reviews faster. The deck says so; the site must too.
- **Currency.** Never compare raw prices across markets. Price index is the default; FX and PPP appear
  only where a money comparison is the point, and both get shown because they disagree.
- **Thin cells.** 499 neighbourhoods, many tiny. Suppress rather than print. Every number carries `n`.
- **Mobile.** Per-panel SVGs, one column, controls stack, scorecard scrolls sideways with a sticky first
  column.
- **Accessibility.** Never encode a value in colour alone — always print the number. Alt text states the
  finding, not the chart type.

---

## 11. Open questions

1. **LA's legal cap.** The deck uses 120/365 = 32.9%. The 120-night figure is extended home-sharing
   registration; the base LA cap is lower. This now matters much more than it did — it is the difference
   between "LA is blocked" and "LA is tight but workable", and that is a headline claim. Verify against
   the ordinance before publishing.
2. **Rio `PPSQM = R$9,500/m²`.** Confirm the source and year. It drives Rio's "strongest capital case"
   conclusion. At R$9,500 a 50m² unit is R$475,000 ≈ $91,500, roughly a third of LA's in USD — plausible
   for Rio, but it needs a citation.
3. **Minimum wage basis.** Antwerp €2,154 and Amsterdam €2,400 are gross monthly statutory minimums;
   confirm LA's $2,929 is on the same basis (it looks like $16.90/hr × 173h) rather than a different
   convention. The Rio figure should be Brazil's federal minimum for the stated year.
4. **Recolouring.** Confirm the exact deck magenta by sampling the PDF rather than eyeballing `#E8368F`,
   and identify the two typefaces so the web stack can match or substitute deliberately.

---

## 12. Build order

1. `build/export_assets.py` — real JSON and recoloured SVGs on disk first. Everything else is styling
   around real numbers; writing copy against placeholders wastes time. Validate against the regression
   table in §5.
2. `docs/index.html` with Q1, Q2 and Method only. Static, no JS. Already a complete deliverable if time
   runs out.
3. `css/style.css` — settle type scale and spacing before adding interactivity.
4. `js/app.js`: assumption panel → Q3 → Q4 → scorecard.
5. The per-listing tool, last. It is the most novel piece and the most droppable.
6. Deploy, then check on a phone.
