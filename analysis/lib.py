"""Shared loader for candidate-question testing. Extends findings.load with
the raw `name` text and a few derived fields, keeping the same cleaning rules."""
import csv, math, sys
import statistics as st
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/Users/aryan/Desktop/Academics/semester_7/marketing_analytics/group_project_firsthalf")
DATA = ROOT / "datasets"
FILES = {
    "Antwerp":   "listings-Belgium.csv",
    "Amsterdam": "listings-Netherlands.csv",
    "Rio":       "listings-RIo_de_Janeiro.csv",
    "LA":        "listings_California.csv",
}
CITY_ORDER = ["Antwerp", "Amsterdam", "Rio", "LA"]
CCY = {"Antwerp": "EUR", "Amsterdam": "EUR", "Rio": "BRL", "LA": "USD"}


def load(city):
    rows = []
    for r in csv.DictReader(open(DATA / FILES[city], encoding="utf-8")):
        try:
            price = float(r["price"])
        except ValueError:
            continue
        if price <= 0:
            continue
        rows.append({
            "id": r["id"],
            "name": r["name"] or "",
            "price": price,
            "room": r["room_type"],
            "nbhd": r["neighbourhood"],
            "nbhd_group": r["neighbourhood_group"],
            "host": r["host_id"],
            "host_listings": float(r["calculated_host_listings_count"]),
            "reviews": float(r["number_of_reviews"]),
            "rpm": float(r["reviews_per_month"]) if r["reviews_per_month"].strip() else 0.0,
            "min_nights": min(float(r["minimum_nights"]), 365),
            "min_nights_raw": float(r["minimum_nights"]),
            "avail": float(r["availability_365"]),
            "lat": float(r["latitude"]),
            "lon": float(r["longitude"]),
        })
    med = st.median([r["price"] for r in rows])
    for r in rows:
        r["price_index"] = r["price"] / med
        r["pro"] = r["host_listings"] >= 3
        r["city"] = city
    return rows


def all_cities():
    return {c: load(c) for c in CITY_ORDER}


def pctile(values, q):
    v = sorted(values)
    if not v:
        return None
    return v[min(len(v) - 1, int(q * len(v)))]


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def safe_corr(x, y):
    if len(x) < 5 or len(set(x)) < 3 or len(set(y)) < 3:
        return None
    try:
        return st.correlation(x, y)
    except Exception:
        return None


def cellwise(rows, fn, min_n=40, keyfn=lambda r: (r["nbhd"], r["room"]), filt=None):
    """Run fn over each neighbourhood x room-type cell; return list of results.
    This is the workhorse: it is the control that stopped the Simpson's paradox."""
    cells = defaultdict(list)
    for r in rows:
        if filt and not filt(r):
            continue
        cells[keyfn(r)].append(r)
    out = []
    for k, grp in cells.items():
        if len(grp) < min_n:
            continue
        v = fn(grp)
        if v is not None:
            out.append((v, k, len(grp)))
    return out


def summarise(vals):
    if not vals:
        return None
    return {"n": len(vals), "median": st.median(vals),
            "share_pos": sum(1 for v in vals if v > 0) / len(vals)}
