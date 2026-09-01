import statistics as st
from collections import Counter
from lib import all_cities, CITY_ORDER, pctile, CCY

C = all_cities()

print("=== SIZE, PRICE SHAPE ===")
for c in CITY_ORDER:
    r = C[c]
    p = [x["price"] for x in r]
    print(f"{c:10s} n={len(r):6d} {CCY[c]}  p10={pctile(p,.10):8.0f} p25={pctile(p,.25):8.0f} "
          f"med={st.median(p):8.0f} p75={pctile(p,.75):8.0f} p90={pctile(p,.90):8.0f} "
          f"p99={pctile(p,.99):9.0f} max={max(p):9.0f}  IQRratio={pctile(p,.75)/pctile(p,.25):.2f}")

print("\n=== ROOM TYPE MIX (share of listings) ===")
for c in CITY_ORDER:
    ct = Counter(x["room"] for x in C[c])
    n = len(C[c])
    print(f"{c:10s} " + "  ".join(f"{k}={v/n:.1%}" for k, v in ct.most_common()))

print("\n=== ROOM TYPE MIX (share of REVIEWS) ===")
for c in CITY_ORDER:
    tot = sum(x["reviews"] for x in C[c])
    ct = Counter()
    for x in C[c]:
        ct[x["room"]] += x["reviews"]
    print(f"{c:10s} " + "  ".join(f"{k}={v/tot:.1%}" for k, v in ct.most_common()))

print("\n=== ZERO-REVIEW SHARE / DORMANCY ===")
for c in CITY_ORDER:
    r = C[c]
    z = sum(1 for x in r if x["reviews"] == 0) / len(r)
    a0 = sum(1 for x in r if x["avail"] == 0) / len(r)
    a365 = sum(1 for x in r if x["avail"] >= 360) / len(r)
    print(f"{c:10s} zero-review={z:.1%}  avail=0 {a0:.1%}  avail>=360 {a365:.1%}  "
          f"median avail={st.median([x['avail'] for x in r]):.0f}  median rpm={st.median([x['rpm'] for x in r]):.2f}")

print("\n=== MINIMUM NIGHTS DISTRIBUTION ===")
for c in CITY_ORDER:
    r = C[c]
    mn = [x["min_nights"] for x in r]
    ct = Counter(int(m) for m in mn)
    n = len(r)
    print(f"{c:10s} med={st.median(mn):.0f}  <=3n:{sum(1 for m in mn if m<=3)/n:.1%}  "
          f"==30:{ct[30]/n:.1%}  >=28:{sum(1 for m in mn if m>=28)/n:.1%}  "
          f"top: {[(k,round(v/n*100,1)) for k,v in ct.most_common(6)]}")

print("\n=== HOST STRUCTURE ===")
for c in CITY_ORDER:
    r = C[c]
    n = len(r)
    solo = sum(1 for x in r if x["host_listings"] == 1) / n
    pro = sum(1 for x in r if x["host_listings"] >= 3) / n
    big = sum(1 for x in r if x["host_listings"] >= 10) / n
    nh = len(set(x["host"] for x in r))
    print(f"{c:10s} hosts={nh:6d}  1-listing={solo:.1%}  3+={pro:.1%}  10+={big:.1%}  "
          f"listings/host={n/nh:.2f}")

print("\n=== NEIGHBOURHOOD COUNTS ===")
for c in CITY_ORDER:
    r = C[c]
    ct = Counter(x["nbhd"] for x in r)
    big = sum(1 for v in ct.values() if v >= 50)
    print(f"{c:10s} nbhds={len(ct):4d}  with>=50 listings={big:4d}  "
          f"top3={[(k,v) for k,v in ct.most_common(3)]}")

print("\n=== NBHD_GROUP (LA only) ===")
for c in CITY_ORDER:
    ct = Counter(x["nbhd_group"] for x in C[c])
    print(f"{c:10s} {dict(ct.most_common(5))}")

print("\n=== LAT/LON BOUNDING BOX ===")
for c in CITY_ORDER:
    r = C[c]
    print(f"{c:10s} lat {min(x['lat'] for x in r):.3f}..{max(x['lat'] for x in r):.3f}  "
          f"lon {min(x['lon'] for x in r):.3f}..{max(x['lon'] for x in r):.3f}")
