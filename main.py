from scrapers.workday import WorkdayScraper
import pandas as pd
from dataclasses import asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

file_path = "companies.csv"
rows = pd.read_csv(file_path, dtype={
    "Last Scraped": "string"
})
scraper = WorkdayScraper()
today = datetime.now(ZoneInfo("America/Chicago")).date()
records = rows.to_dict(orient="records")
priority_dfs = {
    1: pd.DataFrame(columns=["title"]),
    2: pd.DataFrame(columns=["title"]),
    3: pd.DataFrame(columns=["title"]),
    4: pd.DataFrame(columns=["title"]),
}

for row in records:
    if pd.isna(row["Last Scraped"]) or row["Last Scraped"] != today.isoformat():        
        try:
            company_name = row["Company"]
            print(f"Scraping jobs from {company_name}")

            valid_jobs = scraper.run(row["Workday Link"])

            df = pd.DataFrame(valid_jobs)

            output_path = f"testing/{company_name}.csv"

            df.to_csv(output_path, index=False)

            print(f"Saved {len(valid_jobs)} jobs to {output_path}\n")
            rows.loc[rows["Company"] == company_name, "Last Scraped"] = str(today)
        except Exception:
            continue
        finally:
            rows.to_csv(file_path, index=False)
            
rows.to_csv(file_path, index=False)
