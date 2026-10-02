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

    The metric is **reads per day during a period**: full-text views + PDF downloads (abstract views are ignored)
    in the period ÷ days the preprint was online in it, over **all** tracked preprints whatever their posting date.
    A preprint needs at least **15 days online** in the period to be ranked. bioRxiv reports usage per calendar
    month, so periods are whole months (the current month counts up to the data date).

    * **Timeframe ranking (default):** reads since the 1st of the month 1, 2 or 3 months ago, or over the
      whole tracked period.
    * **Monthly ranking:** reads in a single month.
    * **Rank history:** a paper's rank in each month among all tracked preprints, by that month's reads per day.

    Tracked preprints are new (v1) preprints posted since the scrape start date.
    """
    )
    return


@app.cell
def _(json, mo):
    TOP_N = 50
    TIMEFRAMES = [1, 2, 3]  # complete months back, plus the whole tracked period
    MIN_DAYS = 15  # days online within a period needed to be ranked
    raw = json.loads((mo.notebook_dir() / "data" / "usage.json").read_text())
    papers = [p for p in raw["papers"] if p["usage"]]
    return MIN_DAYS, TIMEFRAMES, TOP_N, papers, raw


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
def _(MIN_DAYS, dt, month_end, month_list, papers, statistics, today):
    def days_online(p, first, last):
        """Days the preprint was online between dates `first` and `last` (inclusive)."""
        return max(0, (min(last, today) - max(dt.date.fromisoformat(p["date"]), first)).days + 1)

    def reads(p, months):
        full = sum(p["usage"].get(m, (0, 0))[0] for m in months)
        pdf = sum(p["usage"].get(m, (0, 0))[1] for m in months)
        return full, pdf

    # rank among all tracked preprints, per month, by that month's full + PDF reads per day online
    rank_history = {p["doi"]: [] for p in papers}
    for _ym in month_list:
        _first, _last = dt.date.fromisoformat(_ym + "-01"), month_end(_ym)
        _rows = []
        for p in papers:
            _days = days_online(p, _first, _last)
            if _ym in p["usage"] and _days >= MIN_DAYS:
                _rows.append((sum(p["usage"][_ym]) / _days, sum(p["usage"][_ym]), p["doi"]))
        _rows.sort(reverse=True)
        for _rank, (_rate, _reads, _doi) in enumerate(_rows, 1):
            rank_history[_doi].append(
                {"month": _ym, "rank": _rank, "of": len(_rows), "reads": _reads, "per_day": round(_rate, 2)}
            )

    def rank_period(months):
        """All tracked preprints with >= MIN_DAYS online in `months`, ranked by full + PDF reads per day online."""
        first = dt.date.fromisoformat(months[0] + "-01")
        last = min(month_end(months[-1]), today)
        rows = []
        for p in papers:
            full, pdf = reads(p, months)
            days = days_online(p, first, last)
            if days < MIN_DAYS or full + pdf == 0:
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
                "history": rank_history[p["doi"]],
            })
        rows.sort(key=lambda r: -r["per_day"])
        rates = sorted(r["per_day"] for r in rows)
        return {
            "median_per_day": round(statistics.median(rates), 2) if rates else 0,
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
def _(TIMEFRAMES, TOP_N, month_list, rank_period):
    # windows start on the 1st of the month N complete months back and run to the data date
    _starts = sorted({max(0, len(month_list) - 1 - _n) for _n in TIMEFRAMES} | {0}, reverse=True)
    timeframe_rankings = []
    for _i in _starts:
        _block = rank_period(month_list[_i:])
        _block["all"] = _i == 0
        _block["results"] = _block["results"][:TOP_N]
        timeframe_rankings.append(_block)
    return (timeframe_rankings,)


@app.cell
def _(MIN_DAYS, monthly_rankings, papers, raw, timeframe_rankings):
    infographic = {
        "min_days": MIN_DAYS,
        "category": raw["category"],
        "updated": raw["updated"],
        "start": raw["start"],
        "end": raw["end"],
        "n_papers": len(raw["papers"]),
        "n_with_metrics": len(papers),
        "timeframes": timeframe_rankings,
        "months": monthly_rankings,
    }
    return (infographic,)


@app.cell
def _(mo, monthly_rankings):
    mo.ui.tabs({
        m["month"]: mo.ui.table(
            [
                {k: r[k] for k in ("per_day", "total", "full", "pdf", "days", "date", "title", "first_author")}
                for r in m["results"]
            ],
            selection=None,
        )
        for m in monthly_rankings
    })
    return


if __name__ == "__main__":
    app.run()
