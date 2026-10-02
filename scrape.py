"""Collect new bioRxiv preprints for recent months and their monthly full-text/PDF usage into data/usage.json."""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; biorxiv-top/1.0; +https://github.com/RobertoDF/biorxiv-top)"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fetch(url, retries=4):
    """Return the page text, "" for a hard HTTP error (e.g. 404), or None if throttled/unreachable."""
    delay = 5
    for _ in range(retries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                return ""
            wait = max(delay, int(e.headers.get("retry-after") or 0))  # Cloudflare rate limit (error 1015)
            log(f"{e.code}, sleeping {wait}s")
            time.sleep(wait)
        except Exception as e:
            log(f"{type(e).__name__}, sleeping {delay}s")
            time.sleep(delay)
        delay = min(delay * 2, 120)
    return None


def list_papers(start, end, category):
    papers, cursor = {}, 0
    while True:
        page = fetch(f"https://api.biorxiv.org/details/biorxiv/{start}/{end}/{cursor}?category={category}", retries=8)
        if page is None:
            sys.exit("bioRxiv API unreachable")
        d = json.loads(page or "{}")
        col = d.get("collection", [])
        if not col:
            break
        for p in col:
            if p["version"] == "1":
                papers[p["doi"]] = p
        cursor += len(col)
        if cursor >= int(d["messages"][0]["total"]):
            break
    return papers


def usage(doi):
    """{"YYYY-MM": [full, pdf]}, None if the page has no usage table, or False if the fetch failed."""
    # The plain URL serves a stale cached page; a unique query string returns live counts.
    h = fetch(f"https://www.biorxiv.org/content/{doi}v1.article-metrics?_={int(time.time())}", retries=2)
    if h is None:
        return False
    i = h.find("Article usage")
    if i < 0:
        return None
    s = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h[i:i + 6000]))
    rows = re.findall(r"([A-Z][a-z]{2}) (\d{4}) ([\d,]+) ([\d,-]+) ([\d,]+)", s)
    if not rows:
        return None
    num = lambda x: int(x.replace(",", "")) if x.strip("-") else 0
    # {"2026-08": [full, pdf]}
    return {
        dt.datetime.strptime(f"{mon} {yr}", "%b %Y").strftime("%Y-%m"): [num(full), num(pdf)]
        for mon, yr, _abstract, full, pdf in rows
    }


def month_keys(today, n):
    first = today.replace(day=1)
    for _ in range(n - 1):
        first = (first - dt.timedelta(days=1)).replace(day=1)
    return first


def save(path, meta, papers):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({**meta, "papers": papers}, f)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="neuroscience")
    ap.add_argument("--months", type=int, default=6, help="number of months incl. the current one")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between metrics requests")
    ap.add_argument("--limit", type=int, default=0, help="debug: only fetch metrics for an evenly spaced sample of N papers")
    ap.add_argument("--refresh-days", type=int, default=6, help="re-fetch usage older than this many days")
    ap.add_argument("--budget-minutes", type=float, default=0, help="stop fetching after this long (0 = no limit)")
    ap.add_argument("--max-failures", type=int, default=5, help="stop after this many consecutive throttled fetches")
    ap.add_argument("--out", default="data/usage.json")
    a = ap.parse_args()
    t0 = time.time()

    today = dt.date.today()
    first = month_keys(today, a.months)
    listed = list_papers(first, today, a.category)
    log(f"{len(listed)} papers posted {first} -> {today}")
    if not listed:
        sys.exit("no papers fetched")

    # incremental: keep usage from earlier runs, only for papers still in the window
    cache = {}
    if os.path.exists(a.out):
        cache = {p["doi"]: p for p in json.load(open(a.out))["papers"]}
    papers = []
    for doi, p in listed.items():
        old = cache.get(doi, {})
        papers.append({
            "doi": doi, "title": p["title"], "first_author": p["authors"].split(";")[0].strip(), "date": p["date"],
            "usage": old.get("usage"), "fetched": old.get("fetched"),  # usage: {"YYYY-MM": [full, pdf]} or None
        })
    meta = {"category": a.category, "start": str(first), "end": str(today)}

    stale = str(today - dt.timedelta(days=a.refresh_days))
    todo = [p for p in papers if not p["fetched"] or p["fetched"] <= stale]
    todo.sort(key=lambda p: (p["fetched"] or "", p["date"]))  # never fetched first, then oldest data
    log(f"{len(papers) - len(todo)} up to date, {len(todo)} to fetch")
    if a.limit:  # evenly spaced sample across the window
        todo = todo[:: max(1, len(todo) // a.limit)][: a.limit]

    done = failures = 0
    for n, p in enumerate(todo, 1):
        if a.budget_minutes and time.time() - t0 > a.budget_minutes * 60:
            log("time budget reached")
            break
        u = usage(p["doi"])
        if u is False:
            failures += 1
            if failures >= a.max_failures:
                log(f"{failures} consecutive throttled fetches, stopping; will continue next run")
                break
        else:
            failures = 0
            done += 1
            p["usage"], p["fetched"] = u, str(today)
        if n % 100 == 0:
            log(f"{n}/{len(todo)} tried, {done} fetched")
            save(a.out, {**meta, "updated": now()}, papers)
        time.sleep(a.delay)

    save(a.out, {**meta, "updated": now()}, papers)
    fresh = sum(1 for p in papers if p["fetched"])
    log(f"wrote {a.out}: fetched {done} this run; {fresh}/{len(papers)} have usage data, "
        f"{sum(1 for p in papers if p['usage'])} with metrics")


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


if __name__ == "__main__":
    main()
