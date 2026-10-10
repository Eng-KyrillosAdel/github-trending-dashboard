# GitHub Trending Repositories Dashboard

## Project Overview
A web-scraping + analytics project. A **BeautifulSoup** scraper collects the repositories
currently trending on GitHub (daily, weekly and monthly), stores them in a CSV file, and an
interactive **Dash / Plotly** dashboard visualises them.

## Data Source
- https://github.com/trending (`?since=daily|weekly|monthly`)

Scraped fields: rank, period, repository, owner, name, description, language, stars, forks,
stars gained in the period, URL, scrape timestamp.
Output: `data/trending_repos.csv`.

## Dashboard Features
- **5 KPI cards:** trending repositories, total stars, average stars per repo, most popular language, top repository
- **Charts:**
  - Top 10 trending repositories (bar)
  - Programming language distribution (donut)
  - Stars vs. stars gained (scatter)
  - Total stars by language (bar)
- **Filters:** trending period dropdown + multi-select programming language dropdown
- **Data table:** sortable, paginated, with repository name, stars, forks and description
- **Bonus - live updates:** a background thread re-scrapes every 30 minutes
  (`REFRESH_MINUTES` env var) and the dashboard re-reads the CSV every minute, so no manual refresh is needed.

## Project Structure
```
├── app.py              # Dash dashboard (+ background auto-scraper)
├── scraper.py          # BeautifulSoup scraper -> CSV
├── data/trending_repos.csv
├── requirements.txt
└── README.md
```

## How to Run
Requires Python 3.9+. From the project folder:
```bash
# 1. (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. scrape fresh data (writes data/trending_repos.csv)
python scraper.py

# 4. launch the dashboard
python app.py
```
Open http://127.0.0.1:8050 in your browser.

To change the auto-refresh interval: `REFRESH_MINUTES=10 python app.py`
(Windows PowerShell: `$env:REFRESH_MINUTES=10; python app.py`).
