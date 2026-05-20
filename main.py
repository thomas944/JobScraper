from scrapers.workday import WorkdayScraper
import pandas as pd
from dataclasses import asdict

file_path = "companies.csv"
rows = pd.read_csv(file_path)
scraper = WorkdayScraper()

records = rows.to_dict(orient="records")

for row in records:
    company_name = row["Company"]

    valid_jobs = scraper.run(row["Workday Link"])

    # jobs_dicts = [
    #     asdict(job)
    #     for job in valid_jobs
    # ]

    df = pd.DataFrame(valid_jobs)

    output_path = f"testing/{company_name}.csv"

    df.to_csv(output_path, index=False)

    print(f"Saved {len(valid_jobs)} jobs to {output_path}")
    