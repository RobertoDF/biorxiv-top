# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["marimo-studio==0.2.3"]
#
# [tool.marimo-studio]
# default = "infographic"
#
# [tool.marimo-studio.cells]
# cell-2 = {ref = "cell:v1:83f4af0a1e11bcce2789859141ccf8eac76fa23eca8a70ccb11373d8b6bf9cfb:3d456a2494d857d545d305c0037b8074dc1e7878f0f7f9a408f1a43c9c4a7f41:0"}
# cell-8 = {ref = "cell:v1:1ff1eb0e4c37a67a22c2a89638d4a254519f02df43e6a403bab5eb99bf50a1f0:1ff1eb0e4c37a67a22c2a89638d4a254519f02df43e6a403bab5eb99bf50a1f0:0"}
# ///

import marimo

__generated_with = "0.16.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import datetime as dt
    import json
    import statistics

    import marimo as mo

    return dt, json, mo, statistics


@app.cell
def _(mo):
    mo.md(
        """
    # Most-read bioRxiv preprints

    New preprints get most of their reads right after posting, so raw reads per day mostly reward recency.
    The ranking therefore uses an **age-adjusted score**: a preprint's reads (full-text views + PDF downloads;
    abstract views are ignored) in the period ÷ the reads expected for a preprint of its age. The expectation for
    each month is the median reads per day that month of all preprints posted within ±3 days of it, times its days
    online. A score of 3× means three times the reads of a typical preprint of the same age. A preprint needs at
    least **15 days online** in the period to be ranked. bioRxiv reports usage per calendar month.

    * **Monthly ranking (default):** a single month (the current month counts up to the data date).
    * **Timeframe ranking:** any From-To range of complete months.
    * **Rank history:** a paper's rank by score in each month among all tracked preprints.

    Tracked preprints are new (v1) preprints posted since the scrape start date.
    """
    )
    return


@app.cell
def _(json, mo):
    TOP_N = 50
    MIN_DAYS = 15  # days online within a period needed to be ranked
    PEER_DAYS = 3  # peers for the age baseline: preprints posted within this many days of each other
    raw = json.loads((mo.notebook_dir() / "data" / "usage.json").read_text())
    papers = [p for p in raw["papers"] if p["usage"]]
    return MIN_DAYS, PEER_DAYS, TOP_N, papers, raw


@app.cell
def _(dt, raw):
    def month_end(ym):
        first = dt.date.fromisoformat(ym + "-01")
        return (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)

    today = dt.date.fromisoformat(raw["end"])
    month_list = []
    _d = dt.date.fromisoformat(raw["start"]).replace(day=1)
    while _d <= today:
        month_list.append(_d.strftime("%Y-%m"))
        _d = month_end(_d.strftime("%Y-%m")) + dt.timedelta(days=1)
    return month_end, month_list, today


