"""
datasets/*.csv  ->  docs/data/*.json + docs/figures/*.svg

Reproduces the computations in dashboard/four_master_questions.ipynb and writes
them out as small JSON plus per-panel SVGs recoloured to the deck's palette.
The site ships no CSVs; this is the only thing that reads them.

    ../../.venv/bin/python export_assets.py

Cleaning rules are findings.py's, restated here in pandas because the notebook
is pandas: price > 0, reviews_per_month blank -> 0 (blank exactly when
number_of_reviews is 0, so dropping would delete 42% of Rio), minimum_nights
capped at 365, professional = 3+ listings for that host.

Prints the regression table from plan.md section 5 at the end. If those twenty
numbers do not match, the site is wrong and nothing downstream is worth styling.
"""

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets"
OUT_DATA = ROOT / "docs" / "data"
OUT_FIG = ROOT / "docs" / "figures"

ORDER = ["Antwerp", "Amsterdam", "LA", "Rio"]
FILES = {
    "Antwerp":   ("listings-Belgium.csv",        "EUR", "€"),
    "Amsterdam": ("listings-Netherlands.csv",    "EUR", "€"),
    "LA":        ("listings_California.csv",     "USD", "$"),
    "Rio":       ("listings-RIo_de_Janeiro.csv", "BRL", "R$"),
}
PRO_THRESHOLD = 3
MIN_CELL_N = 10          # cells thinner than this never reach the browser
TRUST_N = 30             # below this the tool says "too thin" instead of a number

# ---------------------------------------------------------------- deck palette
# Sampled from Airbnb_Marketing_Analytics_Deck_Templated.pdf, not eyeballed.
MAGENTA = "#FF3EB5"      # the deck accent, for the one value each panel is about
MAGENTA_INK = "#B00070"  # darkened for text; #FF3EB5 fails contrast on white
INK = "#1d1d1d"
MUTE = "#6b6b6b"
RULE = "#E3E3E8"
BAR = "#B9BCC4"          # every other bar
TINTS = ["#FF3EB5", "#FF8FD2", "#FFC7E8", "#EFEFF3"]   # sequential, for stacks
SANS = "Carlito, Calibri, 'Segoe UI', system-ui, sans-serif"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": RULE, "text.color": INK,
    "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.grid": False,
    "font.size": 10, "svg.fonttype": "none",
    "xtick.major.size": 0, "ytick.major.size": 0,
})


def load():
    frames = []
    for city, (fname, currency, symbol) in FILES.items():
        df = pd.read_csv(DATA_DIR / fname, low_memory=False)
        df = df[pd.to_numeric(df["price"], errors="coerce") > 0].copy()
        df["price"] = df["price"].astype(float)
        df["city"] = city
        df["currency"] = currency
        df["reviews_per_month"] = df["reviews_per_month"].fillna(0)
        df["minimum_nights"] = df["minimum_nights"].clip(upper=365)
        df["professional"] = df["calculated_host_listings_count"] >= PRO_THRESHOLD
        frames.append(df)
    data = pd.concat(frames, ignore_index=True)
    data["price_index"] = data["price"] / data.groupby("city")["price"].transform("median")
    return data


