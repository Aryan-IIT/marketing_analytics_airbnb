import statistics as st, math, re
from collections import defaultdict
from lib import all_cities, CITY_ORDER, haversine, safe_corr, summarise, pctile

C = all_cities()
def hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# Airport coordinates, looked up. Primary = the airport most arrivals actually use.
AIRPORTS = {
    "Antwerp":   [("ANR Antwerp Intl", 51.1894, 4.4603), ("BRU Brussels", 50.9014, 4.4844)],
    "Amsterdam": [("AMS Schiphol", 52.3105, 4.7683)],
    "Rio":       [("GIG Galeao", -22.8090, -43.2506), ("SDU Santos Dumont", -22.9105, -43.1631)],
    "LA":        [("LAX", 33.9416, -118.4085), ("BUR Burbank", 34.2007, -118.3587),
                  ("LGB Long Beach", 33.8177, -118.1516), ("SNA John Wayne", 33.6757, -117.8683)],
}
PRIMARY = {"Antwerp": "BRU Brussels", "Amsterdam": "AMS Schiphol", "Rio": "GIG Galeao", "LA": "LAX"}

hdr("A1  Distance to nearest major airport -- does it explain anything?")
for c in CITY_ORDER:
    r = C[c]
    for x in r:
        ds = [(haversine(x['lat'], x['lon'], la, lo), nm) for nm, la, lo in AIRPORTS[c]]
        x['d_air'], x['near_air'] = min(ds)
        x['d_primary'] = [d for d, nm in ds if nm == PRIMARY[c]][0]

    d = [x['d_air'] for x in r]
    lp = [math.log(x['price']) for x in r]
    print(f"\n{c}  (airports: {', '.join(nm for nm,_,_ in AIRPORTS[c])})")
    print(f"  distance to NEAREST airport: p10={pctile(d,.1):5.1f} med={st.median(d):5.1f} "
          f"p90={pctile(d,.9):5.1f} max={max(d):5.1f} km")
    print(f"  corr(dist_nearest, log price)  = {safe_corr(d, lp):+.3f}")
    print(f"  corr(dist_primary, log price)  = {safe_corr([x['d_primary'] for x in r], lp):+.3f}")
    print(f"  corr(dist_nearest, rpm)        = {safe_corr(d, [x['rpm'] for x in r]):+.3f}")

    # within neighbourhood x room type -- the control that mattered for Finding 4
    cells = defaultdict(list)
    for x in r: cells[(x['nbhd'], x['room'])].append(x)
    cors = []
    for grp in cells.values():
        if len(grp) < 40: continue
        cc = safe_corr([g['d_air'] for g in grp], [math.log(g['price']) for g in grp])
        if cc is not None: cors.append(cc)
    if cors:
        s = summarise(cors)
        print(f"  within nbhd x room type: {s['n']} cells, median r {s['median']:+.3f}, "
              f"positive in {s['share_pos']:.0%}")
    # median price index by distance band
    bands = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 999)]
    out = []
    for lo_, hi_ in bands:
        g = [x['price_index'] for x in r if lo_ <= x['d_air'] < hi_]
        if len(g) >= 40: out.append(f"{lo_}-{hi_}km:{st.median(g):.2f}(n={len(g)})")
    print("  median price index by band: " + "  ".join(out))

hdr("A2  English-language title -- does positioning for an international guest change demand?")
EN_ONLY = set("""the and with a an in of to for at on your our my is best great new near close view apartment
room house home studio loft private cozy cosy beautiful modern luxury spacious bright charming heart city
centre center beach downtown lovely amazing stunning perfect large small quiet flat suite penthouse""".split())
for c in CITY_ORDER:
    r = C[c]
    def has_en(x): return bool(set(re.findall(r"[a-z]+", x['name'].lower())) & EN_ONLY)
    share = sum(1 for x in r if has_en(x)) / len(r)
    cells = defaultdict(lambda: {'y': [], 'n': []})
    for x in r:
        cells[(x['nbhd'], x['room'])]['y' if has_en(x) else 'n'].append(x)
    gap_rpm = [st.median([g['rpm'] for g in v['y']]) - st.median([g['rpm'] for g in v['n']])
               for v in cells.values() if len(v['y']) >= 15 and len(v['n']) >= 15]
    gap_p = [st.median([g['price'] for g in v['y']]) / st.median([g['price'] for g in v['n']])
             for v in cells.values() if len(v['y']) >= 15 and len(v['n']) >= 15]
    if len(gap_rpm) < 5:
        print(f"{c:10s} English title {share:5.1%} -- too few mixed cells to test ({len(gap_rpm)})")
        continue
    s = summarise(gap_rpm)
    print(f"{c:10s} English title {share:5.1%} | {s['n']} mixed cells | rpm gap {s['median']:+.3f} "
          f"(English higher in {s['share_pos']:.0%}) | price ratio {st.median(gap_p):.2f}x")

hdr("A3  Cross-currency robustness: FX and PPP versions of 'what does a night cost'")
# Mid-2023 rates, roughly contemporaneous with the July-2023 file dates.
FX = {"Antwerp": 1.09, "Amsterdam": 1.09, "Rio": 0.205, "LA": 1.0}       # local -> USD
PPP = {"Antwerp": 1.36, "Amsterdam": 1.36, "Rio": 0.415, "LA": 1.0}      # local -> USD at PPP (OECD-style)
print(f"{'city':10s} {'med local':>10s} {'med USD@FX':>11s} {'med USD@PPP':>12s} {'entire-home med USD@FX':>24s}")
for c in CITY_ORDER:
    r = C[c]
    m = st.median([x['price'] for x in r])
    eh = st.median([x['price'] for x in r if x['room'] == 'Entire home/apt'])
    print(f"{c:10s} {m:10.0f} {m*FX[c]:11.0f} {m*PPP[c]:12.0f} {eh*FX[c]:24.0f}")
print("\n  Rank order under each normalisation (cheapest -> dearest):")
for lab, tbl in (("price index", None), ("FX", FX), ("PPP", PPP)):
    if tbl is None: continue
    order = sorted(CITY_ORDER, key=lambda c: st.median([x['price'] for x in C[c]]) * tbl[c])
    print(f"    {lab:12s} {' < '.join(order)}")
