import statistics as st, math
from collections import Counter, defaultdict
from lib import all_cities, CITY_ORDER, pctile, safe_corr, summarise

C = all_cities()
def hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ---------------------------------------------------------------- M1
hdr("M1  Supply-demand mismatch by neighbourhood (share of listings vs share of monthly reviews)")
for c in CITY_ORDER:
    r = C[c]
    tot_l, tot_d = len(r), sum(x['rpm'] for x in r)
    by = defaultdict(lambda: [0, 0.0])
    for x in r:
        by[x['nbhd']][0] += 1
        by[x['nbhd']][1] += x['rpm']
    big = {k: v for k, v in by.items() if v[0] >= 50}
    ratios = {k: (v[1] / tot_d) / (v[0] / tot_l) for k, v in big.items()}
    vals = sorted(ratios.values())
    top = sorted(ratios.items(), key=lambda kv: -kv[1])[:2]
    bot = sorted(ratios.items(), key=lambda kv: kv[1])[:2]
    # how dispersed is the mismatch: p90/p10 of the demand-per-listing index
    print(f"{c:10s} {len(big):3d} nbhds | demand-share / supply-share: p10={vals[int(.1*len(vals))]:.2f} "
          f"med={st.median(vals):.2f} p90={vals[int(.9*len(vals))]:.2f} | spread={vals[-1]/vals[0]:5.1f}x")
    print(f"{'':10s}    hottest: {', '.join(f'{k} {v:.2f}' for k,v in top)}")
    print(f"{'':10s}    coldest: {', '.join(f'{k} {v:.2f}' for k,v in bot)}")

# ---------------------------------------------------------------- M2
hdr("M2  Inventory health quadrants (bookable? x earning?)")
print("     live = avail>0 & rpm>0 | shelf = avail>0 & rpm=0 (listed, not selling) |")
print("     blocked = avail=0 & rpm>0 (sold out or capped) | dead = avail=0 & rpm=0")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    q = Counter()
    for x in r:
        a, d = x['avail'] > 0, x['rpm'] > 0
        q['live' if (a and d) else 'shelf' if a else 'blocked' if d else 'dead'] += 1
    print(f"{c:10s} live {q['live']/n:5.1%} | shelf {q['shelf']/n:5.1%} | "
          f"blocked {q['blocked']/n:5.1%} | dead {q['dead']/n:5.1%}")

# ---------------------------------------------------------------- M3
hdr("M3  Professionalisation: share of supply from 3+ hosts, and does it sell better?")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    pro_share = sum(1 for x in r if x['pro']) / n
    cells = defaultdict(lambda: {'p': [], 'a': []})
    for x in r:
        cells[(x['nbhd'], x['room'])]['p' if x['pro'] else 'a'].append(x['rpm'])
    d = [st.median(v['p']) - st.median(v['a']) for v in cells.values()
         if len(v['p']) >= 15 and len(v['a']) >= 15]
    s = summarise(d)
    print(f"{c:10s} pro share of listings {pro_share:5.1%} | rpm gap pro-minus-amateur, within cell: "
          f"median {s['median']:+.3f} | pro higher in {s['share_pos']:.0%} of {s['n']} cells")

# ---------------------------------------------------------------- M4
hdr("M4  Geographic concentration of supply (HHI over neighbourhoods) and of demand")
for c in CITY_ORDER:
    r = C[c]
    n = len(r); totd = sum(x['rpm'] for x in r)
    cl = Counter(x['nbhd'] for x in r)
    cd = defaultdict(float)
    for x in r: cd[x['nbhd']] += x['rpm']
    hhi_s = sum((v / n) ** 2 for v in cl.values())
    hhi_d = sum((v / totd) ** 2 for v in cd.values())
    top1 = cl.most_common(1)[0]
    print(f"{c:10s} nbhds={len(cl):3d} | HHI supply {hhi_s:.3f} | HHI demand {hhi_d:.3f} | "
          f"biggest nbhd {top1[0]} = {top1[1]/n:.1%} of supply")

# ---------------------------------------------------------------- M5
hdr("M5  Room-type mix: share of LISTINGS vs share of MONTHLY REVIEWS (flow, not stock)")
for c in CITY_ORDER:
    r = C[c]; n = len(r); totd = sum(x['rpm'] for x in r)
    ls = Counter(x['room'] for x in r)
    ds = defaultdict(float)
    for x in r: ds[x['room']] += x['rpm']
    parts = []
    for rt in ('Entire home/apt', 'Private room'):
        parts.append(f"{rt.split('/')[0][:7]}: {ls[rt]/n:5.1%} supply -> {ds[rt]/totd:5.1%} demand "
                     f"(index {(ds[rt]/totd)/(ls[rt]/n):.2f})")
    print(f"{c:10s} " + " | ".join(parts))

# ---------------------------------------------------------------- M6
hdr("M6  Regulatory fingerprint: the minimum-nights distribution")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    ct = Counter(int(x['min_nights']) for x in r)
    spike30 = (ct[30] + ct[31]) / n
    print(f"{c:10s} 1n {ct[1]/n:5.1%} | 2n {ct[2]/n:5.1%} | 3n {ct[3]/n:5.1%} | "
          f"30-31n {spike30:5.1%} | >=90n {sum(v for k,v in ct.items() if k>=90)/n:5.1%}")
    # does the 30+ segment behave differently?
    lg = [x for x in r if x['min_nights'] >= 28]
    sh = [x for x in r if x['min_nights'] <= 3]
    if len(lg) >= 30:
        print(f"{'':10s}    >=28n segment: median avail {st.median([x['avail'] for x in lg]):3.0f} "
              f"vs short-stay {st.median([x['avail'] for x in sh]):3.0f} | "
              f"median rpm {st.median([x['rpm'] for x in lg]):.2f} vs {st.median([x['rpm'] for x in sh]):.2f} | "
              f"zero-review {sum(1 for x in lg if x['reviews']==0)/len(lg):5.1%} vs "
              f"{sum(1 for x in sh if x['reviews']==0)/len(sh):5.1%}")

# ---------------------------------------------------------------- M7
hdr("M7  Demand concentration: what share of monthly reviews comes from the top decile of listings?")
for c in CITY_ORDER:
    r = sorted(C[c], key=lambda x: -x['rpm'])
    tot = sum(x['rpm'] for x in r); n = len(r)
    t10 = sum(x['rpm'] for x in r[:n // 10]) / tot
    t25 = sum(x['rpm'] for x in r[:n // 4]) / tot
    zero = sum(1 for x in r if x['rpm'] == 0) / n
    print(f"{c:10s} top 10% of listings = {t10:5.1%} of demand | top 25% = {t25:5.1%} | "
          f"listings with zero demand {zero:5.1%}")

# ---------------------------------------------------------------- M8
hdr("M8  Is new supply being absorbed? (zero-review listings: are they even bookable?)")
for c in CITY_ORDER:
    r = C[c]
    nr = [x for x in r if x['reviews'] == 0]
    print(f"{c:10s} zero-review {len(nr)/len(r):5.1%} of stock | of those, avail>0: "
          f"{sum(1 for x in nr if x['avail']>0)/len(nr):5.1%} | median price index "
          f"{st.median([x['price_index'] for x in nr]):.2f} vs 1.00 city median | "
          f"pro-host share {sum(1 for x in nr if x['pro'])/len(nr):5.1%} "
          f"(vs {sum(1 for x in r if x['pro'])/len(r):5.1%} overall)")
