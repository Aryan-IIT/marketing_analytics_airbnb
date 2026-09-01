I'm working on a group assignment for MS 491 Marketing Analytics at IIT Gandhinagar. I need you to
generate and pressure-test 20 candidate research questions, then produce a PDF explaining them.

## The setup

Four Airbnb listings CSVs are in `datasets/`. Read them before proposing anything.

Facts already established. Don't waste time re-deriving them, but do verify anything you build on:

- **The filenames are misleading. These are cities, not countries.** "Belgium" is Antwerp only (2,422
  listings), "Netherlands" is Amsterdam's 22 districts (18,949), "California" is LA County only (33,078),
  and Rio is the municipality (35,731). Confirmed from latitude/longitude bounding boxes.
- Columns: id, name, host_id, host_name, neighbourhood_group, neighbourhood, latitude, longitude,
  room_type, price, minimum_nights, number_of_reviews, last_review, reviews_per_month,
  calculated_host_listings_count, availability_365.
- `neighbourhood_group` is 100% empty except in LA (3 values). `last_review` must be ignored — the
  course brief says so explicitly.
- `reviews_per_month` is blank exactly when `number_of_reviews` is 0. It's structural, not missing at
  random: fill with 0, never drop. Dropping those rows deletes 42% of Rio.
- 19 listings are priced at 0 across all four files — drop them. Rio's maximum price is R$132,358
  against a R$300 median, so use medians, never means.
- **Currency differs**: EUR (Antwerp, Amsterdam), BRL (Rio), USD (LA). No question may compare raw
  prices across cities. Use a price index (price ÷ that city's median) as the primary normalisation,
  with PPP or FX conversion only as a secondary robustness check. **Every cross-city question you
  propose must state explicitly how it normalises.**
- `findings.py` in the project root reproduces our validated results. Run it first.

## What we already validated — include these, reframed to the perspectives

- Professional hosts (3+ listings) price differently in each city, but only once you compare within the
  same neighbourhood AND the same room type: Antwerp +30%, Amsterdam +15.7%, Rio −14.7%, LA +1.1%
  (a genuine null). Pooled comparisons give the opposite answer in Rio and hide Amsterdam's effect
  behind a room-type composition difference — a textbook Simpson's paradox.
- Entire homes cost more than private rooms in 100% of the 142 testable neighbourhoods. The direction
  is lawlike; the magnitude varies by city (1.57× to 2.49×).
- Within neighbourhood and room type, higher price correlates with fewer reviews per month — negative
  in 72–98% of 250 cells.
- Double jeopardy (treating neighbourhoods as brands) does **not** replicate. We report it as a failed
  test on purpose.

## Analyses that already failed — do not propose these

- **Distance from the city centre.** Correlation with log price is *positive* in Rio (+0.15, because the
  value is the beach, not Centro) and flat in LA (+0.08, polycentric, Malibu is 45km out). Antwerp has
  exactly one listing beyond 10km. This is the standard Airbnb analysis and it is simply wrong here.
- **Estimated revenue per listing.** Needs an assumed review rate and stay length, neither in the data.
- **Top-10 host share.** A market-size artifact. Use share of listings from hosts with 3+ instead.
- **Total review count as a demand measure.** It mostly measures how long a listing has existed.

## The task

Generate **20 candidate questions** across three stakeholder perspectives, roughly 7 / 7 / 6:

- **P1 — the traveller.** Someone choosing where to go on holiday. "Which city gives me the most space
  for my money?" "Where can I get a whole apartment rather than a room at my budget?" Practical and
  consumer-facing.
- **P2 — the Airbnb regional manager.** Someone allocating marketing and ad budget across regions and
  deciding where the platform should push. "Which city has supply that isn't converting into bookings?"
  "Where is there unmet demand worth advertising into?" "Belgium looks expensive, should I put the
  budget behind Rio instead?" Strategic and platform-side.
- **P3 — the prospective host.** Someone who owns a property and wants to list it. "I have a two-bedroom
  in Amsterdam Oost, what should I charge?" "Does a longer minimum stay cost me bookings?" Concrete and
  individual.

We will pick **8 final questions: 3 from P1, 3 from P2, 2 from P3.** Each will then be answered against
all four cities and presented as a comparison. So propose questions that are genuinely comparative —
**a question whose answer is the same in all four cities is a weak question.**

Roughly a third of the 20 should extend the validated findings above. The rest should be genuinely new
angles. Push for questions we wouldn't have thought of; don't just repackage what we already have.

## Verify before you propose — this matters more than anything else

For each of the 20:

1. Actually run the numbers, at least roughly, across all four cities.
2. Confirm it's answerable with the available columns.
3. Confirm the answer **differs across the four cities**, since that's what makes it worth presenting.
4. Kill anything that doesn't survive, and tell us what you killed and why.

An earlier version of this project recommended the distance-to-centre analysis on reasoning alone, and
it turned out to be backwards. Don't reason about whether a question will work. Test it.

## One idea to evaluate

We wondered about distance from each listing to the nearest major airport, using lat/long plus airport
coordinates you look up. Test it properly and tell us honestly whether it holds. Be sceptical given the
distance-to-centre failure, and note that airport proximity often correlates with *lower* desirability
rather than higher. If it doesn't work, say so plainly and drop it.

## Dashboard

We want one interactive dashboard as an extra deliverable. Use your judgment: recommend **which single
perspective, or which specific questions, should drive it**, and justify the choice. Consider which
perspective is naturally parametric — where a user changing inputs produces genuinely different answers
— versus which is better told as a fixed narrative. Give a light spec: inputs, outputs, and what the
user actually learns. Argue against a generic filter-and-histogram dashboard; it should do something a
static slide cannot.

## Deliverable

A PDF, concise but properly explained, so five team members can read it and confidently choose 8
questions. For each question include:

- The question, plainly stated
- Which perspective it belongs to, and why a real person would ask it
- Which columns answer it, and how it normalises across currencies
- What you found when you tested it, including roughly how much the four cities differ
- Any trap or caveat

Then a short section on what you killed and why, and the dashboard recommendation. Group by
perspective, and rank within each perspective by how strong you think the question is, so your
recommendation is visible at a glance.

**Environment note:** pandas, matplotlib, reportlab and pandoc are all unavailable here. Use the Python
3 standard library (`csv`, `statistics`, `math`) for the analysis, and render the PDF by writing HTML
and converting it with headless Chrome:
`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=out.pdf "file://$PWD/in.html"`

**Style:** write it plainly, like a memo to teammates. No callout boxes, no letter badges, no hype
phrases, no consultant voice. Short sentences, ordinary words, and say when something is uncertain.
