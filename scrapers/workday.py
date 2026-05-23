import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException
)

from scrapers.base_scraper import BaseScraper
from utils import utils
from filters import workday_filter as filter
import re
from datetime import date, datetime, timedelta
from utils.types import JobCardInfo, JobDescriptionInfo
from typing import Optional
import time


class WorkdayScraper(BaseScraper):
    def __init__(self, priority_dfs: dict[int, pd.DataFrame]):
        super().__init__()
        self.priority_dfs = priority_dfs

    def open_jobs_page(self, url: str):
        self.driver.get(url)

    def get_job_results_section(self):

        return WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section[data-automation-id='jobResults']")
            )
        )
    
    def wait_for_valid_job_section(self):

        def section_is_ready(driver):

            try:
                section = driver.find_element(
                    By.CSS_SELECTOR,
                    "section[data-automation-id='jobResults']"
                )

                cards = section.find_elements(By.XPATH, ".//li")

                if len(cards) == 0:
                    return False

                titles = section.find_elements(
                    By.CSS_SELECTOR,
                    "a[data-automation-id='jobTitle']"
                )

                if len(titles) == 0:
                    return False

                # ensure at least some titles are non-empty
                for t in titles:
                    if t.text.strip():
                        return True

                return False

            except:
                return False

        WebDriverWait(self.driver, 30).until(section_is_ready)

        return self.driver.find_element(
            By.CSS_SELECTOR,
            "section[data-automation-id='jobResults']"
        )
   
    def get_pagination_info(self, section):
        try:
            ul = section.find_element(
                By.CSS_SELECTOR,
                "ul[role='list']"
            )
        except:
            return None


        aria_label = ul.get_attribute("aria-label")

        # Example:
        # "Page 1 of 54"

        match = re.search(r'Page\s+(\d+)\s+of\s+(\d+)', aria_label)

        if not match:
            return None

        current_page = int(match.group(1))
        total_pages = int(match.group(2))

        return current_page, total_pages
            # "current_page": current_page,
            # "total_pages": total_pages
        
    def get_job_cards(self, section):
        jobs_list = section.find_element(
            By.CSS_SELECTOR,
            "ul[role='list']"
        )

        cards = jobs_list.find_elements(
            By.XPATH,
            "./li"
        )

        return cards
    
    def parse_posted_date(self, date_text: str) -> tuple[Optional[date], Optional[int]]:

        if not date_text:
            return None, None

        text = date_text.strip().lower()
        now = self.today.date()

        parsed_date = None
        days_old = None

        # Today
        if "today" in text:
            parsed_date = now
            days_old = 0

        # Yesterday
        elif "yesterday" in text:
            parsed_date = now - timedelta(days=1)
            days_old = 1

        # 30+ days ago
        elif "30+" in text:
            parsed_date = date(1999, 1, 1)
            days_old = 9999

        # X days ago
        elif match := re.search(r"(\d+)\s+day", text):
            days_old = int(match.group(1))
            parsed_date = now - timedelta(days=days_old)

        # X weeks ago
        elif match := re.search(r"(\d+)\s+week", text):
            weeks = int(match.group(1))
            days_old = weeks * 7
            parsed_date = now - timedelta(days=days_old)

        # X months ago
        elif match := re.search(r"(\d+)\s+month", text):
            months = int(match.group(1))
            days_old = months * 30
            parsed_date = now - timedelta(days=days_old)

        if parsed_date is None:
            return None, None

        # Priority calculation
        # if days_old <= 2:
        #     priority = 1
        # elif days_old <= 7:
        #     priority = 2
        # elif days_old <= 30:
        #     priority = 3
        # else:
        #     priority = 4

        return parsed_date, days_old

    def parse_job_card(self, card, page) -> JobCardInfo:
        try:

            title_el = card.find_element(
                By.CSS_SELECTOR,
                "a[data-automation-id='jobTitle']"
            )

            title = title_el.text.strip()

            link = title_el.get_attribute("href")

        except:
            title = None
            link = None

        # LOCATION
        try:

            location_el = card.find_element(
                By.CSS_SELECTOR,
                "div[data-automation-id='locations'] dd"
            )

            location = location_el.text.strip()

        except:
            location = None

        # REMOTE TYPE
        try:

            remote_el = card.find_element(
                By.CSS_SELECTOR,
                "div[data-automation-id='remoteType'] dd"
            )

            remote_type = remote_el.text.strip()

        except:
            remote_type = None

        # POSTED DATE
        try:

            posted_el = card.find_element(
                By.CSS_SELECTOR,
                "div[data-automation-id='postedOn'] dd"
            )

            posted_date = posted_el.text.strip()

        except:
            posted_date = None

        # JOB ID
        try:

            job_id_el = card.find_element(
                By.CSS_SELECTOR,
                "ul[data-automation-id='subtitle'] li"
            )

            job_id = job_id_el.text.strip()

        except:
            job_id = None

        posted_date, days_old = self.parse_posted_date(posted_date)
        jobInfo = JobCardInfo(
            page=page,
            title=title,
            location=location,
            remote_type=remote_type,
            posted_date=posted_date,
            job_id=job_id,
            parsed_date=self.today.date(),
            link=link,
            days_old=days_old
        )

        return jobInfo
    
    def navigate_to_next_page(self):

        try:

            old_section = self.get_job_results_section()

            old_cards = self.get_job_cards(old_section)

            next_button = old_section.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='next']"
            )

            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);",
                next_button
            )

            next_button.click()

            # wait for old DOM to disappear
            WebDriverWait(self.driver, 30).until(
                EC.staleness_of(old_cards[0])
            )

            return True

        except Exception as e:

            print(f"Failed to navigate: {e}")

            return False
        
    def parse_job_description(self, url: str) -> JobDescriptionInfo:
        self.driver.get(url)

        # wait for page load
        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        selectors = [
            (By.CSS_SELECTOR, "div[data-automation-id='jobPostingDescription']"),
            (By.CSS_SELECTOR, "div.job-description"),
            (By.CSS_SELECTOR, "[data-automation-id*='description']")
        ]
         # wait for description container
        # description_el = WebDriverWait(self.driver, 30).until(
        #     EC.presence_of_element_located(
        #         (By.CSS_SELECTOR, "div[data-automation-id='jobPostingDescription']")
        #     )
        # )

        description_el = None
        for sel in selectors:
            try:
                description_el = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(sel)
                )
                break
            except:
                continue

        if not description_el:
            print(url)
            raise Exception("Job description not found")

        raw_text = description_el.text
        yoe = self._yoe_parser.parse(raw_text)
        salary = self._salary_parser.parse(raw_text)

        jobDescriptionInfo = JobDescriptionInfo(
            end_date=None,
            min_yoe=yoe.min_years,
            max_yoe=yoe.max_years,
            degrees=yoe.degrees,
            min_salary=salary.min_salary,
            max_salary=salary.max_salary,
            pay_type=salary.pay_type
        )

        return jobDescriptionInfo
    
    def format_row(self, jobCard: JobCardInfo, jobDesc: JobDescriptionInfo):
        row = {}

        if jobCard.page:
            row["page"] = jobCard.page
        
        if jobCard.title:
            row["title"] = jobCard.title

        if jobCard.posted_date:
            row["posted_date"] = jobCard.posted_date

        if jobDesc.min_yoe and jobDesc.max_yoe:
            row["yoe_range"] = f"{jobDesc.min_yoe},{jobDesc.max_yoe}"
        elif jobDesc.min_yoe:
            row["yoe"] = jobDesc.min_yoe
        elif jobDesc.max_yoe:
            row["yoe"] = jobDesc.max_yoe

        if jobCard.link:
            row["link"] = jobCard.link

        if jobCard.job_id:
            row["id"] = jobCard.job_id
        
        if jobDesc.degrees:
            row["degree"] = jobDesc.degrees
        
        if jobCard.location:
            row["location"] = jobCard.location
        
        if jobDesc.min_salary and jobDesc.max_salary:
            row["salary_range"] = f"{jobDesc.min_salary},{jobDesc.max_salary}"
        elif jobDesc.min_salary:
            row["salary"] = jobDesc.min_salary
        elif jobDesc.max_salary:
            row["salary"] = jobDesc.max_salary
        
        if jobCard.parsed_date:
            row["parsed_date"] = jobCard.parsed_date

        return row
    
    def process_with_retries(
        self,
        items,
        processor,
        max_retries: int = 1
    ):
        """
        Generic retry processor.

        Args:
            items:
                Iterable of items to process.

            processor:
                Function that processes one item.
                Should:
                    return result -> success
                    return None   -> filtered/skipped
                    raise Exception -> retry

            max_retries:
                Number of retry attempts.

        Returns:
            successes
            filtered_count
            failed_items
        """

        remaining_items = list(items)

        successes = []
        filtered_count = 0

        for attempt in range(max_retries + 1):
            next_failures = []

            for item in remaining_items:
                try:
                    result = processor(item)

                    if result is not None:
                        successes.append(result)
                    else:
                        filtered_count += 1

                except Exception:
                    next_failures.append(item)

            remaining_items = next_failures

            if not remaining_items:
                break

        return successes, filtered_count, remaining_items


    def process_job_card(self, item):
        card, current_page = item

        job = self.parse_job_card(card, current_page)

        if filter.passes_preliminary_filters(
            job,
            self.config["BLOCKED_TITLE_WORDS"],
            self.config["BLOCKED_COUNTRIES"]
        ):
            return job

        return None
    
    def stage_one(self, url: str):
        print("------------Proceeding with initial filtering------------")
        self.open_jobs_page(url)

        all_cards = []

        while True:
            section = self.wait_for_valid_job_section()

            pagination = self.get_pagination_info(section)
            if not pagination:
                break

            current_page, total_pages = pagination

            cards = self.get_job_cards(section)

            all_cards.extend(
                (card, current_page)
                for card in cards
            )

            if current_page == total_pages:
                break

            self.navigate_to_next_page()

        candidate_jobs, eliminated, failed = self.process_with_retries(
            items=all_cards,
            processor=self.process_job_card,
            max_retries=1
        )

        print(f"------------Stage one permanent failures: {len(failed)}------------")
        print(f"------------Removed {eliminated} jobs at initial filtering------------")

        return candidate_jobs

    def process_job_description(self, job):
        job_description_info = self.parse_job_description(job.link)

        if not filter.passes_secondary_filters(
            job_description_info,
            self.config["DEGREES"],
            self.config["MIN_YOE"],
            self.config["MAX_YOE"]
        ):
            return None

        priority = self.get_priority(job["days_old"])

        self.priority_dfs[priority].loc[
            len(self.priority_dfs[priority])
        ] = self.format_row(job, job_description_info)

        return job

    def stage_two(self, candidate_jobs):
        print(f"------------Proceeding with secondary filtering, {len(candidate_jobs)} remaining------------")
        _, eliminated, failed = self.process_with_retries(
            items=candidate_jobs,
            processor=self.process_job_description,
            max_retries=1
        )
        print(f"------------Stage two permanent failures: {len(failed)}------------")
        print(f"------------Removed {eliminated} jobs at initial filtering------------")
        return None

        
    def run(self, url: str):
        try:
            candidate_jobs = self.stage_one(url)

            self.stage_two(candidate_jobs)

        except Exception as e:
            print("------------Encountered error while scraping for this company, returning empty array------------")
            print(e)
            
                
    
