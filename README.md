# biorxiv-top

Infographic of the most-read new bioRxiv **neuroscience** preprints, refreshed weekly.

**Site:** https://robertodf.github.io/biorxiv-top/

## Metric

**Reads per day.** Reads are full-text views + PDF downloads; abstract views are ignored. A paper needs at least 10 days of data to be ranked.

- **Last N days** (default; N = 30/60/90/180): preprints posted in the window, ranked by all of their reads so far ÷ days since posting.
- **By month:** preprints posted in that month, ranked by that month's reads ÷ *eligible days* (the days the preprint was online during the month).
- **Rank history** (click a paper): its rank in each month among *all* tracked preprints, using that month's reads ÷ days online that month.

## How it works

1. `scrape.py` lists new (v1) preprints from the last 6 months via the [bioRxiv API](https://api.biorxiv.org/). It scrapes each preprint's `.article-metrics` page for monthly usage, making one request per second to stay under bioRxiv's rate limit. Output: `data/usage.json`.
2. `notebook.py` ([marimo](https://marimo.io)) computes the rankings and rank histories.
3. The [marimo Studio](https://marimo-team.github.io/marimo-studio/) view `infographic` (`__marimo__/studio/notebook/infographic/`) renders them. It is exported as a static (Prepared, zero-python) site.
4. `.github/workflows/update.yml` runs all of this every Monday and deploys to GitHub Pages.

## Run locally

```bash
python scrape.py --months 3 --limit 150          # quick sample; omit --limit for the full run (~1 h)
uvx --with "marimo-studio[deno]" marimo edit notebook.py --sandbox --watch   # edit notebook + view
uvx --with marimo-studio==0.2.3 marimo-studio view export infographic --target notebook.py --runtime zero-python --output site
```
