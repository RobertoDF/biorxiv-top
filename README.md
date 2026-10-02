# biorxiv-top

Infographic of the most-read recent bioRxiv **neuroscience** preprints, refreshed daily.

**Site:** https://robertodf.github.io/biorxiv-top/

## Metric

**Reads during the period.** Reads are full-text views + PDF downloads; abstract views are ignored. Every tracked preprint counts, whenever it was posted. bioRxiv reports usage per calendar month, so periods are whole months, and the current month counts up to the latest data.

- **Timeframe** (default): reads since the 1st of the month 1, 2 or 3 months ago, or over the whole tracked period.
- **By month:** reads in a single month.
- **Rank history** (click a paper): its rank in each month among all tracked preprints, by that month's reads.

Only new (v1) preprints posted in the last 6 months are tracked, so older papers are not ranked.

## How it works

1. `scrape.py` lists new (v1) preprints from the last 6 months via the [bioRxiv API](https://api.biorxiv.org/). It scrapes each preprint's `.article-metrics` page for monthly usage, making one request per second to stay under bioRxiv's rate limit. Output: `data/usage.json`.
2. `notebook.py` ([marimo](https://marimo.io)) computes the rankings and rank histories.
3. The [marimo Studio](https://marimo-team.github.io/marimo-studio/) view `infographic` (`__marimo__/studio/notebook/infographic/`) renders them. It is exported as a static (Prepared, zero-python) site.
4. `.github/workflows/update.yml` runs all of this daily and deploys to GitHub Pages.

**Incremental scraping.** bioRxiv throttles GitHub's runners heavily (HTTP 429), so one run can't refresh every paper. `data/usage.json` is kept on the `data` branch. Each run restores it, fetches papers never fetched or with data older than 6 days (`--refresh-days`), and stops after 150 minutes or 5 consecutive throttled requests (honoring Cloudflare's `retry-after`). It then saves the file back. Papers it can't reach keep their last known usage. The site footer shows how many preprints have usage data.

## Run locally

```bash
git fetch origin data && git show FETCH_HEAD:usage.json > data/usage.json   # current data
python scrape.py --months 3 --limit 150          # quick sample; omit --limit for a full refresh (~1.5 h)
uvx --with "marimo-studio[deno]" marimo edit notebook.py --sandbox --watch   # edit notebook + view
uvx --with marimo-studio==0.2.3 marimo-studio view export infographic --target notebook.py --runtime zero-python --output site
```
