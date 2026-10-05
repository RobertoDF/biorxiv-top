# biorxiv-top

Infographic of the most-read recent bioRxiv **neuroscience** preprints, refreshed every few hours.

**Site:** https://robertodf.github.io/biorxiv-top/

## Metric

**Age-adjusted score.** New preprints get most of their reads right after posting, so raw reads per day mostly reward recency. Each preprint's reads (full-text views + PDF downloads; abstract views are ignored) in the period are divided by the reads expected for a preprint of its age: month by month, the median reads per day of all tracked preprints posted within ±3 days of it, times its days online. 3× means three times the reads of a typical same-age preprint. A preprint needs at least 15 days online in the period to be ranked. bioRxiv reports usage per calendar month, so periods are whole months.

- **By month** (default, opens on the last complete month, with a year selector): score in a single month; the current month counts up to the latest data.
- **Timeframe:** score over any range of complete months, picked with From / To selectors (default: the last 3 complete months).
- **Rank history** (click a paper): its rank in each month among all tracked preprints, by that month's score.

Only new (v1) preprints posted in the last 6 months are tracked, so older papers are not ranked.

## How it works

1. `scrape.py` lists new (v1) preprints from the last 6 months via the [bioRxiv API](https://api.biorxiv.org/). It scrapes each preprint's `.article-metrics` page for monthly usage, making one request per second to stay under bioRxiv's rate limit. Output: `data/usage.json`.
2. `notebook.py` ([marimo](https://marimo.io)) computes the rankings and rank histories.
3. The [marimo Studio](https://marimo-team.github.io/marimo-studio/) view `infographic` (`__marimo__/studio/notebook/infographic/`) renders them. It is exported as a static (Prepared, zero-python) site.
4. `.github/workflows/update.yml` runs all of this every 3 hours (metrics fetched on 20 parallel runners) and deploys to GitHub Pages.

**Incremental scraping.** bioRxiv throttles GitHub's runners heavily (HTTP 429), so one run can't refresh every paper. `data/usage.json` is kept on the `data` branch. Each run restores it, fetches papers never fetched or with data older than 6 days (`--refresh-days`), and stops after 150 minutes or 5 consecutive throttled requests (honoring Cloudflare's `retry-after`). It then saves the file back. Papers it can't reach keep their last known usage. The site footer shows how many preprints have usage data.

**Runs.** Scheduled runs (every 3 h) and manual runs re-scrape bioRxiv. Pushes to `main` only rebuild the site from the saved data, so code changes go live in a few minutes. A manual run with `refresh` off does the same.

## Run locally

```bash
git fetch origin data && git show FETCH_HEAD:usage.json > data/usage.json   # current data
python scrape.py --months 3 --limit 150          # quick sample; omit --limit for a full refresh (~1.5 h)
uvx --with "marimo-studio[deno]" marimo edit notebook.py --sandbox --watch   # edit notebook + view
uvx --with marimo-studio==0.2.3 marimo-studio view export infographic --target notebook.py --runtime zero-python --output site
```
