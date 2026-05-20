from scrapers.workday import WorkdayScraper
import pandas as pd
from dataclasses import asdict
from datetime import datetime, timezone

file_path = "companies.csv"
rows = pd.read_csv(file_path)
scraper = WorkdayScraper()
today = datetime.now(timezone.utc).date()
records = rows.to_dict(orient="records")

for row in records:
    if row["Last Scraped"] != str(today):
        # try:
        company_name = row["Company"]
        print(f"Scraping jobs from {company_name}")

        valid_jobs = scraper.run(row["Workday Link"])

        df = pd.DataFrame(valid_jobs)

        output_path = f"testing/{company_name}.csv"

        df.to_csv(output_path, index=False)

        print(f"Saved {len(valid_jobs)} jobs to {output_path}\n")
        rows.loc[rows["Company"] == company_name, "Last Scraped"] = str(today)
        # except Exception:
        #     continue
        # finally:
        #     rows.to_csv(file_path, index=False)
            
rows.to_csv(file_path, index=False)
