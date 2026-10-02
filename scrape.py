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


def fetch(url, retries=8):
    delay = 5
    for _ in range(retries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                log(f"{e.code}, sleeping {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            return ""
        except Exception:
            time.sleep(delay)
    return ""


def list_papers(start, end, category):
    papers, cursor = {}, 0
    while True:
        d = json.loads(fetch(f"https://api.biorxiv.org/details/biorxiv/{start}/{end}/{cursor}?category={category}") or "{}")
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
    h = fetch(f"https://www.biorxiv.org/content/{doi}v1.article-metrics")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="neuroscience")
    ap.add_argument("--months", type=int, default=6, help="number of months incl. the current one")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0, help="debug: only fetch metrics for an evenly spaced sample of N papers")
    ap.add_argument("--out", default="data/usage.json")
    a = ap.parse_args()

    today = dt.date.today()
    first = month_keys(today, a.months)
    papers = list_papers(first, today, a.category)
    log(f"{len(papers)} papers posted {first} -> {today}")
    if not papers:
        sys.exit("no papers fetched")

    out = []
    dois = list(papers)
    if a.limit:  # evenly spaced sample across the window
        dois = dois[:: max(1, len(dois) // a.limit)][: a.limit]
    for n, doi in enumerate(dois):
        p = papers[doi]
        out.append({
            "doi": doi, "title": p["title"], "first_author": p["authors"].split(";")[0].strip(),
            "date": p["date"], "usage": usage(doi),  # {"YYYY-MM": [full, pdf]} or None
        })
        if n % 100 == 0:
            log(f"{n}/{len(dois)} fetched")
        time.sleep(a.delay)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump({
            "category": a.category, "start": str(first), "end": str(today),
            "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "papers": out,
        }, f)
    log(f"wrote {a.out}: {sum(1 for p in out if p['usage'])}/{len(out)} with metrics")


if __name__ == "__main__":
    main()