# ------------------------------------------------------------------ SVG output
def save(fig, name):
    """Write a viewBox-only SVG so CSS controls the size, with a web font stack."""
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    path = OUT_FIG / f"{name}.svg"
    fig.savefig(path, format="svg", bbox_inches="tight", pad_inches=0.08,
                transparent=True)
    plt.close(fig)
    svg = path.read_text()
    svg = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"\s+height="[^"]*"', r"\1", svg, count=1)
    svg = svg.replace("DejaVu Sans", SANS.replace("'", ""))
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    path.write_text(svg)
    return path


def panel(w=6.4, h=2.9):
    fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax


def hbars(ax, labels, values, fmt, highlight, xpad=1.34, note=None):
    """Horizontal bars, ink-grey except the one the panel is about.

    No x tick labels: every value is printed at the end of its own bar, so a
    scale underneath would be decoration. The bottom spine goes too.
    """
    colors = [MAGENTA if c in highlight else BAR for c in labels]
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, height=0.6, zorder=3)
    span = max(abs(v) for v in values) or 1
    for yi, v, lab in zip(y, values, labels):
        off = 0.025 * span * (1 if v >= 0 else -1)
        ax.text(v + off, yi, fmt.format(v), va="center",
                ha="left" if v >= 0 else "right", fontsize=10.5,
                fontweight="bold",
                color=MAGENTA_INK if lab in highlight else INK)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10.5)
    ax.invert_yaxis()
    lo, hi = min(0, min(values)), max(0, max(values))
    ax.set_xlim(lo * xpad if lo < 0 else 0, hi * xpad if hi > 0 else 0)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    if note:
        ax.set_xlabel(note, fontsize=9, labelpad=6)
    return ax


