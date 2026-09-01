import statistics as st, math
from collections import Counter, defaultdict
from lib import all_cities, CITY_ORDER, pctile, safe_corr, summarise

C = all_cities()
def hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ---------------------------------------------------------------- T1
hdr("T1  Budget ladder: what does a below-median budget actually buy?")
print("For budgets at the city's own p25 / p50 / p75, share of AFFORDABLE stock that is an entire home")
for c in CITY_ORDER:
    r = C[c]; p = [x['price'] for x in r]
    line = f"{c:10s}"
    for q in (.25, .50, .75):
        thr = pctile(p, q)
        aff = [x for x in r if x['price'] <= thr]
        eh = sum(1 for x in aff if x['room'] == 'Entire home/apt') / len(aff)
        line += f"  p{int(q*100)}={eh:.1%}"
    # and: what percentile of the price distribution must you reach for a 50/50 shot at an entire home
    thr50 = None
    for q in range(1, 100):
        t = pctile(p, q / 100)
        aff = [x for x in r if x['price'] <= t]
        if sum(1 for x in aff if x['room'] == 'Entire home/apt') / len(aff) >= 0.5:
            thr50 = q; break
    line += f"   | 50% entire-home reached at p{thr50}"
    print(line)

# ---------------------------------------------------------------- T2
hdr("T2  Cost of trading up: price index at each decile (unit-free)")
print("price / city median, at deciles -- shows how steep the ladder is")
for c in CITY_ORDER:
    p = sorted(x['price_index'] for x in C[c])
    dec = [pctile(p, q / 10) for q in range(1, 10)]
    print(f"{c:10s} " + " ".join(f"{d:5.2f}" for d in dec) + f"   p90/p10={dec[8]/dec[0]:.1f}x")

# ---------------------------------------------------------------- T3
hdr("T3  Short-stay feasibility: can I book a weekend?")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    s2 = [x for x in r if x['min_nights'] <= 2]
    s3 = [x for x in r if x['min_nights'] <= 3]
    lng = [x for x in r if x['min_nights'] >= 28]
    # price penalty for short-stay-friendly stock, within nbhd x room type
    cells = defaultdict(lambda: {'s': [], 'l': []})
    for x in r:
        k = (x['nbhd'], x['room'])
        cells[k]['s' if x['min_nights'] <= 3 else 'l'].append(x['price'])
    d = [st.median(v['s']) / st.median(v['l']) for v in cells.values()
         if len(v['s']) >= 15 and len(v['l']) >= 15]
    dd = f"{st.median(d):.2f}x in {len(d)} cells" if d else "n/a"
    print(f"{c:10s} <=2n {len(s2)/n:5.1%} | <=3n {len(s3)/n:5.1%} | >=28n {len(lng)/n:5.1%} "
          f"| short-stay price vs long-stay, within cell: {dd}")

# ---------------------------------------------------------------- T4
hdr("T4  Ghost supply: how much of what I browse is actually bookable?")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    a0 = [x for x in r if x['avail'] == 0]
    a0_norev = sum(1 for x in a0 if x['reviews'] == 0) / max(1, len(a0))
    live = [x for x in r if x['avail'] > 0 and x['rpm'] > 0]
    print(f"{c:10s} avail=0 {len(a0)/n:5.1%} (of which never reviewed {a0_norev:5.1%}) | "
          f"avail>0 AND rpm>0 = genuinely live {len(live)/n:5.1%} | "
          f"median avail among bookable {st.median([x['avail'] for x in r if x['avail']>0]):5.0f}")

# ---------------------------------------------------------------- T5
hdr("T5  Does the crowd's favourite cost more? (top-rpm quartile vs rest, within cell)")
for c in CITY_ORDER:
    r = [x for x in C[c] if x['reviews'] > 0]
    cells = defaultdict(list)
    for x in r:
        cells[(x['nbhd'], x['room'])].append(x)
    ratios = []
    for grp in cells.values():
        if len(grp) < 40: continue
        thr = pctile([g['rpm'] for g in grp], .75)
        hi = [g['price'] for g in grp if g['rpm'] >= thr]
        lo = [g['price'] for g in grp if g['rpm'] < thr]
        if len(hi) >= 8 and len(lo) >= 8:
            ratios.append(st.median(hi) / st.median(lo))
    s = summarise([x - 1 for x in ratios])
    print(f"{c:10s} {s['n']:3d} cells | busiest-quartile price vs rest: {st.median(ratios):.2f}x "
          f"| dearer in {s['share_pos']:.0%} of cells")

# ---------------------------------------------------------------- T6
hdr("T6  Risk of a dud: share of listings with no reviews at all, by price tier")
for c in CITY_ORDER:
    r = C[c]
    p = [x['price'] for x in r]
    q1, q3 = pctile(p, .25), pctile(p, .75)
    cheap = [x for x in r if x['price'] <= q1]
    mid = [x for x in r if q1 < x['price'] <= q3]
    dear = [x for x in r if x['price'] > q3]
    f = lambda g: sum(1 for x in g if x['reviews'] == 0) / len(g)
    print(f"{c:10s} overall {f(r):5.1%} | cheapest quartile {f(cheap):5.1%} | "
          f"middle {f(mid):5.1%} | dearest quartile {f(dear):5.1%}")

# ---------------------------------------------------------------- T7
hdr("T7  Does neighbourhood shopping pay? spread of neighbourhood medians")
for c in CITY_ORDER:
    r = C[c]
    by = defaultdict(list)
    for x in r:
        if x['room'] == 'Entire home/apt':
            by[x['nbhd']].append(x['price'])
    meds = sorted(st.median(v) / st.median([y['price'] for y in r if y['room']=='Entire home/apt'])
                  for v in by.values() if len(v) >= 50)
    if len(meds) < 4:
        print(f"{c:10s} too few neighbourhoods"); continue
    print(f"{c:10s} {len(meds):3d} nbhds >=50 entire homes | index p10={meds[int(.1*len(meds))]:.2f} "
          f"med={st.median(meds):.2f} p90={meds[int(.9*len(meds))]:.2f} "
          f"| dearest/cheapest = {meds[-1]/meds[0]:.1f}x")

# ---------------------------------------------------------------- T8
hdr("T8  Where does the market actually transact? median rpm by price decile")
for c in CITY_ORDER:
    r = [x for x in C[c] if x['reviews'] > 0]
    r.sort(key=lambda x: x['price'])
    n = len(r); out = []
    for d in range(10):
        g = r[d * n // 10:(d + 1) * n // 10]
        out.append(st.median([x['rpm'] for x in g]))
    print(f"{c:10s} " + " ".join(f"{v:4.2f}" for v in out) + f"   (d1/d10 = {out[0]/out[-1]:.2f}x)")
