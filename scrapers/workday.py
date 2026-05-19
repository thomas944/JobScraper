from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException
)

from scrapers.base_scraper import BaseScraper
from utils import utils
from filters import preliminary_filter as filter
import re
from datetime import datetime, timedelta
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
    
    def parse_posted_date(self, date_text: str) -> Optional[datetime]:
        if not date_text:
            return None
        
        text = date_text.strip().lower()
        now = self.today
    
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
            parsed_date=self.today,
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

         # wait for description container
        description_el = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-automation-id='jobPostingDescription']")
            )
        )

        text = description_el.text
        yoe = self.extract_years_of_experience(text)

        jobDescriptionInfo = JobDescriptionInfo(
            end_date=None,
            years_of_exp=yoe,
        )

        return jobDescriptionInfo
    

    def extract_years_of_experience(self, text: str):
        text = utils.normalize_text(text)
        text = utils.replace_words(text)

        match = re.search(r"(\d+)\s*[-to]+\s*(\d+)\s*years", text)
        if match:
            return int(match.group(1)), int(match.group(2))

        match = re.search(r"(\d+)\+?\s*years", text)
        if match:
            val = int(match.group(1))
            return val, None  # open-ended

        match = re.search(r"minimum\s*(\d+)\+?\s*years", text)
        if match:
            val = int(match.group(1))
            return val, None

        return None
    
    def run(self, url: str):
        candidate_jobs = []
        self.open_jobs_page(url)
        eliminated = 0

        while True:
            section = self.wait_for_valid_job_section()
            pagination = self.get_pagination_info(section)
            if not pagination:
                break
            current_page, total_pages = pagination

            cards = self.get_job_cards(section)
            for card in cards:
                job = self.parse_job_card(card, current_page)
                if filter.passes_preliminary_filters(job, current_page):
                    candidate_jobs.append(job)
                else:
                    eliminated += 1
            
            # break
            if current_page == total_pages:
                break
            else:
                self.navigate_to_next_page()
                        #   print(self.parse_job_description(job.link))
        print(f"Removed {eliminated} jobs")
        print("------------Proceeding with secondary filtering------------")

        parsed_jobs = []
        for candidate in candidate_jobs:
            print(f"{candidate.title}: {self.parse_job_description(candidate.link)}")
        return candidate_jobs

            
    
