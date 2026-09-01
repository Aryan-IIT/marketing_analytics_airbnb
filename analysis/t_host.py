import statistics as st, math, re
from collections import Counter, defaultdict
from lib import all_cities, CITY_ORDER, pctile, safe_corr, summarise

C = all_cities()
def hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ---------------------------------------------------------------- H1
hdr("H1  How much pricing guidance does the data give? variance of log price explained")
print("R2 of log(price) on neighbourhood x room-type cell means -- high R2 = the comps tell you what to charge")
for c in CITY_ORDER:
    r = C[c]
    y = [math.log(x['price']) for x in r]
    gm = st.mean(y)
    sst = sum((v - gm) ** 2 for v in y)
    for label, keyfn in (("nbhd only", lambda x: x['nbhd']),
                         ("room only", lambda x: x['room']),
                         ("nbhd x room", lambda x: (x['nbhd'], x['room']))):
        g = defaultdict(list)
        for x in r: g[keyfn(x)].append(math.log(x['price']))
        ssb = sum(len(v) * (st.mean(v) - gm) ** 2 for v in g.values())
        print(f"{c:10s} {label:12s} R2={ssb/sst:.3f}  (k={len(g)})" if label != "nbhd x room"
              else f"{c:10s} {label:12s} R2={ssb/sst:.3f}  (k={len(g)})   <-- residual spread left to the host: "
                   f"{math.exp(math.sqrt((sst-ssb)/len(y))):.2f}x")

# ---------------------------------------------------------------- H2
hdr("H2  Does a longer minimum stay cost bookings? corr(min_nights, rpm) within cell")
for c in CITY_ORDER:
    r = [x for x in C[c] if x['reviews'] > 0]
    cells = defaultdict(list)
    for x in r: cells[(x['nbhd'], x['room'])].append(x)
    cors = []
    for grp in cells.values():
        if len(grp) < 40: continue
        cc = safe_corr([math.log(g['min_nights']) for g in grp], [g['rpm'] for g in grp])
        if cc is not None: cors.append(cc)
    s = summarise(cors)
    # also the blunt version: median rpm at 1n vs 2-3n vs 7n vs 30n
    seg = {}
    for lab, f in (("1n", lambda x: x['min_nights'] == 1), ("2-3n", lambda x: 2 <= x['min_nights'] <= 3),
                   ("4-7n", lambda x: 4 <= x['min_nights'] <= 7), ("28n+", lambda x: x['min_nights'] >= 28)):
        g = [x['rpm'] for x in C[c] if f(x)]
        seg[lab] = st.median(g) if len(g) >= 30 else None
    print(f"{c:10s} {s['n']:3d} cells | median r {s['median']:+.3f} | negative in {1-s['share_pos']:.0%} "
          f"|| median rpm all listings: " + " ".join(f"{k}={v:.2f}" for k, v in seg.items() if v is not None))

# ---------------------------------------------------------------- H3
hdr("H3  Does being available more of the year get more reviews? corr(avail, rpm) within cell")
for c in CITY_ORDER:
    r = [x for x in C[c] if x['avail'] > 0]
    cells = defaultdict(list)
    for x in r: cells[(x['nbhd'], x['room'])].append(x)
    cors = []
    for grp in cells.values():
        if len(grp) < 40: continue
        cc = safe_corr([g['avail'] for g in grp], [g['rpm'] for g in grp])
        if cc is not None: cors.append(cc)
    s = summarise(cors)
    print(f"{c:10s} {s['n']:3d} cells | median r {s['median']:+.3f} | positive in {s['share_pos']:.0%}")

# ---------------------------------------------------------------- H4
hdr("H4  Newcomer pricing: do listings with no reviews price above or below their cell?")
for c in CITY_ORDER:
    r = C[c]
    cells = defaultdict(lambda: {'n': [], 'e': []})
    for x in r:
        cells[(x['nbhd'], x['room'])]['n' if x['reviews'] == 0 else 'e'].append(x['price'])
    d = [100 * (st.median(v['n']) / st.median(v['e']) - 1) for v in cells.values()
         if len(v['n']) >= 15 and len(v['e']) >= 15]
    s = summarise(d)
    print(f"{c:10s} {s['n']:3d} cells | no-review listings priced {s['median']:+6.1f}% vs reviewed ones "
          f"| above in {s['share_pos']:.0%} of cells")

# ---------------------------------------------------------------- H5
hdr("H5  Price endings: charm pricing / round numbers, and does it track anything?")
for c in CITY_ORDER:
    r = C[c]; n = len(r)
    ends = Counter(int(x['price']) % 10 for x in r)
    round10 = sum(1 for x in r if int(x['price']) % 10 == 0) / n
    round50 = sum(1 for x in r if int(x['price']) % 50 == 0) / n
    nine = ends[9] / n
    # do round-price hosts differ? compare within cell
    cells = defaultdict(lambda: {'r': [], 'o': []})
    for x in r:
        cells[(x['nbhd'], x['room'])]['r' if int(x['price']) % 10 == 0 else 'o'].append(x)
    gap = [st.median([g['rpm'] for g in v['r']]) - st.median([g['rpm'] for g in v['o']])
           for v in cells.values() if len(v['r']) >= 15 and len(v['o']) >= 15]
    pro_r = sum(1 for x in r if int(x['price']) % 10 == 0 and x['pro'])
    pro_all = sum(1 for x in r if int(x['price']) % 10 == 0)
    s = summarise(gap) if gap else None
    print(f"{c:10s} ends in 0: {round10:5.1%} | multiple of 50: {round50:5.1%} | ends in 9: {nine:5.1%} "
          f"| pro share among round-priced {pro_r/max(1,pro_all):5.1%} vs {sum(1 for x in r if x['pro'])/n:5.1%} overall")
    if s: print(f"{'':10s}    rpm gap round-minus-other within cell: {s['median']:+.3f} in {s['n']} cells "
                f"(round higher in {s['share_pos']:.0%})")

