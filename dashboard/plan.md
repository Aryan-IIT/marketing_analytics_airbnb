# Host dashboard — website plan

A static site for the host perspective, built from `four_master_questions.ipynb` and deployed on GitHub
Pages. This document is the spec: design brief, architecture, file structure, and build steps. A new
Claude picking this up should be able to work from this file alone.

**Status:** planned, not built. Nothing in `site/` or `build/` exists yet.

---

## 1. What this is

One page. A host reads it top to bottom and comes away able to answer, for each of four cities, whether
they should list, how to configure the listing, whether buying a property to run this way makes money,
and what could take it away.

It is a managerial report that happens to be a web page — not a BI tool, not a filter-and-histogram
dashboard. The reader is not exploring; they are being walked through an argument and then handed one
calculator where their own numbers genuinely change the answer.

The four questions, in the order the notebook already puts them:

| | Question | Nature |
|---|---|---|
| Q1 | Where do I actually fit in this market? | Fixed narrative |
| Q2 | How do I configure the listing to get booked? | Fixed narrative |
| Q3 | Does the capital math work? | **Parametric** |
| Q4 | What could take this away, and is the income real? | **Parametric** |

---

## 2. Design brief

The reference is `aryan-iit.github.io/consumer_behaviour/` — a simple GitHub Pages project site. Aim for
the same restraint. Closer to a printed consulting memo or an FT/Economist explainer than to a SaaS
dashboard.

**Do**

- One column, roughly 720–780px of text measure, centred, generous margins.
- A real typographic hierarchy: one display face for headings, one text face, one monospace for numbers
  in tables. System stacks are fine — no webfont loading if it can be avoided.
- `font-variant-numeric: tabular-nums` on every table and every figure in body text. Numbers must align.
- Horizontal rules and whitespace to separate sections, not boxes and borders.
- Muted ink on off-white. `#1d1d1d` on `#fdfdfc` or similar. The notebook's four city colours
  (`#2a9d8f` Antwerp, `#264653` Amsterdam, `#e9c46a` LA, `#e76f51` Rio) carry through to the site so
  charts and text agree — city colour is the *only* colour on the page.
- Sentence-case headings.
- State uncertainty in the prose where it exists. The Q2 Panel D reverse-causation warning already in the
  notebook is a model for this and must survive onto the site verbatim in substance.

**Do not** — this is the "non-AI-like" instruction made concrete

- No emoji anywhere, in headings or bullets.
- No gradient backgrounds, no purple/indigo, no glassmorphism, no `border-radius` above about 4px.
- No card grids with drop shadows. No "🚀 Key Takeaways" callout boxes.
- No badges, pills, or chips. No icon set.
- No hero section with a giant centred tagline.
- No dark mode toggle, no sticky animated nav, no scroll-triggered fade-ins.
- No hype adjectives in copy — no "powerful", "seamless", "unlock", "deep dive", "game-changing".
- No three-column "features" strip. This is a report, not a product page.

The test: it should look like something a person wrote in 2011 and still stands up, not something
generated last week.

---

## 3. Architecture, and the one real decision

**Static narrative for Q1/Q2, live calculator for Q3/Q4.**

Q1 and Q2 are descriptive findings about the data. They have one correct answer per city and nothing the
reader inputs changes them. Ship them as exported figures with prose — no interactivity, because there
is nothing honest to make interactive.

Q3 and Q4 are scenario arithmetic sitting on assumptions from outside the dataset. In the notebook those
assumptions are hard-coded constants. On the site they become controls. This is the part a static slide
cannot do, and it is the reason the site is worth building rather than just exporting the notebook to PDF.

Concretely, from the notebook:

```python
PPSQM      = {'Antwerp': 3100, 'Amsterdam': 8500, 'LA': 6458, 'Rio': 9500}   # local ccy per m²
UNIT_SIZE  = 50            # m²
payback    = 10            # years, implicit in cost/10
nights     = 15            # per month, in Q4
MINWAGE    = {...}         # local ccy per month
```

Every one of those becomes a slider or a number input. The reader watches Amsterdam's breakeven
occupancy bar move against its fixed 8.2% legal cap line and sees for themselves that no plausible
setting of the inputs closes the gap. That is a far stronger claim than asserting 79% and hoping they
believe it — it survives the reader trying to break it.

**Stack: none.** Vanilla HTML, one CSS file, one small JS file. No framework, no build step, no npm, no
chart library. Five teammates can edit it and it will still work in three years. The calculator's output
is CSS-width bars, which is all it needs.

**Charts: SVG exported from matplotlib.** Text stays selectable, it stays crisp on retina, and the site
cannot drift from the notebook because the figures *are* the notebook's figures.

**One thing to get right:** export each panel as its own SVG, not the 2×2 grid as one file. A 14×9in
four-panel figure is illegible on a phone. Per-panel files let the CSS reflow 2×2 on desktop into a
single column on mobile. This means restructuring the notebook's plotting cells to loop over panels and
save individually, which is the main piece of real work in the build script.

