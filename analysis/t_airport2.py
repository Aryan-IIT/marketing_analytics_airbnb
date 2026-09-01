"""The airport question, reframed: not 'does distance predict price' but
'if I must sleep near the airport, is there supply, what does it cost, and is it any good?'"""
import statistics as st, math
from collections import Counter, defaultdict
from lib import all_cities, CITY_ORDER, haversine, pctile, summarise

C = all_cities()
PRIMARY = {"Antwerp": ("BRU Brussels", 50.9014, 4.4844), "Amsterdam": ("AMS Schiphol", 52.3105, 4.7683),
           "Rio": ("GIG Galeao", -22.8090, -43.2506), "LA": ("LAX", 33.9416, -118.4085)}
SECOND = {"Antwerp": ("ANR Antwerp", 51.1894, 4.4603), "Rio": ("SDU Santos Dumont", -22.9105, -43.1631)}

def hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

hdr("B1  The airport catchment: is there supply within 5km / 10km of the main airport?")
for c in CITY_ORDER:
    nm, la, lo = PRIMARY[c]
    r = C[c]
    for x in r: x['da'] = haversine(x['lat'], x['lon'], la, lo)
    n = len(r)
    print(f"\n{c}  primary airport {nm}")
    for lim in (5, 10, 15):
        g = [x for x in r if x['da'] <= lim]
        if len(g) < 25:
            print(f"   <={lim:2d}km: {len(g):5d} listings ({len(g)/n:4.1%}) -- too thin to book into")
            continue
        eh = sum(1 for x in g if x['room'] == 'Entire home/apt') / len(g)
        short = sum(1 for x in g if x['min_nights'] <= 2) / len(g)
        print(f"   <={lim:2d}km: {len(g):5d} listings ({len(g)/n:4.1%}) | price index {st.median([x['price_index'] for x in g]):.2f} "
              f"| entire home {eh:4.1%} | bookable for <=2n {short:4.1%} | median rpm {st.median([x['rpm'] for x in g]):.2f} "
              f"(city {st.median([x['rpm'] for x in r]):.2f})")

hdr("B2  Do airport-adjacent neighbourhoods punch above their weight on demand?")
print("demand share / supply share for the neighbourhoods closest to the primary airport")
for c in CITY_ORDER:
    nm, la, lo = PRIMARY[c]
    r = C[c]
    totl, totd = len(r), sum(x['rpm'] for x in r)
    by = defaultdict(lambda: [0, 0.0, []])
    for x in r:
        b = by[x['nbhd']]
        b[0] += 1; b[1] += x['rpm']; b[2].append(haversine(x['lat'], x['lon'], la, lo))
    big = [(k, v[0], (v[1]/totd)/(v[0]/totl), st.median(v[2])) for k, v in by.items() if v[0] >= 50]
    big.sort(key=lambda t: t[3])
    print(f"\n{c}  ({nm})   nearest 4 neighbourhoods with >=50 listings:")
    for k, cnt, idx, d in big[:4]:
        print(f"    {k[:34]:34s} {d:5.1f}km  n={cnt:5d}  demand/supply index {idx:.2f}")
    allidx = [t[2] for t in big]
    print(f"    (city median index 1.00 by construction; observed median {st.median(allidx):.2f}, "
          f"p90 {pctile(sorted(allidx), .9):.2f})")

hdr("B3  Short-notice / early-flight suitability of airport stock vs the city as a whole")
for c in CITY_ORDER:
    nm, la, lo = PRIMARY[c]
    r = C[c]
    near = [x for x in r if haversine(x['lat'], x['lon'], la, lo) <= 10]
    if len(near) < 25:
        print(f"{c:10s} fewer than 25 listings within 10km of {nm} -- question is unanswerable here")
        continue
    f1 = lambda g: sum(1 for x in g if x['min_nights'] == 1) / len(g)
    print(f"{c:10s} within 10km of {nm}: 1-night-OK {f1(near):5.1%} vs city {f1(r):5.1%} | "
          f"price index {st.median([x['price_index'] for x in near]):.2f} | "
          f"zero-review {sum(1 for x in near if x['reviews']==0)/len(near):5.1%} vs city "
          f"{sum(1 for x in r if x['reviews']==0)/len(r):5.1%}")

hdr("B4  Secondary/city airports, where they exist")
for c, (nm, la, lo) in SECOND.items():
    r = C[c]
    for lim in (5, 10):
        g = [x for x in r if haversine(x['lat'], x['lon'], la, lo) <= lim]
        if len(g) >= 25:
            print(f"{c:10s} {nm:20s} <={lim:2d}km: {len(g):5d} listings ({len(g)/len(r):4.1%}) "
                  f"price index {st.median([x['price_index'] for x in g]):.2f} "
                  f"median rpm {st.median([x['rpm'] for x in g]):.2f}")
        else:
            print(f"{c:10s} {nm:20s} <={lim:2d}km: {len(g)} listings -- too thin")