@app.cell
def _(MIN_DAYS, PEER_DAYS, dt, month_end, month_list, papers, statistics, today):
    def days_online(p, first, last):
        """Days the preprint was online between dates `first` and `last` (inclusive)."""
        return max(0, (min(last, today) - max(dt.date.fromisoformat(p["date"]), first)).days + 1)

    def bounds(ym):
        return dt.date.fromisoformat(ym + "-01"), month_end(ym)

    # Typical reads/day of a preprint of a given age: for each month and posting date, the median reads/day that
    # month of all preprints posted within +-PEER_DAYS of that date (so peers share its age and days online).
    _rates = {}  # (month, posting date) -> [reads/day]
    for p in papers:
        for _ym in month_list:
            _days = days_online(p, *bounds(_ym))
            if _days and _ym in p["usage"]:
                _rates.setdefault((_ym, p["date"]), []).append(sum(p["usage"][_ym]) / _days)
    typical = {}
    for _ym in month_list:
        for _d in {d for (m, d) in _rates if m == _ym}:
            _d0 = dt.date.fromisoformat(_d)
            _peers = [
                r
                for k in range(-PEER_DAYS, PEER_DAYS + 1)
                for r in _rates.get((_ym, str(_d0 + dt.timedelta(days=k))), [])
            ]
            if len(_peers) >= 10 and statistics.median(_peers) > 0:
                typical[(_ym, _d)] = statistics.median(_peers)

    def score(p, months):
        """Reads, days and expected reads over the months where the preprint has usage and a peer baseline."""
        full = pdf = days = expected = 0
        for _ym in months:
            _days = days_online(p, *bounds(_ym))
            if not _days or _ym not in p["usage"] or (_ym, p["date"]) not in typical:
                continue
            full += p["usage"][_ym][0]
            pdf += p["usage"][_ym][1]
            days += _days
            expected += typical[(_ym, p["date"])] * _days
        return full, pdf, days, expected

    # rank among all tracked preprints, per month, by that month's age-adjusted score
    rank_history = {p["doi"]: [] for p in papers}
    for _ym in month_list:
        _rows = []
        for p in papers:
            _full, _pdf, _days, _exp = score(p, [_ym])
            if _days >= MIN_DAYS and _exp:
                _rows.append(((_full + _pdf) / _exp, _full + _pdf, _days, p["doi"]))
        _rows.sort(reverse=True)
        for _rank, (_score, _reads, _days, _doi) in enumerate(_rows, 1):
            rank_history[_doi].append({
                "month": _ym, "rank": _rank, "of": len(_rows), "reads": _reads,
                "per_day": round(_reads / _days, 2), "score": round(_score, 2),
            })

    def rank_period(months):
        """Tracked preprints with >= MIN_DAYS online in `months`, ranked by reads / reads expected for their age."""
        first, last = bounds(months[0])[0], min(month_end(months[-1]), today)
        rows = []
        for p in papers:
            full, pdf, days, expected = score(p, months)
            if days < MIN_DAYS or not expected:
                continue
            rows.append({
                "doi": p["doi"],
                "title": p["title"],
                "first_author": p["first_author"],
                "date": p["date"],
                "full": full,
                "pdf": pdf,
                "total": full + pdf,
                "days": days,
                "per_day": round((full + pdf) / days, 2),
                "typical_per_day": round(expected / days, 2),
                "score": round((full + pdf) / expected, 2),
                "history": rank_history[p["doi"]],
            })
        rows.sort(key=lambda r: -r["score"])
        return {
            "since": str(first),
            "until": str(last),
            "days": (last - first).days + 1,
            "n_ranked": len(rows),
            "n_new": sum(1 for r in rows if first <= dt.date.fromisoformat(r["date"]) <= last),  # ranked & posted in it
            "reads": sum(r["total"] for r in rows),
            "results": rows,
        }

    return (rank_period,)


@app.cell
def _(TOP_N, month_end, month_list, rank_period, today):
    def _month(ym):
        block = rank_period([ym])
        return {**block, "month": ym, "in_progress": month_end(ym) > today, "results": block["results"][:TOP_N]}

    monthly_rankings = [_m for _m in (_month(_ym) for _ym in reversed(month_list)) if _m["results"]]
    return (monthly_rankings,)


@app.cell
def _(TOP_N, month_end, month_list, rank_period, today):
    # every From-To range of complete calendar months (the in-progress month is left out)
    _full = [_m for _m in month_list if month_end(_m) < today] or month_list[:1]
    timeframe_rankings = []
    for _i in range(len(_full)):
        for _j in range(_i, len(_full)):
            _block = rank_period(_full[_i : _j + 1])
            _block["from"], _block["to"] = _full[_i], _full[_j]
            _block["results"] = _block["results"][:TOP_N]
            timeframe_rankings.append(_block)
    return (timeframe_rankings,)


@app.cell
def _(MIN_DAYS, PEER_DAYS, monthly_rankings, papers, raw, timeframe_rankings):
    infographic = {
        "min_days": MIN_DAYS,
        "peer_days": PEER_DAYS,
        "category": raw["category"],
        "updated": raw["updated"],
        "start": raw["start"],
        "end": raw["end"],
        "n_papers": len(raw["papers"]),
        "n_with_metrics": len(papers),
        # rank histories are shared by all blocks, so store each shown paper's once
        "histories": {r["doi"]: r["history"] for b in timeframe_rankings + monthly_rankings for r in b["results"]},
        "timeframes": [{**b, "results": [{k: v for k, v in r.items() if k != "history"} for r in b["results"]]} for b in timeframe_rankings],
        "months": [{**b, "results": [{k: v for k, v in r.items() if k != "history"} for r in b["results"]]} for b in monthly_rankings],
    }
    return (infographic,)


@app.cell
def _(mo, monthly_rankings):
    mo.ui.tabs({
        m["month"]: mo.ui.table(
            [
                {k: r[k] for k in ("score", "per_day", "typical_per_day", "total", "days", "date", "title", "first_author")}
                for r in m["results"]
            ],
            selection=None,
        )
        for m in monthly_rankings
    })
    return


if __name__ == "__main__":
    app.run()