---

## 4. Page structure

Single page, `index.html`, with a thin sticky contents rail on desktop only (plain text links, no
animation) and anchor links.

```
Header
  Title, one-line standfirst, date, "four cities" line.
  No hero image.

Framing — ~150 words
  Why these four questions and why in this order. Sets up that the reader
  is deciding, not browsing.

Q1 — Where do I fit
  4 panel figures + prose. Ends with the notebook's one-breath summary.

Q2 — How do I configure it
  4 panel figures + prose. Includes the Panel D reverse-causation warning,
  set apart typographically (indent + rule, not a coloured box).

Q3 — Does the money work                        [INTERACTIVE]
  Assumption panel, then two live charts, then prose.

Q4 — What could take it away                    [INTERACTIVE]
  Shares the assumption panel state with Q3. Two charts, then prose.

Scorecard
  The 4×4 heatmap as an HTML table, not an image — so it is readable,
  selectable, and responsive. Cell shading via CSS background.
  Q3 and Q4 rows update live with the assumption panel.

Method and limits
  Cleaning rules, the price-index normalisation, where the outside numbers
  came from, what the data cannot answer. Honest and short.

Footer
  Course, group, data attribution (Inside Airbnb, CC BY 4.0), repo link.
```

---

## 5. The assumption panel — spec

One panel, placed at the top of Q3, controlling both Q3 and Q4. Sticky on desktop while those two
sections are in view; inline on mobile.

| Control | Default | Range | Affects |
|---|---|---|---|
| Unit size | 50 m² | 25–120 | Q3 both panels |
| Payback horizon | 10 yr | 5–25 | Q3 breakeven |
| Nights let per month | 15 | 5–30 | Q4 income multiple |
| Property price per m² | per city, from `PPSQM` | ±50% of default | Q3 both panels |

Each control shows its current value inline. A "reset to notebook defaults" text link, so the figures on
screen can always be returned to the ones in the report and the deck.

Outputs that recompute on input:

1. **Breakeven occupancy vs legal cap** — four horizontal bars, one per city, with a fixed red rule at
   each city's legal cap (Amsterdam 8.2%, LA 32.9%; Antwerp and Rio have none). Bars above 100% clamp
   visually and show the true figure as text.
2. **Price-to-property-cost ceiling** — four bars.
3. **Income as a multiple of local minimum wage** — four bars with a rule at 1.0×.
4. **Scorecard rows Q3 and Q4** update in place.

**The line the calculator should make unavoidable:** at *no* setting within these ranges does Amsterdam's
breakeven occupancy fall to its 30-nights-a-year legal cap. Consider a small persistent note under chart
1 that reads the current state — e.g. "at these settings Amsterdam needs 79% occupancy; the law allows
8.2%" — so the conclusion is stated in words, not left for the reader to infer from bar lengths.

All arithmetic is a direct port of the notebook cells. It must not diverge; the build script writes the
defaults into `assumptions.json` so there is one source of truth.

---

## 6. Data pipeline

The site ships no CSVs. `build/export_assets.py` reads the four datasets, reproduces the notebook's
computations, and writes small JSON plus SVG figures into `site/`.

```
datasets/*.csv  ──►  build/export_assets.py  ──►  site/data/*.json
   (~12 MB, not committed)                   └─►  site/figures/*.svg
```

Three JSON files, all small:

- `city_stats.json` — the per-city aggregates Q3/Q4 need at runtime: median entire-home price,
  median price, listing counts, professional share, currency code. A few dozen numbers.
- `assumptions.json` — `PPSQM`, `UNIT_SIZE`, payback, nights, `MINWAGE`, `FX_TO_USD`,
  `LEGAL_CAP_PCT`, each with a `source` string naming where the number came from and its year.
  The Method section renders this table straight from the file, so the site can never claim a
  provenance the build did not record.
- `scorecard.json` — the Q1 and Q2 rows, which are static.

The script must apply the same cleaning as `findings.py`: drop `price <= 0`, fill `reviews_per_month`
with 0 rather than dropping (blank exactly when `number_of_reviews` is 0 — dropping deletes 42% of Rio),
ignore `last_review`. Reuse `findings.py`'s rules rather than restating them.

Fix the notebook's `/mnt/user-data/uploads/` paths to `../datasets/` relative paths as part of this.

---

## 7. File structure

```
dashboard/
├── plan.md                          ← this file
├── four_master_questions.ipynb      ← analysis, source of truth for the figures
│
├── build/
│   ├── export_assets.py             ← datasets → site/data/*.json + site/figures/*.svg
│   └── README.md                    ← how to re-run the build
│
└── site/                            ← everything here is what gets deployed
    ├── index.html                   ← the whole page
    ├── css/
    │   └── style.css                ← single stylesheet
    ├── js/
    │   └── calculator.js            ← assumption panel + Q3/Q4 recompute. No dependencies.
    ├── data/
    │   ├── city_stats.json
    │   ├── assumptions.json
    │   └── scorecard.json
    ├── figures/
    │   ├── q1-a-room-mix.svg
    │   ├── q1-b-price-guess-error.svg
    │   ├── q1-c-host-concentration.svg
    │   ├── q1-d-price-spread.svg
    │   ├── q2-a-entire-home-premium.svg
    │   ├── q2-b-professional-premium.svg
    │   ├── q2-c-minimum-stay.svg
    │   ├── q2-d-reviews-vs-price.svg
    │   └── ...
    └── README.md                    ← what the site is, how to run locally
```

