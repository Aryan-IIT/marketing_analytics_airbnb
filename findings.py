"""
Reproduces the five findings in Airbnb_Assignment_Approach.pdf.

Pure standard library, so it runs anywhere without installing anything.
    python3 findings.py

Once pandas/matplotlib are available, spec_curve() returns the rows you need
to plot the actual specification curve (Finding 3).
"""

import csv
import math
import statistics as st
from pathlib import Path

DATA = Path(__file__).parent / "datasets"
FILES = {
    "Antwerp":   "listings-Belgium.csv",       # NOT Belgium -- Antwerp city only
    "Amsterdam": "listings-Netherlands.csv",   # NOT the Netherlands -- Amsterdam, 22 districts
    "Rio":       "listings-RIo_de_Janeiro.csv",
    "LA":        "listings_California.csv",    # NOT California -- Los Angeles County
}
PRO_DEFAULT = 3          # a "professional" host holds at least this many listings
CITY_ORDER = ["Antwerp", "Amsterdam", "Rio", "LA"]


def load(city):
    """Apply the shared cleaning rules. Everyone imports this, nobody rewrites it."""
    rows = []
    for r in csv.DictReader(open(DATA / FILES[city], encoding="utf-8")):
        try:
            price = float(r["price"])
        except ValueError:
            continue
        if price <= 0:                      # 19 such listings across all four files
            continue
        rows.append({
            "price": price,
            "room": r["room_type"],
            "nbhd": r["neighbourhood"],
            "host": r["host_id"],
            "host_listings": float(r["calculated_host_listings_count"]),
            "reviews": float(r["number_of_reviews"]),
            # blank exactly when reviews == 0, so this is structural, not missing-at-random
            "rpm": float(r["reviews_per_month"]) if r["reviews_per_month"].strip() else 0.0,
            "min_nights": min(float(r["minimum_nights"]), 365),
            "avail": float(r["availability_365"]),
            "lat": float(r["latitude"]),
            "lon": float(r["longitude"]),
        })
    med = st.median([r["price"] for r in rows])
    for r in rows:
        r["price_index"] = r["price"] / med          # unit-free, survives the currency problem
        r["pro"] = r["host_listings"] >= PRO_DEFAULT
    return rows


def pctile(values, q):
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


# --------------------------------------------------------------------------
# Finding 1 -- the entire-home premium replicates in every neighbourhood
# --------------------------------------------------------------------------
def finding1(rows, min_per_cell=30):
    by = {}
    for r in rows:
        by.setdefault(r["nbhd"], {}).setdefault(r["room"], []).append(r["price"])
    ratios = [
        st.median(v["Entire home/apt"]) / st.median(v["Private room"])
        for v in by.values()
        if len(v.get("Entire home/apt", [])) >= min_per_cell
        and len(v.get("Private room", [])) >= min_per_cell
    ]
    if not ratios:
        return None
    return {
        "n_nbhds": len(ratios),
        "median_ratio": st.median(ratios),
        "share_above_1": sum(1 for x in ratios if x > 1) / len(ratios),
    }


# --------------------------------------------------------------------------
# Finding 2 -- higher price, fewer reviews per month, within nbhd x room type
# --------------------------------------------------------------------------
def finding2(rows, min_per_cell=40):
    cells = {}
    for r in rows:
        if r["reviews"] > 0:                       # active listings only
            cells.setdefault((r["nbhd"], r["room"]), []).append(r)
    cors = []
    for grp in cells.values():
        if len(grp) < min_per_cell:
            continue
        x = [r["price"] for r in grp]
        y = [r["rpm"] for r in grp]
        if len(set(x)) > 5 and len(set(y)) > 5:
            cors.append(st.correlation(x, y))
    if not cors:
        return None
    return {
        "n_cells": len(cors),
        "median_r": st.median(cors),
        "share_negative": sum(1 for c in cors if c < 0) / len(cors),
    }


