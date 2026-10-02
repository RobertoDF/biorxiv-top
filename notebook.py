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

    import marimo as mo

    return dt, json, mo


@app.cell
def _(mo):
    mo.md(
        """
    # Most-read bioRxiv preprints by month

    Only papers with at least **10 days of data** are ranked (in a month: at least 10 days online that month).
    The metric is **reads per day**, where reads = full-text views + PDF downloads (abstract views are ignored).

    * **Timeframe ranking (default):** preprints posted in the last *N* days, ranked by
      all of their reads so far ÷ days since posting.
    * **Monthly ranking:** preprints posted in a month, ranked by that month's reads ÷
      *eligible days* (days the preprint was online during that month).
    * **Rank history:** a paper's rank in each month among **all** tracked preprints
      (including papers posted in earlier months), by that month's reads ÷ days online in that month.
    """
    )
    return


@app.cell
def _(json, mo):
    TOP_N = 50
    TIMEFRAMES = [30, 60, 90, 180]
    MIN_DAYS = 10  # a paper needs at least this many days of data to be ranked
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
def _(MIN_DAYS, dt, month_end, month_list, papers, today):
    def days_online(p, ym):
        """Days the preprint was online during month `ym` (up to the data date)."""
        start = max(dt.date.fromisoformat(p["date"]), dt.date.fromisoformat(ym + "-01"))
        return (min(month_end(ym), today) - start).days + 1

    # rank among all tracked preprints, per month, by that month's (full + PDF) / days online
    rank_history = {p["doi"]: [] for p in papers}
    for _ym in month_list:
        _rows = sorted(
            (
                (sum(p["usage"][_ym]) / days_online(p, _ym), sum(p["usage"][_ym]), p["doi"])
                for p in papers
                if _ym in p["usage"] and days_online(p, _ym) >= MIN_DAYS
            ),
            reverse=True,
        )
        for _rank, (_rate, _reads, _doi) in enumerate(_rows, 1):
            rank_history[_doi].append(
                {"month": _ym, "rank": _rank, "of": len(_rows), "reads": _reads, "per_day": round(_rate, 2)}
            )
    return days_online, rank_history


@app.cell
def _(MIN_DAYS, TOP_N, days_online, month_end, month_list, papers, rank_history, raw, today):
    def rank_month(ym):
        rows = []
        for p in papers:
            if not p["date"].startswith(ym) or ym not in p["usage"]:
                continue
            full, pdf = p["usage"][ym]
            eligible = days_online(p, ym)
            if eligible < MIN_DAYS:
                continue
            rows.append({
                "doi": p["doi"],
                "title": p["title"],
                "first_author": p["first_author"],
                "date": p["date"],
                "full": full,
                "pdf": pdf,
                "total": full + pdf,
                "eligible_days": eligible,
                "per_day": round((full + pdf) / eligible, 2),
                "history": rank_history[p["doi"]],
            })
        rows.sort(key=lambda r: -r["per_day"])
        return {
            "month": ym,
            "in_progress": month_end(ym) > today,
            "days_in_month": month_end(ym).day,
            "n_posted": sum(1 for p in raw["papers"] if p["date"].startswith(ym)),
            "n_ranked": len(rows),
            "reads": sum(r["total"] for r in rows),
            "results": rows[:TOP_N],
        }

    monthly_rankings = [_m for _m in (rank_month(_ym) for _ym in reversed(month_list)) if _m["results"]]
    return (monthly_rankings,)


@app.cell
def _(MIN_DAYS, TIMEFRAMES, TOP_N, dt, papers, rank_history, raw, today):
    def rank_timeframe(days):
        """Preprints posted in the last `days` days, ranked by all reads so far / days since posting."""
        since = today - dt.timedelta(days=days - 1)
        rows = []
        for p in papers:
            posted = dt.date.fromisoformat(p["date"])
            if posted < since:
                continue
            age = (today - posted).days + 1
            if age < MIN_DAYS:
                continue
            full = sum(v[0] for v in p["usage"].values())
            pdf = sum(v[1] for v in p["usage"].values())
            rows.append({
                "doi": p["doi"],
                "title": p["title"],
                "first_author": p["first_author"],
                "date": p["date"],
                "full": full,
                "pdf": pdf,
                "total": full + pdf,
                "days": age,
                "per_day": round((full + pdf) / age, 2),
                "history": rank_history[p["doi"]],
            })
        rows.sort(key=lambda r: -r["per_day"])
        return {
            "days": days,
            "since": str(since),
            "n_posted": sum(1 for p in raw["papers"] if dt.date.fromisoformat(p["date"]) >= since),
            "n_ranked": len(rows),
            "results": rows[:TOP_N],
        }

    timeframe_rankings = [rank_timeframe(_d) for _d in TIMEFRAMES]
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
                {k: r[k] for k in ("per_day", "total", "full", "pdf", "eligible_days", "date", "title", "first_author")}
                for r in m["results"]
            ],
            selection=None,
        )
        for m in monthly_rankings
    })
    return


if __name__ == "__main__":
    app.run()
