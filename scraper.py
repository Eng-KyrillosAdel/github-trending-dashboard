import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://github.com/trending"
PERIODS = ["daily", "weekly", "monthly"]
CSV_PATH = Path(__file__).parent / "data" / "trending_repos.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def to_int(text: str) -> int:
    text = (text or "").strip().lower().replace(",", "")
    m = re.search(r"([\d.]+)\s*(k)?", text)
    if not m:
        return 0
    value = float(m.group(1))
    return int(value * 1000) if m.group(2) else int(value)


def parse_article(article, rank: int, period: str, scraped_at: str) -> dict:
    link = article.select_one("h2 a")
    full_name = re.sub(r"\s+", "", link.get_text()) if link else ""
    owner, _, name = full_name.partition("/")

    desc = article.select_one("p")
    lang = article.select_one('[itemprop="programmingLanguage"]')
    stars = article.select_one('a[href$="/stargazers"]')
    forks = article.select_one('a[href$="/forks"]')
    gained = next((sp for sp in article.select("span.float-sm-right")
                   if re.search(r"stars?\s+(today|this week|this month)", sp.get_text(), re.I)), None)

    return {
        "rank": rank,
        "period": period,
        "repository": full_name,
        "owner": owner,
        "name": name,
        "description": desc.get_text(strip=True) if desc else "",
        "language": lang.get_text(strip=True) if lang else "Unknown",
        "stars": to_int(stars.get_text()) if stars else 0,
        "forks": to_int(forks.get_text()) if forks else 0,
        "stars_gained": to_int(gained.get_text()) if gained else 0,
        "url": f"https://github.com/{full_name}",
        "scraped_at": scraped_at,
    }


def scrape_period(period: str, scraped_at: str) -> list[dict]:
    resp = requests.get(BASE_URL, params={"since": period}, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    return [parse_article(a, i, period, scraped_at)
            for i, a in enumerate(soup.select("article.Box-row"), start=1)]


def scrape_all() -> pd.DataFrame:
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for period in PERIODS:
        rows.extend(scrape_period(period, scraped_at))
        time.sleep(1)
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    df = scrape_all()
    if df.empty:
        raise RuntimeError("No repositories scraped - GitHub markup may have changed.")
    CSV_PATH.parent.mkdir(exist_ok=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"Saved {len(df)} rows to {CSV_PATH}")
    return df


if __name__ == "__main__":
    run()