# --------------------------------------------------------------------------
# Finding 3 -- the specification curve. The centrepiece.
# Returns one row per specification: (effect_pct, choices dict).
# Sort by effect_pct and plot; the dict drives the panel underneath.
# --------------------------------------------------------------------------
def spec_curve(rows):
    out = []
    for thr in (2, 3, 5):
        for sample in ("all", "active", "entire"):
            for outlier in ("none", "winsor", "trim"):
                for stat in ("median", "geomean"):
                    s = rows
                    if sample == "active":
                        s = [r for r in s if r["reviews"] > 0]
                    elif sample == "entire":
                        s = [r for r in s if r["room"] == "Entire home/apt"]
                    if not s:
                        continue
                    prices = [r["price"] for r in s]
                    lo, hi = pctile(prices, 0.01), pctile(prices, 0.99)
                    if outlier == "winsor":
                        s = [{**r, "price": min(max(r["price"], lo), hi)} for r in s]
                    elif outlier == "trim":
                        s = [r for r in s if lo <= r["price"] <= hi]

                    pro = [r["price"] for r in s if r["host_listings"] >= thr]
                    ama = [r["price"] for r in s if r["host_listings"] < thr]
                    if len(pro) < 30 or len(ama) < 30:
                        continue
                    if stat == "median":
                        a, b = st.median(pro), st.median(ama)
                    else:
                        a = math.exp(st.mean(map(math.log, pro)))
                        b = math.exp(st.mean(map(math.log, ama)))
                    out.append((100 * (a / b - 1),
                                {"threshold": thr, "sample": sample,
                                 "outlier": outlier, "statistic": stat}))
    return sorted(out, key=lambda row: row[0])


# --------------------------------------------------------------------------
# Finding 4 -- control for neighbourhood AND room type, and the strategies split
# --------------------------------------------------------------------------
def finding4(rows, min_per_side=15):
    cells = {}
    for r in rows:
        key = (r["nbhd"], r["room"])
        cells.setdefault(key, {"pro": [], "ama": []})
        cells[key]["pro" if r["pro"] else "ama"].append(r["price"])
    diffs = [
        (100 * (st.median(v["pro"]) / st.median(v["ama"]) - 1), nbhd, room)
        for (nbhd, room), v in cells.items()
        if len(v["pro"]) >= min_per_side and len(v["ama"]) >= min_per_side
    ]
    if not diffs:
        return None
    vals = [d[0] for d in diffs]
    return {
        "n_cells": len(diffs),
        "median_premium": st.median(vals),
        "n_pro_cheaper": sum(1 for v in vals if v < 0),
        "extremes": (min(diffs), max(diffs)),   # inspect these before quoting any cell
    }


# --------------------------------------------------------------------------
# Finding 5 -- double jeopardy, treating neighbourhoods as brands. This one FAILS.
# Report it anyway; a failed test is worth more than another confirmed one.
# --------------------------------------------------------------------------
def finding5(rows, min_size=50):
    by = {}
    for r in rows:
        by.setdefault(r["nbhd"], []).append(r)
    big = [v for v in by.values() if len(v) >= min_size]
    if len(big) < 8:
        return None
    x = [math.log(len(v)) for v in big]
    y = [st.median([r["rpm"] for r in v]) for v in big]
    return {"n_nbhds": len(big), "corr": st.correlation(x, y)}


if __name__ == "__main__":
    cities = {c: load(c) for c in CITY_ORDER}

    print("\nFINDING 1 -- entire-home premium replicates")
    for c, rows in cities.items():
        f = finding1(rows)
        print(f"  {c:10s} {f['n_nbhds']:3d} nbhds | median {f['median_ratio']:.2f}x "
              f"| above 1.0 in {f['share_above_1']:.0%}")

    print("\nFINDING 2 -- price vs reviews/month, within nbhd x room type")
    for c, rows in cities.items():
        f = finding2(rows)
        print(f"  {c:10s} {f['n_cells']:3d} cells | median r {f['median_r']:+.3f} "
              f"| negative in {f['share_negative']:.0%}")

    print("\nFINDING 3 -- specification curve, 'do professionals charge more?'")
    for c, rows in cities.items():
        specs = spec_curve(rows)
        vals = [v for v, _ in specs]
        pos = sum(1 for v in vals if v > 0)
        flag = "SIGN FLIPS" if 0 < pos < len(vals) else "stable"
        print(f"  {c:10s} {len(specs):2d} specs | {vals[0]:+6.1f}% to {vals[-1]:+6.1f}% "
              f"| median {st.median(vals):+6.1f}% | positive {pos:2d}/{len(vals)}  {flag}")

    print("\nFINDING 4 -- premium within neighbourhood AND room type")
    for c, rows in cities.items():
        f = finding4(rows)
        print(f"  {c:10s} {f['n_cells']:3d} cells | median {f['median_premium']:+6.1f}% "
              f"| pros cheaper in {f['n_pro_cheaper']}/{f['n_cells']}")

    print("\nFINDING 5 -- double jeopardy (expected to fail)")
    for c, rows in cities.items():
        f = finding5(rows)
        print(f"  {c:10s} {f['n_nbhds']:3d} nbhds | corr(log size, median rpm) = {f['corr']:+.3f}")
    print("  -> no consistent pattern: the law does not hold here. Report it.\n")