Local preview: `cd site && python3 -m http.server 8000`. The `fetch()` calls for JSON need a server —
opening `index.html` directly from the filesystem will fail on CORS.

---

## 8. Deploying to GitHub Pages

**This project is not currently a git repository.** That is step zero.

GitHub Pages only serves from a repository root or from `/docs` on the default branch — it cannot serve
an arbitrary subfolder like `dashboard/site/`. Two options:

**Recommended — separate public repo.** Matches how `consumer_behaviour` is set up and keeps the
datasets out of a public repo entirely.

```bash
cd dashboard/site
git init && git add . && git commit -m "Host dashboard"
gh repo create airbnb-host-dashboard --public --source=. --push
# then: Settings → Pages → Source: main, folder / (root)
```
URL: `https://aryan-iit.github.io/airbnb-host-dashboard/`

**Alternative — same repo, `/docs`.** Copy `dashboard/site/` to `docs/` at the project root and set Pages
to `main` + `/docs`. Simpler to keep in sync, but the repo must then be public, so the datasets and the
4 MB zip need a `.gitignore`.

Either way, add to `.gitignore`: `datasets/`, `*.zip`, `.DS_Store`, `.ipynb_checkpoints/`.

### On authentication

There isn't any. GitHub Pages project sites on a free account are fully public — no login, no access
control, and they are crawlable. Same as the `consumer_behaviour` reference site.

If the page needs to be non-public there are only three real options: don't deploy it and open
`index.html` locally or share the folder; deploy under an unguessable repo name and don't link it, which
is obscurity rather than security; or use GitHub Enterprise, which supports private Pages. For a course
deliverable that a professor and classmates need to open, public is almost certainly right — but if you
meant something else by the question, say so, because it changes the deploy step and nothing else.

---

## 9. Things to get right

- **Label every imported assumption on the page, not just in the method section.** Q3 and Q4 use outside
  data — property prices, minimum wages, legal caps, FX. Each chart caption names its source and year.
  Earlier in this project we killed an "estimated revenue per listing" analysis for needing assumptions
  that were not in the data; Q3 and Q4 are the same shape and survive only because the assumptions are
  visible and adjustable. Do not let them read as measurements.
- **Keep the Panel D warning.** Listings with more reviews charging less is reverse causation — cheap
  listings book faster and accumulate reviews faster. The notebook says so; the site must too. It is the
  clearest evidence in the deliverable that the analysis was read critically.
- **Currency.** Never compare raw prices across cities. Price index (price ÷ city median) is the default;
  FX and PPP appear only where a money comparison is the point, and both get shown because they disagree.
- **Mobile.** Per-panel SVGs, one column, controls stack. The scorecard is an HTML table with the first
  column sticky so it stays readable when scrolled sideways.
- **Accessibility.** The four city colours are not distinguishable in greyscale or to some colourblind
  readers — never encode a value in colour alone; always label the number. Alt text on every figure
  stating the finding, not the chart type.
- **No build step means no minification and no cache-busting.** If a teammate edits CSS and the browser
  serves a stale copy, that is a hard-refresh problem, not a bug. Note it in the site README.

---

## 10. Open questions

1. **Q1 panels C and D** — the notebook cell is truncated in places; confirm exactly what "host
   concentration" and "price spread within niche" are computing before writing captions that assert a
   finding.
2. **Rio `PPSQM = 9500`** — confirm this is BRL/m² and note the source. It is the single number driving
   Rio's "best breakeven" conclusion, and at BRL it makes Rio's property roughly half LA's in USD, which
   is plausible but worth a citation.
3. **LA legal cap** — the notebook uses 120/365. Confirm against the LA ordinance; the 120-night figure
   applies to extended home-sharing registration, and the base cap is lower. This changes a red line on
   the headline chart.
4. Does the deck need the same figures? If so, export PNGs at 2× alongside the SVGs in the same build.

---

## 11. Suggested build order

1. `build/export_assets.py` — get real JSON and SVGs on disk first. Everything else is styling around
   real numbers, and writing copy against placeholder figures wastes time.
2. `index.html` with Q1 and Q2 only, plus the method section. Static, no JS. This is already a complete
   deliverable if time runs out.
3. `style.css` — settle the type scale and spacing here, before adding interactivity.
4. `calculator.js` and the Q3/Q4 sections.
5. Scorecard, wired to the calculator.
6. Deploy, then check on a phone.
