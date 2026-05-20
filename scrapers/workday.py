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
    
    def parse_posted_date(self, date_text: str) -> Optional[date]:
        if not date_text:
            return None

        text = date_text.strip().lower()
        now = self.today.date()

        if "today" in text:
            return now

        # Posted Yesterday
        if "yesterday" in text:
            return now - timedelta(days=1)

        # Posted X Days Ago
        match = re.search(r'(\d+)\s+day', text)

        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)

        # Posted X Weeks Ago
        match = re.search(r'(\d+)\s+week', text)

        if match:
            weeks = int(match.group(1))
            return now - timedelta(weeks=weeks)

        # Posted X Months Ago
        match = re.search(r'(\d+)\s+month', text)

        if match:
            months = int(match.group(1))

            # approximate month length
            return now - timedelta(days=months * 30)

        return None

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

        jobInfo = JobCardInfo(
            page=page,
            title=title,
            location=location,
            remote_type=remote_type,
            posted_date=self.parse_posted_date(posted_date),
            job_id=job_id,
            parsed_date=self.today.date(),
            link=link
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

    def run(self, url: str):
        candidate_jobs = []
        self.open_jobs_page(url)
        eliminated = 0
        print("------------Proceeding with initial filtering------------")

        while True:
            section = self.wait_for_valid_job_section()
            pagination = self.get_pagination_info(section)
            if not pagination:
                break
            current_page, total_pages = pagination

            cards = self.get_job_cards(section)
            for card in cards:
                try:
                    job = self.parse_job_card(card, current_page)
                    if filter.passes_preliminary_filters(job, self.config["BLOCKED_TITLE_WORDS"], self.config["BLOCKED_COUNTRIES"]):
                        candidate_jobs.append(job)
                    else:
                        eliminated += 1
                except Exception:
                    continue

            
            # break
            if current_page == total_pages:
                break
            else:
                self.navigate_to_next_page()
                        #   print(self.parse_job_description(job.link))
        print(f"------------Removed {eliminated} jobs at initial filtering------------")
        print(f"------------Proceeding with secondary filtering, {len(candidate_jobs)} remaining------------")
        eliminated = 0
        parsed_jobs = []
        for job in candidate_jobs:
            try:
                jobDescriptionInfo = self.parse_job_description(job.link)
                if filter.passes_secondary_filters(jobDescriptionInfo, self.config["DEGREES"], self.config["MIN_YOE"], self.config["MAX_YOE"]):
                    parsed_jobs.append(self.format_row(job, jobDescriptionInfo))
                else:
                    eliminated += 1
            except Exception:
                continue

        print(f"------------Removed {eliminated} jobs at secondary filtering------------")
        return parsed_jobs

            
    