# ---------------------------------------------------------------- H6
hdr("H6  Competitive density: in a busier neighbourhood, does each listing get fewer bookings?")
print("corr(log listings in nbhd, median rpm of nbhd) -- and within room type")
for c in CITY_ORDER:
    r = C[c]
    by = defaultdict(list)
    for x in r:
        if x['room'] == 'Entire home/apt': by[x['nbhd']].append(x)
    big = [(k, v) for k, v in by.items() if len(v) >= 50]
    if len(big) < 8:
        print(f"{c:10s} too few"); continue
    cc = safe_corr([math.log(len(v)) for _, v in big], [st.median([g['rpm'] for g in v]) for _, v in big])
    cp = safe_corr([math.log(len(v)) for _, v in big], [math.log(st.median([g['price'] for g in v])) for _, v in big])
    print(f"{c:10s} {len(big):3d} nbhds | corr(size, rpm) {cc:+.3f} | corr(size, log price) {cp:+.3f}")

# ---------------------------------------------------------------- H7
hdr("H7  Does the host's own scale change their listing's fate? (within-host spread)")
for c in CITY_ORDER:
    r = C[c]
    by = defaultdict(list)
    for x in r: by[x['host']].append(x)
    multi = [v for v in by.values() if len(v) >= 3]
    if len(multi) < 20:
        print(f"{c:10s} too few multi-listing hosts"); continue
    # within a host's portfolio, how much do prices vary? and do they diversify room type / nbhd?
    cv = [st.pstdev([g['price'] for g in v]) / st.mean([g['price'] for g in v]) for v in multi]
    one_nbhd = sum(1 for v in multi if len(set(g['nbhd'] for g in v)) == 1) / len(multi)
    one_room = sum(1 for v in multi if len(set(g['room'] for g in v)) == 1) / len(multi)
    print(f"{c:10s} {len(multi):5d} hosts with 3+ | median within-host price CV {st.median(cv):.2f} | "
          f"all in one nbhd {one_nbhd:5.1%} | all one room type {one_room:5.1%}")

# ---------------------------------------------------------------- H8
hdr("H8  Listing title: length and language signals")
EN = set("the and with a in of to for at on your our my is best great new near close view apartment room house home studio loft private cozy cosy beautiful modern luxury spacious bright charming heart city centre center beach downtown".split())
LOCAL = {
    "Antwerp": set("het een met van in op voor bij aan kamer woning appartement huis gezellig prachtig ruim nabij stad centrum en de".split()),
    "Amsterdam": set("het een met van in op voor bij aan kamer woning appartement huis gezellig prachtig ruim nabij stad centrum en de".split()),
    "Rio": set("o a os as um uma com de do da em no na para casa quarto apartamento apto praia perto vista lindo otimo ótimo espacoso espaçoso e centro".split()),
    "LA": set(),
}
for c in CITY_ORDER:
    r = C[c]
    lens = [len(x['name']) for x in r]
    def toks(s): return set(re.findall(r"[a-zà-ÿ]+", s.lower()))
    en = sum(1 for x in r if toks(x['name']) & EN)
    lo = sum(1 for x in r if toks(x['name']) & LOCAL[c]) if LOCAL[c] else 0
    print(f"{c:10s} median title length {st.median(lens):3.0f} chars | title has an English word {en/len(r):5.1%} "
          + (f"| has a local-language word {lo/len(r):5.1%}" if LOCAL[c] else ""))

# ---------------------------------------------------------------- H9
hdr("H9  Keyword premia in the title, within nbhd x room type (price ratio, keyword vs not)")
KW = ["beach", "praia", "view", "vista", "pool", "piscina", "studio", "loft", "luxury", "luxo",
      "metro", "canal", "centro", "downtown", "quiet", "new", "garden"]
for c in CITY_ORDER:
    r = C[c]
    out = []
    for kw in KW:
        cells = defaultdict(lambda: {'y': [], 'n': []})
        for x in r:
            has = kw in x['name'].lower()
            cells[(x['nbhd'], x['room'])]['y' if has else 'n'].append(x['price'])
        d = [st.median(v['y']) / st.median(v['n']) for v in cells.values()
             if len(v['y']) >= 15 and len(v['n']) >= 15]
        if len(d) >= 5:
            out.append((kw, len(d), st.median(d)))
    out.sort(key=lambda t: -t[2])
    print(f"{c:10s} " + " | ".join(f"{k}:{v:.2f}x(n={n})" for k, n, v in out[:6]))
    print(f"{'':10s} " + " | ".join(f"{k}:{v:.2f}x(n={n})" for k, n, v in out[-3:]))
