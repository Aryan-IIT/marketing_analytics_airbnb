import statistics as st, math
from collections import Counter, defaultdict
from lib import all_cities, CITY_ORDER, haversine, safe_corr, summarise, pctile

C = all_cities()
def hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ---------------------------------------------------------------- K1
hdr("K1  REPLACEMENT GEOGRAPHY: distance to the supply centroid (where the listings actually are)")
print("Self-defining per city, so comparable in a way 'the city centre' is not.")
for c in CITY_ORDER:
    r = C[c]
    # centroid = median lat/lon of listings, robust to the Malibu tail
    clat, clon = st.median([x['lat'] for x in r]), st.median([x['lon'] for x in r])
    for x in r:
        x['d_hub'] = haversine(x['lat'], x['lon'], clat, clon)
    d = [x['d_hub'] for x in r]
    lp = [math.log(x['price']) for x in r]
    cells = defaultdict(list)
    for x in r: cells[(x['nbhd'], x['room'])].append(x)
    cors = [safe_corr([g['d_hub'] for g in v], [math.log(g['price']) for g in v])
            for v in cells.values() if len(v) >= 40]
    cors = [x for x in cors if x is not None]
    s = summarise(cors)
    print(f"{c:10s} centroid ({clat:.3f},{clon:.3f}) | median dist {st.median(d):5.1f}km p90 {pctile(d,.9):5.1f}km "
          f"| corr(d, log price) {safe_corr(d, lp):+.3f} | corr(d, rpm) {safe_corr(d,[x['rpm'] for x in r]):+.3f}")
    print(f"{'':10s} within nbhd x room: {s['n']} cells median r {s['median']:+.3f} positive {s['share_pos']:.0%}")

# ---------------------------------------------------------------- K2
hdr("K2  Total review count as a demand measure -- show it is mostly listing age")
for c in CITY_ORDER:
    r = [x for x in C[c] if x['reviews'] > 0]
    # implied months live = reviews / rpm.  If reviews measured demand this would be flat.
    age = [x['reviews'] / x['rpm'] for x in r if x['rpm'] > 0]
    cr = safe_corr([math.log(x['reviews']) for x in r if x['rpm'] > 0],
                   [math.log(x['reviews'] / x['rpm']) for x in r if x['rpm'] > 0])
    cr2 = safe_corr([math.log(x['reviews']) for x in r if x['rpm'] > 0],
                    [math.log(x['rpm']) for x in r if x['rpm'] > 0])
    print(f"{c:10s} implied months-live: med {st.median(age):5.1f} p10 {pctile(age,.1):5.1f} p90 {pctile(age,.9):5.1f} "
          f"| corr(log reviews, log months-live) {cr:+.3f} | corr(log reviews, log rpm) {cr2:+.3f}")

# ---------------------------------------------------------------- K3
hdr("K3  Segment sizes that are too small to compare across four cities")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    ct = Counter(x['room'] for x in r)
    print(f"{c:10s} Shared {ct['Shared room']:5d} ({ct['Shared room']/n:.1%})  "
          f"Hotel {ct['Hotel room']:5d} ({ct['Hotel room']/n:.1%})  "
          f"| nbhds with >=50 shared/hotel listings: "
          f"{sum(1 for k,v in Counter(x['nbhd'] for x in r if x['room'] in ('Shared room','Hotel room')).items() if v>=50)}")

# ---------------------------------------------------------------- K4
hdr("K4  Robustness of the availability-vs-demand result (H3) among REVIEWED listings only")
for c in CITY_ORDER:
    r = [x for x in C[c] if x['avail'] > 0 and x['reviews'] > 0]
    cells = defaultdict(list)
    for x in r: cells[(x['nbhd'], x['room'])].append(x)
    cors = [safe_corr([g['avail'] for g in v], [g['rpm'] for g in v]) for v in cells.values() if len(v) >= 40]
    cors = [x for x in cors if x is not None]
    s = summarise(cors)
    print(f"{c:10s} {s['n']:3d} cells | median r {s['median']:+.3f} | positive in {s['share_pos']:.0%}")

# ---------------------------------------------------------------- K5
hdr("K5  Robustness of the newcomer-pricing result (H4): winsorised, and entire homes only")
for c in CITY_ORDER:
    r = C[c]
    p = [x['price'] for x in r]; lo, hi = pctile(p, .01), pctile(p, .99)
    rw = [{**x, 'price': min(max(x['price'], lo), hi)} for x in r]
    for lab, src in (("winsorised", rw), ("entire homes", [x for x in r if x['room'] == 'Entire home/apt'])):
        cells = defaultdict(lambda: {'n': [], 'e': []})
        for x in src:
            cells[(x['nbhd'], x['room'])]['n' if x['reviews'] == 0 else 'e'].append(x['price'])
        d = [100 * (st.median(v['n']) / st.median(v['e']) - 1) for v in cells.values()
             if len(v['n']) >= 15 and len(v['e']) >= 15]
        s = summarise(d)
        print(f"{c:10s} {lab:13s} {s['n']:3d} cells | {s['median']:+7.1f}% | above in {s['share_pos']:.0%}")

# ---------------------------------------------------------------- K6
hdr("K6  Does the Rio short-stay discount (T3) survive dropping the mega-priced tail?")
for c in CITY_ORDER:
    r = C[c]
    p = [x['price'] for x in r]; lo, hi = pctile(p, .01), pctile(p, .99)
    src = [x for x in r if lo <= x['price'] <= hi]
    cells = defaultdict(lambda: {'s': [], 'l': []})
    for x in src:
        cells[(x['nbhd'], x['room'])]['s' if x['min_nights'] <= 3 else 'l'].append(x['price'])
    d = [st.median(v['s']) / st.median(v['l']) for v in cells.values()
         if len(v['s']) >= 15 and len(v['l']) >= 15]
    print(f"{c:10s} trimmed 1-99%: {len(d):3d} cells | short-stay vs long-stay price {st.median(d):.2f}x")