def main():
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    data = load()
    print(f"loaded {len(data):,} listings")

    ent = data[data["room_type"] == "Entire home/apt"]
    med_entire = {c: float(ent[ent["city"] == c]["price"].median()) for c in ORDER}
    med_all = {c: float(data[data["city"] == c]["price"].median()) for c in ORDER}

    # ============================================================ Q1
    # A - room type mix
    mix = (pd.crosstab(data["city"], data["room_type"], normalize="index")
             .reindex(ORDER)
             .reindex(columns=["Entire home/apt", "Private room", "Shared room", "Hotel room"],
                      fill_value=0) * 100)
    fig, ax = panel(6.4, 3.1)
    left = np.zeros(len(ORDER))
    y = np.arange(len(ORDER))
    for col, c in zip(mix.columns, TINTS):
        ax.barh(y, mix[col], left=left, color=c, height=0.6, label=col, zorder=3)
        for yi, (l, v) in enumerate(zip(left, mix[col])):
            if v > 7:
                ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center",
                        fontsize=9.5, fontweight="bold",
                        color="white" if c == MAGENTA else INK)
        left += mix[col].values
    ax.set_yticks(y); ax.set_yticklabels(ORDER, fontsize=10.5); ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=4,
              frameon=False, fontsize=8.5, handlelength=1.1, columnspacing=1.2)
    save(fig, "q1-a-room-mix")

    # B - cost of guessing the citywide price
    errs = {}
    for city in ORDER:
        g = ent[ent["city"] == city]
        nb = g.groupby("neighbourhood")["price"].median()
        errs[city] = float(((nb - g["price"].median()).abs() / nb).median() * 100)
    worst = max(errs, key=errs.get)
    fig, ax = panel()
    hbars(ax, ORDER, [errs[c] for c in ORDER], "{:.0f}% off", {worst},
          note="median % error, entire-home listings")
    save(fig, "q1-b-price-guess-error")

    # C - host concentration
    conc = {}
    for city in ORDER:
        g = data[data["city"] == city]
        hc = g.groupby("host_id").size()
        conc[city] = {"pro_share": float(g["professional"].mean() * 100),
                      "hhi": float(((hc / hc.sum()) ** 2).sum() * 10000)}
    top_hhi = max(conc, key=lambda c: conc[c]["hhi"])
    fig, ax = panel(6.4, 3.4)
    for city in ORDER:
        c = MAGENTA if city == top_hhi else BAR
        ax.scatter(conc[city]["pro_share"], conc[city]["hhi"], s=620, color=c,
                   edgecolor="white", linewidth=2, zorder=3)
        ax.annotate(city, (conc[city]["pro_share"], conc[city]["hhi"]),
                    xytext=(0, -22), textcoords="offset points", ha="center",
                    fontsize=10.5, fontweight="bold", color=INK, zorder=4)
    ax.set_xlabel("% of listings from professional (3+) hosts", fontsize=9)
    ax.set_ylabel("market concentration (HHI)", fontsize=9)
    ax.margins(0.28)
    ax.spines["left"].set_visible(True)
    ax.tick_params(labelsize=9)
    save(fig, "q1-c-host-concentration")

    # D - price spread within a niche
    cvs, spreads = {}, {}
    for city in ORDER:
        g = data[data["city"] == city]
        cv_vals, sp_vals = [], []
        for _, cell in g.groupby(["neighbourhood", "room_type"], observed=True):
            if len(cell) >= 8:
                q1, q3 = cell["price"].quantile([0.25, 0.75])
                med = cell["price"].median()
                if med > 0:
                    cv_vals.append((q3 - q1) / med)
                if q1 > 0:
                    sp_vals.append(q3 / q1)
        cvs[city] = float(np.median(cv_vals))
        spreads[city] = float(np.median(sp_vals))
    widest = max(cvs, key=cvs.get)
    fig, ax = panel()
    hbars(ax, ORDER, [cvs[c] for c in ORDER], "{:.2f}", {widest},
          note="IQR ÷ median, within neighbourhood × room type")
    save(fig, "q1-d-price-spread")

    # ============================================================ Q2
    # A - entire-home premium
    ratios = {}
    for city in ORDER:
        vals = []
        for _, cell in data[data["city"] == city].groupby("neighbourhood", observed=True):
            eh = cell.loc[cell["room_type"] == "Entire home/apt", "price"]
            pr = cell.loc[cell["room_type"] == "Private room", "price"]
            if len(eh) >= 3 and len(pr) >= 3:
                vals.append(eh.median() / pr.median())
        ratios[city] = float(np.median(vals))
    best = max(ratios, key=ratios.get)
    fig, ax = panel(6.4, 3.0)
    y = np.arange(len(ORDER))
    for yi, city in zip(y, ORDER):
        c = MAGENTA if city == best else BAR
        ax.plot([1, ratios[city]], [yi, yi], color=c, lw=4, solid_capstyle="butt", zorder=3)
        ax.scatter([ratios[city]], [yi], s=260, color=c, zorder=4,
                   edgecolor="white", linewidth=1.5)
        ax.text(ratios[city] + 0.09, yi, f"{ratios[city]:.2f}×", va="center",
                fontsize=10.5, fontweight="bold",
                color=MAGENTA_INK if city == best else INK)
    ax.axvline(1.0, color=MUTE, lw=1, ls=(0, (4, 3)), zorder=2)
    ax.text(1.0, -0.75, "parity", color=MUTE, fontsize=9, ha="center")
    ax.set_yticks(y); ax.set_yticklabels(ORDER, fontsize=10.5); ax.invert_yaxis()
    ax.set_xlim(0.8, max(ratios.values()) * 1.2)
    ax.set_ylim(len(ORDER) - 0.4, -0.95)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_xlabel("price ratio, entire home ÷ private room", fontsize=9, labelpad=6)
    save(fig, "q2-a-entire-home-premium")

    # B - professional pricing premium
    prems = {}
    for city in ORDER:
        vals = []
        for _, cell in data[data["city"] == city].groupby(
                ["neighbourhood", "room_type"], observed=True):
            pro = cell.loc[cell["professional"], "price"]
            ind = cell.loc[~cell["professional"], "price"]
            if len(pro) >= 3 and len(ind) >= 3:
                vals.append((pro.median() - ind.median()) / ind.median())
        prems[city] = float(np.median(vals) * 100)
    penal = min(prems, key=prems.get)
    fig, ax = panel()
    hbars(ax, ORDER, [prems[c] for c in ORDER], "{:+.0f}%", {penal},
          note="price premium vs individual hosts, same niche")
    ax.axvline(0, color=INK, lw=1, zorder=4)
    save(fig, "q2-b-professional-premium")

    # C - minimum-stay penalty
    rhos = {}
    for city in ORDER:
        vals = []
        for _, cell in data[data["city"] == city].groupby(
                ["neighbourhood", "room_type"], observed=True):
            if len(cell) >= 10 and cell["minimum_nights"].nunique() > 1:
                r, _ = stats.spearmanr(cell["minimum_nights"], cell["reviews_per_month"])
                if not np.isnan(r):
                    vals.append(r)
        rhos[city] = float(np.median(vals))
    steep = min(rhos, key=rhos.get)
    fig, ax = panel()
    hbars(ax, ORDER, [rhos[c] for c in ORDER], "{:.2f}", {steep},
          note="Spearman ρ: minimum nights vs bookings/month")
    ax.axvline(0, color=INK, lw=1, zorder=4)
    save(fig, "q2-c-minimum-stay")

    # D - review count vs price (the reverse-causation panel)
    rhos2 = {}
    for city in ORDER:
        vals = []
        for _, cell in data[data["city"] == city].groupby(
                ["neighbourhood", "room_type"], observed=True):
            if len(cell) >= 10 and cell["number_of_reviews"].nunique() > 1:
                r, _ = stats.spearmanr(cell["number_of_reviews"], cell["price"])
                if not np.isnan(r):
                    vals.append(r)
        rhos2[city] = float(np.median(vals))
    steep2 = min(rhos2, key=rhos2.get)
    fig, ax = panel()
    hbars(ax, ORDER, [rhos2[c] for c in ORDER], "{:.2f}", {steep2},
          note="Spearman ρ: review count vs price — not a causal estimate")
    ax.axvline(0, color=INK, lw=1, zorder=4)
    save(fig, "q2-d-reviews-vs-price")

    # ============================================================ Q4 supporting
    ams = data[data["city"] == "Amsterdam"]
    rio = data[data["city"] == "Rio"]
    groups = [
        ("Amsterdam\nCentrum", ams[ams["neighbourhood"].str.contains("Centrum", case=False, na=False)], True),
        ("Amsterdam\ncitywide", ams, False),
        ("Rio\nZona Sul", rio[rio["neighbourhood"].isin(["Copacabana", "Ipanema", "Leblon"])], True),
        ("Rio\ncitywide", rio, False),
    ]
    fig, ax = panel(6.4, 2.8)
    vals = [float(g["professional"].mean() * 100) for _, g, _ in groups]
    cols = [MAGENTA if t else BAR for _, _, t in groups]
    ax.bar([g[0] for g in groups], vals, color=cols, width=0.62, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.03, f"{v:.0f}%", ha="center",
                fontweight="bold", fontsize=10.5,
                color=MAGENTA_INK if cols[i] == MAGENTA else INK)
    ax.set_ylim(0, max(vals) * 1.22)
    ax.set_xlabel("% of listings from professional (3+) hosts", fontsize=9, labelpad=8)
    ax.tick_params(axis="x", labelsize=9.5)
    ax.set_yticks([])
    ax.spines["bottom"].set_color(RULE)
    save(fig, "q4-b-professionalisation")
    targeted = {name: float(g["professional"].mean() * 100) for name, g, _ in groups}

    # ============================================================ cells.json
    rows = []
    for (city, nbhd, room), cell in data.groupby(
            ["city", "neighbourhood", "room_type"], observed=True):
        n = len(cell)
        if n < MIN_CELL_N:
            continue
        q25, q50, q75 = cell["price"].quantile([0.25, 0.5, 0.75])
        short = cell[cell["minimum_nights"] <= 1]["reviews_per_month"]
        longer = cell[cell["minimum_nights"].between(4, 7)]["reviews_per_month"]
        rows.append({
            "c": city, "nb": nbhd, "rt": room, "n": int(n),
            "p25": round(float(q25), 1), "p50": round(float(q50), 1),
            "p75": round(float(q75), 1),
            "rpm": round(float(cell["reviews_per_month"].median()), 2),
            "rpm1": round(float(short.median()), 2) if len(short) >= 5 else None,
            "n1": int(len(short)),
            "rpm4": round(float(longer.median()), 2) if len(longer) >= 5 else None,
            "n4": int(len(longer)),
        })
    rows.sort(key=lambda r: (ORDER.index(r["c"]), r["nb"], r["rt"]))
    (OUT_DATA / "cells.json").write_text(json.dumps(rows, separators=(",", ":")))
    kept = {c: sum(1 for r in rows if r["c"] == c) for c in ORDER}
    print(f"cells.json: {len(rows)} cells kept (n>={MIN_CELL_N}) {kept}")

    # ============================================================ market_stats
    market_stats = {
        "generated_from": "Inside Airbnb quarterly snapshots, files dated 2023-07-06",
        "min_cell_n": MIN_CELL_N, "trust_n": TRUST_N,
        "order": ORDER,
        "markets": {c: {
            "currency": FILES[c][1], "symbol": FILES[c][2],
            "listings": int((data["city"] == c).sum()),
            "neighbourhoods": int(data[data["city"] == c]["neighbourhood"].nunique()),
            "median_price": round(med_all[c], 1),
            "median_entire_home": round(med_entire[c], 1),
            "pro_share": round(conc[c]["pro_share"], 1),
            "hhi": round(conc[c]["hhi"], 1),
            "guess_error_pct": round(errs[c], 1),
            "price_cv": round(cvs[c], 2),
            "price_spread_ratio": round(spreads[c], 2),
            "entire_home_premium": round(ratios[c], 2),
            "pro_premium_pct": round(prems[c], 1),
            "min_stay_rho": round(rhos[c], 2),
            "reviews_price_rho": round(rhos2[c], 2),
        } for c in ORDER},
        "room_mix": {c: {k: round(float(mix.loc[c, k]), 1) for k in mix.columns} for c in ORDER},
        "targeted_pro_share": {k: round(v, 1) for k, v in targeted.items()},
    }
    (OUT_DATA / "market_stats.json").write_text(json.dumps(market_stats, indent=1))

    # ============================================================ assumptions
    assumptions = {
        "defaults": {"unit_size": 50, "payback_years": 10, "nights_per_month": 15},
        "ranges": {"unit_size": [25, 120], "payback_years": [5, 25],
                   "nights_per_month": [5, 30], "ppsqm_pct": [50, 150],
                   "cap_nights": [0, 365]},
        "markets": {
            "Antwerp": {"ppsqm": 3100, "minwage": 2154, "fx_to_usd": 1.17, "cap_nights": None},
            "Amsterdam": {"ppsqm": 8500, "minwage": 2400, "fx_to_usd": 1.17, "cap_nights": 30},
            "LA": {"ppsqm": 6458, "minwage": 2929, "fx_to_usd": 1.0, "cap_nights": 120},
            "Rio": {"ppsqm": 9500, "minwage": 1621, "fx_to_usd": 1 / 5.19, "cap_nights": None},
        },
        "sources": [
            {"field": "Property price per m²", "market": "Antwerp", "value": "€3,100/m²",
             "source": "Deck working assumption, Belgian residential asking prices, 2023. Not sourced from the listings file.",
             "confidence": "assumption"},
            {"field": "Property price per m²", "market": "Amsterdam", "value": "€8,500/m²",
             "source": "Deck working assumption, Amsterdam residential asking prices, 2023. Not sourced from the listings file.",
             "confidence": "assumption"},
            {"field": "Property price per m²", "market": "LA", "value": "$6,458/m²",
             "source": "Deck working assumption, LA County median converted from price per ft², 2023. Not sourced from the listings file.",
             "confidence": "assumption"},
            {"field": "Property price per m²", "market": "Rio", "value": "R$9,500/m²",
             "source": "Deck working assumption, Rio asking prices, 2023. Source and year not independently confirmed — treat Rio's capital conclusion as the least firm of the four.",
             "confidence": "unverified"},
            {"field": "Minimum wage", "market": "Antwerp", "value": "€2,154/month",
             "source": "Belgian gross statutory monthly minimum (GGMMI), 2023.", "confidence": "assumption"},
            {"field": "Minimum wage", "market": "Amsterdam", "value": "€2,400/month",
             "source": "Dutch gross statutory monthly minimum, adult rate, 2023.", "confidence": "assumption"},
            {"field": "Minimum wage", "market": "LA", "value": "$2,929/month",
             "source": "City of LA minimum wage $16.90/hr × 173.3 hours. Gross, pre-tax — same basis as the European figures.",
             "confidence": "assumption"},
            {"field": "Minimum wage", "market": "Rio", "value": "R$1,621/month",
             "source": "Brazilian federal minimum wage, 2023 (salário mínimo R$1,320 base; deck uses R$1,621). Year not independently confirmed.",
             "confidence": "unverified"},
            {"field": "Nightly cap", "market": "Amsterdam", "value": "30 nights/yr = 8.2%",
             "source": "Amsterdam holiday-rental rules: 30 nights/year for unhosted short-stay rental.",
             "confidence": "assumption"},
            {"field": "Nightly cap", "market": "LA", "value": "120 nights/yr = 32.9%",
             "source": "LA Home-Sharing Ordinance base cap of 120 days/year. Extended Home-Sharing approval can lift it; the control below lets you test that.",
             "confidence": "unverified"},
            {"field": "Nightly cap", "market": "Antwerp / Rio", "value": "no modelled cap",
             "source": "No nightly cap modelled. Both cities regulate short-stay rental by other means, so 'none' means 'not a nights ceiling', not 'unregulated'.",
             "confidence": "assumption"},
            {"field": "FX to USD", "market": "all", "value": "EUR 1.17 · BRL 1/5.19",
             "source": "Deck rates, 2023. Used only for the cross-market USD comparison, never inside a single market's arithmetic.",
             "confidence": "assumption"},
        ],
    }
    (OUT_DATA / "assumptions.json").write_text(json.dumps(assumptions, indent=1))

    # ============================================================ scorecard
    (OUT_DATA / "scorecard.json").write_text(json.dumps({
        "static_rows": [
            {"id": "q1", "label": "Cost of guessing the citywide price",
             "unit": "% off", "fmt": "{:.0f}% off", "worse": "high",
             "values": {c: round(errs[c], 1) for c in ORDER}},
            {"id": "q2", "label": "Professional-host pricing premium",
             "unit": "%", "fmt": "{:+.0f}%", "worse": "low",
             "values": {c: round(prems[c], 1) for c in ORDER}},
        ]
    }, indent=1))

    # ============================================================ regression
    A = assumptions["markets"]
    d = assumptions["defaults"]
    print("\nplan.md §5 regression table")
    print(f"{'market':<10}{'median EH':>11}{'breakeven':>11}{'cap':>9}{'ceiling':>10}{'multiple':>10}")
    expected = {"Antwerp": (80, 53.1, None, 18.8, 0.56),
                "Amsterdam": (147, 79.2, 8.2, 12.6, 0.92),
                "Rio": (391, 33.3, None, 30.0, 3.62),
                "LA": (148, 59.8, 32.9, 16.7, 0.76)}
    ok = True
    for c in ["Antwerp", "Amsterdam", "Rio", "LA"]:
        p, cost = med_entire[c], A[c]["ppsqm"] * d["unit_size"]
        be = (cost / d["payback_years"] / p) / 365 * 100
        ceil = p * 365 / cost * 100
        mult = p * d["nights_per_month"] / A[c]["minwage"]
        cap = A[c]["cap_nights"] / 365 * 100 if A[c]["cap_nights"] else None
        got = (p, be, cap, ceil, mult)
        exp = expected[c]
        match = all(e is None and g is None or
                    (e is not None and g is not None and abs(g - e) <= 0.06 * max(1, abs(e)))
                    for g, e in zip(got, exp))
        ok &= match
        print(f"{c:<10}{p:>11.0f}{be:>10.1f}%"
              f"{('%.1f%%' % cap) if cap else '     —':>9}"
              f"{ceil:>9.1f}%{mult:>9.2f}×   {'ok' if match else 'MISMATCH ' + str(exp)}")
    print("\nregression:", "PASS" if ok else "FAIL")
    for f in sorted(OUT_DATA.glob("*.json")):
        print(f"  {f.name:<20}{f.stat().st_size / 1024:>8.1f} KB")


if __name__ == "__main__":
    main()
