import json
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://github.com/orgs/google/repositories"
DB_NAME = "repos.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (class assignment scraper)"}
MAX_RETRIES = 5
PER_PAGE = 30


def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            language TEXT,
            stars INTEGER
        )"""
    )
    conn.commit()
    return conn


def parse_page(html):
    """Extract (name, language, stars) from the JSON embedded in the page."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", attrs={"data-target": "react-app.embeddedData"})
    if not script:
        return []
    data = json.loads(script.string)
    repos = data["payload"]["orgReposPageRoute"]["repositories"]
    results = []
    for r in repos:
        lang = (r.get("primaryLanguage") or {}).get("name")
        results.append((r["name"], lang, r.get("starsCount", 0)))
    return results


def fetch(session, url):
    """Fetch a URL. On 429, wait and retry instead of giving up."""
    res = None
    for attempt in range(MAX_RETRIES):
        res = session.get(url, headers=HEADERS)
        time.sleep(1)  # required by the assignment
        if res.status_code != 429:
            return res
        # Use Retry-After if GitHub sends it, otherwise back off: 30s, 60s, 90s...
        try:
            wait = int(res.headers.get("Retry-After", 30 * (attempt + 1)))
        except ValueError:
            wait = 30 * (attempt + 1)
        print(f"  429 rate limited. Waiting {wait}s (retry {attempt + 1}/{MAX_RETRIES})")
        time.sleep(wait)
    return res


def main():
    conn = init_db()
    session = requests.Session()

    # Resume from where the DB left off (overlap by one page to be safe)
    saved = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
    page = max(1, saved // PER_PAGE)
    print(f"{saved} repos already saved. Starting at page {page}")

    while True:
        url = f"{BASE_URL}?page={page}"
        print(f"Fetching: {url}")
        res = fetch(session, url)

        if res.status_code != 200:
            print(f"Status {res.status_code}. Stopping. Run again later to resume.")
            break

        repos = parse_page(res.text)
        if not repos:  # no data = past the last page
            print("Reached the last page.")
            break

        conn.executemany(
            "INSERT OR REPLACE INTO repositories (name, language, stars) VALUES (?, ?, ?)",
            repos,
        )
        conn.commit()
        print(f"  {len(repos)} repos")
        page += 1

    conn.close()


if __name__ == "__main__":
    main()